"""Deterministic audit checks — ground truth the LLM auditor cannot contradict."""

import re

from models import MachineCheck

_HREF_RE = re.compile(r'href="([^"]+)"')
_EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#", "//")
_ROOT_VAR_RE = re.compile(r"--([a-z-]+)\s*:\s*#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luminance(hex_str: str) -> float:
    def lin(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (_rgb(hex_str))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(hex1: str, hex2: str) -> float:
    l1, l2 = _luminance(hex1), _luminance(hex2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _root_colors(css: str) -> dict[str, str]:
    colors: dict[str, str] = {}
    for name, value in _ROOT_VAR_RE.findall(css):
        colors.setdefault(name, value)  # first :root definition wins
    return colors


def _html_files(files: dict[str, str]) -> dict[str, str]:
    return {n: c for n, c in files.items() if n.endswith(".html")}


def run_all(files: dict[str, str]) -> list[MachineCheck]:
    checks: list[MachineCheck] = []
    html_files = _html_files(files)
    all_js = files.get("script.js", "")
    inline_scripts = " ".join(html_files.values())

    # 1. Basic document structure on every page
    bad_structure = [
        name for name, content in html_files.items()
        if not (re.search(r"<!doctype html>", content, re.IGNORECASE)
                and "</html>" in content.lower() and "<body" in content.lower())]
    checks.append(MachineCheck(
        name="HTML structure (doctype, body, closing html)",
        passed=not bad_structure,
        detail=f"malformed: {', '.join(bad_structure)}" if bad_structure else "all pages well-formed"))

    # 2. Viewport meta on every page
    missing_viewport = [n for n, c in html_files.items() if 'name="viewport"' not in c]
    checks.append(MachineCheck(
        name="Responsive viewport meta",
        passed=not missing_viewport,
        detail=f"missing on: {', '.join(missing_viewport)}" if missing_viewport else "present on all pages"))

    # 3. Shared assets linked on every page
    unlinked = [n for n, c in html_files.items()
                if "style.css" not in c or "script.js" not in c]
    checks.append(MachineCheck(
        name="style.css + script.js linked on every page",
        passed=not unlinked,
        detail=f"not wired on: {', '.join(unlinked)}" if unlinked else "wired everywhere"))

    # 4. Internal links resolve to real files
    broken: list[str] = []
    for name, content in html_files.items():
        for href in _HREF_RE.findall(content):
            if href.startswith(_EXTERNAL_PREFIXES) or href.startswith("data:"):
                continue
            target = href.split("#")[0].split("?")[0]
            if target and target not in files:
                broken.append(f"{name} → {href}")
    checks.append(MachineCheck(
        name="Internal links resolve",
        passed=not broken,
        detail="; ".join(broken[:8]) if broken else "every internal link points to a real file"))

    # 5. Forbidden dialog APIs
    dialog_hits = re.findall(r"\b(alert|confirm|prompt)\s*\(", all_js + inline_scripts)
    checks.append(MachineCheck(
        name="No alert()/confirm()/prompt()",
        passed=not dialog_hits,
        detail=f"found: {sorted(set(dialog_hits))}" if dialog_hits else "clean"))

    # 6. Forbidden web storage (throws inside the sandboxed preview)
    storage_hits = re.findall(r"\b(localStorage|sessionStorage)\b", all_js + inline_scripts)
    checks.append(MachineCheck(
        name="No localStorage/sessionStorage",
        passed=not storage_hits,
        detail="web storage APIs found" if storage_hits else "clean"))

    # 7. Every form has a success element
    forms_without_success = [
        n for n, c in html_files.items()
        if "<form" in c and "form-success" not in c]
    checks.append(MachineCheck(
        name="Forms include .form-success feedback element",
        passed=not forms_without_success,
        detail=(f"missing on: {', '.join(forms_without_success)}"
                if forms_without_success else "all forms covered")))

    # 8. Titles and meta descriptions
    missing_meta = [n for n, c in html_files.items()
                    if "<title>" not in c or 'name="description"' not in c]
    checks.append(MachineCheck(
        name="Title + meta description on every page",
        passed=not missing_meta,
        detail=f"missing on: {', '.join(missing_meta)}" if missing_meta else "present everywhere"))

    # 9. Animations never on section elements (visibility bug from v1)
    animated_sections = [
        n for n, c in html_files.items()
        if re.search(r'<section[^>]*class="[^"]*(?:fade-in|slide-up)', c)]
    checks.append(MachineCheck(
        name="No fade-in/slide-up on <section> elements",
        passed=not animated_sections,
        detail=(f"sections animated on: {', '.join(animated_sections)}"
                if animated_sections else "clean")))

    # 10. Images carry alt text (accessibility)
    missing_alt = [n for n, c in html_files.items()
                   if re.search(r"<img(?![^>]*\balt=)[^>]*>", c)]
    checks.append(MachineCheck(
        name="Images have alt attributes",
        passed=not missing_alt,
        detail=f"missing alt on: {', '.join(missing_alt)}" if missing_alt else "clean"))

    # 11. Images lazy-load with explicit dimensions (perf + no layout shift, and
    #     lets the JS gradient-fallback size itself when a photo host is unreachable)
    _IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
    heavy_imgs: list[str] = []
    for name, content in html_files.items():
        for tag in _IMG_RE.findall(content):
            if not ("loading=" in tag and "width=" in tag and "height=" in tag):
                heavy_imgs.append(name)
                break
    checks.append(MachineCheck(
        name="Images lazy-load with dimensions",
        passed=not heavy_imgs,
        detail=(f"missing loading/width/height on: {', '.join(heavy_imgs)}"
                if heavy_imgs else "all images sized and lazy-loaded")))

    # 12. Colour contrast (computed WCAG AA on the :root palette — the thing the
    #     LLM auditor cannot reliably judge from code)
    colors = _root_colors(files.get("style.css", ""))
    pairs = []
    if "text" in colors and "bg" in colors:
        pairs.append(("body text on background", colors["text"], colors["bg"]))
    if "text" in colors and "surface" in colors:
        pairs.append(("body text on surface", colors["text"], colors["surface"]))
    if "primary-dark" in colors:
        pairs.append(("white text on dark brand", "ffffff", colors["primary-dark"]))
    contrast_fail = [f"{label} {_contrast(fg, bg):.1f}:1"
                     for label, fg, bg in pairs if _contrast(fg, bg) < 4.5]
    checks.append(MachineCheck(
        name="Colour contrast (WCAG AA text ≥ 4.5:1)",
        passed=not contrast_fail,
        detail=("; ".join(contrast_fail) if contrast_fail
                else "text/background pairs pass AA" if pairs
                else "no :root palette found to check")))

    return checks
