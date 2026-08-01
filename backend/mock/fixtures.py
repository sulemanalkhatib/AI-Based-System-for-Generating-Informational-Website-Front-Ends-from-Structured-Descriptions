"""Canned pipeline data for MOCK_LLM=1 — deterministic, free, demo-friendly.

Delays are deliberate: they make the parallel agent cards visibly run
side-by-side in the UI, which is the point of the demo.
"""

import asyncio

from models import (AuditIssue, AuditReport, CategoryScore, CopyDeck,
                    DesignSpec, MachineCheck, NavItem, PageCopy, ProjectBrief,
                    SectionCopy)

MOCK_BRIEF = ProjectBrief(
    business_name="Ember & Oak",
    business_type="Restaurant — modern wood-fired bistro",
    description="A cozy wood-fired bistro in the old town serving seasonal small plates and slow-roasted mains.",
    target_audience="Couples and food lovers aged 25-45 looking for a warm night out",
    tone_style="warm, elegant, inviting",
    color_preferences="deep charcoal, ember orange, warm cream",
    pages=["index", "menu", "contact"],
    sections=["hero", "about", "menu", "testimonials", "hours", "contact"],
    content_details=("Tagline: 'Fire makes flavor.' Signature dishes: 48-hour short rib, "
                     "charred leek burrata, smoked honey flan. Open Tue-Sun 17:00-23:00. "
                     "Located at 14 Old Mill Lane. Chef-owner: Maya Aldein."),
    special_requirements="Reservation form on the contact page",
)


