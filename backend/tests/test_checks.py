"""Deterministic audit checks against a clean and a deliberately broken site."""

import checks

CLEAN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Home</title>
  <meta name="description" content="A clean page">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <nav><a href="index.html">Home</a><a href="about.html">About</a></nav>
  <section class="hero" id="hero"><h1>Hi</h1></section>
  <section class="section section-contact" id="contact">
    <form class="contact-form">
      <button type="submit">Send</button>
      <p class="form-success" style="display:none;"></p>
    </form>
  </section>
  <img src="x.svg" alt="decorative" width="400" height="300" loading="lazy">
  <script src="script.js"></script>
</body>
</html>"""

CLEAN_SITE = {
    "index.html": CLEAN_PAGE,
    "about.html": CLEAN_PAGE.replace("<title>Home</title>", "<title>About</title>"),
    "style.css": "body { margin: 0; }",
    "script.js": "document.querySelectorAll('.x').forEach(function (e) {});",
}

BROKEN_SITE = {
    "index.html": """<html>
<head><title>Broken</title></head>
<body>
  <nav><a href="missing.html">Ghost</a></nav>
  <section class="section fade-in" id="a"><img src="x.png"></section>
  <form><button>Go</button></form>
</body>
</html>""",
    "script.js": "alert('hi'); localStorage.setItem('k', 'v');",
}


def _by_name(results):
    return {c.name: c for c in results}


def test_clean_site_passes_everything():
    results = checks.run_all(CLEAN_SITE)
    failed = [c.name for c in results if not c.passed]
    assert failed == []


def test_broken_site_fails_the_right_checks():
    by_name = _by_name(checks.run_all(BROKEN_SITE))
    assert not by_name["HTML structure (doctype, body, closing html)"].passed
    assert not by_name["Responsive viewport meta"].passed
    assert not by_name["Internal links resolve"].passed
    assert not by_name["No alert()/confirm()/prompt()"].passed
    assert not by_name["No localStorage/sessionStorage"].passed
    assert not by_name["Forms include .form-success feedback element"].passed
    assert not by_name["No fade-in/slide-up on <section> elements"].passed
    assert not by_name["Images have alt attributes"].passed
    assert not by_name["Images lazy-load with dimensions"].passed


def test_broken_link_detail_names_the_page():
    by_name = _by_name(checks.run_all(BROKEN_SITE))
    assert "missing.html" in by_name["Internal links resolve"].detail


_GOOD_CONTRAST = ":root { --text: #241b16; --bg: #fdf9f4; --surface: #f3ebe2; --primary-dark: #241b16; }"
_BAD_CONTRAST = ":root { --text: #cccccc; --bg: #ffffff; --surface: #f7f7f7; --primary-dark: #9aa0a6; }"
_CONTRAST_CHECK = "Colour contrast (WCAG AA text ≥ 4.5:1)"


def test_contrast_passes_on_readable_palette():
    by = _by_name(checks.run_all({"index.html": CLEAN_PAGE, "style.css": _GOOD_CONTRAST}))
    assert by[_CONTRAST_CHECK].passed


def test_contrast_flags_low_contrast_palette():
    check = _by_name(checks.run_all({"index.html": CLEAN_PAGE, "style.css": _BAD_CONTRAST}))[_CONTRAST_CHECK]
    assert not check.passed
    assert ":1" in check.detail  # names the failing ratio


def test_contrast_skipped_when_no_palette():
    by = _by_name(checks.run_all(CLEAN_SITE))  # style.css has no :root vars
    assert by[_CONTRAST_CHECK].passed
    assert "no :root palette" in by[_CONTRAST_CHECK].detail
