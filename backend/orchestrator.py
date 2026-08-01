"""The pipeline: interviewer's brief in → finished, audited multi-page site out.

    brief ──► [copywriter ∥ designer] ──► css ──► [page ∥ page ∥ page ∥ js] ──► recheck ──► audit

Design rules baked in:
- every parallel branch catches its OWN exceptions and degrades to a typed
  fallback, so one failed specialist never cancels its sibling
- the orchestrator owns all data flow and all event emission — agents never
  talk to each other directly
- artifacts live in the DB (preview + editor read from there); the desktop
  folder is written once at the end, v1-style
"""

import asyncio
import json
import time
import traceback

import checks
import config
import db
import events
import writer
from agents import auditor, builder, copywriter, designer, rechecker
from models import (AppSettings, AuditReport, CopyDeck, DesignSpec, PageCopy,
                    ProjectBrief)

import fallback


async def load_settings() -> AppSettings:
    stored = await db.get_settings_json()
    return AppSettings.model_validate(stored) if stored else AppSettings()


def _files_for_recheck(all_files: dict, report: AuditReport) -> dict:
    """Send recheck only the files it needs — but everything when a fix is
    cross-cutting (nav/links or a site-wide issue), since it can't be localized.
    """
    flagged = {i.page for i in report.issues if i.page}
    site_wide = any(i.page is None for i in report.issues)

    def _text(issue) -> str:
        return f"{issue.category} {issue.message}".lower()

    nav_related = (
        any(not c.passed and "link" in c.name.lower() for c in report.machine_checks)
        or any(k in _text(i) for i in report.issues
               for k in ("nav", "link", "footer", "menu")))

    if site_wide or nav_related or not flagged:
        return dict(all_files)
    selected = set(flagged) | {f for f in ("style.css", "script.js") if f in all_files}
    return {f: all_files[f] for f in selected if f in all_files}


