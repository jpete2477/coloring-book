"""Pydantic models for book.yaml (PRD section 9) and loader."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class BookMeta(BaseModel):
    id: str
    title: str
    subtitle: str = "An Adult Coloring Collection"
    trim_size: str = "8.5x11"
    orientation: str = "portrait"
    target_pages: int = 40
    bleed: bool = False
    author: str = ""
    audience: str = "Adult"
    """Drives style.medium ("{audience} coloring book line art") and the
    wording of every generated prompt end to end - the pipeline itself isn't
    adult-specific, "Adult" is just the default. A "Kids" (or any other)
    audience works the same way, but its base_elements/constraints/complexity
    are still a per-book judgment call to set in book.yaml - e.g. the
    anxiety-reduction, no-representational-subjects reasoning in STYLE.md is
    specific to that one adult-focused product line, not a pipeline default."""
    theme: str = ""
    """Free-text theme (e.g. "4 Seasons") used for flavor in prompts/front
    matter. Does not by itself pick base_elements - that's still a curated,
    reviewed judgment call per book, not an automated mapping."""


class StyleConfig(BaseModel):
    style_reference: str | None = None
    style_weight: int = 150
    medium: str = "adult coloring book line art"
    line_style: str = (
        "bold uniform-width black outlines, every shape fully closed with no open or "
        "dangling line ends, no hatching or texture linework"
    )
    background: str = "pure white background, no texture or noise"
    complexity: str = "high"
    midjourney_stylize: int = 50
    """Midjourney --stylize value (0-1000, default 100). Lower makes MJ follow
    the literal prompt (flat, no shading) instead of layering on its default
    aesthetic embellishment, which is what overrides "no shading"/"no gradients"
    text instructions in practice."""
    midjourney_style_raw: bool = True
    """Append --style raw: further reduces Midjourney's default "opinionated"
    look in favor of literal prompt adherence."""
    style_anchor: str | None = None
    """A single fixed art-genre anchor (e.g. "stained glass window") used on
    every page instead of rotating through STYLE_ANCHORS in prompts.py. The
    rotating version was built for per-page variety, but a real book needs
    one cohesive visual identity throughout - rotating styles trades cohesion
    for variety in the wrong direction. Leave unset to keep the legacy
    rotating behavior (used by books created before this existed)."""
    border_style: str | None = None
    """A single fixed border/frame description used on every page instead of
    randomly choosing from `borders` per page - same cohesion reasoning as
    style_anchor. Leave unset to keep the legacy per-page random behavior."""
    notes: str = ""
    """Free-text, folded into every prompt verbatim - an escape hatch for
    book-specific direction not otherwise modeled (e.g. from book.json)."""


class ProductionConfig(BaseModel):
    dpi: int = 300
    border: bool = True
    target_width_inches: float = 8.5
    target_height_inches: float = 11.0
    threshold: bool = True
    """Convert to pure black/white after grayscale conversion (PRD section 17.2)."""
    threshold_value: int = 200
    margin_inches: float = 0.4
    """White safe-interior margin applied when production.border is true (PRD section 23)."""
    recto_only: bool = False
    """When true, every interior image lands on a right-hand (odd) page - a
    blank left-hand page is inserted before the first image if needed, and
    after every image, so the next one also lands on the right. Roughly
    doubles the interior page count (and KDP print cost) - opt-in per book."""


class OrderingConfig(BaseModel):
    avoid_adjacent_same_element: bool = True
    avoid_adjacent_same_composition: bool = True
    target_density_variation: bool = True


class DiversityConfig(BaseModel):
    max_same_element_consecutive: int = 1
    max_same_composition_consecutive: int = 1
    max_same_element_count: int = 4
    max_same_composition_count: int = 6
    max_duplicate_combination_count: int = 1
    candidates_per_page: int = 3
    duplicate_phash_threshold: int = 10
    """Hamming distance (0-64) at/below which two phashes are flagged as likely-similar."""


class FrontMatterConfig(BaseModel):
    pages: list[str] = Field(default_factory=lambda: ["title_page", "copyright_page", "belongs_to_page"])


class BackMatterConfig(BaseModel):
    pages: list[str] = Field(default_factory=list)


class CoverTextConfig(BaseModel):
    enabled: bool = False
    """When true, build_cover_pdf draws title/subtitle/author/description text
    on top of the cover art (front, spine, and back). Off by default since
    cover art alone is still a valid, no-text output some books may want."""
    front_title: str | None = None
    """Defaults to book.title when unset."""
    front_subtitle: str | None = None
    """Cover-facing subtitle - may differ from book.subtitle (front matter
    wording vs. cover marketing wording)."""
    author: str | None = None
    """Defaults to book.author when unset."""
    back_description: str = ""
    """Back-cover blurb. Blank lines separate paragraphs; a line starting
    with "- " is rendered as a bullet."""


class BookConfig(BaseModel):
    book: BookMeta
    style: StyleConfig = Field(default_factory=StyleConfig)
    base_elements: list[str] = Field(default_factory=list)
    compositions: list[str] = Field(default_factory=list)
    densities: list[int] = Field(default_factory=lambda: [1, 2, 3, 4])
    """5 ("extremely intricate") dropped from the default pool: real user
    feedback said designs were too detailed to color even at moderate
    density. Still selectable if a book.yaml explicitly lists 5."""
    symmetries: list[str] = Field(
        default_factory=lambda: ["none", "loose", "bilateral", "four-way", "tiled", "rotational"]
    )
    scales: list[str] = Field(
        default_factory=lambda: ["macro", "medium", "fine", "mixed", "large_dominant", "dense_uniform"]
    )
    borders: list[str] = Field(
        default_factory=lambda: [
            # "open edge" and "edge-to-edge pattern" were removed: every page
            # needs a clear contained edge with white margin for printing, so
            # no remaining option should invite content to bleed to the image
            # boundary.
            "enclosed border",
            "decorative frame",
            "central framed composition",
            "border plus open interior",
        ]
    )
    constraints: list[str] = Field(default_factory=list)
    production: ProductionConfig = Field(default_factory=ProductionConfig)
    ordering: OrderingConfig = Field(default_factory=OrderingConfig)
    diversity: DiversityConfig = Field(default_factory=DiversityConfig)
    front_matter: FrontMatterConfig = Field(default_factory=FrontMatterConfig)
    back_matter: BackMatterConfig = Field(default_factory=BackMatterConfig)
    cover_text: CoverTextConfig = Field(default_factory=CoverTextConfig)


def load_book_config(book_yaml_path: Path) -> BookConfig:
    data = yaml.safe_load(book_yaml_path.read_text())
    return BookConfig.model_validate(data)


def book_dir_for(root: Path, book_id: str) -> Path:
    return root / "books" / book_id


def book_yaml_path(root: Path, book_id: str) -> Path:
    return book_dir_for(root, book_id) / "book.yaml"
