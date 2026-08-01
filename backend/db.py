"""Async SQLite layer — one shared aiosqlite connection, WAL mode, hand-written SQL.

A single connection is deliberate: aiosqlite serializes all statements through one
worker thread, so the parallel page builders can write artifacts concurrently
without locking errors. Never open a second write connection.
"""

import json
import uuid

import aiosqlite

import config

_SCHEMA = """
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS sessions (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL DEFAULT 'New website',
  brief_json  TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  role        TEXT NOT NULL,
  agent       TEXT,
  content     TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);

CREATE TABLE IF NOT EXISTS builds (
  id          TEXT PRIMARY KEY,
  session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  status      TEXT NOT NULL DEFAULT 'running',
  brief_json  TEXT,
  copy_json   TEXT,
  design_json TEXT,
  audit_json  TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_builds_session ON builds(session_id, created_at);

CREATE TABLE IF NOT EXISTS artifacts (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  build_id    TEXT NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
  filename    TEXT NOT NULL,
  content     TEXT NOT NULL,
  revision    INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_artifacts_build ON artifacts(build_id, filename, revision);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

_conn: aiosqlite.Connection | None = None


async def init_db(db_path=None) -> None:
    global _conn
    path = db_path or config.DB_PATH
    if hasattr(path, "parent"):
        path.parent.mkdir(parents=True, exist_ok=True)
    _conn = await aiosqlite.connect(path)
    _conn.row_factory = aiosqlite.Row
    await _conn.execute("PRAGMA journal_mode=WAL")
    await _conn.executescript(_SCHEMA)
    await _conn.commit()


async def close_db() -> None:
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


def conn() -> aiosqlite.Connection:
    if _conn is None:
        raise RuntimeError("DB not initialised — call init_db() first")
    return _conn


# ---------------------------------------------------------------- sessions

async def create_session(title: str = "New website") -> dict:
    sid = uuid.uuid4().hex
    await conn().execute("INSERT INTO sessions (id, title) VALUES (?, ?)", (sid, title))
    await conn().commit()
    return await get_session(sid)


async def get_session(session_id: str) -> dict | None:
    cur = await conn().execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def list_sessions() -> list[dict]:
    cur = await conn().execute(
        "SELECT id, title, created_at, updated_at, brief_json IS NOT NULL AS has_brief "
        "FROM sessions ORDER BY updated_at DESC")
    return [dict(r) for r in await cur.fetchall()]


async def rename_session(session_id: str, title: str) -> None:
    await conn().execute(
        "UPDATE sessions SET title = ?, updated_at = datetime('now') WHERE id = ?",
        (title, session_id))
    await conn().commit()


async def touch_session(session_id: str) -> None:
    await conn().execute(
        "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?", (session_id,))
    await conn().commit()


async def set_session_brief(session_id: str, brief: dict) -> None:
    await conn().execute(
        "UPDATE sessions SET brief_json = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(brief), session_id))
    await conn().commit()


async def delete_session(session_id: str) -> None:
    await conn().execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await conn().commit()


# ---------------------------------------------------------------- messages

async def add_message(session_id: str, role: str, content: str, agent: str | None = None) -> int:
    cur = await conn().execute(
        "INSERT INTO messages (session_id, role, agent, content) VALUES (?, ?, ?, ?)",
        (session_id, role, agent, content))
    await conn().execute(
        "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?", (session_id,))
    await conn().commit()
    return cur.lastrowid


async def list_messages(session_id: str) -> list[dict]:
    cur = await conn().execute(
        "SELECT id, role, agent, content, created_at FROM messages "
        "WHERE session_id = ? ORDER BY id", (session_id,))
    return [dict(r) for r in await cur.fetchall()]


# ---------------------------------------------------------------- builds

async def create_build(session_id: str, brief: dict) -> str:
    bid = uuid.uuid4().hex
    await conn().execute(
        "INSERT INTO builds (id, session_id, status, brief_json) VALUES (?, ?, 'running', ?)",
        (bid, session_id, json.dumps(brief)))
    await conn().commit()
    return bid


async def get_build(build_id: str) -> dict | None:
    cur = await conn().execute("SELECT * FROM builds WHERE id = ?", (build_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def list_builds(session_id: str) -> list[dict]:
    cur = await conn().execute(
        "SELECT id, status, created_at FROM builds WHERE session_id = ? ORDER BY created_at DESC",
        (session_id,))
    return [dict(r) for r in await cur.fetchall()]


async def set_build_status(build_id: str, status: str) -> None:
    await conn().execute("UPDATE builds SET status = ? WHERE id = ?", (status, build_id))
    await conn().commit()


async def save_build_specs(build_id: str, copy_json: dict, design_json: dict) -> None:
    await conn().execute(
        "UPDATE builds SET copy_json = ?, design_json = ? WHERE id = ?",
        (json.dumps(copy_json), json.dumps(design_json), build_id))
    await conn().commit()


async def save_build_audit(build_id: str, audit_json: dict) -> None:
    await conn().execute(
        "UPDATE builds SET audit_json = ? WHERE id = ?", (json.dumps(audit_json), build_id))
    await conn().commit()


# ---------------------------------------------------------------- artifacts

async def write_artifact(build_id: str, filename: str, content: str) -> int:
    """Insert the next revision of a file and return its revision number."""
    cur = await conn().execute(
        "SELECT COALESCE(MAX(revision), 0) FROM artifacts WHERE build_id = ? AND filename = ?",
        (build_id, filename))
    (prev,) = await cur.fetchone()
    revision = prev + 1
    await conn().execute(
        "INSERT INTO artifacts (build_id, filename, content, revision) VALUES (?, ?, ?, ?)",
        (build_id, filename, content, revision))
    await conn().commit()
    return revision


async def list_artifacts(build_id: str) -> list[dict]:
    """Latest revision of every file in a build."""
    cur = await conn().execute(
        """
        SELECT a.filename, a.revision, LENGTH(a.content) AS size
        FROM artifacts a
        JOIN (SELECT filename, MAX(revision) AS mr FROM artifacts
              WHERE build_id = ? GROUP BY filename) m
          ON a.filename = m.filename AND a.revision = m.mr
        WHERE a.build_id = ?
        ORDER BY a.filename
        """,
        (build_id, build_id))
    return [dict(r) for r in await cur.fetchall()]


async def get_build_files(build_id: str) -> dict[str, str]:
    """Latest revision of every file, as {filename: content}."""
    files: dict[str, str] = {}
    for meta in await list_artifacts(build_id):
        artifact = await get_artifact(build_id, meta["filename"])
        if artifact:
            files[meta["filename"]] = artifact["content"]
    return files


async def get_artifact(build_id: str, filename: str) -> dict | None:
    cur = await conn().execute(
        "SELECT filename, content, revision FROM artifacts "
        "WHERE build_id = ? AND filename = ? ORDER BY revision DESC LIMIT 1",
        (build_id, filename))
    row = await cur.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------- settings

async def get_settings_json() -> dict | None:
    cur = await conn().execute("SELECT value FROM settings WHERE key = 'app'")
    row = await cur.fetchone()
    return json.loads(row["value"]) if row else None


async def put_settings_json(value: dict) -> None:
    await conn().execute(
        "INSERT INTO settings (key, value) VALUES ('app', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (json.dumps(value),))
    await conn().commit()
