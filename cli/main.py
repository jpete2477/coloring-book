from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import typer

from app.config import book_dir_for, book_yaml_path, load_book_config
from app.db import db
from app.ingestion.files import find_candidate_file
from app.ingestion.ingest import ingest_inbox
from app.images.normalize import normalize_image
from app.ordering.order import OrderItem, balanced_order
from app.pdf.build import build_interior_pdf
from app.pdf.cover import CoverArtMissing, build_cover_pdf
from app.pdf.validate import validate_interior_pdf
from app.planning import cover_prompts as cover_prompt_gen
from app.planning import prompts as prompt_gen
from app.planning.book_spec import load_book_spec
from app.planning.planner import plan_pages, summarize_plan
from app.planning.scaffold import render_book_yaml, render_book_yaml_from_spec
from app.qc.basic import run_basic_qc
from app.qc.duplicates import phash_of, sha256_of

ROOT = Path(__file__).resolve().parents[1]

app = typer.Typer(help="Local production pipeline for generative adult coloring books.")


def _book_dir(book_id: str) -> Path:
    d = book_dir_for(ROOT, book_id)
    if not d.exists():
        typer.secho(f"Book '{book_id}' not found at {d}. Run 'bookfactory init {book_id}' first.", fg="red")
        raise typer.Exit(1)
    return d


@app.command()
def init(
    book_id: str,
    title: str = typer.Option(None, help="Book title. Defaults to a title-cased version of book_id."),
    author: str = typer.Option("", help="Author name for front matter."),
    target_pages: int = typer.Option(40, help="Target number of interior pages."),
    spec: Path = typer.Option(
        None, "--spec", help="Path to a book.json spec - drives style/theme/border/elements consistently."
    ),
):
    """Scaffold a new book: directories, book.yaml, and its database."""
    book_dir = book_dir_for(ROOT, book_id)
    for sub in [
        "style", "inbox", "originals", "candidates", "approved", "rejected",
        "production", "previews", "metadata", "interior", "cover",
    ]:
        (book_dir / sub).mkdir(parents=True, exist_ok=True)

    yaml_path = book_yaml_path(ROOT, book_id)
    if yaml_path.exists():
        typer.secho(f"book.yaml already exists at {yaml_path}, leaving it in place.", fg="yellow")
    elif spec is not None:
        book_spec = load_book_spec(spec)
        resolved_title = title or book_id.replace("_", " ").title()
        yaml_path.write_text(render_book_yaml_from_spec(book_id=book_id, title=resolved_title, spec=book_spec))
        typer.secho(f"Wrote {yaml_path} (from {spec})", fg="green")
        if book_spec.create_cover:
            typer.echo(f"create_cover is true - run 'bookfactory cover-prompts {book_id}' after planning.")
    else:
        resolved_title = title or book_id.replace("_", " ").title()
        yaml_path.write_text(
            render_book_yaml(book_id=book_id, title=resolved_title, author=author, target_pages=target_pages)
        )
        typer.secho(f"Wrote {yaml_path}", fg="green")

    db.init_db(book_dir, book_id=book_id, title=title or book_id, config_path=str(yaml_path))
    typer.secho(f"Initialized book '{book_id}' at {book_dir}", fg="green")


@app.command()
def plan(book_id: str, seed: int = typer.Option(None, help="Random seed for reproducible planning.")):
    """Generate diverse page specifications from book.yaml."""
    book_dir = _book_dir(book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))
    pages = plan_pages(config, seed=seed)
    report = summarize_plan(pages)

    with db.connect(book_dir) as conn:
        db.clear_page_specs(conn, book_id)
        for p in pages:
            db.insert_page_spec(
                conn,
                id=p.id,
                book_id=book_id,
                sequence=p.sequence,
                element=p.element,
                composition=p.composition,
                density=p.density,
                symmetry=p.symmetry,
                scale=p.scale,
                border=p.border,
                status="PLANNED",
            )
        db.set_book_status(conn, book_id, "PLANNED")

    typer.secho(f"Created {report.total_pages} page specifications.", fg="green")
    typer.echo(f"{report.unique_combinations} unique element/composition combinations.")
    typer.echo(f"{report.duplicate_combinations} duplicate combinations.")


