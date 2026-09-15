"""KDP wraparound cover assembly (PRD section 28): back cover + spine + front
cover as one PDF, sized from the current interior page count. Cover art is
full color (unlike the grayscale interior) and carries no AI-rendered text.
Title/subtitle/author/spine/back-description text is drawn on top of the
prepared art afterward (never baked into the art images themselves) when
book.yaml's `cover_text.enabled` is set - see cover_text.py. Left off by
default, since cover art alone is still a valid output some books want to
finish in KDP's own cover creator instead.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

from app.config import BookConfig
from app.pdf.cover_text import draw_cover_text
from app.production_geometry import CoverGeometry, cover_geometry

POINTS_PER_INCH = 72
RAW_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


class CoverArtMissing(Exception):
    pass


def find_cover_art(book_dir: Path, name: str) -> Path:
    for ext in RAW_EXTENSIONS:
        candidate = book_dir / "cover" / f"{name}{ext}"
        if candidate.exists():
            return candidate
    raise CoverArtMissing(
        f"No {name} art found in {book_dir / 'cover'} (expected {name}.png/.jpg/.jpeg/.webp)"
    )


def _center_crop_to_aspect(img: Image.Image, target_aspect: float) -> Image.Image:
    w, h = img.size
    current_aspect = w / h
    if abs(current_aspect - target_aspect) < 1e-3:
        return img
    if current_aspect > target_aspect:
        new_w = round(h * target_aspect)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = round(w / target_aspect)
    top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))


def _prepare_panel(src_path: Path, dest_path: Path, width_in: float, height_in: float, dpi: int) -> None:
    width_px = round(width_in * dpi)
    height_px = round(height_in * dpi)
    with Image.open(src_path) as raw:
        img = raw.convert("RGB")
    img = _center_crop_to_aspect(img, width_px / height_px)
    img = img.resize((width_px, height_px), Image.LANCZOS)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path, "PNG", dpi=(dpi, dpi))


def _edge_average_color(image_path: Path, side: str) -> Color:
    """Samples a thin strip along one edge of the front cover art to pick a
    spine color that blends reasonably instead of an arbitrary fixed color."""
    with Image.open(image_path) as img:
        arr = np.asarray(img.convert("RGB"))
    strip = arr[:, :8, :] if side == "left" else arr[:, -8:, :]
    r, g, b = (float(x) / 255.0 for x in strip.reshape(-1, 3).mean(axis=0))
    return Color(r, g, b)


def build_cover_pdf(book_dir: Path, config: BookConfig, interior_page_count: int) -> tuple[Path, CoverGeometry]:
    geometry = cover_geometry(config, interior_page_count)
    front_raw = find_cover_art(book_dir, "front_raw")
    back_raw = find_cover_art(book_dir, "back_raw")

    cover_dir = book_dir / "cover"
    front_prepared = cover_dir / "front_prepared.png"
    back_prepared = cover_dir / "back_prepared.png"
    back_panel_width_in = geometry.spine_x_in
    _prepare_panel(front_raw, front_prepared, geometry.full_width_in - geometry.front_panel_x_in, geometry.full_height_in, geometry.dpi)
    _prepare_panel(back_raw, back_prepared, back_panel_width_in, geometry.full_height_in, geometry.dpi)

    width_pt = geometry.full_width_in * POINTS_PER_INCH
    height_pt = geometry.full_height_in * POINTS_PER_INCH
    out_path = cover_dir / "cover.pdf"
    c = canvas.Canvas(str(out_path), pagesize=(width_pt, height_pt))

    c.drawImage(str(back_prepared), 0, 0, width=back_panel_width_in * POINTS_PER_INCH, height=height_pt)
    c.drawImage(
        str(front_prepared),
        geometry.front_panel_x_in * POINTS_PER_INCH,
        0,
        width=(geometry.full_width_in - geometry.front_panel_x_in) * POINTS_PER_INCH,
        height=height_pt,
    )

    spine_x_pt = geometry.spine_x_in * POINTS_PER_INCH
    spine_w_pt = geometry.spine_width_in * POINTS_PER_INCH
    spine_color = _edge_average_color(front_prepared, side="left")
    c.setFillColor(spine_color)
    c.rect(spine_x_pt, 0, spine_w_pt, height_pt, fill=1, stroke=0)

    draw_cover_text(c, config, geometry)

    c.save()
    return out_path, geometry
