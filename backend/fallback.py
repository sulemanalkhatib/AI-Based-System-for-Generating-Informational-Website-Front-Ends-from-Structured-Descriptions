"""Deterministic site renderer — no LLM involved.

Two consumers:
- MOCK_LLM mode renders the whole mock site with it (free, instant demos)
- the orchestrator renders a failed page from its copy so the pipeline degrades
  gracefully instead of shipping a hole (recheck may still regenerate it)

Output honors the same class contract as the LLM prompts, so the shared CSS/JS
work regardless of who produced a given file.
"""

import html as html_mod
import re

from models import CopyDeck, DesignSpec, NavItem, PageCopy, SectionCopy


def _esc(text: str) -> str:
    return html_mod.escape(text or "", quote=True)


def _slug(subject: str) -> str:
    """Deterministic picsum seed from a photo subject phrase."""
    s = re.sub(r"[^a-z0-9]+", "-", (subject or "photo").lower()).strip("-")
    return s or "photo"


def _photo_url(subject: str, w: int, h: int) -> str:
    return f"https://picsum.photos/seed/{_slug(subject)}/{w}/{h}"


def _media(subject: str, w: int, h: int, use_photos: bool, extra_cls: str = "") -> str:
    """A <figure class="media"> — a real photo, or a brand-gradient fill when photos are off."""
    cls = ("media " + extra_cls).strip()
    if use_photos:
        return (f'<figure class="{cls}"><img class="media-img" '
                f'src="{_photo_url(subject, w, h)}" width="{w}" height="{h}" '
                f'alt="{_esc(subject)}" loading="lazy"></figure>')
    return f'<figure class="{cls} media--gradient" role="img" aria-label="{_esc(subject)}"></figure>'


