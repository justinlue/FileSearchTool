"""The SQLite name index: build it from (path, name, is_dir) entries, search it by name."""

import fnmatch
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

BATCH = 50_000


@dataclass(frozen=True)
class Hit:
    path: str
    is_dir: bool


@dataclass(frozen=True)
class Result:
    hits: list[Hit]
    total: int


def is_wildcard(query):
    return "*" in query or "?" in query


def build(db_path, entries, on_progress=None):
    """Write a fresh index from entries, then swap it in over any existing one."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_path.with_name(db_path.name + ".tmp")
    tmp.unlink(missing_ok=True)

    con = sqlite3.connect(tmp)
    try:
        con.execute("PRAGMA journal_mode=OFF")
        con.execute("PRAGMA synchronous=OFF")
        con.execute("CREATE TABLE entries (path TEXT, name_fold TEXT, is_dir INTEGER)")
        con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value)")
        count = 0
        batch = []
        for path, name, is_dir in entries:
            batch.append((path, name.casefold(), int(is_dir)))
            if len(batch) >= BATCH:
                con.executemany("INSERT INTO entries VALUES (?, ?, ?)", batch)
                count += len(batch)
                batch.clear()
                if on_progress:
                    on_progress(count)
        con.executemany("INSERT INTO entries VALUES (?, ?, ?)", batch)
        count += len(batch)
        con.execute("INSERT INTO meta VALUES ('built_at', ?)", (time.time(),))
        con.commit()
    finally:
        con.close()
    os.replace(tmp, db_path)
    return count


def built_at(db_path):
    """Unix time the index was built, or None if there is no index."""
    if not Path(db_path).exists():
        return None
    con = sqlite3.connect(db_path)
    try:
        row = con.execute("SELECT value FROM meta WHERE key = 'built_at'").fetchone()
    except sqlite3.DatabaseError:
        return None
    finally:
        con.close()
    return row[0] if row else None


def _glob_escape(text):
    # In SQLite GLOB and fnmatch alike, only [ needs escaping once * and ? are wildcards.
    return text.replace("[", "[[]")


def matches(query, name):
    """The same test search() applies in SQL, for filtering names during a live scan."""
    q, n = query.casefold(), name.casefold()
    if is_wildcard(q):
        return fnmatch.fnmatchcase(n, _glob_escape(q))
    return q in n


def search(db_path, query, limit=50):
    """Case-insensitive name search, ranked exact > prefix > contains, then shorter path."""
    q = query.casefold()
    if is_wildcard(q):
        # Wildcards have no exact/prefix notion; rank by path length alone.
        where, order, q = "name_fold GLOB :q", "", _glob_escape(q)
    else:
        where = "instr(name_fold, :q) > 0"
        order = "CASE WHEN name_fold = :q THEN 0 WHEN substr(name_fold, 1, length(:q)) = :q THEN 1 ELSE 2 END, "
    sql = (
        f"SELECT path, is_dir, COUNT(*) OVER () FROM entries WHERE {where} "
        f"ORDER BY {order}length(path), path LIMIT :limit"
    )
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(sql, {"q": q, "limit": -1 if limit is None else limit}).fetchall()
    finally:
        con.close()
    hits = [Hit(path, bool(is_dir)) for path, is_dir, _ in rows]
    return Result(hits, rows[0][2] if rows else 0)
