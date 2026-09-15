"""Prompt generation from page specifications (PRD sections 11, 33, 57).

Uses several prompt "families" (templates expressing the same visual
language differently) so that template repetition doesn't become a source
of visual repetition (PRD section 11). Families are plain Jinja2 text
templates under templates/prompts/ so they're easy to tweak without
touching code.
"""
from __future__ import annotations

import csv
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.config import BookConfig
from app.planning.planner import PlannedPage
from app.production_geometry import midjourney_aspect_ratio

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "prompts"

# Kept deliberately short: Midjourney adjusts/truncates prompts past a length
# threshold ("increased variability" warning), so every concept below is
# stated exactly once across the whole prompt - not repeated in different
# words at every round of fixes. line_style and background (StyleConfig)
# already cover outlines/hatching/texture and background cleanliness; this
# only adds what isn't covered anywhere else.
LINE_ART_EMPHASIS = (
    "flat vector line art, no double outlines or stray accent strokes, "
    "content kept within the page with white space at the edge, not bleeding off the page, "
    "no gear or cog motifs unless gear is the requested subject, "
    "a genuinely unique design, not a repeat of anything already generated in this session"
)
"""The "no gear/cog" clause is evidence-based, not precautionary: Gemini
repeatedly inserted mechanical gear/cog details into unrelated pages (wheel,
rose) as part of its own default ornamental-medallion style.
Deliberately doesn't say "border" - that's page.border's job (enclosed
border / decorative frame / central framed composition / border plus open
interior), and it already varies per page. A fixed phrase that also says
"visible border" here dominated the varied per-page border_phrase and made
every page's actual border treatment look the same regardless of which
border style was requested.
The "not a repeat of anything already generated in this session" clause
only does real work for chat-style tools (Gemini) where consecutive prompts
share conversational context and can visibly drift toward a groove -
Midjourney/Civitai treat each generation independently, so it's a no-op
there, but harmless to include everywhere."""

STYLE_ANCHORS = [
    "stained glass window",
    "linocut woodblock print",
    "papercut silhouette art",
    "mosaic tile",
    "batik textile",
]
"""Concrete, well-known art genres that *structurally* require the
properties we've been fighting for in the abstract: stained glass literally
cannot have an open lead line (the glass would fall out), papercut cannot
have a floating disconnected line (the paper would separate), both are
inherently bold-outlined and flat-colored. Naming one is a stronger anchor
than a list of "no X" rules, and rotating through several is itself a
diversity axis - it was pairing one dominant unnamed style (Gemini's own
default) with every element/composition that produced the medallion-grid
sameness in the first place."""

DENSITY_LABELS = {
    1: "very sparse, a few large simple shapes, generous open space",
    2: "light detail, large shapes with open space between them",
    3: "moderate detail, large easy-to-color regions, not edge-to-edge",
    4: "dense detail but large simple regions, not fully packed",
    5: "intricate detail, but regions still large enough to color easily",
}
"""A bare word like "moderate" wasn't enough to stop Midjourney from tiling
motifs edge-to-edge with no breathing room (see OF001-001 attempts). Spelling
out the white-space expectation explicitly, per density level, is what
actually worked in practice - kept concise so it doesn't add to prompt bloat.
"large" was added to every level (not just the sparse ones) after real user
feedback: designs were too detailed/fussy to color even at "moderate" -
sparse PLACEMENT of small intricate shapes isn't the same as large,
easy-to-fill shapes, and the old wording only controlled placement."""

SYMMETRY_PHRASES = {
    "none": "asymmetric, organic arrangement",
    "loose": "loose, imperfect symmetry",
    "bilateral": "bilateral symmetry",
    "four-way": "four-way grid symmetry, not a kaleidoscope",
    "tiled": "tiled grid symmetry, not a kaleidoscope",
    "rotational": "subtle rotational repeat, not a mandala",
}

