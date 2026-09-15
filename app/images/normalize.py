"""Deterministic production image normalization (PRD section 21-23).

Original -> orientation fix -> trim to content -> strip the AI's own
border -> scale to cover and center-crop to exactly fill the margin box ->
resize -> denoise -> threshold last for crisp edges -> 300 DPI metadata ->
production PNG. The source file is never opened in write mode; a new file
is always written to production/. The page border itself is drawn later, at
PDF-composition time (app/pdf/build.py) rather than baked into this PNG -
that keeps the border a single, uniform, programmatic element applied once
across the whole book instead of duplicated per-image logic here.

Redesigned after real print-quality problems: cropping to an exact target
aspect ratio *before* scaling (using a mismatched box) stretched every
image, and thresholding to pure black/white *before* the final upscale let
the resize reintroduce soft gray edges that never got re-thresholded - both
are fixed below. A "fit inside, letterbox the leftover space" approach was
tried in between, but real books need the artwork to completely fill the
bordered box edge-to-edge with no internal white gap - so the box's own
aspect ratio is used as the crop target (computed correctly this time,
unlike the original bug), preserving aspect ratio and only ever cropping
overflow, never stretching.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from app.config import BookConfig
from app.production_geometry import PageGeometry, page_geometry

CONTENT_BBOX_WHITE_THRESHOLD = 245
EDGE_STRIP_FRACTION = 0.03
"""Stripped uniformly from all four sides after trimming to content, before
fitting - reliably removes whatever border/frame the AI drew near its own
edge (measured at ~1-1.6% in on real generations; 3% gives margin for
variance) so it can never look like a partial, inconsistent, or doubled-up
border next to the one drawn at PDF-build time. A small, deliberate,
uniform content loss (not content-dependent) in exchange for total
consistency."""


def _trim_to_content_bbox(img: Image.Image) -> Image.Image:
    """Crops away any near-white padding around the source's own drawn
    content, independently on all four sides (unlike a single aspect-ratio
    crop, which only ever adjusts one dimension)."""
    gray = np.asarray(img.convert("L"))
    rows = np.where((gray < CONTENT_BBOX_WHITE_THRESHOLD).any(axis=1))[0]
    cols = np.where((gray < CONTENT_BBOX_WHITE_THRESHOLD).any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        return img  # blank image - nothing to trim, let downstream QC catch it
    h, w = gray.shape
    top, bottom = rows.min(), rows.max() + 1
    left, right = cols.min(), cols.max() + 1
    return img.crop((left, top, right, bottom))


def _strip_edge_fraction(img: Image.Image, fraction: float) -> Image.Image:
    w, h = img.size
    dx, dy = round(w * fraction), round(h * fraction)
    if w - 2 * dx < 1 or h - 2 * dy < 1:
        return img
    return img.crop((dx, dy, w - dx, h - dy))


def _cover_and_crop(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """Scales to fully cover (box_w, box_h) preserving aspect ratio - the
    smaller dimension is scaled up until it meets the box exactly, then any
    overflow on the other axis is center-cropped away. Fills the box
    completely with no letterboxing, without distorting the aspect ratio
    (unlike the original squish bug, which resized into a box of the wrong
    aspect ratio instead of cropping to it)."""
    w, h = img.size
    scale = max(box_w / w, box_h / h)
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - box_w) // 2
    top = (new_h - box_h) // 2
    return resized.crop((left, top, left + box_w, top + box_h))


def normalize_image(source_path: Path, dest_path: Path, config: BookConfig) -> PageGeometry:
    geometry = page_geometry(config)

    if config.production.border and config.production.margin_inches > 0:
        margin_px = round(config.production.margin_inches * geometry.dpi)
    else:
        margin_px = 0
    inner_w = max(1, geometry.page_width_px - margin_px * 2)
    inner_h = max(1, geometry.page_height_px - margin_px * 2)

    with Image.open(source_path) as raw:
        img = ImageOps.exif_transpose(raw.convert("RGB"))

    img = _trim_to_content_bbox(img)
    img = _strip_edge_fraction(img, EDGE_STRIP_FRACTION)
    img = img.convert("L")

    # Resize while still grayscale (continuous-tone), so the upscale
    # interpolates smoothly - then denoise and threshold LAST, at final
    # resolution, so edges come out crisp and pure black/white instead of
    # re-blurred by a resize that happens after binarization.
    content = _cover_and_crop(img, inner_w, inner_h)
    content = content.filter(ImageFilter.MedianFilter(size=3))
    if config.production.threshold:
        threshold = config.production.threshold_value
        content = content.point(lambda p: 255 if p >= threshold else 0)

    canvas = Image.new("L", (geometry.page_width_px, geometry.page_height_px), color=255)
    canvas.paste(content, (margin_px, margin_px))

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest_path, "PNG", dpi=(geometry.dpi, geometry.dpi))
    return geometry