@app.command()
def prompts(book_id: str, repeat: int = typer.Option(1, help="Midjourney --repeat value to append (1 = omit).")):
    """Generate copy-ready prompts from the planned pages, for Midjourney and
    for other tools (Gemini, Civitai's generator, etc.) alike."""
    book_dir = _book_dir(book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))

    with db.connect(book_dir) as conn:
        rows = db.list_page_specs(conn, book_id)
        if not rows:
            typer.secho(f"No page specifications found. Run 'bookfactory plan {book_id}' first.", fg="red")
            raise typer.Exit(1)

        from app.planning.planner import PlannedPage

        pages = [
            PlannedPage(
                id=r["id"], sequence=r["sequence"], element=r["element"], composition=r["composition"],
                density=r["density"], symmetry=r["symmetry"], scale=r["scale"], border=r["border"],
                variation_seed=0,
            )
            for r in rows
        ]
        generic_prompts = prompt_gen.generate_prompts(config, pages, provider="generic")
        for page_id, prompt_text in generic_prompts.items():
            db.update_page_spec(conn, page_id, prompt=prompt_text, status="PROMPT_READY")
        db.set_book_status(conn, book_id, "PROMPT_READY")
        statuses = db.page_review_statuses(conn, book_id)

    mj_prompts = prompt_gen.generate_prompts(config, pages, provider="midjourney")
    mj_csv, mj_md = prompt_gen.export_prompt_manifest(
        book_dir, pages, mj_prompts, repeat=repeat, basename="prompts_midjourney", statuses=statuses
    )
    generic_csv, generic_md = prompt_gen.export_prompt_manifest(
        book_dir, pages, generic_prompts, basename="prompts_generic", statuses=statuses
    )

    approved = sum(1 for s in statuses.values() if s == "APPROVED")
    pending = sum(1 for s in statuses.values() if s == "NEEDS_REVIEW")
    typer.secho("Created:", fg="green")
    typer.echo(f"  {mj_csv}  (Midjourney - includes --ar/--stylize/--style raw)")
    typer.echo(f"  {mj_md}")
    typer.echo(f"  {generic_csv}  (Gemini, Civitai, or any other tool - plain text, no MJ flags)")
    typer.echo(f"  {generic_md}")
    typer.echo("")
    typer.echo(f"Progress: {approved} approved, {pending} awaiting review, {len(pages) - approved - pending} not yet generated")
    typer.echo("Each manifest marks every page's status, so already-decided pages are easy to skip.")
    typer.echo("")
    typer.echo("Generate these prompts in your chosen tool, then drop downloads into:")
    typer.echo(f"  {book_dir / 'inbox'}")
    typer.echo(f"Then run: bookfactory ingest {book_id}")


@app.command()
def ingest(book_id: str):
    """Scan inbox/ for new candidate images and run ingestion + basic QC."""
    book_dir = _book_dir(book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))
    summary = ingest_inbox(book_dir, book_id, config)
    if summary.imported == 0:
        typer.secho("No new files found in inbox/.", fg="yellow")
        return
    typer.secho(f"Imported {summary.imported} candidates.", fg="green")
    typer.echo(f"{summary.passed_qc} passed basic QC.")
    typer.echo(f"{summary.flagged} flagged.")
    if summary.failed:
        typer.echo(f"{summary.failed} failed QC.")


@app.command()
def qc(book_id: str):
    """Re-run basic QC over existing candidate assets without re-ingesting."""
    book_dir = _book_dir(book_id)
    checked = 0
    with db.connect(book_dir) as conn:
        for asset in db.list_assets(conn):
            path = find_candidate_file(book_dir, asset["id"])
            if not path:
                continue
            result = run_basic_qc(path)
            db.insert_qc_result(
                conn,
                asset_id=asset["id"],
                resolution_score=result.resolution_score,
                line_art_score=None,
                text_detected=None,
                gray_detected=int(result.gray_detected),
                color_detected=int(result.color_detected),
                black_fill_score=result.black_fill_score,
                edge_quality_score=None,
                duplicate_score=None,
                overall_score=result.overall_score,
                machine_decision=result.machine_decision,
                notes="; ".join(result.notes) or None,
            )
            if not result.ok and asset["status"] not in ("APPROVED", "IN_PRODUCTION", "FINAL"):
                db.update_asset(conn, asset["id"], status="QC_FAILED")
            checked += 1
    typer.secho(f"Re-ran QC on {checked} assets.", fg="green")


