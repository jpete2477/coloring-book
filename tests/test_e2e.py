"""End-to-end pipeline test on a tiny 5-page synthetic book (PRD section 48).

Drives the same functions the CLI commands wrap, against an isolated
tmp_path book directory, standing in for real Midjourney downloads with
locally generated placeholder line-art images.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw
from PIL.PngImagePlugin import PngInfo

from app.config import BookConfig
from app.db import db
from app.images.normalize import normalize_image
from app.ingestion.ingest import ingest_inbox
from app.ordering.order import OrderItem, balanced_order
from app.pdf.build import build_interior_pdf
from app.pdf.validate import validate_interior_pdf
from app.planning.planner import plan_pages, summarize_plan
from app.planning.prompts import export_prompt_manifest, generate_prompts


def make_config(book_dir: Path) -> BookConfig:
    return BookConfig.model_validate(
        {
            "book": {"id": "demo", "title": "Demo Book", "author": "Test Author", "target_pages": 5, "bleed": False},
            "base_elements": ["flower", "wheel", "bird"],
            "compositions": ["organic_all_over", "nested"],
            "constraints": ["no text", "no color", "no traditional mandala"],
            "diversity": {"max_same_element_count": 3, "max_same_composition_count": 4, "candidates_per_page": 1},
            "production": {"dpi": 300, "target_width_inches": 8.5, "target_height_inches": 11, "threshold": True, "border": True, "margin_inches": 0.3},
            "front_matter": {"pages": ["title_page", "belongs_to_page"]},
            "back_matter": {"pages": []},
        }
    )


def make_placeholder(path: Path, description: str, seed: int) -> None:
    """Each call draws a distinct pattern so pages aren't flagged as duplicates."""
    import random

    rng = random.Random(seed)
    img = Image.new("RGB", (1400, 1800), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 1300, 1700], outline="black", width=6)
    for _ in range(6):
        cx, cy = rng.randint(200, 1200), rng.randint(200, 1600)
        r = rng.randint(80, 300)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", width=4)
    info = PngInfo()
    info.add_text("Description", description)
    img.save(path, "PNG", dpi=(300, 300), pnginfo=info)


def test_full_pipeline_produces_valid_kdp_pdf(tmp_path):
    book_dir = tmp_path / "books" / "demo"
    for sub in ["inbox", "originals", "candidates", "production", "interior", "metadata"]:
        (book_dir / sub).mkdir(parents=True, exist_ok=True)

    config = make_config(book_dir)
    db.init_db(book_dir, book_id="demo", title=config.book.title, config_path="book.yaml")

    # Plan
    pages = plan_pages(config, seed=3)
    assert len(pages) == 5
    report = summarize_plan(pages)
    assert report.total_pages == 5

    with db.connect(book_dir) as conn:
        db.clear_page_specs(conn, "demo")
        for p in pages:
            db.insert_page_spec(
                conn, id=p.id, book_id="demo", sequence=p.sequence, element=p.element,
                composition=p.composition, density=p.density, symmetry=p.symmetry,
                scale=p.scale, border=p.border,
            )

    # Prompts
    rendered = generate_prompts(config, pages)
    assert len(rendered) == 5
    with db.connect(book_dir) as conn:
        for page_id, prompt in rendered.items():
            db.update_page_spec(conn, page_id, prompt=prompt, status="PROMPT_READY")
    csv_path, md_path = export_prompt_manifest(book_dir, pages, rendered)
    assert csv_path.exists() and md_path.exists()

    # Simulate Midjourney downloads landing in inbox/, one per planned page,
    # with embedded metadata so ingestion can auto-assign them.
    for i, p in enumerate(pages):
        make_placeholder(book_dir / "inbox" / f"{p.id}.png", f"{p.element} {p.composition}", seed=i)

    summary = ingest_inbox(book_dir, "demo", config)
    assert summary.imported == 5
    assert summary.failed == 0

    with db.connect(book_dir) as conn:
        assets = db.list_assets(conn)
        assert len(assets) == 5
        assigned = [a for a in assets if a["page_spec_id"]]
        assert len(assigned) == 5, "all candidates should auto-assign via embedded description metadata"

        # Review: approve everything (simulates keyboard-shortcut review UI decisions).
        for a in assets:
            db.update_asset(conn, a["id"], status="APPROVED")
            db.insert_review(conn, asset_id=a["id"], decision="APPROVE", quality=4, complexity=4, uniqueness=4)

    # Process: normalize into production/
    with db.connect(book_dir) as conn:
        approved = db.list_assets(conn, status="APPROVED")
        for a in approved:
            src = next((book_dir / "candidates").glob(f"{a['id']}.*"))
            dest = book_dir / "production" / f"{a['id']}.png"
            geometry = normalize_image(src, dest, config)
            db.update_asset(conn, a["id"], normalized_path=str(dest.relative_to(book_dir)),
                             width=geometry.page_width_px, height=geometry.page_height_px,
                             dpi=geometry.dpi, status="IN_PRODUCTION")

    # Order + build
    with db.connect(book_dir) as conn:
        in_production = db.list_assets(conn, status="IN_PRODUCTION")
        items = []
        normalized_paths = {}
        for a in in_production:
            spec = db.get_page_spec(conn, a["page_spec_id"])
            items.append(OrderItem(a["id"], spec["element"], spec["composition"], spec["density"]))
            normalized_paths[a["id"]] = book_dir / a["normalized_path"]

        ordered = balanced_order(items, config.ordering)
        db.clear_book_pages(conn, "demo")
        for seq, item in enumerate(ordered, start=1):
            db.insert_book_page(conn, book_id="demo", asset_id=item.asset_id, final_sequence=seq)

        ordered_pages = [{"asset_id": it.asset_id, "normalized_path": normalized_paths[it.asset_id]} for it in ordered]
        pdf_path = build_interior_pdf(book_dir, config, ordered_pages)
        for it in ordered:
            db.update_asset(conn, it.asset_id, status="FINAL")

    assert pdf_path.exists()

    # Validate
    with db.connect(book_dir) as conn:
        expected_pages = len(db.list_book_pages(conn, "demo"))
    report = validate_interior_pdf(pdf_path, config, expected_pages)
    assert report.passed, report.render()

    import pymupdf
    doc = pymupdf.open(pdf_path)
    expected_total = len(config.front_matter.pages) + 5 + len(config.back_matter.pages)
    assert doc.page_count == expected_total
    doc.close()
