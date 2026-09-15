"""Front/back cover art prompts (PRD section 28).

Unlike interior pages, cover art is meant to be striking and sell the book
on a shelf, not be colored in - so it deliberately does NOT carry the
interior's "no color"/"no single central object"/anti-anxiety constraints.
Text is intentionally excluded from the art itself; the cover assembly
pipeline (app/pdf/cover.py) draws real title/author text on top afterward,
the same reasoning as the interior title page (PRD section 26): AI-rendered
text has been unreliable all session, so don't gamble on it for the one
piece of text every buyer actually reads.
"""
from __future__ import annotations

from pathlib import Path

from app.config import BookConfig
from app.production_geometry import midjourney_aspect_ratio


def _signature_motifs(config: BookConfig, limit: int = 4) -> str:
    """Samples evenly across the full base_elements list rather than just
    taking the first N - for a themed book (e.g. elements grouped season by
    season) the first N would only represent one slice of the book instead
    of the whole collection."""
    all_elements = config.base_elements or ["ornamental"]
    if len(all_elements) <= limit:
        elements = all_elements
    else:
        step = len(all_elements) / limit
        elements = [all_elements[round(i * step)] for i in range(limit)]
    if len(elements) == 1:
        return elements[0]
    return ", ".join(elements[:-1]) + f", and {elements[-1]}"


def _cover_params(config: BookConfig, provider: str) -> str:
    if provider == "midjourney":
        return f"--ar {midjourney_aspect_ratio(config)} --stylize 250 --style raw"
    return f"{config.book.orientation} orientation, {midjourney_aspect_ratio(config)} aspect ratio."


def front_cover_prompt(config: BookConfig, *, provider: str = "midjourney") -> str:
    motifs = _signature_motifs(config)
    text = (
        f"vibrant colorful book cover illustration for an adult coloring book titled \"{config.book.title}\", "
        f"a striking ornamental hero composition blending {motifs} motifs, rich jewel-tone color palette, "
        "dynamic and eye-catching, professional decorative book cover art, intricate linework, "
        "balanced composition with open space near the top and bottom for title and author text to be "
        "added afterward, no text, no numbers, no logos, no watermark, "
        f"full-page {config.book.orientation} composition, bleeding to the edge with no border"
    )
    return f"{text} {_cover_params(config, provider)}"


def back_cover_prompt(config: BookConfig, *, provider: str = "midjourney") -> str:
    motifs = _signature_motifs(config)
    text = (
        f"vibrant colorful decorative background pattern for the back cover of an adult coloring book, "
        f"softer and simpler than a front cover, echoing {motifs} motifs in a matching color palette, "
        "plenty of open plain space in the lower right corner for a barcode, plenty of open space "
        "for description text, no text, no numbers, no logos, no watermark, "
        f"full-page {config.book.orientation} composition, bleeding to the edge with no border"
    )
    return f"{text} {_cover_params(config, provider)}"


def export_cover_prompt_manifest(book_dir: Path, config: BookConfig, *, provider: str = "midjourney") -> Path:
    basename = f"cover_prompts_{provider}"
    metadata_dir = book_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    path = metadata_dir / f"{basename}.md"
    front = front_cover_prompt(config, provider=provider)
    back = back_cover_prompt(config, provider=provider)
    lines = [
        "# Cover Prompts",
        "",
        "Drop the results into:",
        f"  {book_dir / 'cover' / 'front_raw.png'}  (or .jpg/.jpeg)",
        f"  {book_dir / 'cover' / 'back_raw.png'}",
        "then run: bookfactory build-cover <book_id>",
        "",
        "## Front cover",
        "",
        f"```text\n{front}\n```",
        "",
        "## Back cover",
        "",
        f"```text\n{back}\n```",
        "",
    ]
    path.write_text("\n".join(lines))
    return path
