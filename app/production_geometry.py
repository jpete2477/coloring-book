"""Derives production page/image dimensions from book.yaml (PRD section 22).

Never hard-code 2550x3300 etc. - always compute from trim size, bleed, and DPI.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from app.config import BookConfig

BLEED_INCHES = 0.125


@dataclass(frozen=True)
class PageGeometry:
    trim_width_in: float
    trim_height_in: float
    page_width_in: float
    """Width including bleed on the outside edge, if bleed is enabled."""
    page_height_in: float
    """Height including bleed on top and bottom, if bleed is enabled."""
    dpi: int
    bleed: bool

    @property
    def page_width_px(self) -> int:
        return round(self.page_width_in * self.dpi)

    @property
    def page_height_px(self) -> int:
        return round(self.page_height_in * self.dpi)


def page_geometry(config: BookConfig) -> PageGeometry:
    trim_w = config.production.target_width_inches
    trim_h = config.production.target_height_inches
    bleed = config.book.bleed
    if bleed:
        # Bleed extends past trim on top, bottom, and outside edge only (KDP interior spec).
        page_w = trim_w + BLEED_INCHES
        page_h = trim_h + BLEED_INCHES * 2
    else:
        page_w = trim_w
        page_h = trim_h
    return PageGeometry(
        trim_width_in=trim_w,
        trim_height_in=trim_h,
        page_width_in=page_w,
        page_height_in=page_h,
        dpi=config.production.dpi,
        bleed=bleed,
    )


COVER_SPINE_IN_PER_PAGE = 0.002252
"""KDP's measured caliper thickness of standard white 60lb interior paper.
Cream paper uses 0.0025 instead, but this project's interiors are grayscale
line art on white, so white paper is the right coefficient here."""
COVER_SPINE_FIXED_IN = 0.06
"""Fixed allowance for the cover stock's own thickness, independent of the
interior page count."""


@dataclass(frozen=True)
class CoverGeometry:
    trim_width_in: float
    trim_height_in: float
    spine_width_in: float
    full_width_in: float
    """Back cover + spine + front cover, plus bleed on both outer edges."""
    full_height_in: float
    dpi: int

    @property
    def back_panel_x_in(self) -> float:
        return BLEED_INCHES

    @property
    def spine_x_in(self) -> float:
        return BLEED_INCHES + self.trim_width_in

    @property
    def front_panel_x_in(self) -> float:
        return BLEED_INCHES + self.trim_width_in + self.spine_width_in

    @property
    def full_width_px(self) -> int:
        return round(self.full_width_in * self.dpi)

    @property
    def full_height_px(self) -> int:
        return round(self.full_height_in * self.dpi)

    @property
    def spine_text_fits(self) -> bool:
        """Spine text becomes illegible below roughly 0.19in / a ~100-page
        book at this coefficient; KDP itself omits spine text under similar
        thresholds rather than print unreadable type."""
        return self.spine_width_in >= 0.19


def cover_geometry(config: BookConfig, interior_page_count: int) -> CoverGeometry:
    trim_w = config.production.target_width_inches
    trim_h = config.production.target_height_inches
    spine_w = interior_page_count * COVER_SPINE_IN_PER_PAGE + COVER_SPINE_FIXED_IN
    full_w = 2 * trim_w + spine_w + 2 * BLEED_INCHES
    full_h = trim_h + 2 * BLEED_INCHES
    return CoverGeometry(
        trim_width_in=trim_w,
        trim_height_in=trim_h,
        spine_width_in=round(spine_w, 4),
        full_width_in=full_w,
        full_height_in=full_h,
        dpi=config.production.dpi,
    )


def midjourney_aspect_ratio(config: BookConfig) -> str:
    """Simplest integer W:H ratio for a Midjourney --ar flag, from the trim size.

    Without this, Midjourney defaults to a square image, which then has to be
    heavily center-cropped to fit the book's portrait trim (PRD section 22).
    """
    frac = Fraction(
        config.production.target_width_inches / config.production.target_height_inches
    ).limit_denominator(64)
    return f"{frac.numerator}:{frac.denominator}"