def render_css(design: DesignSpec) -> str:
    p = {**{"primary": "#1f3a5f", "primary_dark": "#16293f", "accent": "#e0a458",
            "bg": "#ffffff", "surface": "#f4f6f8", "text": "#1d2733", "muted": "#5b6b7c"},
         **design.palette}
    heading = design.typography.get("heading_font", "Poppins")
    body = design.typography.get("body_font", "Inter")
    radius = design.radius or "12px"
    return f""":root {{
  --primary: {p['primary']}; --primary-dark: {p['primary_dark']}; --accent: {p['accent']};
  --bg: {p['bg']}; --surface: {p['surface']}; --text: {p['text']}; --muted: {p['muted']};
  --radius: {radius};
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{ font-family: '{body}', sans-serif; color: var(--text); background: var(--bg); padding-top: 70px; line-height: 1.6; }}
h1, h2, h3 {{ font-family: '{heading}', serif; line-height: 1.2; }}
.container {{ max-width: 1140px; margin: 0 auto; padding: 0 1.5rem; }}

.navbar {{ position: fixed; top: 0; left: 0; width: 100%; height: 70px; z-index: 1000;
  background: rgba(0,0,0,0.35); transition: background 0.3s ease, box-shadow 0.3s ease; }}
.navbar.scrolled {{ background: var(--primary-dark); box-shadow: 0 2px 12px rgba(0,0,0,0.25); }}
.nav-inner {{ display: flex; align-items: center; justify-content: space-between; height: 70px; }}
.logo {{ color: #fff; font-family: '{heading}', serif; font-size: 1.35rem; font-weight: 700; text-decoration: none; }}
.hamburger {{ display: none; background: none; border: none; color: #fff; font-size: 1.6rem; cursor: pointer; }}
.nav-links {{ display: flex; gap: 1.75rem; list-style: none; }}
.nav-links a {{ color: #fff; text-decoration: none; font-size: 0.95rem; transition: color 0.3s ease; }}
.nav-links a:hover {{ color: var(--accent); }}
.nav-links a.active {{ color: var(--accent); border-bottom: 2px solid var(--accent); padding-bottom: 3px; }}

.hero {{ position: relative; min-height: 85vh; display: flex; align-items: center; margin-top: -70px; padding-top: 70px;
  overflow: hidden; background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: #fff; }}
.hero-bg {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; }}
.hero-overlay {{ position: absolute; inset: 0; z-index: 1;
  background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 82%, transparent), color-mix(in srgb, var(--primary-dark) 90%, transparent)); }}
.hero .container {{ position: relative; z-index: 2; }}
.hero-content {{ max-width: 720px; }}
.hero h1 {{ font-size: clamp(2.2rem, 5vw, 3.6rem); margin-bottom: 1rem; animation: heroRise 0.7s ease both; }}
.hero p {{ font-size: 1.15rem; opacity: 0.92; margin-bottom: 2rem; animation: heroRise 0.7s ease 0.12s both; }}
.hero .btn {{ animation: heroRise 0.7s ease 0.24s both; }}
@keyframes heroRise {{ from {{ opacity: 0; transform: translateY(22px); }} to {{ opacity: 1; transform: none; }} }}

.btn {{ display: inline-block; padding: 0.85rem 2rem; border-radius: var(--radius); text-decoration: none;
  font-weight: 600; border: 2px solid transparent; cursor: pointer; font-size: 1rem;
  transition: transform 0.3s ease, box-shadow 0.3s ease, filter 0.3s ease, color 0.3s ease; }}
.btn:hover {{ transform: scale(1.04); }}
.btn-primary {{ background: linear-gradient(135deg, var(--accent), var(--primary));
  color: #fff; box-shadow: 0 10px 24px color-mix(in srgb, var(--primary-dark) 35%, transparent); }}
.btn-primary:hover {{ filter: brightness(1.06); box-shadow: 0 14px 30px color-mix(in srgb, var(--primary-dark) 45%, transparent); }}
.btn-outline {{ border-color: currentColor; color: inherit; background: transparent; }}

.section {{ padding: 5rem 0; }}
.section-head {{ text-align: center; max-width: 640px; margin: 0 auto 3rem; }}
.section-head h2 {{ font-size: 2.1rem; margin-bottom: 0.75rem; }}
.section:not(.section-cta):not(.section-testimonials) .section-head h2 {{
  background: linear-gradient(120deg, var(--text), var(--primary));
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }}
.section-lead {{ color: var(--muted); }}
.section:nth-of-type(odd) {{ background: var(--surface); }}
.section-cta, .section-testimonials {{
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 60%, var(--primary-dark) 100%) !important;
  color: #fff; }}
.section-cta .section-head h2, .section-testimonials .section-head h2 {{ color: #fff; }}
.section-cta .section-lead, .section-testimonials .section-lead {{ color: rgba(255,255,255,0.75); }}

.cards {{ display: grid; grid-template-columns: 1fr; gap: 1.5rem; }}
.card {{ background: var(--bg); border-radius: var(--radius); padding: 2rem; border-left: 4px solid var(--accent);
  box-shadow: 0 4px 18px rgba(0,0,0,0.07); transition: transform 0.3s ease, box-shadow 0.3s ease; color: var(--text); }}
.card:hover {{ transform: translateY(-6px); box-shadow: 0 14px 30px rgba(0,0,0,0.12); }}
.card-icon {{ font-size: 2rem; margin-bottom: 0.8rem; }}
.card h3 {{ margin-bottom: 0.5rem; font-size: 1.15rem; }}
.card p {{ color: var(--muted); font-size: 0.95rem; }}

.contact-form {{ max-width: 560px; margin: 0 auto; }}
.form-group {{ margin-bottom: 1.25rem; }}
.form-group label {{ display: block; margin-bottom: 0.4rem; font-weight: 600; font-size: 0.9rem; }}
.form-group input, .form-group textarea {{ width: 100%; padding: 0.8rem 1rem; border: 1px solid var(--surface);
  border-radius: calc(var(--radius) / 2); font: inherit; background: var(--bg); color: var(--text); }}
.form-group input:focus, .form-group textarea:focus {{ outline: 2px solid var(--accent); border-color: transparent; }}
.form-success {{ margin-top: 1rem; padding: 0.9rem 1.2rem; border-radius: var(--radius);
  background: rgba(46, 160, 90, 0.12); color: #1e7a44; font-weight: 600; }}

.fade-in, .slide-up, .slide-left, .slide-right, .zoom-in {{
  opacity: 0; transition: opacity 0.6s ease, transform 0.6s ease; }}
.slide-up {{ transform: translateY(28px); }}
.slide-left {{ transform: translateX(-32px); }}
.slide-right {{ transform: translateX(32px); }}
.zoom-in {{ transform: scale(0.92); }}
.fade-in.visible, .slide-up.visible, .slide-left.visible, .slide-right.visible, .zoom-in.visible {{
  opacity: 1; transform: none; }}
.cards .card:nth-child(2) {{ transition-delay: 0.1s; }}
.cards .card:nth-child(3) {{ transition-delay: 0.2s; }}
.cards .card:nth-child(4) {{ transition-delay: 0.3s; }}

/* Imagery */
.media {{ position: relative; overflow: hidden; border-radius: var(--radius); aspect-ratio: 4 / 3;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  box-shadow: 0 10px 28px color-mix(in srgb, var(--primary-dark) 22%, transparent); }}
.media-img {{ display: block; width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s ease; }}
.media:hover .media-img {{ transform: scale(1.05); }}
.media--gradient {{ display: block; }}
.media--gradient::after {{ content: ""; position: absolute; inset: 0;
  background-image: repeating-linear-gradient(45deg, rgba(255,255,255,0.06) 0 12px, transparent 12px 24px); }}
.media-row {{ display: grid; grid-template-columns: 1fr; gap: 2rem; align-items: center; }}
.media-row .media {{ aspect-ratio: 16 / 11; }}
.gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; }}
.gallery-item {{ aspect-ratio: 1 / 1; }}
.gallery-item figcaption {{ position: absolute; left: 0; right: 0; bottom: 0; padding: 0.6rem 0.8rem;
  font-size: 0.85rem; color: #fff; background: linear-gradient(to top, rgba(0,0,0,0.6), transparent); }}

/* Stats (count-up) */
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1.5rem; text-align: center; }}
.stat-value {{ display: block; font-family: '{heading}', serif; font-weight: 700;
  font-size: clamp(2rem, 4vw, 3rem); color: var(--primary);
  background: linear-gradient(135deg, var(--primary), var(--accent));
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }}
.stat-label {{ color: var(--muted); font-size: 0.95rem; }}

/* One subtle ambient motion on the bold brand section */
.section-cta, .section-testimonials {{ background-size: 180% 180%; animation: brandDrift 14s ease infinite; }}
@keyframes brandDrift {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}

.footer {{ background: var(--primary-dark); color: rgba(255,255,255,0.85); padding: 3rem 0 2rem; }}
.footer-inner {{ display: flex; flex-wrap: wrap; gap: 2rem; justify-content: space-between; }}
.footer h3 {{ color: #fff; margin-bottom: 0.6rem; }}
.footer-links {{ list-style: none; }}
.footer-links a {{ color: rgba(255,255,255,0.85); text-decoration: none; }}
.footer-links a:hover {{ color: var(--accent); }}
.copyright {{ width: 100%; text-align: center; margin-top: 2rem; font-size: 0.85rem; opacity: 0.7; }}

@media (max-width: 767px) {{
  .hamburger {{ display: block; }}
  .nav-links {{ display: none; flex-direction: column; position: absolute; top: 100%; left: 0; width: 100%;
    background: var(--primary-dark); padding: 1.5rem 2rem; z-index: 999; gap: 1rem; }}
  .nav-links.active {{ display: flex; }}
}}
@media (min-width: 768px) {{
  .cards {{ grid-template-columns: repeat(2, 1fr); }}
  .media-row {{ grid-template-columns: 1fr 1fr; }}
  .media-row.media-row--reverse .media {{ order: 2; }}
}}
@media (min-width: 1024px) {{
  .cards {{ grid-template-columns: repeat(3, 1fr); }}
}}
@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; transition: none !important; }}
  .fade-in, .slide-up, .slide-left, .slide-right, .zoom-in {{ opacity: 1 !important; transform: none !important; }}
  .media:hover .media-img {{ transform: none; }}
}}
"""