@app.command()
def process(book_id: str):
    """Normalize all APPROVED assets into production/ (PRD section 21-22)."""
    book_dir = _book_dir(book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))
    production_dir = book_dir / "production"
    processed = 0
    with db.connect(book_dir) as conn:
        for asset in db.list_assets(conn, status="APPROVED"):
            src = find_candidate_file(book_dir, asset["id"])
            if not src:
                typer.secho(f"Skipping {asset['id']}: no candidate file found.", fg="yellow")
                continue
            dest = production_dir / f"{asset['id']}.png"
            geometry = normalize_image(src, dest, config)
            db.update_asset(
                conn,
                asset["id"],
                normalized_path=str(dest.relative_to(book_dir)),
                width=geometry.page_width_px,
                height=geometry.page_height_px,
                dpi=geometry.dpi,
                status="IN_PRODUCTION",
            )
            processed += 1
    typer.secho(f"Normalized {processed} approved pages into production/.", fg="green")


@app.command()
def build(book_id: str, preview: bool = typer.Option(False, help="Also write interior-preview.pdf.")):
    """Order approved/processed pages and assemble the interior PDF (PRD sections 24-27)."""
    book_dir = _book_dir(book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))

    with db.connect(book_dir) as conn:
        # FINAL, not just IN_PRODUCTION, so re-running build (e.g. after saving
        # a manual order) works instead of finding nothing on the second pass.
        in_production = [a for a in db.list_assets(conn) if a["status"] in ("IN_PRODUCTION", "FINAL")]
        if not in_production:
            typer.secho(
                f"No pages in production. Approve pages in the review UI, then run 'bookfactory process {book_id}'.",
                fg="red",
            )
            raise typer.Exit(1)

        items = []
        normalized_paths = {}
        for asset in in_production:
            spec = db.get_page_spec(conn, asset["page_spec_id"]) if asset["page_spec_id"] else None
            items.append(
                OrderItem(
                    asset_id=asset["id"],
                    element=spec["element"] if spec else "unknown",
                    composition=spec["composition"] if spec else "unknown",
                    density=spec["density"] if spec else 3,
                )
            )
            normalized_paths[asset["id"]] = book_dir / asset["normalized_path"]

        current_ids = {item.asset_id for item in items}
        manual_order = [r["asset_id"] for r in db.list_book_pages(conn, book_id)]
        items_by_id = {item.asset_id: item for item in items}

        if manual_order and set(manual_order) == current_ids:
            ordered = [items_by_id[aid] for aid in manual_order]
            typer.secho("Using the manual order saved in the review UI's Book Order screen.", fg="cyan")
        else:
            ordered = balanced_order(items, config.ordering)
            db.clear_book_pages(conn, book_id)
            for seq, item in enumerate(ordered, start=1):
                db.insert_book_page(conn, book_id=book_id, asset_id=item.asset_id, final_sequence=seq)

        ordered_pages = [
            {"asset_id": item.asset_id, "normalized_path": normalized_paths[item.asset_id]} for item in ordered
        ]

        out_path = build_interior_pdf(book_dir, config, ordered_pages, preview=False)
        if preview:
            build_interior_pdf(book_dir, config, ordered_pages, preview=True)

        for item in ordered:
            db.update_asset(conn, item.asset_id, status="FINAL")
        db.set_book_status(conn, book_id, "IN_PRODUCTION")

    typer.secho(f"Built {out_path} with {len(ordered)} interior pages.", fg="green")


@app.command()
def validate(book_id: str):
    """Run the KDP validation report (PRD section 29)."""
    book_dir = _book_dir(book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))
    with db.connect(book_dir) as conn:
        expected_pages = len(db.list_book_pages(conn, book_id))
    pdf_path = book_dir / "interior" / "interior.pdf"
    report = validate_interior_pdf(pdf_path, config, expected_pages)
    typer.echo(report.render())
    if not report.passed:
        raise typer.Exit(1)


@app.command()
def cover_prompts(book_id: str):
    """Generate front/back cover art prompts (PRD section 28). Cover art is
    full color and carries no text - the pipeline draws title/author text
    afterward with build-cover."""
    book_dir = _book_dir(book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))
    mj_path = cover_prompt_gen.export_cover_prompt_manifest(book_dir, config, provider="midjourney")
    generic_path = cover_prompt_gen.export_cover_prompt_manifest(book_dir, config, provider="generic")
    typer.secho("Created:", fg="green")
    typer.echo(f"  {mj_path}")
    typer.echo(f"  {generic_path}")
    typer.echo("")
    typer.echo("Generate front and back cover art, then save it as:")
    typer.echo(f"  {book_dir / 'cover' / 'front_raw.png'}  (or .jpg/.jpeg/.webp)")
    typer.echo(f"  {book_dir / 'cover' / 'back_raw.png'}")
    typer.echo(f"Then run: bookfactory build-cover {book_id}")