SCALE_PHRASES = {
    "macro": "large bold motifs, easy to color",
    "medium": "medium-large motifs, generous coloring space",
    "fine": "moderately sized motifs, not tiny or fussy",
    "mixed": "mostly large shapes with a few small accents",
    "large_dominant": "large dominant forms, minimal small detail",
    "dense_uniform": "large uniform shapes, evenly sized for easy coloring",
}
"""Every entry redefined toward "large/easy to color" after real user
feedback that designs were too detailed to color even at moderate density -
"fine" and "dense_uniform" used to mean the literal opposite (fine
intricate detail / dense uniform detail), which worked directly against
that regardless of what density said. Config books that already picked
"fine" or "dense_uniform" per page keep working (same option names, just
the wording now means the opposite of the old failure mode) - no database
migration needed, this fixes every page's wording as soon as prompts are
regenerated."""

COMPOSITION_STRUCTURE_PHRASES = {
    "organic_all_over": "one continuous organic pattern flowing edge to edge across the whole page, not a grid of repeated framed medallions",
    "interlocking": "shapes directly interlocking across the full page as one continuous design, not isolated into separate framed compartments",
    "flowing_diagonal": "a single diagonal flow of motifs sweeping corner to corner, not a symmetric grid of repeated blocks",
    "branching": "one organic branching structure spreading unevenly from a few origin points, not four identical repeated branches in a grid",
    "nested": "motifs nested concentrically within each other as one unified form, not split into multiple repeated medallions",
    "alternating_bands": "horizontal bands stacked top to bottom spanning the full page width, not a 2x2 grid of framed sections",
    "overlapping": "motifs directly overlapping and layered across the entire page as one continuous design, not isolated framed compartments",
    "asymmetric_repeating": "irregular asymmetric repetition scattered unevenly across the page, not a symmetric grid of identical quadrants",
    "geometric_lattice": "one continuous interlocking geometric mesh spanning the full page edge to edge, not broken into separate framed sections",
    "clustered": "a few irregular organic clusters of varying size scattered unevenly across the page, not four identical evenly-spaced medallions",
}
"""Bare composition words ("branching", "clustered", ...) weren't specific
enough to stop Gemini from defaulting to its own strong structural bias: a
2x2 grid of oval medallion frames bridged by scrollwork, regardless of what
composition was actually requested (confirmed across wheel/gear/rose/grape
pages). Spelling out the intended structure - and explicitly ruling out the
observed default - is the same fix that worked for density and symmetry."""


def _composition_phrase(composition: str) -> str:
    return composition.replace("_", " ").replace("-", " ")


def _composition_structure_phrase(composition: str) -> str:
    return COMPOSITION_STRUCTURE_PHRASES.get(composition, _composition_phrase(composition))


def _load_families() -> list[str]:
    names = sorted(p.name for p in TEMPLATES_DIR.glob("*.txt.jinja"))
    if not names:
        raise FileNotFoundError(f"No prompt family templates found in {TEMPLATES_DIR}")
    return names


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), trim_blocks=True, lstrip_blocks=True)