def copy_deck(brief: ProjectBrief | None = None) -> CopyDeck:
    b = brief or MOCK_BRIEF
    nav = [NavItem(label="Home", filename="index.html"),
           NavItem(label="Menu", filename="menu.html"),
           NavItem(label="Reservations", filename="contact.html")]
    return CopyDeck(
        seo_title=f"{b.business_name} — Fire makes flavor",
        nav=nav,
        pages=[
            PageCopy(
                filename="index.html",
                title=f"{b.business_name} — Wood-fired bistro in the old town",
                meta_description="Seasonal small plates and slow-roasted mains from a wood-fired kitchen. Book your table tonight.",
                sections=[
                    SectionCopy(id="hero", kind="hero",
                                heading="Fire makes flavor.",
                                subheading="Seasonal plates, slow-roasted mains and a room that glows — welcome to Ember & Oak.",
                                cta={"label": "Book a table", "href": "contact.html"},
                                image="steaks and vegetables searing over open flames in a wood-fired oven"),
                    SectionCopy(id="about", kind="about",
                                heading="Cooked over living flame",
                                subheading="Every dish passes through our wood-fired hearth.",
                                body=("Chef-owner Maya Aldein built Ember & Oak around a single oak-fired oven. "
                                      "The menu changes with the market, but the fire never goes out."),
                                image="chef tending a glowing wood-fired oven in a warm restaurant kitchen"),
                    SectionCopy(id="numbers", kind="stats",
                                heading="A room that keeps filling",
                                items=[
                                    {"value": "1200", "label": "Plates served each week"},
                                    {"value": "48", "label": "Hours our short rib smokes"},
                                    {"value": "9", "label": "Years by the old mill"},
                                ]),
                    SectionCopy(id="gallery", kind="gallery",
                                heading="From the hearth",
                                subheading="A few nights at Ember & Oak.",
                                items=[
                                    {"title": "The open hearth", "image": "flames in a restaurant wood-fired oven"},
                                    {"title": "Short rib, plated", "image": "plated braised short rib with charred vegetables"},
                                    {"title": "The dining room", "image": "warm candlelit restaurant dining room at night"},
                                    {"title": "Ember flatbread", "image": "charred flatbread with herbs on a wooden board"},
                                ]),
                    SectionCopy(id="signatures", kind="services",
                                heading="Signature plates",
                                subheading="Three dishes people cross the city for.",
                                items=[
                                    {"title": "48-hour short rib", "body": "Slow-smoked, glazed over embers, served with charred roots.", "icon": "🔥"},
                                    {"title": "Charred leek burrata", "body": "Smoky leeks, cold burrata, ember oil and toasted rye.", "icon": "🧀"},
                                    {"title": "Smoked honey flan", "body": "Silky flan finished with honey pulled straight from the smoker.", "icon": "🍮"},
                                ]),
                    SectionCopy(id="testimonials", kind="testimonials",
                                heading="What guests say",
                                items=[
                                    {"title": "— Lina, local guide", "body": "“The short rib is the best thing I ate this year. The room feels like a hug.”"},
                                    {"title": "— Omar, food blogger", "body": "“Smoke, warmth, candlelight. Ember & Oak is date night done right.”"},
                                ]),
                    SectionCopy(id="cta", kind="cta",
                                heading="Tonight deserves a fire",
                                subheading="Tables go fast on weekends — reserve yours now.",
                                cta={"label": "Reserve now", "href": "contact.html"}),
                ]),
            PageCopy(
                filename="menu.html",
                title=f"Menu — {b.business_name}",
                meta_description="Seasonal small plates, wood-fired mains and desserts from the ember oven.",
                sections=[
                    SectionCopy(id="hero", kind="hero",
                                heading="The menu",
                                subheading="Seasonal, market-driven, always touched by fire.",
                                image="rustic wooden table of wood-fired dishes shot from above"),
                    SectionCopy(id="small-plates", kind="menu",
                                heading="Small plates",
                                items=[
                                    {"title": "Charred leek burrata — 9", "body": "Smoky leeks, cold burrata, ember oil, toasted rye.", "icon": "🥬"},
                                    {"title": "Ash-roasted beets — 8", "body": "Whipped feta, dill, smoked walnut crumble.", "icon": "🥗"},
                                    {"title": "Ember flatbread — 7", "body": "Blistered crust, rosemary oil, sea salt.", "icon": "🫓"},
                                ]),
                    SectionCopy(id="mains", kind="menu",
                                heading="From the hearth",
                                items=[
                                    {"title": "48-hour short rib — 24", "body": "Slow-smoked, ember-glazed, charred roots.", "icon": "🔥"},
                                    {"title": "Cedar-plank trout — 21", "body": "Brown butter, capers, fire-licked lemon.", "icon": "🐟"},
                                    {"title": "Oak-fired mushroom pot — 17", "body": "Wild mushrooms, smoked cream, hearth bread.", "icon": "🍄"},
                                ]),
                    SectionCopy(id="dessert", kind="menu",
                                heading="Sweet endings",
                                items=[
                                    {"title": "Smoked honey flan — 8", "body": "Silky flan, smoker-pulled honey.", "icon": "🍮"},
                                    {"title": "Burnt orange tart — 8", "body": "Caramelised citrus, torched meringue.", "icon": "🍊"},
                                ]),
                    SectionCopy(id="cta", kind="cta",
                                heading="Hungry yet?",
                                cta={"label": "Book a table", "href": "contact.html"}),
                ]),
            PageCopy(
                filename="contact.html",
                title=f"Reservations — {b.business_name}",
                meta_description="Book a table at Ember & Oak. Open Tue-Sun 17:00-23:00, 14 Old Mill Lane.",
                sections=[
                    SectionCopy(id="hero", kind="hero",
                                heading="Reserve your table",
                                subheading="Open Tue–Sun, 17:00–23:00 · 14 Old Mill Lane",
                                image="cozy candlelit restaurant table set for two by a window"),
                    SectionCopy(id="hours", kind="hours",
                                heading="Hours & location",
                                items=[
                                    {"title": "Opening hours", "body": "Tuesday to Sunday, 17:00 – 23:00. Closed Mondays.", "icon": "🕐"},
                                    {"title": "Find us", "body": "14 Old Mill Lane, in the heart of the old town.", "icon": "📍"},
                                    {"title": "Groups", "body": "Parties of 7+? Email us and we'll set the long table by the hearth.", "icon": "🍽️"},
                                ]),
                    SectionCopy(id="contact", kind="contact",
                                heading="Book a table",
                                subheading="We confirm every reservation within the hour."),
                ]),
        ],
        footer={"tagline": "Fire makes flavor.",
                "copyright": f"© 2026 {b.business_name} · 14 Old Mill Lane"},
    )