async def run_build(build_id: str) -> None:
    bus = events.bus(build_id)
    emit = bus.emit

    build = await db.get_build(build_id)
    if build is None:
        await emit("error", {"message": "build not found", "fatal": True})
        await emit("done", {"status": "failed"})
        return

    brief = ProjectBrief.model_validate_json(build["brief_json"])
    settings = await load_settings()
    build_notes: list[str] = []
    files: dict[str, str] = {}   # latest content per filename, mirrors the DB

    def status_fn(agent: str):
        async def on_status(text: str) -> None:
            await emit("agent_status", {"agent": agent, "text": text})
        return on_status

    async def write_file(filename: str, content: str, agent: str = "builder") -> None:
        files[filename] = content
        revision = await db.write_artifact(build_id, filename, content)
        await emit("file_written", {"filename": filename, "revision": revision,
                                    "size": len(content), "agent": agent})

    async def branch(agent: str, coro_factory, fallback_factory):
        """Run one specialist; skipped if disabled, degraded on failure."""
        # settings.is_enabled uses the base agent name ("builder:css" -> "builder")
        if not settings.is_enabled(agent.split(":")[0]):
            await emit("agent_skipped", {"agent": agent})
            return fallback_factory()
        await emit("agent_start", {"agent": agent,
                                   "model": settings.model_for(agent.split(":")[0])})
        started = time.monotonic()
        try:
            result = await coro_factory()
            await emit("agent_done", {"agent": agent,
                                      "ms": int((time.monotonic() - started) * 1000)})
            return result
        except Exception as error:
            print(f"[ORCHESTRATOR] {agent} failed: {error}")
            traceback.print_exc()
            await emit("error", {"agent": agent, "message": str(error), "fatal": False})
            build_notes.append(f"The {agent} agent failed ({error}); a fallback was used.")
            return fallback_factory()

    try:
        await emit("run_start", {"build_id": build_id, "kind": "build"})

        # ---- Stage 1: copywriter ∥ designer (the fan-out) --------------------
        deck, design = await asyncio.gather(
            branch("copywriter",
                   lambda: copywriter.run(brief, model=settings.model_for("copywriter"),
                                          on_status=status_fn("copywriter")),
                   lambda: CopyDeck.fallback(brief)),
            branch("designer",
                   lambda: designer.run(brief, model=settings.model_for("designer"),
                                        on_status=status_fn("designer")),
                   lambda: DesignSpec.fallback(brief)),
        )
        await db.save_build_specs(build_id, deck.model_dump(), design.model_dump())
        await emit("artifact", {"kind": "copy_deck", "data": deck.model_dump()})
        await emit("artifact", {"kind": "design_spec", "data": design.model_dump()})
        await emit("pages_planned", {"pages": deck.page_manifest()})

        # ---- Stage 2a: shared CSS (everything depends on it) -----------------
        css = await branch(
            "builder:css",
            lambda: builder.build_css(design, deck, model=settings.model_for("builder"),
                                      on_status=status_fn("builder:css")),
            lambda: fallback.render_css(design))
        await write_file("style.css", css, agent="builder:css")

        # ---- Stage 2b: pages in parallel ∥ script.js --------------------------
        semaphore = asyncio.Semaphore(config.PAGE_CONCURRENCY)

        async def one_page(page: PageCopy) -> None:
            agent = f"builder:{page.filename}"
            if not settings.is_enabled("builder"):
                await emit("agent_skipped", {"agent": agent})
                html = fallback.render_page(page, deck.nav, deck.footer, design,
                                            brief.business_name, settings.use_photos)
                await write_file(page.filename, html)
                return
            async with semaphore:
                await emit("agent_start", {"agent": agent,
                                           "model": settings.model_for("builder")})
                started = time.monotonic()
                try:
                    html = await builder.build_page(
                        page, brief, design, deck, css,
                        model=settings.model_for("builder"),
                        use_photos=settings.use_photos,
                        on_status=status_fn(agent))
                    await emit("agent_done", {"agent": agent,
                                              "ms": int((time.monotonic() - started) * 1000)})
                except Exception as error:
                    print(f"[ORCHESTRATOR] {agent} failed: {error}")
                    await emit("error", {"agent": agent, "message": str(error),
                                         "fatal": False})
                    html = fallback.render_page(page, deck.nav, deck.footer, design,
                                                brief.business_name, settings.use_photos)
                    build_notes.append(
                        f"{page.filename} failed LLM generation and was rendered from its copy "
                        f"by a deterministic fallback — regenerate it fully from the copy deck.")
                await write_file(page.filename, html, agent=agent)

        async def js_task() -> None:
            js = await branch(
                "builder:js",
                lambda: builder.build_js(deck, model=settings.model_for("builder"),
                                         on_status=status_fn("builder:js")),
                fallback.render_js)
            await write_file("script.js", writer.inject_above_fold(js), agent="builder:js")

        await asyncio.gather(*(one_page(p) for p in deck.pages), js_task())

        # ---- Stage 3: review loop — audit first, recheck fixes, re-audit ------
        # The site is already visible in Preview. The auditor scores it; if it
        # finds problems the rechecker fixes exactly those (fed the findings);
        # we re-audit and repeat until the audit reports ZERO issues, progress
        # genuinely stalls, or the pass cap is hit (so it always ends).
        MAX_FIX_PASSES = 4
        # Progress is measured by weighted SEVERITY, not raw issue count: the audit
        # is stochastic (each run rewords/reorders minor items), so a raw count can
        # stay flat even when a pass cleared a real warning. Clearing a warning must
        # count even if the re-audit surfaces a fresh info nit. Failing machine
        # checks are criticals.
        SEVERITY_WEIGHT = {"critical": 100, "warning": 10, "info": 1}

        def audit_badness(rep: AuditReport) -> int:
            w = sum(SEVERITY_WEIGHT.get(i.severity, 1) for i in rep.issues)
            w += 100 * sum(1 for c in rep.machine_checks if not c.passed)
            return w

        audit_enabled = settings.is_enabled("audit")
        recheck_enabled = settings.is_enabled("recheck")

        async def run_audit() -> AuditReport:
            machine = checks.run_all(dict(files))
            if not audit_enabled:
                await emit("agent_skipped", {"agent": "audit"})
                passed = sum(1 for c in machine if c.passed)
                rep = AuditReport(
                    score=round(100 * passed / len(machine)) if machine else 0,
                    machine_checks=machine,
                    summary="Audit agent disabled in settings — score reflects the "
                            "automated machine checks only.")
                await emit("audit", {"report": rep.model_dump()})
                return rep
            await emit("agent_start", {"agent": "audit",
                                       "model": settings.model_for("audit")})
            started = time.monotonic()
            screenshot = None
            if settings.vision_audit and not config.MOCK_LLM:
                await emit("agent_status",
                           {"agent": "audit", "text": "capturing screenshot for visual audit…"})
                import vision
                screenshot = await vision.capture(build_id)
                if screenshot is None:
                    await emit("agent_status", {"agent": "audit",
                               "text": "screenshot unavailable — using code-only audit"})
            try:
                rep = await auditor.run(brief, dict(files), machine,
                                        model=settings.model_for("audit"),
                                        on_status=status_fn("audit"),
                                        screenshot=screenshot)
            except Exception as error:
                print(f"[ORCHESTRATOR] audit failed: {error}")
                await emit("error", {"agent": "audit", "message": str(error),
                                     "fatal": False})
                rep = AuditReport(
                    score=0, machine_checks=machine,
                    summary="The audit agent failed; only machine checks are available.")
            await emit("agent_done", {"agent": "audit",
                                      "ms": int((time.monotonic() - started) * 1000),
                                      "notes": f"scored {rep.score}/100"})
            await emit("audit", {"report": rep.model_dump()})
            return rep

        report = await run_audit()
        prev_badness = audit_badness(report)
        stalls = 0  # consecutive passes that did NOT reduce weighted badness
        for pass_no in range(1, MAX_FIX_PASSES + 1):
            machine_failed = [c for c in report.machine_checks if not c.passed]
            # STOP when the audit is clean: no issues left in the report (and no
            # failing machine check or pending build note is being carried).
            if not report.issues and not machine_failed and not build_notes:
                break
            if not recheck_enabled:
                await emit("agent_skipped", {"agent": "recheck"})
                break

            await emit("agent_start", {"agent": "recheck", "pass": pass_no,
                                       "model": settings.model_for("recheck")})
            started = time.monotonic()
            subset = _files_for_recheck(dict(files), report)
            try:
                notes, fixed = await rechecker.run(
                    brief, deck, design, subset, build_notes, report, pass_no,
                    model=settings.model_for("recheck"),
                    on_status=status_fn("recheck"))
            except Exception as error:
                print(f"[ORCHESTRATOR] recheck failed: {error}")
                await emit("error", {"agent": "recheck", "message": str(error),
                                     "fatal": False})
                break
            for filename, content in fixed.items():
                if filename == "script.js":
                    content = writer.inject_above_fold(content)
                await write_file(filename, content, agent="recheck")
            await emit("agent_done", {"agent": "recheck",
                                      "ms": int((time.monotonic() - started) * 1000),
                                      "fixed": sorted(fixed), "notes": notes[:400]})
            build_notes.clear()
            if not fixed:
                break  # recheck changed nothing — re-auditing won't differ

            report = await run_audit()
            # Progress guard: measure weighted severity, and tolerate ONE
            # non-improving pass before stopping — the audit wobbles run to run,
            # so a single flat pass isn't proof we're stuck. Two in a row means the
            # remaining issues are ones recheck can't clear (copy-law paraphrase
            # nits, intended stock imagery) and more passes won't help.
            badness = audit_badness(report)
            if badness < prev_badness:
                stalls = 0
                prev_badness = badness
            else:
                stalls += 1
                if stalls >= 2:
                    break

        await db.save_build_audit(build_id, report.model_dump())

        # ---- Finish: desktop folder + chat trail ------------------------------
        output_path = ""
        try:
            output_path = str(writer.write_build_to_disk(brief.business_name, files))
        except Exception as error:
            print(f"[ORCHESTRATOR] disk write failed: {error}")

        await db.set_build_status(build_id, "done")
        await db.add_message(
            build["session_id"], "assistant",
            f"Build finished — audit score {report.score}/100. "
            f"{len([f for f in files if f.endswith('.html')])} pages generated."
            + (f" Files saved to {output_path}" if output_path else ""),
            agent="system")
        await emit("done", {"status": "done", "build_id": build_id,
                            "output_path": output_path, "score": report.score})

    except asyncio.CancelledError:  # user pressed Stop
        print(f"[ORCHESTRATOR] build {build_id} stopped by user")
        await emit("error", {"message": "Build stopped.", "fatal": True})
        await emit("done", {"status": "stopped", "build_id": build_id})
        try:
            await db.set_build_status(build_id, "failed")
        except Exception:
            pass
    except Exception as error:  # truly fatal — a bug in the orchestrator itself
        print(f"[ORCHESTRATOR] fatal: {error}")
        traceback.print_exc()
        await db.set_build_status(build_id, "failed")
        await emit("error", {"message": str(error), "fatal": True})
        await emit("done", {"status": "failed", "build_id": build_id})
    finally:
        events.evict_later(build_id)
