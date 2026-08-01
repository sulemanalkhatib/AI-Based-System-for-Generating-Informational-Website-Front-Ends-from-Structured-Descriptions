"""Pydantic contracts for every agent handoff and API payload.

Ownership rules the pipeline depends on:
- CopyDeck owns ALL words (the builder must use its text exactly — "copy is law").
- DesignSpec owns ALL look (palette, typography, layout rhythm).
The two never overlap, which is what makes the parallel fan-out safe.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Windows reserved device names — "con.html" would be unwritable on disk
_RESERVED_STEMS = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def safe_page_filename(name: str) -> str:
    """Normalize any page name the LLM produces into a safe *.html filename."""
    stem = name.strip().lower()
    stem = stem.removesuffix(".html").removesuffix(".htm")
    stem = re.sub(r"[^a-z0-9-]+", "-", stem)
    stem = re.sub(r"-+", "-", stem).strip("-") or "page"
    if stem in _RESERVED_STEMS:
        stem = f"site-{stem}"
    return f"{stem}.html"


# ---------------------------------------------------------------- interview

class ProjectBrief(BaseModel):
    business_name: str = "My Website"
    business_type: str = ""
    description: str = ""
    target_audience: str = ""
    tone_style: str = ""
    color_preferences: str = ""
    pages: list[str] = Field(default_factory=lambda: ["index"])
    sections: list[str] = Field(default_factory=list)
    content_details: str = ""
    special_requirements: str = ""
    # The #1 action the site should drive toward (book / call / buy / donate…) —
    # sharpens every CTA. And any sites/looks the owner admires — a design north star.
    primary_goal: str = ""
    references: str = ""


# ---------------------------------------------------------------- copywriter

class NavItem(BaseModel):
    label: str
    filename: str

    @field_validator("filename")
    @classmethod
    def _safe(cls, v: str) -> str:
        return safe_page_filename(v)


class SectionCopy(BaseModel):
    id: str
    kind: str = "content"        # hero|services|about|team|testimonials|faq|contact|cta|gallery|stats|...
    heading: str = ""
    subheading: str = ""
    body: str = ""
    cta: dict | None = None      # {"label": ..., "href": ...}
    items: list[dict] = Field(default_factory=list)  # cards: {title, body, icon, image}
    # Optional concrete photo subject for a section-level image (e.g. "chef at a
    # wood-fired oven"). Doubles as the image's alt text. Empty = no photo here.
    image: str = ""


class PageCopy(BaseModel):
    filename: str
    title: str
    meta_description: str = ""
    sections: list[SectionCopy] = Field(default_factory=list)

    @field_validator("filename")
    @classmethod
    def _safe(cls, v: str) -> str:
        return safe_page_filename(v)


class CopyDeck(BaseModel):
    seo_title: str = ""
    nav: list[NavItem] = Field(default_factory=list)
    pages: list[PageCopy] = Field(default_factory=list)
    footer: dict = Field(default_factory=dict)  # {"tagline": ..., "copyright": ...}

    def page_manifest(self) -> list[dict]:
        return [{"filename": p.filename, "title": p.title} for p in self.pages]

    def section_inventory(self) -> list[str]:
        """Distinct section kinds across all pages — feeds the shared-CSS prompt."""
        seen: list[str] = []
        for page in self.pages:
            for section in page.sections:
                if section.kind not in seen:
                    seen.append(section.kind)
        return seen

    @classmethod
    def fallback(cls, brief: ProjectBrief) -> "CopyDeck":
        """Mechanical single-source deck used when the copywriter branch fails."""
        page_names = brief.pages or ["index"]
        nav = [
            NavItem(label=("Home" if n.lower().startswith("index") else n.replace("-", " ").title()),
                    filename=n)
            for n in page_names
        ]
        pages = []
        for i, item in enumerate(nav):
            sections = [SectionCopy(
                id="hero", kind="hero",
                heading=brief.business_name,
                subheading=brief.description or brief.business_type,
                cta={"label": "Contact us", "href": "#contact"},
            )]
            if i == 0:
                for name in (brief.sections or ["about", "contact"]):
                    sid = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "section"
                    sections.append(SectionCopy(
                        id=sid, kind=sid,
                        heading=name.title(),
                        body=brief.content_details[:600],
                    ))
            pages.append(PageCopy(
                filename=item.filename,
                title=f"{brief.business_name} — {item.label}",
                meta_description=brief.description[:150],
                sections=sections,
            ))
        return cls(
            seo_title=brief.business_name,
            nav=nav,
            pages=pages,
            footer={"tagline": brief.description[:120],
                    "copyright": f"© {brief.business_name}"},
        )


# ---------------------------------------------------------------- designer

class DesignSpec(BaseModel):
    palette: dict[str, str] = Field(default_factory=dict)   # hex by role
    typography: dict = Field(default_factory=dict)          # heading_font, body_font, google_fonts_url
    layout_style: str = "modern"
    hero_treatment: str = "gradient overlay"
    section_rhythm: list[str] = Field(default_factory=list) # background treatment per section
    radius: str = "12px"
    css_notes: str = ""
    # Photographic direction: mood/subject of imagery and where photos help
    # (hero, about, gallery) vs where icons are enough (small feature cards).
    imagery: str = "warm, authentic photography relevant to the business"

    @classmethod
    def fallback(cls, brief: ProjectBrief) -> "DesignSpec":
        """Safe modern defaults used when the designer branch fails."""
        return cls(
            palette={
                "primary": "#1f3a5f", "primary_dark": "#16293f", "accent": "#e0a458",
                "bg": "#ffffff", "surface": "#f4f6f8", "text": "#1d2733", "muted": "#5b6b7c",
            },
            typography={
                "heading_font": "Poppins", "body_font": "Inter",
                "google_fonts_url": ("https://fonts.googleapis.com/css2?"
                                     "family=Poppins:wght@500;600;700&family=Inter:wght@400;500&display=swap"),
            },
            layout_style="clean modern",
            hero_treatment="diagonal gradient from primary to primary_dark with soft overlay",
            section_rhythm=["surface", "bg", "primary tint 10%", "bg", "primary_dark solid"],
            radius="12px",
            css_notes=f"Respect the user's color words if any: {brief.color_preferences!r}",
            imagery="warm, authentic photography relevant to the business; hero photo under a brand overlay",
        )


# ---------------------------------------------------------------- audit

class MachineCheck(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class AuditIssue(BaseModel):
    severity: Literal["critical", "warning", "info"] = "info"
    category: str = "general"
    page: str | None = None
    message: str
    suggestion: str = ""


class CategoryScore(BaseModel):
    name: str
    score: int
    max: int = 25


class AuditReport(BaseModel):
    score: int = 0                                    # 0–100
    categories: list[CategoryScore] = Field(default_factory=list)
    issues: list[AuditIssue] = Field(default_factory=list)
    machine_checks: list[MachineCheck] = Field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------- settings

# "editor" runs post-build (chat becomes the site editor); it has its own model
# slot but defaults to following the builder's model (see routes/chat.py).
AGENT_NAMES = ["interviewer", "copywriter", "designer", "builder", "recheck", "audit", "editor"]


class AppSettings(BaseModel):
    # "auto" is the one id guaranteed accepted by the proxy (v1 used it); users can
    # pin concrete model ids per agent in Settings — recommended for builder/recheck.
    models: dict[str, str] = Field(
        default_factory=lambda: {name: "auto" for name in AGENT_NAMES})
    theme_accent: str = "#cc785c"
    # Empty string = fall back to the .env values (backend/.env)
    api_key: str = ""
    base_url: str = ""
    # Feed a rendered screenshot to the auditor so it judges the site visually.
    # Off by default: needs Playwright installed and a vision-capable audit model.
    vision_audit: bool = False
    # Use real stock photos (deterministic Picsum URLs) in generated sites. On by
    # default. When off, the builder uses only brand-gradient SVG imagery — fully
    # offline-safe (no external URLs) for exported sites with no network.
    use_photos: bool = True
    # Disabled agents are skipped by the pipeline (deterministic fallback instead)
    enabled: dict[str, bool] = Field(
        default_factory=lambda: {name: True for name in AGENT_NAMES})

    def model_for(self, agent: str) -> str:
        return self.models.get(agent) or "auto"

    def is_enabled(self, agent: str) -> bool:
        return self.enabled.get(agent, True)
