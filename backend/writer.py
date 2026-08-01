"""Disk output — ports v1's clean_name and above-the-fold JS fix."""

import re
from pathlib import Path

import config

# Injected into script.js so above-the-fold animated elements are visible on load
# even if the IntersectionObserver misses them (proven fix from v1 — Python-side
# injection because the model can't be trusted to include it).
ABOVE_FOLD_FIX = """
// Reveal any elements already visible in the viewport on page load
(function () {
  document.querySelectorAll('.fade-in, .slide-up').forEach(function (el) {
    if (el.getBoundingClientRect().top < window.innerHeight) {
      el.classList.add('visible');
    }
  });
})();
"""

_RESERVED = {"con", "prn", "aux", "nul",
             *(f"com{i}" for i in range(1, 10)),
             *(f"lpt{i}" for i in range(1, 10))}


def clean_name(name: str) -> str:
    """Business name → safe lowercase hyphenated folder name (v1 behavior + reserved guard)."""
    name = name.lower().replace(" ", "-")
    name = re.sub(r"[^a-z0-9-]", "", name)
    name = re.sub(r"-+", "-", name).strip("-")
    if not name:
        name = "my-website"
    if name in _RESERVED:
        name = f"site-{name}"
    return name


def inject_above_fold(js: str) -> str:
    if "getBoundingClientRect().top < window.innerHeight" in js:
        return js  # already present (e.g. recheck echoed it back)
    return js.rstrip() + "\n" + ABOVE_FOLD_FIX


def write_build_to_disk(business_name: str, files: dict[str, str]) -> Path:
    """Write the latest revision of every file to ~/Desktop/output/<name>/ (v1 parity)."""
    folder = config.OUTPUT_DIR / clean_name(business_name)
    folder.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        (folder / filename).write_text(content, encoding="utf-8")
    return folder