def design_spec(brief: ProjectBrief | None = None) -> DesignSpec:
    return DesignSpec(
        palette={"primary": "#c2571b", "primary_dark": "#241b16", "accent": "#e8a852",
                 "bg": "#fdf9f4", "surface": "#f3ebe2", "text": "#241b16", "muted": "#6e6259"},
        typography={"heading_font": "Playfair Display", "body_font": "Inter",
                    "google_fonts_url": ("https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700"
                                         "&family=Inter:wght@400;500;600&display=swap")},
        layout_style="warm editorial with generous whitespace",
        hero_treatment="full-bleed photo of the wood-fired oven under a charcoal-to-ember gradient overlay so the white headline pops",
        section_rhythm=["bg", "surface", "primary tint 10%", "bg", "primary_dark solid with white text"],
        radius="12px",
        imagery="Warm, moody close-ups of fire-cooked food, the glowing hearth and the candlelit room. Full-bleed hero photo under a brand overlay, a photo beside the story, and a small gallery. Signature-dish cards stay icon-led.",
        css_notes="Ember-orange border-left accents on cards, gradient text on key headings, ember→charcoal gradient CTA buttons, soft glow behind the hero CTA.",
    )


def audit_report(high: bool = False) -> AuditReport:
    """high=True → post-fix report that clears the 95 target and ends the loop."""
    if high:
        return AuditReport(
            score=97,
            categories=[
                CategoryScore(name="Content fidelity", score=25, max=25),
                CategoryScore(name="Design & visual", score=24, max=25),
                CategoryScore(name="Code quality", score=24, max=25),
                CategoryScore(name="Responsiveness & UX", score=24, max=25),
            ],
            issues=[],  # clean — the review loop stops here (no issues left)
            machine_checks=[],
            summary=("Polished and cohesive — the recheck pass alternated the menu "
                     "rhythm and tightened the hero. No open issues remain."),
        )
    return AuditReport(
        score=88,
        categories=[
            CategoryScore(name="Content fidelity", score=24, max=25),
            CategoryScore(name="Design & visual", score=21, max=25),
            CategoryScore(name="Code quality", score=22, max=25),
            CategoryScore(name="Responsiveness & UX", score=21, max=25),
        ],
        issues=[
            AuditIssue(severity="warning", category="Design & visual", page="menu.html",
                       message="Menu sections reuse the same card background three times in a row, flattening the rhythm.",
                       suggestion="Alternate the middle menu section onto the surface tone."),
            AuditIssue(severity="info", category="Responsiveness & UX", page="index.html",
                       message="Hero CTA sits close to the fold on small phones.",
                       suggestion="Reduce hero vertical padding under 400px width."),
            AuditIssue(severity="info", category="Code quality", page=None,
                       message="Consider width/height attributes on any future images to avoid layout shift.",
                       suggestion="Add explicit dimensions when imagery is introduced."),
        ],
        machine_checks=[],
        summary=("A warm, cohesive site that uses the real menu and hours throughout. "
                 "Minor rhythm and spacing polish would lift it further; nothing blocks launch."),
    )


async def interviewer_turn(history: list[dict], user_message: str) -> tuple[str, ProjectBrief | None]:
    """Scripted interview: one follow-up question, then the brief on the second user turn."""
    await asyncio.sleep(0.8)
    user_turns = sum(1 for m in history if m.get("role") == "user") + 1
    if user_turns < 2:
        return ("Lovely — a restaurant site is a great fit for this pipeline! [mock] "
                "Tell me anything else (or just say 'go') and I'll kick off the build with "
                "a demo brief for a wood-fired bistro called Ember & Oak.", None)
    return ("Perfect — I have everything I need. The team is starting your build now! [mock]",
            MOCK_BRIEF)