def render_prompt(config: BookConfig, page: PlannedPage, family_index: int, *, provider: str = "midjourney") -> str:
    """provider: "midjourney" appends MJ's --ar/--stylize/--style flags; any
    other value (e.g. "generic") omits them and states aspect ratio in plain
    English instead - those flags are Midjourney-specific syntax that other
    tools (Gemini, Civitai's generator, ...) don't understand and will either
    ignore unpredictably or try to render as literal text."""
    families = _load_families()
    template_name = families[family_index % len(families)]
    template = _env().get_template(template_name)
    base_constraints = ", ".join(config.constraints) if config.constraints else ""
    constraints_line = (
        f"{base_constraints}, {LINE_ART_EMPHASIS}" if base_constraints else LINE_ART_EMPHASIS
    )
    if config.style.notes:
        constraints_line = f"{constraints_line}, {config.style.notes}"

    text = template.render(
        element=page.element,
        composition_phrase=_composition_structure_phrase(page.composition),
        density_label=DENSITY_LABELS.get(page.density, "moderate"),
        symmetry_phrase=SYMMETRY_PHRASES.get(page.symmetry, page.symmetry),
        scale_phrase=SCALE_PHRASES.get(page.scale, page.scale),
        medium=config.style.medium,
        line_style=config.style.line_style,
        background=config.style.background,
        orientation=config.book.orientation,
        constraints_line=constraints_line,
    )
    text = " ".join(text.split())

    style_anchor = config.style.style_anchor or STYLE_ANCHORS[family_index % len(STYLE_ANCHORS)]
    audience_label = (config.book.audience or "adult").lower()
    if config.book.theme:
        text = f'Using a "{style_anchor}" style with a "{config.book.theme}" theme, create a {audience_label} coloring book image with {text}'
    else:
        text = f'Using a "{style_anchor}" style, create a {audience_label} coloring book image with {text}'

    if provider == "midjourney":
        params = f"--ar {midjourney_aspect_ratio(config)} --stylize {config.style.midjourney_stylize}"
        if config.style.midjourney_style_raw:
            params += " --style raw"
        return f"{text} {params}"

    return f"{text}. {config.book.orientation} orientation, {midjourney_aspect_ratio(config)} aspect ratio."


def generate_prompts(config: BookConfig, pages: list[PlannedPage], *, provider: str = "midjourney") -> dict[str, str]:
    """Returns {page_id: prompt}. Family chosen deterministically per page index."""
    return {page.id: render_prompt(config, page, i, provider=provider) for i, page in enumerate(pages)}


STATUS_LABELS = {
    "APPROVED": "✅ APPROVED",
    "NEEDS_REVIEW": "🔍 needs review",
    "REJECTED": "✗ rejected — needs regeneration",
    "NOT_GENERATED": "not yet generated",
}


def export_prompt_manifest(
    book_dir: Path,
    pages: list[PlannedPage],
    prompts: dict[str, str],
    *,
    repeat: int = 1,
    basename: str = "prompts",
    statuses: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    """repeat (Midjourney's --r) is only meaningful for provider="midjourney"
    prompts; pass repeat=1 for a generic-provider manifest.

    statuses: {page_id: "NOT_GENERATED"|"NEEDS_REVIEW"|"APPROVED"|"REJECTED"},
    e.g. from db.page_review_statuses(). When given, both files show review
    progress per page so already-decided pages don't get re-run by mistake."""
    statuses = statuses or {}
    metadata_dir = book_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    csv_path = metadata_dir / f"{basename}.csv"
    md_path = metadata_dir / f"{basename}.md"

    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["page_id", "element", "composition", "prompt", "status"])
        for page in pages:
            prompt = prompts[page.id]
            if repeat > 1:
                prompt = f"{prompt} --r {repeat}"
            status = statuses.get(page.id, "NOT_GENERATED")
            writer.writerow([page.id, page.element, page.composition, prompt, status])

    counts = {label: 0 for label in ("NOT_GENERATED", "NEEDS_REVIEW", "APPROVED", "REJECTED")}
    for page in pages:
        counts[statuses.get(page.id, "NOT_GENERATED")] += 1

    lines = [
        "# Prompt Manifest",
        "",
        f"Progress: {counts['APPROVED']} approved, {counts['NEEDS_REVIEW']} awaiting review, "
        f"{counts['REJECTED']} rejected, {counts['NOT_GENERATED']} not yet generated "
        f"(of {len(pages)} pages)",
        "",
    ]
    for page in pages:
        prompt = prompts[page.id]
        if repeat > 1:
            prompt = f"{prompt} --r {repeat}"
        status = statuses.get(page.id, "NOT_GENERATED")
        label = STATUS_LABELS[status]
        lines.append(f"## {page.id} — {page.element} / {_composition_phrase(page.composition)} — {label}")
        lines.append("")
        lines.append(f"```text\n{prompt}\n```")
        lines.append("")
    md_path.write_text("\n".join(lines))

    return csv_path, md_path
