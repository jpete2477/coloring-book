"""Interior PDF builder (PRD sections 25-27)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from reportlab.pdfgen import canvas

from app.config import BookConfig
from app.pdf.layout import interior_page_plan
from app.production_geometry import page_geometry

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "frontmatter"
POINTS_PER_INCH = 72
BORDER_LINE_WIDTH_IN = 0.02
"""~0.02in - matches the "bold uniform-width" line_style used throughout."""


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def _render_matter_page(name: str, variables: dict) -> list[str]:
    template = _env().get_template(f"{name}.txt.jinja")
    text = template.render(**variables)
    return [line for line in text.splitlines() if line.strip() != "" or line == ""]


def _draw_text_page(c: canvas.Canvas, width_pt: float, height_pt: float, lines: list[str]) -> None:
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, width_pt, height_pt, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    non_empty = [l for l in lines if l.strip()]
    line_height = 28
    total_height = line_height * len(non_empty)
    y = height_pt / 2 + total_height / 2
    for i, line in enumerate(lines):
        if not line.strip():
            y -= line_height
            continue
        size = 22 if i == 0 else 13
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", size)
        c.drawCentredString(width_pt / 2, y, line.strip())
        y -= line_height


def _draw_page_border(c: canvas.Canvas, width_pt: float, height_pt: float, margin_pt: float) -> None:
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(BORDER_LINE_WIDTH_IN * POINTS_PER_INCH)
    c.rect(margin_pt, margin_pt, width_pt - 2 * margin_pt, height_pt - 2 * margin_pt, fill=0, stroke=1)


def _draw_blank_page(c: canvas.Canvas, width_pt: float, height_pt: float) -> None:
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, width_pt, height_pt, fill=1, stroke=0)


def build_interior_pdf(
    book_dir: Path,
    config: BookConfig,
    ordered_pages: list[dict],
    *,
    preview: bool = False,
) -> Path:
    """ordered_pages: [{"asset_id": str, "normalized_path": Path}, ...] in final order."""
    geometry = page_geometry(config)
    width_pt = geometry.page_width_in * POINTS_PER_INCH
    height_pt = geometry.page_height_in * POINTS_PER_INCH

    interior_dir = book_dir / "interior"
    interior_dir.mkdir(parents=True, exist_ok=True)
    out_path = interior_dir / ("interior-preview.pdf" if preview else "interior.pdf")

    matter_vars = {
        "title": config.book.title,
        "subtitle": config.book.subtitle,
        "author": config.book.author or "Unknown Author",
        "year": datetime.now(timezone.utc).year,
        "page_count": len(ordered_pages),
    }

    c = canvas.Canvas(str(out_path), pagesize=(width_pt, height_pt))

    for matter_name in config.front_matter.pages:
        lines = _render_matter_page(matter_name, matter_vars)
        _draw_text_page(c, width_pt, height_pt, lines)
        c.showPage()

    draw_border = config.production.border and config.production.margin_inches > 0
    margin_pt = config.production.margin_inches * POINTS_PER_INCH

    plan = interior_page_plan(config, len(ordered_pages))
    pages_iter = iter(ordered_pages)
    for is_image in plan:
        if not is_image:
            _draw_blank_page(c, width_pt, height_pt)
            c.showPage()
            continue
        page = next(pages_iter)
        c.drawImage(
            str(page["normalized_path"]),
            0,
            0,
            width=width_pt,
            height=height_pt,
            preserveAspectRatio=False,
        )
        if draw_border:
            _draw_page_border(c, width_pt, height_pt, margin_pt)
        c.showPage()

    for matter_name in config.back_matter.pages:
        lines = _render_matter_page(matter_name, matter_vars)
        _draw_text_page(c, width_pt, height_pt, lines)
        c.showPage()

    c.save()
    return out_path
