"""Builder agent — three per-file generators sharing one class contract.

Each function is one independent LLM call, which is what lets the orchestrator
fan pages out in parallel. Coherence across the calls comes from the shared
CLASS_CONTRACT in the prompts plus the design spec / copy deck passed to all.
"""

import asyncio
import json

import config
import fallback
import llm
from models import CopyDeck, DesignSpec, PageCopy, ProjectBrief
from prompts.builder import CSS_PROMPT, JS_PROMPT, PAGE_PROMPT


def _manifest_json(deck: CopyDeck) -> str:
    return json.dumps(deck.page_manifest(), indent=2)


async def build_css(design: DesignSpec, deck: CopyDeck, *, model: str,
                    on_status: llm.StatusFn | None = None) -> str:
    if config.MOCK_LLM:
        await asyncio.sleep(1.4)
        return fallback.render_css(design)

    user = (f"DESIGN SPEC:\n{design.model_dump_json(indent=2)}\n\n"
            f"SECTION KINDS USED ACROSS THE SITE:\n{json.dumps(deck.section_inventory())}\n\n"
            f"PAGE MANIFEST:\n{_manifest_json(deck)}")
    css = await llm.complete_text(CSS_PROMPT, user, model=model,
                                  max_tokens=config.CSS_MAX_TOKENS,
                                  temperature=0.3, on_status=on_status)
    return llm.strip_fences(css)


async def build_page(page: PageCopy, brief: ProjectBrief, design: DesignSpec,
                     deck: CopyDeck, css: str, *, model: str, use_photos: bool = True,
                     on_status: llm.StatusFn | None = None) -> str:
    if config.MOCK_LLM:
        await asyncio.sleep(1.0 + 0.6 * (hash(page.filename) % 3))
        return fallback.render_page(page, deck.nav, deck.footer, design,
                                    brief.business_name, use_photos)

    image_mode = "photos" if use_photos else "svg-only"
    user = (f"SITE BRIEF (context):\n{brief.model_dump_json(indent=2)}\n\n"
            f"NAV MANIFEST (every page of the site):\n{_manifest_json(deck)}\n\n"
            f"FOOTER COPY:\n{json.dumps(deck.footer)}\n\n"
            f"DESIGN SPEC:\n{design.model_dump_json(indent=2)}\n\n"
            f"IMAGE MODE: {image_mode}\n\n"
            f"COPY FOR THIS PAGE ({page.filename}) — use it EXACTLY:\n"
            f"{page.model_dump_json(indent=2)}\n\n"
            f"SHARED STYLESHEET (style.css) — use its classes, do not restyle:\n{css}")
    html = await llm.complete_text(PAGE_PROMPT, user, model=model,
                                   max_tokens=config.PAGE_MAX_TOKENS,
                                   temperature=0.3, on_status=on_status)
    return llm.strip_fences(html)


async def build_js(deck: CopyDeck, *, model: str,
                   on_status: llm.StatusFn | None = None) -> str:
    if config.MOCK_LLM:
        await asyncio.sleep(1.2)
        return fallback.render_js()

    user = (f"PAGE MANIFEST:\n{_manifest_json(deck)}\n\n"
            f"SECTION KINDS USED:\n{json.dumps(deck.section_inventory())}")
    js = await llm.complete_text(JS_PROMPT, user, model=model,
                                 max_tokens=config.JS_MAX_TOKENS,
                                 temperature=0.3, on_status=on_status)
    return llm.strip_fences(js)
