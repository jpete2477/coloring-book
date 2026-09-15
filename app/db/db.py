"""Thin sqlite3 wrapper for the book factory (PRD section 15).

Each book gets its own database file at books/<book_id>/metadata/factory.db,
so all tables are implicitly scoped to one book even though they carry a
book_id/page_spec_id column (kept for fidelity to the PRD schema and so a
future cross-book export/report can make sense of a single table dump).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def db_path_for(book_dir: Path) -> Path:
    return book_dir / "metadata" / "factory.db"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect(book_dir: Path) -> Iterator[sqlite3.Connection]:
    path = db_path_for(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(book_dir: Path, *, book_id: str, title: str, config_path: str) -> None:
    with connect(book_dir) as conn:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.execute(
            """
            INSERT INTO books (id, title, version, config_path, created_at, updated_at, status)
            VALUES (?, ?, '0.1', ?, ?, ?, 'PLANNED')
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, updated_at=excluded.updated_at
            """,
            (book_id, title, config_path, now(), now()),
        )


def set_book_status(conn: sqlite3.Connection, book_id: str, status: str) -> None:
    conn.execute(
        "UPDATE books SET status = ?, updated_at = ? WHERE id = ?",
        (status, now(), book_id),
    )


# ---- page_specs -----------------------------------------------------------

def clear_page_specs(conn: sqlite3.Connection, book_id: str) -> None:
    conn.execute("DELETE FROM page_specs WHERE book_id = ?", (book_id,))


def insert_page_spec(
    conn: sqlite3.Connection,
    *,
    id: str,
    book_id: str,
    sequence: int,
    element: str,
    composition: str,
    density: int,
    symmetry: str,
    scale: str,
    border: str,
    prompt: str | None = None,
    status: str = "PLANNED",
) -> None:
    conn.execute(
        """
        INSERT INTO page_specs
            (id, book_id, sequence, element, composition, density, symmetry, scale, border, prompt, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (id, book_id, sequence, element, composition, density, symmetry, scale, border, prompt, status, now()),
    )


def list_page_specs(conn: sqlite3.Connection, book_id: str, status: str | None = None) -> list[sqlite3.Row]:
    if status:
        return conn.execute(
            "SELECT * FROM page_specs WHERE book_id = ? AND status = ? ORDER BY sequence",
            (book_id, status),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM page_specs WHERE book_id = ? ORDER BY sequence", (book_id,)
    ).fetchall()


def get_page_spec(conn: sqlite3.Connection, page_spec_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM page_specs WHERE id = ?", (page_spec_id,)).fetchone()


def update_page_spec(conn: sqlite3.Connection, page_spec_id: str, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE page_specs SET {cols} WHERE id = ?", (*fields.values(), page_spec_id))


# ---- assets -----------------------------------------------------------

def insert_asset(
    conn: sqlite3.Connection,
    *,
    id: str,
    page_spec_id: str | None,
    source_path: str,
    original_path: str,
    width: int | None = None,
    height: int | None = None,
    dpi: int | None = None,
    file_size: int | None = None,
    sha256: str | None = None,
    phash: str | None = None,
    thumbnail_path: str | None = None,
    status: str = "INGESTED",
) -> None:
    conn.execute(
        """
        INSERT INTO assets
            (id, page_spec_id, source_path, original_path, thumbnail_path, width, height, dpi,
             file_size, sha256, phash, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (id, page_spec_id, source_path, original_path, thumbnail_path, width, height, dpi,
         file_size, sha256, phash, status, now()),
    )


def get_asset(conn: sqlite3.Connection, asset_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()


def list_assets(conn: sqlite3.Connection, status: str | None = None) -> list[sqlite3.Row]:
    if status:
        return conn.execute("SELECT * FROM assets WHERE status = ? ORDER BY created_at", (status,)).fetchall()
    return conn.execute("SELECT * FROM assets ORDER BY created_at").fetchall()


def update_asset(conn: sqlite3.Connection, asset_id: str, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE assets SET {cols} WHERE id = ?", (*fields.values(), asset_id))


def find_asset_by_sha256(conn: sqlite3.Connection, sha256: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM assets WHERE sha256 = ?", (sha256,)).fetchone()


# ---- qc_results -----------------------------------------------------------

def insert_qc_result(conn: sqlite3.Connection, *, asset_id: str, **fields) -> None:
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    conn.execute(
        f"INSERT INTO qc_results (asset_id, {cols}, created_at) VALUES (?, {placeholders}, ?)",
        (asset_id, *fields.values(), now()),
    )


def latest_qc_result(conn: sqlite3.Connection, asset_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM qc_results WHERE asset_id = ? ORDER BY id DESC LIMIT 1", (asset_id,)
    ).fetchone()


# ---- reviews -----------------------------------------------------------

def insert_review(
    conn: sqlite3.Connection,
    *,
    asset_id: str,
    decision: str,
    quality: int | None = None,
    complexity: int | None = None,
    uniqueness: int | None = None,
    notes: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO reviews (asset_id, decision, quality, complexity, uniqueness, notes, reviewed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (asset_id, decision, quality, complexity, uniqueness, notes, now()),
    )


# ---- book_pages -----------------------------------------------------------

def clear_book_pages(conn: sqlite3.Connection, book_id: str) -> None:
    conn.execute("DELETE FROM book_pages WHERE book_id = ?", (book_id,))


def insert_book_page(
    conn: sqlite3.Connection, *, book_id: str, asset_id: str, final_sequence: int, page_role: str = "interior"
) -> None:
    conn.execute(
        "INSERT INTO book_pages (book_id, asset_id, final_sequence, page_role, status) VALUES (?, ?, ?, ?, 'ORDERED')",
        (book_id, asset_id, final_sequence, page_role),
    )


def list_book_pages(conn: sqlite3.Connection, book_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM book_pages WHERE book_id = ? ORDER BY final_sequence", (book_id,)
    ).fetchall()


def set_manual_book_page_order(conn: sqlite3.Connection, book_id: str, ordered_asset_ids: list[str]) -> None:
    """Overwrites book_pages with a user-chosen order (from the web UI's
    reorder screen). `build` prefers this over auto-ordering when it already
    covers every current IN_PRODUCTION/FINAL asset."""
    clear_book_pages(conn, book_id)
    for seq, asset_id in enumerate(ordered_asset_ids, start=1):
        insert_book_page(conn, book_id=book_id, asset_id=asset_id, final_sequence=seq)


APPROVED_STATUSES = ("APPROVED", "IN_PRODUCTION", "FINAL")


def page_review_statuses(conn: sqlite3.Connection, book_id: str) -> dict[str, str]:
    """One of NOT_GENERATED / NEEDS_REVIEW / APPROVED / REJECTED per page_spec_id,
    based on the best-status asset currently assigned to it. Lets prompt
    manifests show review progress so already-decided pages aren't re-run."""
    by_page: dict[str, list[sqlite3.Row]] = {}
    for a in list_assets(conn):
        if a["page_spec_id"]:
            by_page.setdefault(a["page_spec_id"], []).append(a)

    statuses: dict[str, str] = {}
    for spec in list_page_specs(conn, book_id):
        page_assets = by_page.get(spec["id"], [])
        if any(a["status"] in APPROVED_STATUSES for a in page_assets):
            statuses[spec["id"]] = "APPROVED"
        elif any(a["status"] == "INGESTED" for a in page_assets):
            statuses[spec["id"]] = "NEEDS_REVIEW"
        elif page_assets:
            statuses[spec["id"]] = "REJECTED"
        else:
            statuses[spec["id"]] = "NOT_GENERATED"
    return statuses