@app.command()
def build_cover(book_id: str):
    """Assemble the full KDP wraparound cover PDF (back + spine + front)
    from cover/front_raw.* and cover/back_raw.*, sized from the current
    interior page count."""
    book_dir = _book_dir(book_id)
    config = load_book_config(book_yaml_path(ROOT, book_id))
    interior_pdf_path = book_dir / "interior" / "interior.pdf"
    if not interior_pdf_path.exists():
        typer.secho(
            f"No interior.pdf yet - run 'bookfactory build {book_id}' at least once first "
            "so the spine width can be computed from the real, physical printed page count.",
            fg="red",
        )
        raise typer.Exit(1)
    # Spine thickness depends on every physical sheet that prints - front/back
    # matter and any recto_only blank filler pages included, not just the
    # count of images - so read it straight from the built interior.pdf
    # rather than the logical image count in book_pages.
    with fitz.open(interior_pdf_path) as doc:
        page_count = doc.page_count
    with db.connect(book_dir) as conn:
        image_count = len(db.list_book_pages(conn, book_id))

    try:
        out_path, geometry = build_cover_pdf(book_dir, config, page_count)
    except CoverArtMissing as e:
        typer.secho(str(e), fg="red")
        typer.echo(f"Run 'bookfactory cover-prompts {book_id}' if you haven't generated cover art yet.")
        raise typer.Exit(1)

    typer.secho(f"Built {out_path}", fg="green")
    typer.echo(
        f"Spine width: {geometry.spine_width_in:.4f}in (from {page_count} physical interior pages, "
        f"{image_count} of them images) — "
        f"{'wide enough for' if geometry.spine_text_fits else 'too narrow for legible'} spine title text."
    )
    if config.cover_text.enabled:
        typer.echo("Title/subtitle/author/spine/back-description text was drawn on this PDF from book.yaml's cover_text section.")
    else:
        typer.echo("No title/author/spine text is drawn on this PDF - add it in KDP's cover creator, or set cover_text.enabled in book.yaml.")
    typer.echo(f"Full cover size: {geometry.full_width_in:.3f}in x {geometry.full_height_in:.3f}in (with bleed).")
    if image_count < config.book.target_pages:
        typer.secho(
            f"Note: only {image_count} of {config.book.target_pages} target pages are built so far - "
            "rebuild the cover once the final page count is locked in, since spine width depends on it.",
            fg="yellow",
        )


@app.command()
def retry(book_id: str, asset_id: str):
    """Re-run QC + hashing for one asset after a failed processing step (PRD section 50)."""
    book_dir = _book_dir(book_id)
    src = find_candidate_file(book_dir, asset_id)
    if not src:
        typer.secho(f"No candidate file found for {asset_id}.", fg="red")
        raise typer.Exit(1)
    result = run_basic_qc(src)
    with db.connect(book_dir) as conn:
        db.insert_qc_result(
            conn,
            asset_id=asset_id,
            resolution_score=result.resolution_score,
            line_art_score=None,
            text_detected=None,
            gray_detected=int(result.gray_detected),
            color_detected=int(result.color_detected),
            black_fill_score=result.black_fill_score,
            edge_quality_score=None,
            duplicate_score=None,
            overall_score=result.overall_score,
            machine_decision=result.machine_decision,
            notes="; ".join(result.notes) or None,
        )
        db.update_asset(conn, asset_id, sha256=sha256_of(src), phash=phash_of(src) if result.ok else None,
                         status="INGESTED" if result.ok else "QC_FAILED")
    typer.secho(f"Retried {asset_id}: {result.machine_decision}", fg="green")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    """Launch the local review UI (FastAPI) at http://host:port/."""
    import uvicorn

    uvicorn.run("app.web.main:app", host=host, port=port, reload=False)


@app.command()
def run(book_id: str):
    """Plan + generate prompts, then pause for manual Midjourney generation (PRD section 32)."""
    plan(book_id)
    prompts(book_id)
    book_dir = _book_dir(book_id)
    with db.connect(book_dir) as conn:
        n = len(db.list_page_specs(conn, book_id))
    typer.echo("")
    typer.secho(f"{n} page specifications are ready.", fg="cyan")
    typer.echo("")
    typer.echo("Generate the images in Midjourney and place the downloaded files into:")
    typer.echo("")
    typer.echo(f"  {book_dir / 'inbox'}")
    typer.echo("")
    typer.echo("Run:")
    typer.echo("")
    typer.echo(f"  bookfactory ingest {book_id}")


if __name__ == "__main__":
    app()