def _render_section(section: SectionCopy, use_photos: bool = True) -> str:
    parts: list[str] = []
    parts.append(f'  <section class="section section-{_esc(section.kind)}" id="{_esc(section.id)}">')
    parts.append('    <div class="container">')
    parts.append('      <div class="section-head">')
    if section.heading:
        parts.append(f'        <h2 class="fade-in">{_esc(section.heading)}</h2>')
    if section.subheading:
        parts.append(f'        <p class="section-lead fade-in">{_esc(section.subheading)}</p>')
    parts.append('      </div>')

    # Stats section → animated count-up figures
    if section.kind == "stats" and section.items:
        parts.append('      <div class="stats">')
        for item in section.items:
            digits = re.sub(r"[^0-9]", "", str(item.get("value", ""))) or "0"
            parts.append('        <div class="stat zoom-in">')
            parts.append(f'          <span class="stat-value" data-target="{digits}">0</span>')
            parts.append(f'          <span class="stat-label">{_esc(str(item.get("label", item.get("title", ""))))}</span>')
            parts.append('        </div>')
        parts.append('      </div>')
        parts.append('    </div>')
        parts.append('  </section>')
        return "\n".join(parts)

    # Gallery section → grid of photos
    if section.kind == "gallery" and section.items:
        parts.append('      <div class="gallery">')
        for item in section.items:
            subject = str(item.get("image") or item.get("title") or section.heading)
            cls = "gallery-item slide-up"
            if use_photos:
                inner = (f'<img class="media-img" src="{_photo_url(subject, 600, 600)}" '
                         f'width="600" height="600" alt="{_esc(subject)}" loading="lazy">')
            else:
                inner = ""
                cls += " media--gradient"
            caption = (f'<figcaption>{_esc(str(item["title"]))}</figcaption>'
                       if item.get("title") else "")
            label = "" if use_photos else f' role="img" aria-label="{_esc(subject)}"'
            parts.append(f'        <figure class="media {cls}"{label}>{inner}{caption}</figure>')
        parts.append('      </div>')
        parts.append('    </div>')
        parts.append('  </section>')
        return "\n".join(parts)

    # A section-level photo beside its text (about/story), else plain body
    if section.image and section.body:
        parts.append('      <div class="media-row">')
        parts.append(f'        <div class="slide-left">{_media(section.image, 800, 600, use_photos)}</div>')
        parts.append(f'        <div class="media-text slide-right"><p>{_esc(section.body)}</p></div>')
        parts.append('      </div>')
    else:
        if section.image:
            parts.append(f'      <div class="slide-up" style="max-width:900px;margin:0 auto 2rem;">{_media(section.image, 900, 500, use_photos)}</div>')
        if section.body:
            parts.append(f'      <p class="slide-up" style="max-width:720px;margin:0 auto 2rem;">{_esc(section.body)}</p>')

    if section.items:
        parts.append('      <div class="cards">')
        for item in section.items:
            parts.append('        <div class="card slide-up">')
            if item.get("image"):
                parts.append(f'          {_media(str(item["image"]), 600, 450, use_photos)}')
            if item.get("icon") and not item.get("image"):
                parts.append(f'          <div class="card-icon">{_esc(str(item["icon"]))}</div>')
            if item.get("title"):
                parts.append(f'          <h3>{_esc(str(item["title"]))}</h3>')
            if item.get("body"):
                parts.append(f'          <p>{_esc(str(item["body"]))}</p>')
            parts.append('        </div>')
        parts.append('      </div>')
    if section.kind == "contact":
        parts.append("""      <form class="contact-form">
        <div class="form-group"><label for="name">Name</label><input id="name" name="name" type="text" required></div>
        <div class="form-group"><label for="email">Email</label><input id="email" name="email" type="email" required></div>
        <div class="form-group"><label for="message">Message</label><textarea id="message" name="message" rows="5" required></textarea></div>
        <button type="submit" class="btn btn-primary">Send message</button>
        <p class="form-success" style="display:none;"></p>
      </form>""")
    if section.cta:
        label = _esc(str(section.cta.get("label", "Learn more")))
        href = _esc(str(section.cta.get("href", "#")))
        parts.append(f'      <p style="text-align:center;margin-top:2rem;"><a class="btn btn-primary" href="{href}">{label}</a></p>')
    parts.append('    </div>')
    parts.append('  </section>')
    return "\n".join(parts)


