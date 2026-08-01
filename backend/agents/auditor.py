"""Audit agent — read-only QA report. Machine checks are ground truth."""

import asyncio
import json

import config
import llm
from models import AuditReport, MachineCheck, ProjectBrief
from prompts.audit import AUDIT_PROMPT, VISION_ADDENDUM


async def run(brief: ProjectBrief, files: dict[str, str],
              machine_checks: list[MachineCheck], *, model: str,
              on_status: llm.StatusFn | None = None,
              screenshot: bytes | None = None) -> AuditReport:
    if config.MOCK_LLM:
        from mock import fixtures
        await asyncio.sleep(1.5)
        # Once recheck has polished the site, the score clears the target so the
        # review loop stops — demonstrating audit → fix → re-audit → done.
        reviewed = any("reviewed and polished" in c for c in files.values())
        report = fixtures.audit_report(high=reviewed)
        report.machine_checks = machine_checks
        return report

    checks_json = json.dumps([c.model_dump() for c in machine_checks], indent=2)
    file_dump = "\n\n".join(
        f"===== {name} =====\n{content}" for name, content in files.items())
    user = (f"SITE BRIEF:\n{brief.model_dump_json(indent=2)}\n\n"
            f"MACHINE CHECK RESULTS (ground truth — every failure must appear as a critical issue):\n"
            f"{checks_json}\n\n"
            f"ALL SITE FILES:\n{file_dump}")

    if screenshot:
        report = await llm.complete_json_image(
            AuditReport, AUDIT_PROMPT + "\n\n" + VISION_ADDENDUM, user, screenshot,
            model=model, max_tokens=config.AUDIT_MAX_TOKENS, temperature=0.3,
            on_status=on_status, timeout=config.AUDIT_TIMEOUT_S)
    else:
        report = await llm.complete_json(
            AuditReport, AUDIT_PROMPT, user, model=model,
            max_tokens=config.AUDIT_MAX_TOKENS, temperature=0.3, on_status=on_status,
            timeout=config.AUDIT_TIMEOUT_S)

    report.machine_checks = machine_checks
    if report.categories:  # keep the headline score honest
        report.score = max(0, min(100, sum(c.score for c in report.categories)))
    return report
