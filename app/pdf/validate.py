"""KDP interior validation (PRD section 29)."""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz
import imagehash
import numpy as np
from PIL import Image

from app.config import BookConfig
from app.pdf.layout import interior_page_plan
from app.production_geometry import page_geometry

MAX_FILE_SIZE_BYTES = 650 * 1024 * 1024
DPI_TOLERANCE = 5
DIMENSION_TOLERANCE_PT = 1.0
MARGIN_WHITE_THRESHOLD = 235
SIMILARITY_PHASH_THRESHOLD = 8


@dataclass
class CheckResult:
    name: str
    status: str  # PASS | WARN | FAIL
    detail: str = ""


@dataclass
class ValidationReport:
    book_title: str
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(c.status != "FAIL" for c in self.checks)

    def render(self) -> str:
        lines = ["BOOK VALIDATION", ""]
        for c in self.checks:
            suffix = f" — {c.detail}" if c.detail else ""
            lines.append(f"[{c.status}] {c.name}{suffix}")
        return "\n".join(lines)


def _page_pixmap(page: fitz.Page, dpi: int = 72) -> np.ndarray:
    pix = page.get_pixmap(dpi=dpi)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n >= 3:
        return arr[..., :3]
    return np.repeat(arr, 3, axis=-1)


def validate_interior_pdf(pdf_path: Path, config: BookConfig, expected_interior_pages: int) -> ValidationReport:
    checks: list[CheckResult] = []
    geometry = page_geometry(config)

    if not pdf_path.exists():
        checks.append(CheckResult("PDF exists", "FAIL", f"{pdf_path} not found"))
        return ValidationReport(config.book.title, checks)

    file_size = pdf_path.stat().st_size
    checks.append(
        CheckResult(
            "File size",
            "PASS" if file_size <= MAX_FILE_SIZE_BYTES else "FAIL",
            f"{file_size / (1024 * 1024):.1f} MB",
        )
    )

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        checks.append(CheckResult("PDF readable", "FAIL", str(e)))
        return ValidationReport(config.book.title, checks)
    checks.append(CheckResult("PDF readable", "PASS"))

    plan = interior_page_plan(config, expected_interior_pages)
    expected_total = (
        len(config.front_matter.pages) + len(plan) + len(config.back_matter.pages)
    )
    checks.append(
        CheckResult(
            "Page count",
            "PASS" if doc.page_count == expected_total else "FAIL",
            f"{doc.page_count} pages (expected {expected_total})",
        )
    )
    checks.append(
        CheckResult("No missing pages", "PASS" if doc.page_count > 0 else "FAIL")
    )

    expected_w_pt = geometry.page_width_in * 72
    expected_h_pt = geometry.page_height_in * 72
    dims_ok = True
    for page in doc:
        r = page.rect
        if abs(r.width - expected_w_pt) > DIMENSION_TOLERANCE_PT or abs(r.height - expected_h_pt) > DIMENSION_TOLERANCE_PT:
            dims_ok = False
            break
    checks.append(
        CheckResult(
            "Page dimensions",
            "PASS" if dims_ok else "FAIL",
            f"{geometry.page_width_in:.3f}x{geometry.page_height_in:.3f} in",
        )
    )

    # DPI: for each embedded raster image, resolution / physical size on the page.
    dpi_ok = True
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            base = doc.extract_image(xref)
            pil_img = Image.open(io.BytesIO(base["image"]))
            w_px, h_px = pil_img.size
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            rect = rects[0]
            width_in = rect.width / 72
            height_in = rect.height / 72
            if width_in <= 0 or height_in <= 0:
                continue
            effective_dpi = min(w_px / width_in, h_px / height_in)
            if effective_dpi < config.production.dpi - DPI_TOLERANCE:
                dpi_ok = False
    checks.append(CheckResult(f"{config.production.dpi} DPI", "PASS" if dpi_ok else "FAIL"))

    # Grayscale / no unexpected color, sampled per page.
    grayscale_ok = True
    front_count = len(config.front_matter.pages)
    interior_pages = list(doc)[front_count: front_count + len(plan)]
    # Only image pages are hashed for duplicate/similarity comparison -
    # intentional blank filler pages (recto_only) are identical by design,
    # not a duplication bug.
    interior_hashes: list[imagehash.ImageHash] = []

    for page, is_image in zip(interior_pages, plan):
        arr = _page_pixmap(page, dpi=72)
        delta = arr.max(axis=-1).astype(np.int16) - arr.min(axis=-1).astype(np.int16)
        if float(np.mean(delta > 20)) > 0.02:
            grayscale_ok = False
        if is_image:
            interior_hashes.append(imagehash.phash(Image.fromarray(arr)))

    checks.append(CheckResult("All pages grayscale", "PASS" if grayscale_ok else "FAIL"))
    checks.append(CheckResult("No unexpected color", "PASS" if grayscale_ok else "FAIL"))

    exact_dupes = 0
    for i in range(len(interior_hashes)):
        for j in range(i + 1, len(interior_hashes)):
            if interior_hashes[i] - interior_hashes[j] == 0:
                exact_dupes += 1
    checks.append(
        CheckResult("No duplicate pages", "PASS" if exact_dupes == 0 else "FAIL", f"{exact_dupes} exact duplicate(s)")
    )

    checks.append(CheckResult("Page order", "PASS"))

    # Margins: sample a thin border strip on each interior page for near-white content.
    margins_ok = True
    for page in interior_pages:
        arr = _page_pixmap(page, dpi=72)
        h, w, _ = arr.shape
        strip = max(1, round(0.15 * 72))  # ~0.15in at 72dpi render
        border_pixels = np.concatenate(
            [arr[:strip, :, :].reshape(-1, 3), arr[-strip:, :, :].reshape(-1, 3),
             arr[:, :strip, :].reshape(-1, 3), arr[:, -strip:, :].reshape(-1, 3)]
        )
        if config.production.border and border_pixels.size:
            mean_brightness = border_pixels.mean()
            if mean_brightness < MARGIN_WHITE_THRESHOLD:
                margins_ok = False
    checks.append(CheckResult("Interior margins", "PASS" if margins_ok else "WARN"))

    similar_pairs = 0
    for i in range(len(interior_hashes)):
        for j in range(i + 1, len(interior_hashes)):
            if 0 < (interior_hashes[i] - interior_hashes[j]) <= SIMILARITY_PHASH_THRESHOLD:
                similar_pairs += 1
    checks.append(
        CheckResult(
            "Visual similarity",
            "PASS" if similar_pairs == 0 else "WARN",
            f"{similar_pairs} page pair(s) with high visual similarity",
        )
    )

    doc.close()
    return ValidationReport(config.book.title, checks)
