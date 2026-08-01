"""Recheck agent — fixes the problems the auditor found, and returns corrected files.

The auditor is the finder; this agent is the fixer. It receives the audit
report (issues + failed machine checks) plus the files it may change, and
returns a ---NOTES--- block then ---FILE: name--- … ---END FILE--- per fixed
file. The parser tolerates a truncated final block and only accepts filenames
that were actually handed to it.
"""

import asyncio

import config
import llm
from models import AuditReport, CopyDeck, DesignSpec, ProjectBrief
from prompts.recheck import RECHECK_PROMPT


_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def format_findings(report: AuditReport, build_notes: list[str]) -> str:
    """Turn the audit report into a concrete, prioritized worklist for the fixer.

    Includes info-level items too — the loop now aims to clear EVERY issue, so
    the fixer should resolve polish nits it reasonably can, not just criticals.
    """
    lines: list[str] = []
    for note in build_notes:
        lines.append(f"- (critical) {note}")
    for check in report.machine_checks:
        if not check.passed:
            lines.append(f"- (critical) automated check failed — {check.name}: {check.detail}")
    for issue in sorted(report.issues, key=lambda i: _SEVERITY_ORDER.get(i.severity, 3)):
        where = f" [{issue.page}]" if issue.page else " [site-wide]"
        fix = f" → suggested fix: {issue.suggestion}" if issue.suggestion else ""
        lines.append(f"- ({issue.severity}){where} {issue.message}{fix}")
    return "\n".join(lines) or (
        "No specific defects were flagged. Do a light coherence pass and return "
        "ONLY files that genuinely still need a fix; otherwise return no files.")


def parse_recheck_output(text: str, known_files: set[str]) -> tuple[str, dict[str, str], bool]:
    """Returns (notes, fixed_files, truncated)."""
    text = llm.strip_fences(text)
    chunks = text.split("---FILE:")
    notes = chunks[0].replace("---NOTES---", "").strip()

    fixed: dict[str, str] = {}
    truncated = False
    for i, chunk in enumerate(chunks[1:], start=1):
        header, sep, body = chunk.partition("---")
        if not sep:
            truncated = True
            continue
        filename = header.strip()
        is_last = i == len(chunks) - 1
        end_index = body.find("---END FILE---")
        if end_index == -1:
            if is_last:
                # Likely cut off mid-file — unsafe to keep a half-written file
                truncated = True
                continue
            content = body
        else:
            content = body[:end_index]
        if filename in known_files and content.strip():
            fixed[filename] = content.strip() + "\n"
    return notes, fixed, truncated


async def run(brief: ProjectBrief, deck: CopyDeck, design: DesignSpec,
              files: dict[str, str], build_notes: list[str],
              report: AuditReport, pass_no: int,
              *, model: str, on_status: llm.StatusFn | None = None,
              ) -> tuple[str, dict[str, str]]:
    """Fix the auditor's findings. Returns (notes, fixed_files)."""
    if config.MOCK_LLM:
        await asyncio.sleep(1.8)
        # Demo a visible fix: revision 2 on the home page. The marker also lets
        # the mock auditor "see" the fix and raise the score on the next pass.
        fixed = {}
        if "index.html" in files:
            fixed["index.html"] = files["index.html"].replace(
                "</body>", "  <!-- reviewed and polished by the recheck agent -->\n</body>")
        return "Applied the auditor's fixes to index.html. [mock]", fixed

    findings = format_findings(report, build_notes)
    file_dump = "\n\n".join(
        f"===== {name} =====\n{content}" for name, content in files.items())
    user = (f"AUDITOR FINDINGS TO FIX (review pass {pass_no}):\n{findings}\n\n"
            f"SITE BRIEF:\n{brief.model_dump_json(indent=2)}\n\n"
            f"COPY DECK (the text the pages must match):\n{deck.model_dump_json(indent=2)}\n\n"
            f"DESIGN SPEC:\n{design.model_dump_json(indent=2)}\n\n"
            f"FILES YOU MAY CHANGE:\n{file_dump}")

    raw = await llm.complete_text(RECHECK_PROMPT, user, model=model,
                                  max_tokens=config.RECHECK_MAX_TOKENS,
                                  temperature=0.2, on_status=on_status,
                                  timeout=config.RECHECK_TIMEOUT_S)
    notes, fixed, truncated = parse_recheck_output(raw, set(files))
    if truncated:
        notes += " (one file came back incomplete and was skipped)"
    return notes, fixed
