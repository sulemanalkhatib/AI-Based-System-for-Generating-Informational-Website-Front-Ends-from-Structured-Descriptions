"""DB layer: CRUD, cascade deletes, and artifact revision bumps."""

import pytest

import db


@pytest.fixture
async def database(tmp_path):
    await db.init_db(tmp_path / "test.db")
    yield
    await db.close_db()


async def test_session_crud(database):
    session = await db.create_session("My site")
    assert session["title"] == "My site"

    await db.rename_session(session["id"], "Renamed")
    assert (await db.get_session(session["id"]))["title"] == "Renamed"

    await db.set_session_brief(session["id"], {"business_name": "X"})
    listed = await db.list_sessions()
    assert listed[0]["has_brief"] == 1

    await db.delete_session(session["id"])
    assert await db.get_session(session["id"]) is None


async def test_messages_ordering_and_cascade(database):
    session = await db.create_session()
    await db.add_message(session["id"], "user", "one")
    await db.add_message(session["id"], "assistant", "two", agent="interviewer")
    messages = await db.list_messages(session["id"])
    assert [m["content"] for m in messages] == ["one", "two"]
    assert messages[1]["agent"] == "interviewer"

    await db.delete_session(session["id"])
    assert await db.list_messages(session["id"]) == []


async def test_artifact_revisions(database):
    session = await db.create_session()
    build_id = await db.create_build(session["id"], {"business_name": "X"})

    assert await db.write_artifact(build_id, "index.html", "v1") == 1
    assert await db.write_artifact(build_id, "index.html", "v2") == 2
    assert await db.write_artifact(build_id, "style.css", "css") == 1

    latest = await db.get_artifact(build_id, "index.html")
    assert latest["content"] == "v2"
    assert latest["revision"] == 2

    files = {f["filename"]: f for f in await db.list_artifacts(build_id)}
    assert files["index.html"]["revision"] == 2
    assert files["style.css"]["revision"] == 1


async def test_settings_roundtrip(database):
    assert await db.get_settings_json() is None
    await db.put_settings_json({"theme_accent": "#123456"})
    assert (await db.get_settings_json())["theme_accent"] == "#123456"
    await db.put_settings_json({"theme_accent": "#654321"})
    assert (await db.get_settings_json())["theme_accent"] == "#654321"
