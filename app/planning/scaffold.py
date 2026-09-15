"""Default book.yaml content for `bookfactory init` (PRD sections 6, 8, 9)."""
from __future__ import annotations

from app.planning.book_spec import BookSpec, border_style_phrase, parse_size

DEFAULT_BASE_ELEMENTS = [
    # Deliberately abstract/ornamental only: no "correct" real-world reference
    # to compare against, which matters for an anxiety-reduction coloring book.
    # Representational subjects (bird, butterfly, fish, dragonfly, beetle,
    # mushroom, feather, star, sun) carry an implicit right/wrong answer and
    # tend to render as shaded illustrative portraits rather than flat pattern
    # line art (see PRD discussion / STYLE.md). "honeycomb" and "window" were
    # tried and dropped too: both are conceptually dense/architectural
    # (cellular tessellation, ornate window tracery) and kept producing
    # packed, breathing-room-free pages regardless of density wording -
    # confirmed across two different generation tools for "window", not just
    # one. "compass" dropped too, for a different reason: 2/2 real generations
    # rendered it as a literal navigational instrument with actual degree
    # numbers and N/S/E/W letters baked in, violating "no text, no numbers" -
    # automated QC has no OCR/text detection (out of scope for this build),
    # so this specifically needs a human to catch. Watch
    # crystal/pinecone/lattice/arch for the density/faceting failure mode.
    "flower", "wheel", "shell", "leaf", "ribbon", "crystal", "pinecone",
    "spiral", "gear", "fan", "lattice", "vine", "arch",
    "key", "wave",
]

DEFAULT_COMPOSITIONS = [
    # "four_way_tile" was dropped: tiling a motif into mirrored quadrants
    # reliably read as dense/ornate in real generations regardless of the
    # requested density, same structural issue as honeycomb among elements.
    # "branching" (organic, non-repeating) takes its slot.
    "organic_all_over", "interlocking", "flowing_diagonal", "branching",
    "nested", "alternating_bands", "overlapping", "asymmetric_repeating",
    "geometric_lattice", "clustered",
]

DEFAULT_CONSTRAINTS = [
    "no text", "no numbers", "no people", "no shading", "no gray", "no color",
    "no gradients", "no solid black areas", "no traditional mandala",
    "no single central object", "no concentric rings", "no generic clip art",
]


def render_book_yaml(*, book_id: str, title: str, author: str, target_pages: int = 40) -> str:
    elements_yaml = "\n".join(f"  - {e}" for e in DEFAULT_BASE_ELEMENTS)
    compositions_yaml = "\n".join(f"  - {c}" for c in DEFAULT_COMPOSITIONS)
    constraints_yaml = "\n".join(f"  - {c}" for c in DEFAULT_CONSTRAINTS)
    return f"""\
book:
  id: {book_id}
  title: "{title}"
  subtitle: "An Adult Coloring Collection"
  author: "{author}"
  trim_size: "8.5x11"
  orientation: portrait
  target_pages: {target_pages}
  bleed: false

style:
  style_reference: null  # set after picking early Midjourney favorites (PRD 12.1/12.2)
  style_weight: 150
  medium: "adult coloring book line art"
  line_style: "bold uniform-width black outlines, every shape fully closed with no open or dangling line ends, no hatching or texture linework"
  background: "pure white background, no texture or noise"
  complexity: "high"
  midjourney_stylize: 50  # lower than MJ's default 100: follow the literal prompt, less embellishment
  midjourney_style_raw: true  # --style raw: further reduces MJ's default aesthetic overlay

base_elements:
{elements_yaml}

compositions:
{compositions_yaml}

constraints:
{constraints_yaml}

production:
  dpi: 300
  border: true
  target_width_inches: 8.5
  target_height_inches: 11
  threshold: true
  threshold_value: 200
  margin_inches: 0.4

ordering:
  avoid_adjacent_same_element: true
  avoid_adjacent_same_composition: true
  target_density_variation: true

diversity:
  max_same_element_consecutive: 1
  max_same_composition_consecutive: 1
  max_same_element_count: 4
  max_same_composition_count: 6
  max_duplicate_combination_count: 1
  candidates_per_page: 3
  duplicate_phash_threshold: 10

front_matter:
  pages:
    - title_page
    - copyright_page
    - belongs_to_page

back_matter:
  pages: []
"""


def render_book_yaml_from_spec(*, book_id: str, title: str, spec: BookSpec) -> str:
    """Turns a simple book.json BookSpec into full book.yaml content. Unlike
    render_book_yaml, style/border are FIXED per book (not rotated per page)
    - cohesion across the whole book, not per-page variety, which is what
    style/border rotation was originally built for and turned out to be the
    wrong tradeoff for a real product."""
    if not spec.elements:
        raise ValueError("BookSpec.elements is required - theme-to-elements is a curated judgment call, not automated")

    elements = spec.elements
    compositions = spec.compositions or DEFAULT_COMPOSITIONS
    trim_w, trim_h = parse_size(spec.size)
    medium = f"{spec.audience.lower()} coloring book line art"
    border_phrase = border_style_phrase(spec.border_type)

    max_same_element = max(2, round(spec.page_count / max(1, len(elements)) * 1.5))
    max_same_composition = max(2, round(spec.page_count / max(1, len(compositions)) * 1.5))

    elements_yaml = "\n".join(f"  - {e}" for e in elements)
    compositions_yaml = "\n".join(f"  - {c}" for c in compositions)
    constraints_yaml = "\n".join(f"  - {c}" for c in DEFAULT_CONSTRAINTS)
    notes_line = f'\n  notes: "{spec.notes}"' if spec.notes else ""

    return f"""\
book:
  id: {book_id}
  title: "{title}"
  subtitle: "{spec.subtitle}"
  author: "{spec.author}"
  trim_size: "{spec.size}"
  orientation: portrait
  target_pages: {spec.page_count}
  bleed: {str(spec.bleed).lower()}
  audience: "{spec.audience}"
  theme: "{spec.theme}"

style:
  style_reference: null  # set after picking early favorites (PRD 12.1/12.2)
  style_weight: 150
  medium: "{medium}"
  line_style: "bold uniform-width black outlines, every shape fully closed with no open or dangling line ends, no hatching or texture linework"
  background: "pure white background, no texture or noise"
  complexity: "high"
  midjourney_stylize: 50
  midjourney_style_raw: true
  style_anchor: "{spec.style.lower()}"  # fixed for the whole book (model: {spec.model}) - cohesion, not per-page rotation
  border_style: "{border_phrase}"  # fixed for the whole book, same reasoning{notes_line}

base_elements:
{elements_yaml}

compositions:
{compositions_yaml}

constraints:
{constraints_yaml}

production:
  dpi: 300
  border: true
  target_width_inches: {trim_w}
  target_height_inches: {trim_h}
  threshold: true
  threshold_value: 200
  margin_inches: {spec.margin_width_inches}

ordering:
  avoid_adjacent_same_element: true
  avoid_adjacent_same_composition: true
  target_density_variation: true

diversity:
  max_same_element_consecutive: 1
  max_same_composition_consecutive: 1
  max_same_element_count: {max_same_element}
  max_same_composition_count: {max_same_composition}
  max_duplicate_combination_count: 1
  candidates_per_page: 3
  duplicate_phash_threshold: 10

front_matter:
  pages:
    - title_page
    - copyright_page
    - belongs_to_page

back_matter:
  pages: []
"""