def render_page(page: PageCopy, nav: list[NavItem], footer: dict,
                design: DesignSpec, site_name: str, use_photos: bool = True) -> str:
    fonts_url = design.typography.get(
        "google_fonts_url",
        "https://fonts.googleapis.com/css2?family=Poppins:wght@500;700&family=Inter:wght@400;500&display=swap")

    nav_items = "\n".join(
        f'          <li><a href="{_esc(n.filename)}"'
        f'{" class=\"active\"" if n.filename == page.filename else ""}>{_esc(n.label)}</a></li>'
        for n in nav)
    footer_links = "\n".join(
        f'          <li><a href="{_esc(n.filename)}">{_esc(n.label)}</a></li>' for n in nav)

    hero = page.sections[0] if page.sections and page.sections[0].kind == "hero" else None
    rest = page.sections[1:] if hero else page.sections

    hero_html = ""
    if hero:
        cta_html = ""
        if hero.cta:
            cta_html = (f'        <a class="btn btn-primary" '
                        f'href="{_esc(str(hero.cta.get("href", "#")))}">'
                        f'{_esc(str(hero.cta.get("label", "Get started")))}</a>\n')
        hero_bg = ""
        hero_cls = "hero"
        if hero.image and use_photos:
            hero_cls = "hero has-photo"
            hero_bg = (f'    <img class="hero-bg" src="{_photo_url(hero.image, 1600, 900)}" '
                       f'width="1600" height="900" alt="{_esc(hero.image)}" loading="eager">\n'
                       f'    <div class="hero-overlay"></div>\n')
        hero_html = f"""  <section class="{hero_cls}" id="hero">
{hero_bg}    <div class="container">
      <div class="hero-content">
        <h1>{_esc(hero.heading)}</h1>
        <p>{_esc(hero.subheading or hero.body)}</p>
{cta_html}      </div>
    </div>
  </section>
"""

    sections_html = "\n".join(_render_section(s, use_photos) for s in rest)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(page.title)}</title>
  <meta name="description" content="{_esc(page.meta_description)}">
  <link href="{_esc(fonts_url)}" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="navbar">
    <nav class="nav-inner container">
      <a class="logo" href="index.html">{_esc(site_name)}</a>
      <button class="hamburger" aria-label="Menu">☰</button>
      <ul class="nav-links">
{nav_items}
      </ul>
    </nav>
  </header>
  <main>
{hero_html}{sections_html}
  </main>
  <footer class="footer">
    <div class="footer-inner container">
      <div>
        <h3>{_esc(site_name)}</h3>
        <p>{_esc(str(footer.get("tagline", "")))}</p>
      </div>
      <div>
        <h3>Quick links</h3>
        <ul class="footer-links">
{footer_links}
        </ul>
      </div>
      <p class="copyright">{_esc(str(footer.get("copyright", "")))}</p>
    </div>
  </footer>
  <script src="script.js"></script>
