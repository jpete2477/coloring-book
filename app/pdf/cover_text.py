"""Draws title/subtitle/author/description text on top of an already-assembled
wraparound cover (PRD section 28 follow-up). This never touches the prepared
cover art images - it only adds vector text (and translucent plaque
backgrounds for legibility) as extra PDF content drawn after the art, so the
original artwork is unmodified. Opt-in via book.yaml's `cover_text.enabled`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph

from app.config import BookConfig
from app.production_geometry import CoverGeometry

IN = 72.0
BLEED_IN = 0.125

FONT_DIR = Path(__file__).parent / "fonts"

INK = Color(0.11, 0.15, 0.30)
"""Deep indigo for title/spine text - echoes the stained-glass blues in the art."""
BODY_INK = Color(0.16, 0.14, 0.12)
GOLD_LINE = Color(0.72, 0.56, 0.24, alpha=0.65)
"""Thin accent border on plaques, echoing the gold medallion ring in the art."""

_FONTS_REGISTERED = False


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont("GreatVibes", str(FONT_DIR / "GreatVibes-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("PTSerif", str(FONT_DIR / "PTSerif-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("PTSerif-Bold", str(FONT_DIR / "PTSerif-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("PTSerif-Italic", str(FONT_DIR / "PTSerif-Italic.ttf")))
    _FONTS_REGISTERED = True


def _fit_font_size(font: str, text: str, max_width: float, start: float, min_size: float) -> float:
    size = start
    while size > min_size and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def _extent(font: str, size: float) -> tuple[float, float]:
    """(ascent, descent) in points at this exact size; descent is negative."""
    return pdfmetrics.getAscentDescent(font, size)


def _visual_extent(font: str, size: float) -> tuple[float, float]:
    """Like _extent, but uses the font's capHeight instead of its ascent.
    PT Serif's declared ascent (1039/1000 em) reserves headroom for accented
    glyphs that don't appear in our plain/all-caps UI strings (capHeight is
    only 700/1000) - centering against the full ascent visually shoves short
    strings toward the bottom of their box. Not used for the cursive title,
    whose swashes genuinely reach up past cap height."""
    asc, desc = _extent(font, size)
    cap_height = pdfmetrics.getFont(font).face.capHeight * size / 1000.0
    return (cap_height if cap_height > 0 else asc), desc


def _vcenter_baseline(box_bottom: float, box_height: float, asc: float, desc: float) -> float:
    extent = asc - desc
    return box_bottom + (box_height - extent) / 2 - desc


def _spaced_width(text: str, font: str, size: float, char_space: float) -> float:
    return pdfmetrics.stringWidth(text, font, size) + char_space * max(0, len(text) - 1)


def _draw_text_spaced(c: canvas.Canvas, x: float, y: float, text: str, font: str, size: float, color: Color, char_space: float, center: bool) -> None:
    if center:
        x -= _spaced_width(text, font, size, char_space) / 2
    # Character spacing (Tc) is graphics state, not scoped to one BT/ET block -
    # it leaks into every text draw call after this one unless explicitly
    # saved/restored, silently widening (and off-centering) later text like
    # the "created by" credit line.
    c.saveState()
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setCharSpace(char_space)
    t.textOut(text)
    c.drawText(t)
    c.restoreState()


@dataclass(frozen=True)
class _Plaque:
    left: float
    bottom: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2

    @property
    def top(self) -> float:
        return self.bottom + self.height


def _draw_plaque(c: canvas.Canvas, p: _Plaque, radius: float, alpha: float) -> None:
    c.saveState()
    c.setFillColor(Color(1, 1, 1, alpha=alpha))
    c.setStrokeColor(GOLD_LINE)
    c.setLineWidth(1)
    c.roundRect(p.left, p.bottom, p.width, p.height, radius, fill=1, stroke=1)
    c.restoreState()


def _draw_front_cover_text(c: canvas.Canvas, config: BookConfig, geometry: CoverGeometry) -> None:
    trim_left = geometry.front_panel_x_in * IN
    trim_right = (geometry.full_width_in - BLEED_IN) * IN
    trim_top = (geometry.full_height_in - BLEED_IN) * IN
    trim_bottom = BLEED_IN * IN
    center_x = (trim_left + trim_right) / 2
    max_text_width = (trim_right - trim_left) - 1.2 * IN

    title = config.cover_text.front_title or config.book.title
    subtitle = (config.cover_text.front_subtitle or "").upper()
    author = config.cover_text.author or config.book.author

    # --- title + subtitle plaque ---
    title_size = _fit_font_size("GreatVibes", title, max_text_width, start=100, min_size=44)
    subtitle_size = _fit_font_size("PTSerif-Bold", subtitle, max_text_width, start=22, min_size=14)

    title_asc, title_desc = _extent("GreatVibes", title_size)
    sub_asc_true, sub_desc_true = _extent("PTSerif-Bold", subtitle_size)
    sub_asc_vis, sub_desc_vis = _visual_extent("PTSerif-Bold", subtitle_size)
    pad = 0.32 * IN
    gap = 0.12 * IN
    # Box sizing always uses the font's true (safe) extent so real glyph
    # ink - lowercase ascenders/descenders included - never gets clipped;
    # only the *centering/gap* math below uses the tighter capHeight-based
    # visual extent, since that's what reads as "centered" to the eye.
    plaque_height = pad + (title_asc - title_desc) + gap + (sub_asc_true - sub_desc_true) + pad

    subtitle_char_space = subtitle_size * 0.12
    title_width = pdfmetrics.stringWidth(title, "GreatVibes", title_size)
    subtitle_width = _spaced_width(subtitle, "PTSerif-Bold", subtitle_size, subtitle_char_space)
    plaque_width = min(max(title_width, subtitle_width) + 1.0 * IN, (trim_right - trim_left) - 0.6 * IN)

    plaque_top = trim_top - 1.0 * IN
    plaque = _Plaque(
        left=center_x - plaque_width / 2,
        bottom=plaque_top - plaque_height,
        width=plaque_width,
        height=plaque_height,
    )
    _draw_plaque(c, plaque, radius=16, alpha=0.86)

    title_baseline = plaque.top - pad - title_asc
    c.setFont("GreatVibes", title_size)
    c.setFillColor(INK)
    c.drawCentredString(center_x, title_baseline, title)

    subtitle_baseline = title_baseline + title_desc - gap - sub_asc_vis
    _draw_text_spaced(c, center_x, subtitle_baseline, subtitle, "PTSerif-Bold", subtitle_size, INK, subtitle_char_space, center=True)

    # --- "created by" credit at the very bottom ---
    author_text = f"created by: {author}"
    author_size = _fit_font_size("PTSerif-Italic", author_text, max_text_width * 0.7, start=15, min_size=10)
    a_asc_true, a_desc_true = _extent("PTSerif-Italic", author_size)
    a_asc_vis, a_desc_vis = _visual_extent("PTSerif-Italic", author_size)
    a_pad = 0.20 * IN
    author_plaque_height = (a_asc_true - a_desc_true) + 2 * a_pad
    author_plaque_width = pdfmetrics.stringWidth(author_text, "PTSerif-Italic", author_size) + 0.8 * IN
    author_plaque = _Plaque(
        left=center_x - author_plaque_width / 2,
        bottom=trim_bottom + 0.32 * IN,
        width=author_plaque_width,
        height=author_plaque_height,
    )
    _draw_plaque(c, author_plaque, radius=10, alpha=0.86)
    author_baseline = _vcenter_baseline(author_plaque.bottom, author_plaque.height, a_asc_vis, a_desc_vis)
    c.setFont("PTSerif-Italic", author_size)
    c.setFillColor(INK)
    c.drawCentredString(center_x, author_baseline, author_text)


def _draw_spine_text(c: canvas.Canvas, config: BookConfig, geometry: CoverGeometry) -> None:
    if not geometry.spine_text_fits:
        return

    spine_width_pt = geometry.spine_width_in * IN
    spine_center_x = geometry.spine_x_in * IN + spine_width_pt / 2
    trim_top = (geometry.full_height_in - BLEED_IN) * IN
    trim_bottom = BLEED_IN * IN
    spine_center_y = (trim_top + trim_bottom) / 2

    title = config.cover_text.front_title or config.book.title
    subtitle = (config.cover_text.front_subtitle or "").upper()

    max_thickness = spine_width_pt - 4
    title_size = 16.0
    # Cap sizes so ascent+descent (the "thickness" once rotated) fits the spine.
    while title_size > 8 and (_extent("PTSerif-Bold", title_size)[0] - _extent("PTSerif-Bold", title_size)[1]) > max_thickness:
        title_size -= 1
    subtitle_size = max(7.0, title_size * 0.58)
    subtitle_char_space = subtitle_size * 0.1

    title_asc_true, title_desc_true = _extent("PTSerif-Bold", title_size)
    sub_asc_true, sub_desc_true = _extent("PTSerif", subtitle_size)
    title_asc, title_desc = _visual_extent("PTSerif-Bold", title_size)
    sub_asc, sub_desc = _visual_extent("PTSerif", subtitle_size)
    title_w = pdfmetrics.stringWidth(title, "PTSerif-Bold", title_size)
    subtitle_w = _spaced_width(subtitle, "PTSerif", subtitle_size, subtitle_char_space)
    block_gap = 10
    total_w = title_w + block_gap + subtitle_w

    c.saveState()
    c.translate(spine_center_x, spine_center_y)
    c.rotate(90)

    plaque_pad_x = 10
    # Sized from the true (safe) extent so real ink is never left poking out
    # past the translucent backing strip; baselines below are centered using
    # the tighter capHeight-based visual extent instead.
    plaque_h = max(title_asc_true - title_desc_true, sub_asc_true - sub_desc_true) + 6
    plaque = _Plaque(left=-total_w / 2 - plaque_pad_x, bottom=-plaque_h / 2, width=total_w + 2 * plaque_pad_x, height=plaque_h)
    _draw_plaque(c, plaque, radius=4, alpha=0.82)

    start_x = -total_w / 2
    title_baseline = _vcenter_baseline(-plaque_h / 2, plaque_h, title_asc, title_desc)
    c.setFont("PTSerif-Bold", title_size)
    c.setFillColor(INK)
    c.drawString(start_x, title_baseline, title)

    subtitle_baseline = _vcenter_baseline(-plaque_h / 2, plaque_h, sub_asc, sub_desc)
    _draw_text_spaced(c, start_x + title_w + block_gap, subtitle_baseline, subtitle, "PTSerif", subtitle_size, INK, subtitle_char_space, center=False)

    c.restoreState()


def _parse_description_blocks(text: str) -> list[tuple[str, str]]:
    """Walks the text line by line into (kind, text) items - "bullet" for a
    "- " line, "heading" for a standalone short line ending in ":" (no blank
    line required before a heading's bullets), otherwise lines are merged into
    "body" paragraphs at blank-line boundaries."""
    items: list[tuple[str, str]] = []
    body_buf: list[str] = []

    def flush_body() -> None:
        if body_buf:
            items.append(("body", " ".join(body_buf)))
            body_buf.clear()

    for raw_line in text.strip("\n").split("\n"):
        line = raw_line.strip()
        if not line:
            flush_body()
        elif line.startswith("- "):
            flush_body()
            items.append(("bullet", line[2:].strip()))
        elif line.endswith(":") and len(line) < 60:
            flush_body()
            items.append(("heading", line))
        else:
            body_buf.append(line)
    flush_body()
    return items


def _build_description_flowables(description: str) -> list:
    body_style = ParagraphStyle(
        "back-body", fontName="PTSerif", fontSize=10.3, leading=14.6,
        textColor=BODY_INK, alignment=TA_JUSTIFY, spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "back-heading", fontName="PTSerif-Bold", fontSize=11.3, leading=15,
        textColor=BODY_INK, spaceBefore=2, spaceAfter=5,
    )
    bullet_style = ParagraphStyle(
        "back-bullet", fontName="PTSerif", fontSize=10.3, leading=14.2,
        textColor=BODY_INK, leftIndent=14, bulletIndent=0, spaceAfter=3,
    )

    flowables = []
    for kind, line in _parse_description_blocks(description):
        if kind == "heading":
            flowables.append(Paragraph(escape(line), heading_style))
        elif kind == "bullet":
            flowables.append(Paragraph(escape(line), bullet_style, bulletText="•"))
        else:
            flowables.append(Paragraph(escape(line), body_style))
    return flowables


def _measure_height(flowables: list, width: float) -> float:
    """Matches Frame's actual layout consumption empirically: each flowable
    consumes its own wrapped height plus its own spaceAfter (spaceBefore is
    effectively absorbed into the previous item's spaceAfter via Frame's
    internal max-merge, so it never adds on top of it for this style set)."""
    total = 0.0
    for f in flowables:
        _, h = f.wrap(width, 1e6)
        total += h + (getattr(f.style, "spaceAfter", 0) or 0)
    return total


def _draw_back_cover_text(c: canvas.Canvas, config: BookConfig, geometry: CoverGeometry) -> None:
    description = config.cover_text.back_description.strip()
    if not description:
        return

    trim_left = BLEED_IN * IN
    trim_right = geometry.spine_x_in * IN
    trim_top = (geometry.full_height_in - BLEED_IN) * IN
    trim_bottom = BLEED_IN * IN
    center_x = (trim_left + trim_right) / 2

    pad = 0.32 * IN
    box_width = min(7.7 * IN, (trim_right - trim_left) - 0.4 * IN)
    text_width = box_width - 2 * pad

    flowables = _build_description_flowables(description)
    body_scale = 1.0
    # Shrink slightly (rather than overflow) if the box would run past a safe
    # floor above the bottom bleed / barcode-reservation area.
    max_box_height = (trim_top - 0.5 * IN) - (trim_bottom + 2.0 * IN)
    for _ in range(6):
        content_h = _measure_height(flowables, text_width)
        if content_h + 2 * pad + 36.0 <= max_box_height or body_scale <= 0.85:
            break
        body_scale -= 0.03
        for f in flowables:
            f.style.fontSize *= body_scale
            f.style.leading *= body_scale
        flowables = [Paragraph(f.text, f.style, bulletText=getattr(f, "bulletText", "")) for f in flowables]

    safety_buffer = 36.0
    box_height = content_h + 2 * pad + safety_buffer
    box_top = trim_top - 0.5 * IN
    box_bottom = box_top - box_height
    box_left = center_x - box_width / 2

    plaque = _Plaque(left=box_left, bottom=box_bottom, width=box_width, height=box_height)
    _draw_plaque(c, plaque, radius=10, alpha=1.0)

    frame = Frame(
        box_left + pad, box_bottom + pad, text_width, content_h + safety_buffer,
        showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    remaining = list(flowables)
    frame.addFromList(remaining, c)
    if remaining:
        raise RuntimeError(
            f"Back cover description box too short: {len(remaining)} paragraph(s) "
            "did not fit and were silently dropped by reportlab's Frame. "
            "Increase max_box_height or shrink back_description in book.yaml."
        )


def draw_cover_text(c: canvas.Canvas, config: BookConfig, geometry: CoverGeometry) -> None:
    if not config.cover_text.enabled:
        return
    _register_fonts()
    _draw_back_cover_text(c, config, geometry)
    _draw_spine_text(c, config, geometry)
    _draw_front_cover_text(c, config, geometry)
