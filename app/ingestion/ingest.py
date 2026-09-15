"""Candidate ingestion (PRD sections 13, 14): one-shot scan of inbox/.

Never overwrites or deletes the original bytes: each inbox file is copied
into originals/ (pristine) and candidates/ (working copy for QC/review)
before being removed from inbox, so re-running ingest is idempotent.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from app.config import BookConfig
from app.db import db
from app.ingestion.metadata import extract_embedded_text, match_page_spec
from app.planning.ids import candidate_asset_id, unassigned_asset_id
from app.qc.basic import run_basic_qc
from app.qc.duplicates import find_similar, phash_of, sha256_of

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
THUMBNAIL_MAX_PX = 400


@dataclass
class IngestSummary:
    imported: int = 0
    passed_qc: int = 0
    flagged: int = 0
    failed: int = 0


def _next_candidate_number(conn, page_spec_id: str) -> int:
    existing = conn.execute(
        "SELECT COUNT(*) AS n FROM assets WHERE page_spec_id = ?", (page_spec_id,)
    ).fetchone()
    return (existing["n"] or 0) + 1


def _next_unassigned_counter(conn, date_str: str) -> int:
    existing = conn.execute(
        "SELECT COUNT(*) AS n FROM assets WHERE id LIKE ?", (f"UNASSIGNED-{date_str}-%",)
    ).fetchone()
    return (existing["n"] or 0) + 1


def _make_thumbnail(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as img:
        img = img.convert("RGB")
        img.thumbnail((THUMBNAIL_MAX_PX, THUMBNAIL_MAX_PX))
        img.save(dest, "JPEG", quality=85)


def ingest_inbox(book_dir: Path, book_id: str, config: BookConfig) -> IngestSummary:
    inbox = book_dir / "inbox"
    originals_dir = book_dir / "originals"
    candidates_dir = book_dir / "candidates"
    thumbs_dir = candidates_dir / "thumbnails"
    summary = IngestSummary()

    files = sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    if not files:
        return summary

    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    with db.connect(book_dir) as conn:
        page_specs = db.list_page_specs(conn, book_id)
        approved_phashes = [
            (a["id"], a["phash"]) for a in db.list_assets(conn, status="APPROVED") if a["phash"]
        ]

        for src in files:
            embedded_text = extract_embedded_text(src)
            page_spec_id, _score = match_page_spec(embedded_text, page_specs)

            if page_spec_id:
                candidate_no = _next_candidate_number(conn, page_spec_id)
                asset_id = candidate_asset_id(page_spec_id, candidate_no)
            else:
                counter = _next_unassigned_counter(conn, today)
                asset_id = unassigned_asset_id(today, counter)

            ext = src.suffix.lower()
            original_dest = originals_dir / f"{asset_id}{ext}"
            candidate_dest = candidates_dir / f"{asset_id}{ext}"
            thumb_dest = thumbs_dir / f"{asset_id}.jpg"

            shutil.copy2(src, original_dest)
            shutil.copy2(src, candidate_dest)
            try:
                _make_thumbnail(src, thumb_dest)
            except Exception:
                thumb_dest = None

            qc = run_basic_qc(candidate_dest)
            sha256 = sha256_of(candidate_dest)
            phash = None
            duplicate_of = None
            similar_notes = []
            if qc.ok:
                try:
                    phash = phash_of(candidate_dest)
                except Exception:
                    phash = None

            existing_by_hash = db.find_asset_by_sha256(conn, sha256) if qc.ok else None
            if existing_by_hash is not None:
                duplicate_of = existing_by_hash["id"]
                similar_notes.append(f"exact duplicate of {duplicate_of}")

            if phash and not duplicate_of:
                hits = find_similar(phash, approved_phashes, config.diversity.duplicate_phash_threshold)
                if hits:
                    similar_notes.append(
                        "; ".join(f"likely similar to {aid} (distance {d})" for aid, d in hits[:3])
                    )

            status = "QC_FAILED" if not qc.ok else "INGESTED"

            db.insert_asset(
                conn,
                id=asset_id,
                page_spec_id=page_spec_id,
                source_path=str(src.name),
                original_path=str(original_dest.relative_to(book_dir)),
                width=qc.width or None,
                height=qc.height or None,
                dpi=qc.dpi,
                file_size=candidate_dest.stat().st_size,
                sha256=sha256,
                phash=phash,
                thumbnail_path=str(thumb_dest.relative_to(book_dir)) if thumb_dest else None,
                status=status,
            )

            duplicate_score = 1.0 if duplicate_of else (0.5 if similar_notes else 0.0)
            notes = "; ".join(qc.notes + similar_notes) or None
            db.insert_qc_result(
                conn,
                asset_id=asset_id,
                resolution_score=qc.resolution_score,
                line_art_score=None,
                text_detected=None,
                gray_detected=int(qc.gray_detected),
                color_detected=int(qc.color_detected),
                black_fill_score=qc.black_fill_score,
                edge_quality_score=None,
                duplicate_score=duplicate_score,
                overall_score=qc.overall_score,
                machine_decision=qc.machine_decision,
                notes=notes,
            )

            if page_spec_id:
                db.update_page_spec(conn, page_spec_id, status="INGESTED")

            src.unlink()

            summary.imported += 1
            if status == "QC_FAILED":
                summary.failed += 1
            elif qc.machine_decision == "flag" or similar_notes:
                summary.flagged += 1
            else:
                summary.passed_qc += 1

    return summary
