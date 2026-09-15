# Book Factory

A local production pipeline for generative coloring books of **any kind**:
from a `book.yaml` definition to a KDP-ready interior PDF. Nothing in the
pipeline is adult-specific — `audience`, `theme`, `base_elements`, and
`constraints` are all free-form per book (see `book.yaml`/`book.json`
below), so a kids' book or an all-ages book works exactly the same way as
an adult one. `books/four_seasons/` and `books/ornamental_forms/` just both
happen to be adult titles.

See [`coloring_book_factory_prd.md`](coloring_book_factory_prd.md) for the
full product spec. This implements MVP 0.1 plus perceptual-hash duplicate
detection (PRD section 42/68). The PRD was written with Midjourney as the
running example — in practice, see the note below, that's not what ended up
working.

**No image generation is ever automated.** This tool generates prompts for
you to run manually in whatever tool you choose; everything after you
download the images is handled locally.

**On providers: use Gemini, not Midjourney.** The pipeline still generates
a Midjourney-flavored prompt manifest (`--ar`/`--stylize` flags and all),
but in real use, Midjourney's output for this specific style — clean,
uniform-width, fully-closed-shape line art meant to be colored — was
consistently poor, even with heavily tuned prompts; it kept drifting toward
shaded/illustrated results that don't work as a colorable page. **Gemini,
with the prompts this pipeline generates, produced usable line art
reliably** and is what every real book so far has actually been generated
with. Start with `prompts_generic.{csv,md}` (Gemini and friends); only
bother with `prompts_midjourney.{csv,md}` if you want to experiment
yourself.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Workflow

```bash
# 1. Scaffold a new book (directories, book.yaml, database)
uv run bookfactory init my_book --title "My Book" --author "Your Name" --target-pages 40
#    or, from a book.json spec (see "Defining a book with book.json" below):
uv run bookfactory init my_book --spec book.json

# 2. Generate a diverse page plan + copy-ready prompts (one file per
#    provider - Midjourney needs --ar/--stylize flags, everything else
#    doesn't and gets confused by them)
uv run bookfactory plan my_book
uv run bookfactory prompts my_book
#    -> books/my_book/metadata/prompts_generic.{csv,md}  (Gemini, Civitai, ... - use this one)
#    -> books/my_book/metadata/prompts_midjourney.{csv,md}

# 3. Generate the images in your chosen tool (Gemini is the one that's
#    actually worked well - see the provider note above) using those
#    prompts, then download them into books/my_book/inbox/

# 4. Ingest + basic QC (dimensions, gray/color detection, duplicate hashing)
uv run bookfactory ingest my_book

# 5. Review candidates in the browser (keyboard shortcuts: A/X/R/N/P),
#    then set final page order on the "Review book order" screen
uv run bookfactory serve
#    -> http://127.0.0.1:8000/my_book

# 6. Normalize approved pages to production size/DPI
uv run bookfactory process my_book

# 7. Build the interior PDF (uses your saved manual order if you set one,
#    otherwise a balanced auto-order)
uv run bookfactory build my_book

# 8. Run the KDP validation report
uv run bookfactory validate my_book

# 9. Optional: front/back cover as one KDP wraparound PDF
uv run bookfactory cover-prompts my_book
#    -> generate the art, save as books/my_book/cover/front_raw.png and back_raw.png
uv run bookfactory build-cover my_book
#    -> books/my_book/cover/cover.pdf (spine width computed from the current
#       page count - rebuild once the page count is final)
```

`bookfactory run <book_id>` chains steps 2 and pauses with instructions for
step 3, matching the PRD's human-in-the-loop generation queue.

If a step fails partway through for one asset, re-run QC/hashing for just
that asset with `bookfactory retry <book_id> <asset_id>`.

Re-running `prompts` at any time regenerates both manifests with live status
markers (`APPROVED` / `needs review` / `rejected` / `not yet generated`) for
every page, pulled from the database — safe to run as often as you like.

### Defining a book with `book.json`

For a new book, a simple spec is easier to work from than hand-editing every
`book.yaml` field:

```json
{
    "audience": "Adult",
    "style": "stained glass window",
    "theme": "4 Seasons",
    "model": "Gemini",
    "author": "MBOQ Colors",
    "page_count": 40,
    "create_cover": true,
    "border_type": "solid,black,square",
    "size": "8.5x11",
    "subtitle": "An Adult Coloring Collection",
    "bleed": false,
    "margin_width_inches": 1.0,
    "elements": ["flower", "wave", "leaf", "snowflake", "..."],
    "notes": ""
}
```

`style` and `border_type` become a single **fixed** style anchor and border
treatment used on every page — book-wide visual cohesion, not per-page
variety. `elements` is required and deliberately not auto-derived from
`theme`: picking a good, safe (non-representational, non-"correct-answer")
element list for a theme is a judgment call worth reviewing per book, not a
formula. `bookfactory init <id> --spec book.json` turns this into a full
`book.yaml`.

`audience` is free text (`"Adult"`, `"Kids"`, `"All Ages"`, whatever fits)
and flows straight into every generated prompt's wording — there's no
adult-only logic anywhere downstream of it, just per-book judgment calls
like which `elements`/`constraints` are actually appropriate for that
audience. `model` is likewise just a label recorded into the generated
`book.yaml`'s comments for your own reference (`# model: Gemini`) — it
doesn't route to a provider integration; see the provider note above for
why `"Gemini"` is the value worth defaulting to.

## Repository layout

```
app/            core library: config, db, planning, ingestion, qc, images,
                ordering, pdf, web (FastAPI review UI)
cli/main.py     Typer CLI (entry point: bookfactory)
books/<id>/     one self-contained book: book.yaml, style/, inbox/,
                originals/, candidates/, production/, interior/, metadata/
templates/      prompt-family and front/back-matter text templates
tests/          pytest unit tests + a full pipeline end-to-end test
```

Each book gets its own SQLite database at
`books/<id>/metadata/factory.db`, so books are fully independent — a second
book is just `bookfactory init another_book`, no code changes required.

## Testing

```bash
uv run pytest
```

## Deferred (see PRD section 64/68 for rationale)

n8n orchestration, a React frontend, image-embedding similarity, vision-model
QC, OCR text detection (no automated text/number detection in generated
art — this has to be caught by eye during review), and a multi-provider
`ImageGenerator` abstraction are intentionally out of scope for this pass —
the goal was the smallest system that can take one real book to a validated,
KDP-ready PDF plus cover.
