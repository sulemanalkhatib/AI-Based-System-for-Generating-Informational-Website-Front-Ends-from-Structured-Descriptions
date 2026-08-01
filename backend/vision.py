"""Optional headless screenshot for the visual audit.

Playwright is an OPTIONAL dependency. If it (or its Chromium) isn't installed,
capture() returns None and the auditor silently falls back to a code-only review.
Enable the feature in Settings, then install it once:
    pip install playwright
    playwright install chromium
"""

import config


async def capture(build_id: str, page: str = "index.html") -> bytes | None:
    """Render a build's live preview and return a full-page PNG, or None on any failure."""
    try:
        from playwright.async_api import async_playwright
    except Exception:
        print("[VISION] Playwright not installed — skipping screenshot "
              "(pip install playwright && playwright install chromium)")
        return None

    url = f"{config.SELF_URL.rstrip('/')}/preview/{build_id}/{page}"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox"])
            try:
                pg = await browser.new_page(viewport={"width": 1280, "height": 900})
                await pg.goto(url, wait_until="networkidle", timeout=15000)
                # A full-page screenshot never scrolls, so scroll-triggered entrance
                # animations (.fade-in/.slide-up) would leave below-fold content
                # invisible. Force every animated element visible before capturing.
                await pg.evaluate(
                    "document.querySelectorAll('.fade-in,.slide-up')"
                    ".forEach(function(el){el.style.transitionDelay='0s';"
                    "el.classList.add('visible');})")
                await pg.wait_for_timeout(700)  # let fonts + reveal transitions settle
                return await pg.screenshot(full_page=True)
            finally:
                await browser.close()
    except Exception as error:
        print(f"[VISION] screenshot failed: {error}")
        return None
