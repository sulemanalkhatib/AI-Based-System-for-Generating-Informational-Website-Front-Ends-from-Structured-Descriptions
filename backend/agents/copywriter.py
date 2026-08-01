"""Copywriter agent — ProjectBrief → CopyDeck (owns every word on the site)."""

import asyncio

import config
import llm
from models import CopyDeck, NavItem, ProjectBrief
from prompts.copywriter import COPYWRITER_PROMPT


def _normalize(deck: CopyDeck) -> CopyDeck:
    """Enforce structural invariants the rest of the pipeline relies on."""
    deck.pages = deck.pages[:config.MAX_PAGES]
    if deck.pages and not any(p.filename == "index.html" for p in deck.pages):
        old = deck.pages[0].filename
        deck.pages[0].filename = "index.html"
        for item in deck.nav:
            if item.filename == old:
                item.filename = "index.html"
    known = {p.filename for p in deck.pages}
    deck.nav = [n for n in deck.nav if n.filename in known]
    if not deck.nav:  # never leave the site without navigation
        deck.nav = [
            NavItem(
                label=("Home" if p.filename == "index.html"
                       else p.filename.removesuffix(".html").replace("-", " ").title()),
                filename=p.filename)
            for p in deck.pages
        ]
    return deck


async def run(brief: ProjectBrief, *, model: str,
              on_status: llm.StatusFn | None = None) -> CopyDeck:
    if config.MOCK_LLM:
        from mock import fixtures
        await asyncio.sleep(1.6)
        return fixtures.copy_deck(brief)

    deck = await llm.complete_json(
        CopyDeck, COPYWRITER_PROMPT, brief.model_dump_json(indent=2),
        model=model, max_tokens=config.SPEC_MAX_TOKENS,
        temperature=0.7, on_status=on_status)
    if not deck.pages:
        raise ValueError("copywriter returned no pages")
    return _normalize(deck)
