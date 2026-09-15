from pathlib import Path

from app.db import db


def test_init_and_page_spec_lifecycle(tmp_path):
    book_dir: Path = tmp_path / "books" / "demo"
    db.init_db(book_dir, book_id="demo", title="Demo", config_path="book.yaml")

    with db.connect(book_dir) as conn:
        db.insert_page_spec(
            conn, id="D001-001", book_id="demo", sequence=1, element="flower",
            composition="organic_all_over", density=4, symmetry="loose", scale="mixed",
            border="enclosed border", status="PLANNED",
        )
        specs = db.list_page_specs(conn, "demo")
        assert len(specs) == 1
        assert specs[0]["status"] == "PLANNED"

        db.update_page_spec(conn, "D001-001", status="PROMPT_READY", prompt="a prompt")
        spec = db.get_page_spec(conn, "D001-001")
        assert spec["status"] == "PROMPT_READY"
        assert spec["prompt"] == "a prompt"


def test_asset_status_transitions(tmp_path):
    book_dir: Path = tmp_path / "books" / "demo"
    db.init_db(book_dir, book_id="demo", title="Demo", config_path="book.yaml")

    with db.connect(book_dir) as conn:
        db.insert_page_spec(
            conn, id="D001-001", book_id="demo", sequence=1, element="flower",
            composition="organic_all_over", density=4, symmetry="loose", scale="mixed",
            border="enclosed border",
        )
        db.insert_asset(
            conn, id="D001-001-C01", page_spec_id="D001-001", source_path="x.png",
            original_path="originals/x.png", sha256="abc",
        )
        asset = db.get_asset(conn, "D001-001-C01")
        assert asset["status"] == "INGESTED"

        for next_status in ["APPROVED", "IN_PRODUCTION", "FINAL"]:
            db.update_asset(conn, "D001-001-C01", status=next_status)
            asset = db.get_asset(conn, "D001-001-C01")
            assert asset["status"] == next_status


def test_find_asset_by_sha256_detects_exact_duplicate(tmp_path):
    book_dir: Path = tmp_path / "books" / "demo"
    db.init_db(book_dir, book_id="demo", title="Demo", config_path="book.yaml")

    with db.connect(book_dir) as conn:
        db.insert_asset(conn, id="A1", page_spec_id=None, source_path="a.png", original_path="originals/a.png", sha256="same-hash")
        found = db.find_asset_by_sha256(conn, "same-hash")
        assert found is not None
        assert found["id"] == "A1"
        assert db.find_asset_by_sha256(conn, "other-hash") is None


def test_manual_book_page_order_round_trips(tmp_path):
    book_dir: Path = tmp_path / "books" / "demo"
    db.init_db(book_dir, book_id="demo", title="Demo", config_path="book.yaml")

    with db.connect(book_dir) as conn:
        for asset_id in ["a", "b", "c"]:
            db.insert_asset(conn, id=asset_id, page_spec_id=None, source_path=f"{asset_id}.png", original_path=f"originals/{asset_id}.png")

        db.set_manual_book_page_order(conn, "demo", ["c", "a", "b"])
        pages = db.list_book_pages(conn, "demo")
        assert [p["asset_id"] for p in pages] == ["c", "a", "b"]
        assert [p["final_sequence"] for p in pages] == [1, 2, 3]

        # Saving a new order replaces the old one rather than appending.
        db.set_manual_book_page_order(conn, "demo", ["b", "c"])
        pages = db.list_book_pages(conn, "demo")
        assert [p["asset_id"] for p in pages] == ["b", "c"]


def test_page_review_statuses_reflects_asset_state(tmp_path):
    book_dir: Path = tmp_path / "books" / "demo"
    db.init_db(book_dir, book_id="demo", title="Demo", config_path="book.yaml")

    with db.connect(book_dir) as conn:
        for i, spec_id in enumerate(["D001-001", "D001-002", "D001-003", "D001-004"], start=1):
            db.insert_page_spec(
                conn, id=spec_id, book_id="demo", sequence=i, element="flower",
                composition="organic_all_over", density=4, symmetry="loose", scale="mixed",
                border="enclosed border",
            )
        db.insert_asset(conn, id="approved-asset", page_spec_id="D001-001", source_path="a.png", original_path="originals/a.png")
        db.update_asset(conn, "approved-asset", status="APPROVED")
        db.insert_asset(conn, id="pending-asset", page_spec_id="D001-002", source_path="b.png", original_path="originals/b.png")
        db.insert_asset(conn, id="rejected-asset", page_spec_id="D001-003", source_path="c.png", original_path="originals/c.png")
        db.update_asset(conn, "rejected-asset", status="REJECTED")
        # D001-004 gets no asset at all.

        statuses = db.page_review_statuses(conn, "demo")
        assert statuses["D001-001"] == "APPROVED"
        assert statuses["D001-002"] == "NEEDS_REVIEW"
        assert statuses["D001-003"] == "REJECTED"
        assert statuses["D001-004"] == "NOT_GENERATED"