</body>
</html>
"""


def render_js() -> str:
    return """// Shared site script — loads on every page, so everything is null-checked.
var navbar = document.querySelector('.navbar');
if (navbar) {
  window.addEventListener('scroll', function () {
    navbar.classList.toggle('scrolled', window.scrollY > 50);
  });
}

var hamburger = document.querySelector('.hamburger');
var navLinks = document.querySelector('.nav-links');
if (hamburger && navLinks) {
  hamburger.addEventListener('click', function () {
    navLinks.classList.toggle('active');
    hamburger.textContent = navLinks.classList.contains('active') ? '\\u2715' : '\\u2630';
  });
  navLinks.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', function () {
      navLinks.classList.remove('active');
      hamburger.textContent = '\\u2630';
    });
  });
}

var animated = document.querySelectorAll('.fade-in, .slide-up, .slide-left, .slide-right, .zoom-in');
if (animated.length && 'IntersectionObserver' in window) {
  var observer = new IntersectionObserver(function (entries) {
    var visibleIndex = 0;
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.style.transitionDelay = (visibleIndex * 0.1) + 's';
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
        visibleIndex += 1;
      }
    });
  }, { threshold: 0.15 });
  animated.forEach(function (el) { observer.observe(el); });
}

// Count-up stats: animate .stat-value from 0 to data-target when scrolled into view.
var stats = document.querySelectorAll('.stat-value[data-target]');
if (stats.length && 'IntersectionObserver' in window) {
  var countObs = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var el = entry.target;
      countObs.unobserve(el);
      var target = parseInt(el.getAttribute('data-target'), 10) || 0;
      var start = null, dur = 1500;
      function step(ts) {
        if (start === null) start = ts;
        var p = Math.min((ts - start) / dur, 1);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased).toLocaleString();
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }, { threshold: 0.4 });
  stats.forEach(function (el) { countObs.observe(el); });
}

// Image fallback: swap any failed photo for a brand-gradient SVG so exported/offline
// sites never show a broken-image icon.
(function () {
  var cs = getComputedStyle(document.documentElement);
  var c1 = (cs.getPropertyValue('--primary') || '#334155').trim();
  var c2 = (cs.getPropertyValue('--primary-dark') || '#0f172a').trim();
  function fallback(img) {
    if (img.dataset.fb) return;
    img.dataset.fb = '1';
    var w = img.getAttribute('width') || 1200, h = img.getAttribute('height') || 800;
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '">' +
      '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">' +
      '<stop offset="0" stop-color="' + c1 + '"/><stop offset="1" stop-color="' + c2 + '"/>' +
      '</linearGradient></defs><rect width="100%" height="100%" fill="url(#g)"/></svg>';
    img.src = 'data:image/svg+xml,' + encodeURIComponent(svg);
  }
  document.querySelectorAll('img').forEach(function (img) {
    img.addEventListener('error', function () { fallback(img); });
    if (img.complete && img.naturalWidth === 0) fallback(img);
  });
})();

document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
  anchor.addEventListener('click', function (event) {
    var target = document.querySelector(anchor.getAttribute('href'));
    if (target) {
      event.preventDefault();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  });
});

document.querySelectorAll('form.contact-form').forEach(function (form) {
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var success = form.querySelector('.form-success');
    if (success) {
      success.textContent = 'Thank you! Your message has been sent — we will get back to you soon.';
      success.style.display = 'block';
    }
    setTimeout(function () { form.reset(); }, 400);
  });
});
"""
