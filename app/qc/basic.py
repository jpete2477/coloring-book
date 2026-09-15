"""Basic automated QC (PRD section 17.1-17.3).

Filters obvious failures; does not make the final artistic call. Text
detection (17.4) and vision-model QC (17.5) are out of scope for this pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

BLACK_THRESHOLD = 32
WHITE_THRESHOLD = 240
MIN_RESOLUTION_PX = 1000
SOLID_BLACK_WARN_FRACTION = 0.15


@dataclass
class QCResult:
    ok: bool
    width: int = 0
    height: int = 0
    dpi: int | None = None
    aspect_ratio: float = 0.0
    near_white_fraction: float = 0.0
    dark_fraction: float = 0.0
    gray_fraction: float = 0.0
    solid_black_fraction: float = 0.0
    color_detected: bool = False
    gray_detected: bool = False
    resolution_score: float = 0.0
    black_fill_score: float = 0.0
    overall_score: float = 0.0
    machine_decision: str = "review"
    notes: list[str] = field(default_factory=list)


def run_basic_qc(image_path: Path) -> QCResult:
    try:
        with Image.open(image_path) as img:
            img.load()
            width, height = img.size
            dpi = None
            if "dpi" in img.info:
                dpi = round(img.info["dpi"][0])

            rgb = img.convert("RGB")
            arr = np.asarray(rgb, dtype=np.int16)
    except (UnidentifiedImageError, OSError) as e:
        return QCResult(ok=False, machine_decision="qc_failed", notes=[f"file integrity: {e}"])

    notes: list[str] = []

    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    gray = (r.astype(np.float32) + g + b) / 3.0
    max_channel_delta = np.max(arr, axis=-1) - np.min(arr, axis=-1)
    color_detected = bool(np.mean(max_channel_delta > 20) > 0.01)

    near_white_fraction = float(np.mean(gray >= WHITE_THRESHOLD))
    dark_fraction = float(np.mean(gray <= BLACK_THRESHOLD))
    gray_fraction = float(np.mean((gray > BLACK_THRESHOLD) & (gray < WHITE_THRESHOLD)))
    gray_detected = gray_fraction > 0.05

    # Solid black area: dark pixels that are also part of a large low-variance blob,
    # approximated here by dark-pixel fraction with a stricter threshold.
    solid_black_fraction = float(np.mean(gray <= 10))

    aspect_ratio = width / height if height else 0.0

    resolution_score = 1.0 if min(width, height) >= MIN_RESOLUTION_PX else min(width, height) / MIN_RESOLUTION_PX
    black_fill_score = max(0.0, 1.0 - solid_black_fraction / SOLID_BLACK_WARN_FRACTION) if solid_black_fraction else 1.0

    ok = True
    if min(width, height) < 500:
        ok = False
        notes.append(f"resolution too low: {width}x{height}")
    if solid_black_fraction > 0.5:
        ok = False
        notes.append(f"unusable: mostly solid black ({solid_black_fraction:.1%})")
    if near_white_fraction < 0.15:
        notes.append("very little white space; page may be overly dense or corrupted")
    if solid_black_fraction > SOLID_BLACK_WARN_FRACTION:
        notes.append(f"excessive solid-black area: {solid_black_fraction:.1%}")
    if color_detected:
        notes.append("color detected outside grayscale expectations")
    if gray_detected:
        notes.append(f"gray pixels detected: {gray_fraction:.1%}")

    overall_score = round(
        0.4 * resolution_score + 0.3 * black_fill_score + 0.3 * (0.0 if color_detected else 1.0), 3
    )
    machine_decision = "qc_failed" if not ok else ("flag" if notes else "pass")

    return QCResult(
        ok=ok,
        width=width,
        height=height,
        dpi=dpi,
        aspect_ratio=round(aspect_ratio, 4),
        near_white_fraction=round(near_white_fraction, 4),
        dark_fraction=round(dark_fraction, 4),
        gray_fraction=round(gray_fraction, 4),
        solid_black_fraction=round(solid_black_fraction, 4),
        color_detected=color_detected,
        gray_detected=gray_detected,
        resolution_score=round(resolution_score, 3),
        black_fill_score=round(black_fill_score, 3),
        overall_score=overall_score,
        machine_decision=machine_decision,
        notes=notes,
    )
