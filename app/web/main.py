"""Local review UI (PRD sections 20, 38). FastAPI + Jinja2 + vanilla JS, no build step."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import book_dir_for, book_yaml_path, load_book_config
from app.db import db
from app.qc.duplicates import find_similar

ROOT = Path(__file__).resolve().parents[2]
BOOKS_ROOT = ROOT / "books"
TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Book Factory Review")
app.mount("/media", StaticFiles(directory=str(BOOKS_ROOT)), name="media")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _list_book_ids() -> list[str]:
    if not BOOKS_ROOT.exists():
        return []
    return sorted(p.name for p in BOOKS_ROOT.iterdir() if (p / "book.yaml").exists())


def _media_url(book_id: str, relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    return f"/media/{book_id}/{relative_path}"


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"book_ids": _list_book_ids()})


def _dashboard_stats(book_id: str) -> dict:
    book_dir = book_dir_for(ROOT, book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))
    with db.connect(book_dir) as conn:
        assets = db.list_assets(conn)
        specs = db.list_page_specs(conn, book_id)
        specs_by_id = {s["id"]: s for s in specs}

        overall_scores = []
        duplicate_flags = 0
        for a in assets:
            qc = db.latest_qc_result(conn, a["id"])
            if qc and qc["overall_score"] is not None:
                overall_scores.append(qc["overall_score"])
            if qc and qc["duplicate_score"] and qc["duplicate_score"] >= 0.5:
                duplicate_flags += 1

    approved_statuses = ("APPROVED", "IN_PRODUCTION", "FINAL")
    approved = sum(1 for a in assets if a["status"] in approved_statuses)
    needs_review = sum(1 for a in assets if a["status"] == "INGESTED")
    rejected = sum(1 for a in assets if a["status"] == "REJECTED")
    qc_failed = sum(1 for a in assets if a["status"] == "QC_FAILED")
    ingested_spec_ids = {a["page_spec_id"] for a in assets if a["page_spec_id"]}
    generation_needed = sum(1 for s in specs if s["id"] not in ingested_spec_ids)
    avg_qc = round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else None

    approved_elements = {
        specs_by_id[a["page_spec_id"]]["element"]
        for a in assets
        if a["status"] in approved_statuses and a["page_spec_id"] in specs_by_id
    }
    total_elements = {s["element"] for s in specs}
    diversity_pct = round(100 * len(approved_elements) / len(total_elements)) if total_elements else 0

    return {
        "target_pages": config.book.target_pages,
        "approved": approved,
        "needs_review": needs_review,
        "rejected": rejected,
        "qc_failed": qc_failed,
        "generation_needed": generation_needed,
        "avg_qc": avg_qc,
        "duplicate_flags": duplicate_flags,
        "diversity_pct": diversity_pct,
    }


@app.get("/{book_id}")
def dashboard(request: Request, book_id: str):
    stats = _dashboard_stats(book_id)
    return templates.TemplateResponse(
        request, "dashboard.html", {"book_id": book_id, "stats": stats}
    )


@app.get("/{book_id}/review")
def review_next(book_id: str):
    book_dir = book_dir_for(ROOT, book_id)
    with db.connect(book_dir) as conn:
        candidates = db.list_assets(conn, status="INGESTED")
    if not candidates:
        return RedirectResponse(f"/{book_id}?message=nothing_to_review")
    return RedirectResponse(f"/{book_id}/review/{candidates[0]['id']}")


@app.get("/{book_id}/review/{asset_id}")
def review_asset(request: Request, book_id: str, asset_id: str):
    book_dir = book_dir_for(ROOT, book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))
    with db.connect(book_dir) as conn:
        asset = db.get_asset(conn, asset_id)
        if asset is None:
            return RedirectResponse(f"/{book_id}")
        spec = db.get_page_spec(conn, asset["page_spec_id"]) if asset["page_spec_id"] else None
        qc = db.latest_qc_result(conn, asset_id)
        all_specs = db.list_page_specs(conn, book_id)

        approved_phashes = [
            (a["id"], a["phash"]) for a in db.list_assets(conn, status="APPROVED") if a["phash"] and a["id"] != asset_id
        ]
        similar = find_similar(asset["phash"], approved_phashes, config.diversity.duplicate_phash_threshold) if asset["phash"] else []

        queue = [a["id"] for a in db.list_assets(conn, status="INGESTED")]

    if asset_id in queue:
        pos = queue.index(asset_id)
        prev_id = queue[pos - 1] if pos > 0 else None
        next_id = queue[pos + 1] if pos + 1 < len(queue) else None
    else:
        prev_id, next_id = None, (queue[0] if queue else None)

    return templates.TemplateResponse(
        request,
        "review.html",
        {
            "book_id": book_id,
            "asset": asset,
            "spec": spec,
            "qc": qc,
            "image_url": _media_url(book_id, asset["original_path"]),
            "all_specs": all_specs,
            "similar": similar,
            "queue_count": len(queue),
            "prev_id": prev_id,
            "next_id": next_id,
            "unassigned": spec is None,
        },
    )


@app.get("/{book_id}/pages")
def book_pages_view(request: Request, book_id: str):
    book_dir = book_dir_for(ROOT, book_id)
    approved_statuses = ("APPROVED", "IN_PRODUCTION", "FINAL")
    with db.connect(book_dir) as conn:
        assets = [a for a in db.list_assets(conn) if a["status"] in approved_statuses]
        specs_by_id = {s["id"]: s for s in db.list_page_specs(conn, book_id)}
        stored_order = [r["asset_id"] for r in db.list_book_pages(conn, book_id)]

    assets_by_id = {a["id"]: a for a in assets}
    ordered_ids = [aid for aid in stored_order if aid in assets_by_id]
    ordered_ids += [a["id"] for a in assets if a["id"] not in ordered_ids]

    pages = []
    for i, aid in enumerate(ordered_ids, start=1):
        a = assets_by_id[aid]
        spec = specs_by_id.get(a["page_spec_id"])
        full_path = a["normalized_path"] or a["original_path"]
        # Prefer the normalized production image (border, margins, and
        # cropping exactly as they'll print) over the raw AI-generated
        # candidate thumbnail, which can carry its own inconsistent
        # AI-drawn border and doesn't reflect the production pipeline at
        # all once an asset has been processed.
        thumb_path = a["normalized_path"] or a["thumbnail_path"]
        pages.append(
            {
                "asset_id": aid,
                "sequence": i,
                "element": spec["element"] if spec else "?",
                "composition": spec["composition"] if spec else "?",
                "thumbnail_url": _media_url(book_id, thumb_path),
                "full_image_url": _media_url(book_id, full_path),
            }
        )

    interior_pdf = book_dir / "interior" / "interior.pdf"
    return templates.TemplateResponse(
        request,
        "book_pages.html",
        {
            "book_id": book_id,
            "pages": pages,
            "has_manual_order": bool(stored_order),
            "interior_pdf_exists": interior_pdf.exists(),
        },
    )


@app.post("/{book_id}/api/pages/reorder")
async def reorder_pages(request: Request, book_id: str):
    form = await request.form()
    entries = []
    for key, value in form.multi_items():
        if key.startswith("seq_"):
            asset_id = key[len("seq_"):]
            try:
                seq = int(value)
            except ValueError:
                continue
            entries.append((seq, asset_id))
    entries.sort(key=lambda t: t[0])
    ordered_ids = [asset_id for _, asset_id in entries]

    book_dir = book_dir_for(ROOT, book_id)
    with db.connect(book_dir) as conn:
        db.set_manual_book_page_order(conn, book_id, ordered_ids)
    return RedirectResponse(f"/{book_id}/pages", status_code=303)


@app.post("/{book_id}/api/assets/{asset_id}/approve")
def approve(book_id: str, asset_id: str, quality: int = Form(None), complexity: int = Form(None), uniqueness: int = Form(None)):
    book_dir = book_dir_for(ROOT, book_id)
    with db.connect(book_dir) as conn:
        db.update_asset(conn, asset_id, status="APPROVED")
        db.insert_review(conn, asset_id=asset_id, decision="APPROVE", quality=quality, complexity=complexity, uniqueness=uniqueness)
    return RedirectResponse(f"/{book_id}/review", status_code=303)


@app.post("/{book_id}/api/assets/{asset_id}/reject")
def reject(book_id: str, asset_id: str, notes: str = Form(None)):
    book_dir = book_dir_for(ROOT, book_id)
    with db.connect(book_dir) as conn:
        db.update_asset(conn, asset_id, status="REJECTED")
        db.insert_review(conn, asset_id=asset_id, decision="REJECT", notes=notes)
    return RedirectResponse(f"/{book_id}/review", status_code=303)


@app.post("/{book_id}/api/assets/{asset_id}/remove-from-book")
def remove_from_book(book_id: str, asset_id: str):
    """Same effect as reject (asset drops out of the approved set and off
    the Book Order screen), but reachable from Book Order itself and
    redirects back there instead of into the review queue - reject() redirects
    to /review, which is the right place mid-review but a dead end from
    Book Order, where there was previously no way to undo an approval at
    all once a page had already been reviewed."""
    book_dir = book_dir_for(ROOT, book_id)
    with db.connect(book_dir) as conn:
        db.update_asset(conn, asset_id, status="REJECTED")
        db.insert_review(conn, asset_id=asset_id, decision="REJECT", notes="Removed from Book Order screen")
    return RedirectResponse(f"/{book_id}/pages", status_code=303)


@app.post("/{book_id}/api/assets/{asset_id}/regenerate")
def regenerate(book_id: str, asset_id: str, notes: str = Form(None)):
    book_dir = book_dir_for(ROOT, book_id)
    with db.connect(book_dir) as conn:
        asset = db.get_asset(conn, asset_id)
        db.update_asset(conn, asset_id, status="REJECTED")
        db.insert_review(conn, asset_id=asset_id, decision="REGENERATE", notes=notes)
        if asset and asset["page_spec_id"]:
            db.update_page_spec(conn, asset["page_spec_id"], status="PROMPT_READY")
    return RedirectResponse(f"/{book_id}/review", status_code=303)


@app.post("/{book_id}/api/assets/{asset_id}/assign")
def assign(book_id: str, asset_id: str, page_spec_id: str = Form(...)):
    book_dir = book_dir_for(ROOT, book_id)
    with db.connect(book_dir) as conn:
        db.update_asset(conn, asset_id, page_spec_id=page_spec_id)
        db.update_page_spec(conn, page_spec_id, status="INGESTED")
    return RedirectResponse(f"/{book_id}/review/{asset_id}", status_code=303)
