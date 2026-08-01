"""Parsers are the pipeline's immune system — test them without any network."""

import llm
import writer
from agents.editor import parse_editor_output
from agents.interviewer import (BRIEF_FORMAT_MSG, EMPTY_REPLY_MSG, _finish,
                                extract_brief)
from agents.rechecker import parse_recheck_output
from models import safe_page_filename


def test_strip_fences_removes_language_fence():
    assert llm.strip_fences("```html\n<p>hi</p>\n```") == "<p>hi</p>"
    assert llm.strip_fences("plain text") == "plain text"


def test_extract_json_salvages_surrounding_prose():
    raw = 'Sure! Here you go:\n```json\n{"a": 1}\n```\nHope that helps.'
    assert llm.extract_json(raw) == '{"a": 1}'


def test_extract_brief_parses_delimited_json():
    text = (
        "All set!\nREADY_TO_BUILD\n---BRIEF---\n"
        '{"business_name": "Testco", "business_type": "shop", "pages": ["index", "about"]}'
        "\n---END BRIEF---"
    )
    brief = extract_brief(text)
    assert brief is not None
    assert brief.business_name == "Testco"
    assert brief.pages == ["index", "about"]


def test_extract_brief_returns_none_on_garbage():
    assert extract_brief("---BRIEF---\nnot json\n---END BRIEF---") is None
    assert extract_brief("no delimiters at all") is None


def test_extract_brief_tolerates_trailing_commas_and_comments():
    # The kind of not-quite-valid JSON free models emit
    text = (
        "---BRIEF---\n{\n"
        '  "business_name": "Meridian Studio", // pilates\n'
        '  "pages": ["index", "classes",],\n'
        "}\n---END BRIEF---"
    )
    brief = extract_brief(text)
    assert brief is not None
    assert brief.business_name == "Meridian Studio"
    assert brief.pages == ["index", "classes"]


def test_finish_never_returns_empty_reply():
    # Empty model output must never become a blank chat bubble
    reply, brief = _finish("")
    assert reply == EMPTY_REPLY_MSG
    assert brief is None
    reply, brief = _finish("   \n  ")
    assert reply == EMPTY_REPLY_MSG


def test_finish_malformed_brief_explains_itself():
    reply, brief = _finish("READY_TO_BUILD\n---BRIEF---\n{bad json,}\n---END BRIEF---")
    assert reply == BRIEF_FORMAT_MSG
    assert brief is None


def test_finish_masks_brief_even_without_sentinel():
    # Weaker models sometimes emit the brief without the READY_TO_BUILD line —
    # the raw JSON must NOT leak into the chat, and the build must still start.
    text = (
        "Great, that's everything!\n"
        "---BRIEF---\n"
        '{"business_name": "North & Ember", "pages": ["index", "menu"]}\n'
        "---END BRIEF---"
    )
    reply, brief = _finish(text)
    assert brief is not None
    assert brief.business_name == "North & Ember"
    assert "---BRIEF---" not in reply
    assert "North & Ember" not in reply  # the JSON is masked
    assert reply == "Great, that's everything!"


def test_parse_recheck_complete_blocks():
    text = (
        "---NOTES---\nFixed two files.\n"
        "---FILE: index.html---\n<html>a</html>\n---END FILE---\n"
        "---FILE: style.css---\nbody{}\n---END FILE---\n"
    )
    notes, fixed, truncated = parse_recheck_output(text, {"index.html", "style.css"})
    assert "Fixed two files." in notes
    assert set(fixed) == {"index.html", "style.css"}
    assert not truncated


def test_parse_recheck_drops_truncated_final_block():
    text = (
        "---NOTES---\nok\n"
        "---FILE: index.html---\n<html>a</html>\n---END FILE---\n"
        "---FILE: style.css---\nbody{  /* cut off mid-fi"
    )
    _, fixed, truncated = parse_recheck_output(text, {"index.html", "style.css"})
    assert set(fixed) == {"index.html"}
    assert truncated  # triggers the second recheck pass


def test_parse_recheck_rejects_unknown_filenames():
    text = "---NOTES---\nok\n---FILE: evil.html---\nx\n---END FILE---"
    _, fixed, _ = parse_recheck_output(text, {"index.html"})
    assert fixed == {}


def test_parse_editor_reply_and_files():
    text = (
        "---REPLY---\nI made the hero bolder on the home page.\n"
        "---FILE: index.html---\n<html>new</html>\n---END FILE---\n"
    )
    reply, changed, truncated = parse_editor_output(text, {"index.html", "style.css"})
    assert reply == "I made the hero bolder on the home page."
    assert changed == {"index.html": "<html>new</html>\n"}
    assert not truncated


def test_parse_editor_allows_new_pages_but_blocks_traversal():
    text = (
        "---REPLY---\nAdded a gallery page.\n"
        "---FILE: Gallery Page---\n<html>g</html>\n---END FILE---\n"
        "---FILE: ../evil.html---\n<html>x</html>\n---END FILE---\n"
        "---FILE: hack.exe---\nbad\n---END FILE---\n"
    )
    _, changed, _ = parse_editor_output(text, {"index.html"})
    assert set(changed) == {"gallery-page.html"}


def test_parse_editor_reply_only_changes_nothing():
    reply, changed, truncated = parse_editor_output(
        "---REPLY---\nThat's already how it looks — nothing to change.", {"index.html"})
    assert "nothing to change" in reply
    assert changed == {}
    assert not truncated


def test_safe_page_filename_guards_windows_reserved_names():
    assert safe_page_filename("con") == "site-con.html"
    assert safe_page_filename("About Us!") == "about-us.html"
    assert safe_page_filename("menu.html") == "menu.html"


def test_clean_name_ports_v1_behavior():
    assert writer.clean_name("Ember & Oak!") == "ember-oak"
    assert writer.clean_name("   ") == "my-website"
    assert writer.clean_name("CON") == "site-con"


def test_inject_above_fold_is_idempotent():
    js = "console.log('hi');"
    once = writer.inject_above_fold(js)
    assert "getBoundingClientRect" in once
    assert writer.inject_above_fold(once) == once
