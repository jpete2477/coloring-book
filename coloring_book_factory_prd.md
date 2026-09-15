# PRD: Generative Coloring Book Production Pipeline

**Version:** 0.1  
**Status:** Proposed  
**Primary objective:** Build a local, repeatable production system that turns a book concept into a curated set of unique, stylistically consistent adult coloring pages and a KDP-ready interior PDF, while keeping Midjourney generation within Midjourney's permitted workflow.

---

## 1. Executive Summary

The product is a local "book factory" for producing adult coloring books.

The system should separate the creative generation step from the production pipeline:

1. Define a book.
2. Generate a controlled set of page specifications.
3. Generate prompts from those specifications.
4. Use Midjourney to create candidate artwork.
5. Ingest downloaded artwork automatically from a local folder.
6. Normalize and quality-check the images.
7. Detect likely duplicates or overly similar pages.
8. Present candidates in a fast visual review interface.
9. Approve, reject, or regenerate candidates.
10. Automatically order approved pages.
11. Build the interior PDF.
12. Run a final production validation.
13. Produce a package ready for KDP upload.

The important architectural decision is that **Midjourney is a creative input, not the automation engine**.

Midjourney currently prohibits unauthorized automation and third-party apps, so the system must not automate browser clicks, Discord commands, scraping, account interaction, or other mechanisms intended to control Midjourney. The user can generate images through the normal Midjourney web workflow, then the local pipeline takes over when files are downloaded. This keeps the system useful without depending on an unsupported or prohibited integration.

The architecture should nevertheless be provider-agnostic so that an API-based image generator can be added later if fully automated image generation becomes desirable.

---

# 2. Problem

Creating one coloring page is easy.

Creating 40-100 pages that are:

- visually consistent,
- genuinely different,
- sufficiently intricate,
- printable,
- free of unwanted text/artifacts,
- not repetitive,
- properly ordered,
- correctly sized,
- and ready for KDP

is a production problem rather than an individual image-generation problem.

Manual production creates several bottlenecks:

- deciding what to generate next,
- writing prompts,
- tracking what has already been generated,
- downloading and renaming files,
- checking image quality,
- detecting duplicates,
- converting images to production dimensions,
- organizing pages,
- assembling the manuscript,
- and validating the final PDF.

The goal of this project is to automate the repetitive parts while retaining human judgment where it creates the most value.

---

# 3. Product Vision

Create a reusable local publishing pipeline where a new coloring book can be defined by configuration rather than by rebuilding the process.

A new book should eventually be as simple as:

```text
create book.yaml
        |
        v
generate page specifications
        |
        v
generate prompts
        |
        v
generate artwork in Midjourney
        |
        v
drop downloads into /inbox
        |
        v
automatic processing + QC
        |
        v
review candidates
        |
        v
approve pages
        |
        v
automatic ordering
        |
        v
build KDP PDF
```

The long-term goal is not "a Midjourney automation script."

It is a **generative publishing system**.

---

# 4. Goals

## 4.1 Primary Goals

### G1. Generate unique but stylistically consistent pages

Pages should share a recognizable visual language while varying substantially in:

- base element,
- composition,
- repetition,
- scale,
- density,
- orientation,
- symmetry,
- negative space,
- and visual rhythm.

The system must explicitly prevent the book from becoming a collection of near-identical mandalas.

### G2. Reduce manual production work

Automate:

- prompt creation,
- page IDs,
- metadata,
- image ingestion,
- image normalization,
- basic QC,
- duplicate detection,
- ordering,
- PDF construction,
- and final validation.

### G3. Preserve human creative control

The user should make the final decision about:

- which images are good,
- which images belong in the book,
- ordering,
- and when a page should be regenerated.

### G4. Make production reproducible

Every page should be traceable to:

- a page specification,
- a prompt,
- a generation batch,
- a source image,
- processing steps,
- QC results,
- and approval status.

### G5. Produce KDP-ready output

The system should produce a print-ready PDF using configured trim size, bleed, margins, DPI, page order, and image placement.

### G6. Support multiple books

A second book should require a new configuration, not a new application.

---

# 5. Non-Goals

The MVP will NOT:

- automate Midjourney's website or Discord UI;
- scrape Midjourney;
- bypass Midjourney usage restrictions;
- attempt to reverse engineer a Midjourney API;
- automatically publish books to Amazon KDP;
- automatically choose every final image without human review;
- build a full commercial SaaS application;
- automatically vectorize every image;
- require cloud infrastructure.

---

# 6. Creative Design System

## 6.1 Core Visual Style

The initial product line uses:

- adult coloring-book line art;
- intricate black-and-white artwork;
- crisp clean outlines;
- pure white background;
- black linework;
- no color;
- no gray;
- no gradients;
- no conventional shading;
- no text;
- no numbers;
- no people;
- dense but colorable detail;
- repeating or decorative visual structures;
- sophisticated ornamental compositions;
- printable page layouts.

The important distinction is:

> The pages should have repetition and visual rhythm without becoming conventional radial mandalas.

---

# 7. Style Bible

Create a persistent `STYLE.md` for each product line.

Example:

```markdown
# Style Bible

## Medium
Intricate adult coloring-book line art.

## Linework
- crisp black outlines
- clean closed shapes
- consistent line weight
- high detail
- white background
- no gray
- no color
- no shading
- no gradients
- no large filled black areas

## Complexity
- adult-level complexity
- many small and medium coloring regions
- enough large regions to prevent the page from becoming unusable
- detailed without becoming visually muddy

## Composition
Use:
- interlocking patterns
- flowing patterns
- tiled structures
- nested structures
- overlapping motifs
- diagonal movement
- organic all-over patterns
- geometric lattices
- alternating bands
- asymmetric repetition
- layered motifs

Avoid:
- traditional mandalas
- single central objects
- concentric rings
- four identical quadrants
- kaleidoscope compositions
- generic clip art
- repetitive page templates
```

The style bible should be treated as product IP and version-controlled.

---

# 8. Page Diversity Model

The biggest creative risk is accidental repetition.

Do not generate pages by changing only the noun in one prompt.

Each page specification should combine multiple independent dimensions.

## 8.1 Base Elements

Examples:

- flower
- wheel
- butterfly
- bird
- shell
- feather
- leaf
- sun
- honeycomb
- crystal
- mushroom
- fish
- pinecone
- spiral
- star
- compass
- gear
- fan
- lattice
- window
- arch
- seashell
- beetle
- dragonfly
- tree
- vine
- wave
- eye
- crown
- key

The list should be configurable.

## 8.2 Composition Types

Examples:

- organic all-over
- interlocking
- flowing diagonal
- four-way tile
- nested
- alternating bands
- overlapping
- asymmetric repeating
- vertical flow
- horizontal flow
- geometric lattice
- clustered
- mirrored
- staggered
- woven
- spiral flow
- branching
- framed
- border-driven
- central motif with distributed secondary elements

Avoid using "mandala" as a positive prompt term when the goal is to avoid radial compositions.

## 8.3 Scale

Each page can vary:

- macro motifs
- medium motifs
- fine detail
- mixed scale
- large dominant forms with small supporting forms
- dense uniform detail

## 8.4 Density

Define a controlled range:

```text
1 = sparse
2 = light
3 = moderate
4 = dense
5 = extremely intricate
```

Most adult pages should target 4 or 5, but not every page should use maximum density.

## 8.5 Symmetry

Allow:

- none
- loose symmetry
- bilateral
- four-way
- tiled
- rotational

But explicitly constrain rotational symmetry so it does not dominate the entire book.

## 8.6 Page Boundary

Possible treatments:

- enclosed border
- decorative frame
- open edge
- edge-to-edge pattern
- central framed composition
- border plus open interior

---

# 9. Book Definition

Each book should be defined in YAML.

Example:

```yaml
book:
  id: ornamental_forms_001
  title: "Ornamental Forms"
  trim_size: "8.5x11"
  orientation: portrait
  target_pages: 40
  bleed: true

style:
  style_reference: "./style/style-reference.jpg"
  style_weight: 150
  medium: "adult coloring book line art"
  line_style: "crisp clean black ink outlines"
  background: "pure white"
  complexity: "high"

base_elements:
  - flower
  - wheel
  - butterfly
  - bird
  - shell
  - feather
  - leaf
  - sun
  - honeycomb
  - crystal
  - mushroom
  - fish
  - pinecone
  - spiral
  - star

compositions:
  - organic all-over
  - interlocking
  - flowing diagonal
  - nested
  - alternating bands
  - four-way tile
  - overlapping
  - asymmetric repeating
  - flowing vertical
  - geometric lattice

constraints:
  - no text
  - no numbers
  - no people
  - no shading
  - no gray
  - no color
  - no gradients
  - no solid black areas
  - no traditional mandala
  - no single central object
  - no concentric rings
  - no generic clip art

production:
  dpi: 300
  border: true
  target_width_inches: 8.5
  target_height_inches: 11
```

---

# 10. Page Specification

Each planned page should have a machine-readable specification.

Example:

```yaml
id: OF001-017
element: butterfly
composition: flowing_diagonal
density: 4
symmetry: loose
scale: mixed
border: decorative
variation_seed: 82731
status: planned
```

A page specification is different from a generated image.

One specification may produce multiple candidates.

---

# 11. Prompt Generation

The system should generate prompts from page specifications rather than requiring the user to write every prompt manually.

Example template:

```text
intricate adult coloring book line art of [BASE ELEMENT],
[COMPOSITION TYPE] composition with [DENSITY] detail,
[SYMMETRY DESCRIPTION], mixed-scale ornamental forms,
clean closed black ink outlines on a pure white background,
dense but highly colorable regions, sophisticated decorative pattern,
strong visual rhythm and repetition,
full-page portrait composition with a refined border,
no text, no numbers, no color, no gray, no shading,
no gradients, no solid black areas,
no traditional mandala, no concentric rings, no single central object,
no generic clip art
```

The prompt generator should support prompt families.

Instead of one prompt template, maintain 5-10 templates that express the same visual language differently.

This prevents prompt-template repetition from becoming a source of visual repetition.

---

# 12. Midjourney Strategy

Midjourney should be treated as the primary creative generation tool for the initial MVP.

## 12.1 Style Reference

Use one or more approved sample pages as Style References.

Midjourney's Style Reference feature is designed to carry visual characteristics such as medium, texture, and overall aesthetic into new creations. It supports image references and a configurable style weight. This is useful for maintaining a consistent product-line visual identity. 

Recommended starting approach:

```text
style reference image
+
simple content-focused prompt
+
controlled variation
```

Do not overload the prompt with contradictory style instructions.

## 12.2 Style Reference Asset

Store:

```text
style/
  style-reference-v1.png
  style-reference-v1.yaml
```

Metadata:

```yaml
version: 1
source_pages:
  - approved/OF001-001.png
  - approved/OF001-004.png
style_weight: 150
midjourney_version: "current"
notes: "Primary visual DNA"
```

## 12.3 Midjourney Generation Workflow

The user:

1. Opens Midjourney normally.
2. Uses generated prompts.
3. Applies the approved Style Reference.
4. Generates candidate images.
5. Downloads candidates into the local `inbox/` directory.

The local system then handles everything after download.

## 12.4 Repeat

Midjourney supports `--repeat` for generating multiple sets from the same prompt. Use this selectively for promising page specifications rather than relying on one image per specification.

Example:

```text
--r 3
```

The number of available repeats depends on the user's Midjourney plan.

## 12.5 Variation

Use Midjourney's normal variation tools for strong candidates that are close but not quite right.

The local system should track which page specification produced the candidate, even when multiple variants are downloaded.

---

# 13. Candidate Ingestion

Create a local watched directory:

```text
books/ornamental_forms/inbox/
```

Downloaded Midjourney images are copied into this directory.

A file watcher detects new files.

Example:

```text
inbox/
  image_001.png
  image_002.png
```

The ingestion process:

1. Detect new file.
2. Generate unique asset ID.
3. Preserve original.
4. Extract image metadata.
5. Create thumbnail.
6. Run image normalization preview.
7. Run automated QC.
8. Calculate similarity fingerprints.
9. Add candidate to review database.

The original file must never be overwritten.

---

# 14. Asset Naming

Use deterministic names.

Recommended:

```text
BOOKID-PAGEID-CANDIDATEID.ext
```

Example:

```text
OF001-017-C03.png
```

Where:

- `OF001` = book
- `017` = planned page
- `C03` = third candidate

If a downloaded file cannot be confidently mapped to a planned page, use:

```text
UNASSIGNED-20260913-0001.png
```

and allow manual assignment in the review UI.

---

# 15. Data Model

Use SQLite for the MVP.

It is preferable to CSV as the primary datastore because the workflow has relationships, state transitions, and multiple candidates per page.

CSV should remain available for export.

## 15.1 Books

```text
books
------
id
title
version
config_path
created_at
updated_at
status
```

## 15.2 Page Specifications

```text
page_specs
----------
id
book_id
sequence
element
composition
density
symmetry
scale
border
prompt
status
created_at
```

## 15.3 Assets

```text
assets
------
id
page_spec_id
source_path
original_path
normalized_path
thumbnail_path
width
height
dpi
file_size
created_at
```

## 15.4 QC Results

```text
qc_results
----------
id
asset_id
resolution_score
line_art_score
text_detected
gray_detected
color_detected
black_fill_score
edge_quality_score
duplicate_score
overall_score
machine_decision
notes
created_at
```

## 15.5 Reviews

```text
reviews
-------
id
asset_id
decision
quality
complexity
uniqueness
notes
reviewed_at
```

## 15.6 Book Pages

```text
book_pages
----------
id
book_id
asset_id
final_sequence
page_role
status
```

---

# 16. Review States

Use a finite state machine.

```text
PLANNED
  |
  v
PROMPT_READY
  |
  v
AWAITING_GENERATION
  |
  v
INGESTED
  |
  v
QC_FAILED -----> REJECTED
  |
  v
REVIEW
  |
  +-----> REJECTED
  |
  +-----> REGENERATE
  |
  v
APPROVED
  |
  v
ORDERED
  |
  v
IN_PRODUCTION
  |
  v
FINAL
```

---

# 17. Automated QC

Automated QC should filter obvious failures, not make the final artistic decision.

## 17.1 Basic Image Checks

Python/Pillow/OpenCV should check:

- image dimensions;
- aspect ratio;
- alpha channel;
- grayscale/color channels;
- percentage of near-white pixels;
- percentage of dark pixels;
- excessive solid-black areas;
- border presence;
- empty regions;
- edge clipping;
- resolution;
- file integrity.

## 17.2 Color Check

Target:

```text
pure black + pure white
```

The pipeline can convert the production image to grayscale and optionally threshold it.

However, retain the original candidate so the normalization operation is reversible.

## 17.3 Gray Detection

Flag candidates with significant intermediate grayscale pixels.

Do not automatically reject small antialiasing values because normal rasterization can create gray edge pixels.

Use thresholds.

Example:

```text
black <= 32
white >= 240
gray = 33..239
```

Then calculate:

```text
gray_percentage
```

A configurable threshold determines whether the image is flagged.

## 17.4 Text Detection

Use an OCR or vision model to detect likely text.

A candidate containing text should be flagged.

Do not assume OCR failure means the image contains no text.

## 17.5 Vision QC

A vision model can evaluate:

- line-art quality;
- coloring-book suitability;
- complexity;
- visual clutter;
- presence of shading;
- presence of text;
- obvious artifacts;
- whether the image resembles a traditional mandala;
- whether the page is meaningfully different from existing pages.

The result should be a score plus reasons.

Example:

```json
{
  "quality": 8,
  "colorability": 9,
  "uniqueness": 8,
  "artifact_risk": 2,
  "text_risk": 0,
  "decision": "review"
}
```

---

# 18. Duplicate Detection

Duplicate detection is critical.

The system should use multiple levels.

## Level 1: Exact Hash

Use SHA-256 to identify exact duplicate files.

## Level 2: Perceptual Hash

Use pHash/dHash/aHash to catch visually similar images after resizing.

## Level 3: Image Embeddings

Use an image embedding model to identify semantic/structural similarity.

Store an embedding for each approved page.

For every new candidate:

```text
similarity(candidate, every approved page)
```

Flag candidates above a configurable threshold.

The system should NOT automatically reject all similar pages.

It should say:

> "Likely similar to page 12: 0.91"

and let the user decide.

---

# 19. Uniqueness Scoring

Create a book-level diversity score.

Potential components:

```text
element diversity
composition diversity
visual embedding distance
density diversity
symmetry diversity
scale diversity
```

Example:

```text
uniqueness_score =
  20% element difference
+ 20% composition difference
+ 30% embedding distance
+ 10% density difference
+ 10% symmetry difference
+ 10% scale difference
```

The weights should be configurable.

---

# 20. Review Interface

Build a local web application.

Recommended MVP technology:

- Python
- FastAPI
- simple HTML/JS frontend

Alternative:

- Streamlit for fastest prototype

Long-term:

- React frontend
- FastAPI backend

## 20.1 Review Screen

Each candidate displays:

- large image;
- page specification;
- prompt;
- candidate number;
- QC scores;
- duplicate warnings;
- related approved pages;
- buttons.

Actions:

```text
APPROVE
REJECT
REGENERATE
ASSIGN
NEXT
PREVIOUS
```

## 20.2 Keyboard Shortcuts

Recommended:

```text
A = approve
X = reject
R = regenerate
N = next
P = previous
1-5 = quality score
U = uniqueness score
C = complexity score
```

The goal is to make review extremely fast.

---

# 21. Production Image Normalization

Every approved image passes through a deterministic processing pipeline.

```text
Original
   |
   v
Orientation normalization
   |
   v
Crop / fit
   |
   v
Grayscale
   |
   v
Optional threshold
   |
   v
Artifact cleanup
   |
   v
Border normalization
   |
   v
Resize
   |
   v
300 DPI metadata
   |
   v
Production PNG
```

Never destroy the source image.

---

# 22. Image Dimensions

For an 8.5 x 11 inch trim size at 300 DPI:

```text
2550 x 3300 pixels
```

For full bleed:

```text
8.625 x 11.25 inches
```

At 300 DPI:

```text
2588 x 3375 pixels
```

The production system should calculate these values from configuration rather than hard-code them.

KDP currently requires full-bleed interior PDFs to extend 0.125 inch beyond the trim on the top, bottom, and outside edges. KDP also requires images to be at least 300 DPI. citeturn0search1turn0search4

---

# 23. Border Strategy

For the first product version, prefer a safe interior border.

Why:

- reduces accidental clipping;
- provides visual consistency;
- simplifies production;
- makes pages easier to color;
- reduces dependence on bleed.

The book can still use a full-bleed manuscript if the design calls for it, but the system must support both:

```yaml
bleed: false
```

and

```yaml
bleed: true
```

---

# 24. Book Ordering

Do not simply order pages alphabetically.

The system should support ordering algorithms.

## 24.1 Manual Order

User drags pages into final order.

## 24.2 Automatic Balanced Order

Attempt to alternate:

- dense / moderate;
- organic / geometric;
- symmetrical / asymmetric;
- light / complex;
- different base elements.

Example:

```text
Flower
Wheel
Bird
Shell
Geometric
Butterfly
Leaf
Mechanical
...
```

## 24.3 Page Sequence Constraints

A book configuration can specify:

```yaml
ordering:
  avoid_adjacent_same_element: true
  avoid_adjacent_same_composition: true
  target_density_variation: true
```

---

# 25. Book Builder

The book builder should produce:

```text
interior.pdf
```

and optionally:

```text
interior-preview.pdf
```

The PDF builder should:

- create one PDF page per image;
- preserve page dimensions;
- place images at the correct size;
- embed required content;
- avoid unintended scaling;
- preserve page order;
- add optional front matter;
- add optional copyright page;
- add optional "This book belongs to" page;
- add optional blank pages;
- validate the final page count.

For KDP, manuscript files with bleed must be PDF, and KDP requires single-page files rather than spreads. citeturn0search1

---

# 26. Front Matter

The system should support configurable pages:

```yaml
front_matter:
  - title_page
  - copyright_page
  - belongs_to_page
  - intro_page
```

Example title page:

```text
ORNAMENTAL FORMS

An Adult Coloring Collection

by [Author]
```

The actual content should be configurable.

---

# 27. Back Matter

Support:

```yaml
back_matter:
  - thank_you
  - related_books
  - website
```

This should be optional.

---

# 28. Cover Pipeline

The interior system should be separated from the cover system.

Cover generation may use:

- Midjourney artwork;
- generated artwork from another image provider;
- manually designed artwork;
- a template.

The cover builder should eventually accept:

```yaml
cover:
  title: "Ornamental Forms"
  subtitle: "An Adult Coloring Collection"
  author: "Author Name"
  finish: matte
```

KDP's cover has its own bleed and sizing requirements and should be generated from the final page count and selected print options. KDP provides a cover calculator/template workflow. citeturn0search9

---

# 29. KDP Validation

Create a final validation command:

```bash
bookfactory validate books/ornamental_forms/book.yaml
```

Output:

```text
BOOK VALIDATION

[PASS] Page count
[PASS] Page dimensions
[PASS] 300 DPI
[PASS] No missing pages
[PASS] No duplicate pages
[PASS] All pages grayscale
[PASS] No unexpected color
[PASS] PDF readable
[PASS] File size
[PASS] Page order
[WARN] 2 pages have high visual similarity
[PASS] Interior margins
```

KDP currently caps manuscript file size at 650 MB and requires images to be at least 300 DPI. citeturn0search1turn0search2

---

# 30. Technical Architecture

## 30.1 Recommended Stack

### Core

- Python 3.12+
- SQLite
- FastAPI
- Pydantic
- Pillow
- OpenCV
- NumPy

### PDF

- ReportLab
- PyMuPDF for validation/inspection

### Frontend

MVP:

- Jinja2/HTML
- lightweight JavaScript

Future:

- React
- TypeScript

### Orchestration

- n8n

Use n8n for workflow-level orchestration, notifications, scheduled tasks, and external integrations.

Do not put core image-processing logic in n8n.

### Packaging

- Docker
- Docker Compose

### Version Control

- Git

---

# 31. Suggested Repository

```text
coloring-book-factory/
│
├── README.md
├── PRD.md
├── STYLE.md
├── docker-compose.yml
├── .env.example
├── pyproject.toml
│
├── app/
│   ├── api/
│   ├── db/
│   ├── models/
│   ├── services/
│   ├── qc/
│   ├── images/
│   ├── pdf/
│   ├── prompts/
│   ├── ordering/
│   └── web/
│
├── cli/
│
├── books/
│   └── ornamental_forms/
│       ├── book.yaml
│       ├── style/
│       ├── inbox/
│       ├── originals/
│       ├── candidates/
│       ├── approved/
│       ├── rejected/
│       ├── production/
│       ├── previews/
│       ├── metadata/
│       ├── interior/
│       └── cover/
│
├── templates/
│   ├── prompts/
│   ├── frontmatter/
│   └── cover/
│
├── scripts/
│
└── tests/
```

---

# 32. CLI

The system should be usable from the command line.

## Create a book

```bash
bookfactory init ornamental_forms
```

## Generate page specifications

```bash
bookfactory plan ornamental_forms
```

## Generate prompts

```bash
bookfactory prompts ornamental_forms
```

## Ingest images

```bash
bookfactory ingest ornamental_forms
```

## Run QC

```bash
bookfactory qc ornamental_forms
```

## Build production images

```bash
bookfactory process ornamental_forms
```

## Build PDF

```bash
bookfactory build ornamental_forms
```

## Validate

```bash
bookfactory validate ornamental_forms
```

## Full production pipeline

```bash
bookfactory run ornamental_forms
```

The full command should never automatically control Midjourney. It should pause at the generation stage and report:

```text
32 page specifications are ready.

Generate the images in Midjourney and place the downloaded files into:

books/ornamental_forms/inbox/

Run:

bookfactory ingest ornamental_forms
```

---

# 33. Prompt Manifest

Export prompts to a CSV that is easy to use manually.

Example:

```csv
page_id,element,composition,prompt,status
OF001-001,flower,organic_all_over,"...",READY
OF001-002,wheel,mechanical_lattice,"...",READY
OF001-003,bird,flowing_diagonal,"...",READY
```

This gives the user a practical bridge between the local automation system and Midjourney.

---

# 34. Midjourney Work Queue

The local UI should have a "Generation Queue" view.

Example:

```text
READY TO GENERATE

001  FLOWER       ORGANIC ALL-OVER       [Copy Prompt]
002  WHEEL        LATTICE                [Copy Prompt]
003  BIRD         FLOWING DIAGONAL       [Copy Prompt]
004  SHELL        NESTED                 [Copy Prompt]
```

Buttons:

```text
Copy Prompt
Open Book
Mark Generated
Skip
```

This is intentionally human-in-the-loop.

---

# 35. Organizing Midjourney Output

Midjourney's current Organize interface supports sorting, filtering, downloading, and folders. The local system should not depend on scraping that interface. Instead, use normal downloads and let the local folder watcher handle the files. citeturn0search5

If the user prefers, Midjourney can be organized into a project/folder structure manually while the local system remains the source of truth for production metadata.

---

# 36. n8n Integration

n8n is useful for orchestration around the local application.

Example workflow:

```text
Book created
   |
   v
Generate page plan
   |
   v
Generate prompt manifest
   |
   v
Notify user
   |
   v
[Human generates in Midjourney]
   |
   v
Folder watcher / ingest
   |
   v
QC
   |
   v
Review queue
   |
   v
Approved threshold reached
   |
   v
Build preview PDF
   |
   v
Notify user
```

Potential notifications:

- email;
- desktop notification;
- webhook;
- Slack/Discord if desired.

---

# 37. Folder Watcher

A local watcher can monitor:

```text
books/*/inbox/
```

When an image appears:

```text
file created
    |
    v
wait for write completion
    |
    v
copy original
    |
    v
create asset record
    |
    v
generate thumbnail
    |
    v
QC
    |
    v
review queue
```

This is one of the highest-value automation points because it eliminates repetitive file handling without interacting with Midjourney itself.

---

# 38. Review UI Example

Dashboard:

```text
ORNAMENTAL FORMS
-----------------

Target pages:        40
Approved:            31
Needs review:         7
Rejected:            22
Generation needed:    2

Book diversity:      87%
Average QC:          8.4
Potential duplicates: 1
```

Candidate:

```text
+--------------------------------+
|                                |
|          IMAGE                 |
|                                |
+--------------------------------+

Page: OF001-032
Element: Butterfly
Composition: Flowing Diagonal

QC: 8.7
Uniqueness: 9.1
Text Risk: 0
Gray Risk: Low
Duplicate Risk: Low

[A] Approve
[X] Reject
[R] Regenerate
```

---

# 39. Regeneration Workflow

When a page is rejected, record why.

Examples:

```text
too sparse
too similar to page 12
too much black
contains shading
contains text
bad line quality
composition too radial
not sufficiently colorable
wrong subject
```

The regeneration engine should use rejection reasons to modify the prompt.

Example:

```text
Original:
intricate flower pattern...

Feedback:
"Too much radial symmetry"

Modified:
intricate flower pattern, flowing diagonal composition,
asymmetric repeating structure, no radial symmetry...
```

This creates a learning loop.

---

# 40. Human Review Is the Creative Gate

The system should not optimize for "maximum automation."

The correct optimization target is:

> Minimum human effort per finished, high-quality page.

Human judgment remains the final authority.

A 95% automated workflow that produces mediocre pages is worse than an 80% automated workflow that makes final selection extremely fast.

---

# 41. Performance Targets

For an initial 40-page book:

### Planning

< 30 seconds

### Prompt generation

< 5 seconds

### Ingestion

< 5 seconds per image

### Thumbnail generation

< 1 second per image

### Basic QC

< 3 seconds per image

### Duplicate analysis

Target < 2 seconds per candidate against 100 approved pages

### PDF build

< 30 seconds

### Final validation

< 30 seconds

The exact timings are implementation targets, not hard requirements.

---

# 42. MVP Scope

Do NOT build everything at once.

## MVP 0.1

Build only:

1. `book.yaml`
2. page specification generator
3. prompt generator
4. local inbox
5. image ingestion
6. thumbnails
7. basic image QC
8. SQLite database
9. simple review UI
10. approval/rejection
11. image normalization
12. PDF builder
13. KDP validation

This is enough to produce a real book.

---

# 43. MVP 0.2

Add:

- perceptual hashing;
- duplicate detection;
- automatic ordering;
- front matter;
- richer review scoring;
- CSV export;
- prompt regeneration;
- book statistics.

---

# 44. MVP 0.3

Add:

- image embeddings;
- vision-model QC;
- similarity explanations;
- book-level diversity optimization;
- regeneration suggestions;
- cover builder;
- n8n integration.

---

# 45. V1

Add:

- multiple image-generation providers;
- API-based image generation where permitted;
- batch generation workflows;
- automatic candidate routing;
- advanced book templates;
- multiple product lines;
- analytics;
- reusable style profiles;
- production history;
- versioned books.

---

# 46. Provider Abstraction

Define an interface:

```python
class ImageGenerator(Protocol):

    def generate(
        self,
        prompt: str,
        style_reference: str | None = None,
        count: int = 1
    ) -> list[GeneratedImage]:
        ...
```

Implementations:

```text
MidjourneyProvider
OpenAIProvider
FluxProvider
OtherProvider
```

The initial Midjourney provider should NOT automatically call Midjourney.

Instead:

```python
class MidjourneyManualProvider:
    def export_queue(self, pages):
        ...
```

It generates:

- prompt manifest;
- generation checklist;
- copy-ready prompts;
- style-reference metadata.

A future API provider can implement actual generation if its API terms support it.

---

# 47. Configuration-Driven Design

Avoid code like:

```python
if book == "ornamental_forms":
```

Instead:

```python
book = load_book("book.yaml")
```

Everything possible should come from configuration.

This makes it possible to create:

```text
book A: ornamental patterns
book B: botanical patterns
book C: geometric patterns
book D: animals
book E: fantasy
```

using the same production engine.

---

# 48. Testing Strategy

## Unit Tests

Test:

- page generation;
- prompt generation;
- file naming;
- image dimensions;
- DPI;
- grayscale conversion;
- border placement;
- PDF dimensions;
- ordering;
- state transitions.

## Golden Image Tests

Maintain a small set of known test images.

Verify:

```text
input image
   ->
normalized image
```

produces expected dimensions and color properties.

## PDF Tests

Validate:

- page count;
- page size;
- image placement;
- no missing pages;
- PDF opens successfully.

## End-to-End Test

Create a tiny test book:

```text
5 pages
```

and run the entire pipeline.

---

# 49. Observability

Every pipeline step should log:

```text
timestamp
book_id
asset_id
operation
duration
result
error
```

Example:

```text
2026-09-13 10:42:13
OF001-017-C03
normalize
1.82s
PASS
```

---

# 50. Error Handling

Never lose source assets.

If a step fails:

```text
original -> preserved
candidate -> preserved
error -> recorded
```

Failed processing should be retryable.

Example:

```bash
bookfactory retry OF001-017-C03
```

---

# 51. Security

Keep API keys and credentials out of Git.

Use:

```text
.env
```

and:

```text
.env.example
```

Never store:

- API keys;
- Midjourney credentials;
- session cookies;
- browser tokens.

The local application should run without needing access to the Midjourney account.

---

# 52. Copyright / Commercialization Considerations

The production system should maintain provenance metadata.

For every approved image, store:

```text
generation provider
generation date
prompt
style reference
model/version if known
source asset
processing history
```

This creates a production record for each page.

The user should independently review the current terms of each image-generation provider before commercial publication and retain records of the applicable terms.

---

# 53. Style Consistency Strategy

Use three layers.

## Layer 1: Product-line style

The Style Bible.

## Layer 2: Midjourney style reference

The approved visual reference.

## Layer 3: Prompt constraints

The page-specific composition and content.

This creates:

```text
STYLE
  +
CONTENT
  +
COMPOSITION
  =
PAGE
```

Do not attempt to force every stylistic characteristic into the text prompt.

Midjourney's own guidance recommends keeping text prompts relatively simple when using Style References and focusing the text prompt on the content. citeturn0search0

---

# 54. Style Reference Management

Store style references as versioned assets.

Example:

```text
style/
├── style-v1/
│   ├── reference-01.png
│   ├── reference-02.png
│   └── manifest.yaml
├── style-v2/
│   └── ...
└── active.yaml
```

This allows a future book to intentionally use:

```yaml
style_reference:
  version: v2
```

rather than silently changing the entire product line.

Midjourney also provides a Style Creator that produces reusable custom Style Reference Codes. Those can be stored as metadata alongside image-based style references. citeturn0search7

---

# 55. Diversity Planning Algorithm

Before generating any images, the system should create a page matrix.

For 40 pages:

```text
10 base-element families
8 composition families
5 density levels
4 symmetry modes
```

The planner selects combinations while minimizing repetition.

Example:

```text
Page 01
flower + organic + dense + loose symmetry

Page 02
wheel + lattice + moderate + bilateral

Page 03
bird + diagonal + dense + asymmetric

Page 04
shell + nested + light + radial-lite

...
```

The system should reject a plan if:

```text
same element appears too frequently
same composition repeats too frequently
same combination occurs twice
```

unless explicitly allowed.

---

# 56. Page Matrix Constraints

Example:

```yaml
diversity:
  max_same_element_consecutive: 1
  max_same_composition_consecutive: 1
  max_same_element_count: 4
  max_same_composition_count: 6
  max_duplicate_combination_count: 1
```

---

# 57. Prompt Permutations

Use structured permutations rather than random word soup.

Example:

```text
BASE:
flower

COMPOSITION:
interlocking

STRUCTURE:
nested organic geometry

MOVEMENT:
flowing diagonal

DENSITY:
high

SCALE:
mixed

STYLE:
product-line style reference

CONSTRAINTS:
line art, black and white, no shading...
```

This produces controlled variation.

---

# 58. Candidate Budget

Do not generate exactly one image per final page.

Recommended initial target:

```text
40 final pages
x
3 candidates/page
=
120 candidates
```

Then use:

```text
120 candidates
  ->
automatic QC
  ->
~80 reviewable
  ->
~50 strong
  ->
40 final
```

Actual ratios will be learned during the first book.

The system should track these conversion rates.

---

# 59. Production Metrics

Track:

```text
candidate_count
approved_count
rejected_count
approval_rate
average_candidates_per_page
average_review_time
duplicate_rate
qc_failure_rate
regeneration_rate
```

Example dashboard:

```text
Book: Ornamental Forms

Candidates:          126
Approved:             40
Rejected:             71
Pending:              15

Approval rate:       31.7%
Avg candidates/page:  3.15
Duplicate flags:       7
QC failures:          18

Avg review time:      11 sec
```

This data will improve the process over time.

---

# 60. Suggested Development Order

## Phase 1: Skeleton

Build:

```text
book.yaml
SQLite
CLI
directory structure
```

## Phase 2: Planning

Build:

```text
page specification generator
diversity planner
prompt generator
CSV export
```

## Phase 3: Ingestion

Build:

```text
folder watcher
asset ingestion
thumbnail creation
metadata
```

## Phase 4: Review

Build:

```text
review UI
approve/reject
keyboard shortcuts
```

## Phase 5: Production

Build:

```text
normalization
ordering
PDF generation
```

## Phase 6: Validation

Build:

```text
KDP validator
PDF inspection
production report
```

## Phase 7: Intelligence

Build:

```text
perceptual similarity
embeddings
vision QC
diversity scoring
```

---

# 61. Definition of Done for MVP

MVP is complete when the user can:

1. Create a new `book.yaml`.
2. Generate 40 page specifications.
3. Generate 40 copy-ready prompts.
4. Generate images manually in Midjourney.
5. Drop downloaded images into `inbox/`.
6. Have the system ingest them automatically.
7. Review them in a browser.
8. Approve/reject with keyboard shortcuts.
9. Automatically normalize approved pages.
10. Reorder approved pages.
11. Generate an interior PDF.
12. Run validation.
13. Receive a clear PASS/FAIL report.
14. Open the resulting PDF and see a correctly ordered, printable book.

---

# 62. Example End-to-End Session

```bash
bookfactory init ornamental_forms
```

Edit:

```text
books/ornamental_forms/book.yaml
```

Then:

```bash
bookfactory plan ornamental_forms
```

Output:

```text
Created 40 page specifications.

40 unique element/composition combinations.
0 duplicate combinations.
```

Then:

```bash
bookfactory prompts ornamental_forms
```

Output:

```text
Created:

books/ornamental_forms/metadata/prompts.csv
books/ornamental_forms/metadata/prompts.md
```

Generate those prompts manually in Midjourney.

Download images into:

```text
books/ornamental_forms/inbox/
```

Then:

```bash
bookfactory ingest ornamental_forms
```

Output:

```text
Imported 117 candidates.
103 passed basic QC.
14 flagged.
```

Open:

```text
http://localhost:8000
```

Review.

Approve 40.

Then:

```bash
bookfactory process ornamental_forms
```

Then:

```bash
bookfactory build ornamental_forms
```

Then:

```bash
bookfactory validate ornamental_forms
```

Output:

```text
FINAL VALIDATION
================

Book: Ornamental Forms
Pages: 44
Trim: 8.5 x 11
Bleed: Yes
Resolution: PASS
Color mode: PASS
Page dimensions: PASS
PDF: PASS
File size: PASS

RESULT: READY FOR MANUAL KDP UPLOAD
```

---

# 63. Future Fully Automated Generation

If the goal eventually becomes:

```text
book definition
    ->
automatically generate 500 images
    ->
automatically select 40
    ->
automatically build book
```

then Midjourney should not be the architectural dependency.

Instead:

```text
ImageGenerator interface
        |
        +-- MidjourneyManual
        |
        +-- APIProviderA
        |
        +-- APIProviderB
```

The rest of the system remains unchanged.

This is the key architectural hedge.

---

# 64. Recommended First Implementation

Build the smallest system that can produce one real book.

Do not start with:

- n8n;
- React;
- AI agents;
- embeddings;
- sophisticated computer vision;
- cover automation;
- multi-provider generation.

Start with:

```text
Python
SQLite
FastAPI
Pillow
ReportLab
simple HTML/JS
YAML
Git
```

Then add intelligence only after producing the first book.

---

# 65. Recommended Initial Book Experiment

Use:

```text
40 final coloring pages
120 target candidates
```

Track:

- how many candidates are actually usable;
- what causes rejection;
- what types of prompts create near-duplicates;
- which composition types work;
- how much time review takes;
- whether the Style Reference keeps the style consistent;
- whether normalization damages line quality;
- whether KDP proofing exposes any production problems.

The first book is both a product and a systems test.

---

# 66. Critical Product Principle

The most important design principle is:

> Automate the mechanical work, not the creative judgment.

The system should make it extremely cheap to explore, compare, reject, regenerate, organize, and publish.

The human should spend time on:

- style;
- quality;
- taste;
- book-level coherence;
- final selection.

Everything else should increasingly become software.

---

# 67. Initial Deliverables

The first implementation should produce:

```text
PRD.md
STYLE.md
book.yaml
prompt templates
SQLite schema
CLI
ingestion service
QC service
review UI
normalization pipeline
PDF builder
KDP validator
README
Docker Compose configuration
```

---

# 68. Acceptance Criteria

The project passes MVP acceptance when:

### Creative

- [ ] Pages are recognizably part of the same product line.
- [ ] Pages are not dominated by conventional mandala compositions.
- [ ] Base elements vary.
- [ ] Composition types vary.
- [ ] Pages are sufficiently intricate for adult coloring.
- [ ] No page contains intentional text.

### Technical

- [ ] Source images are never destroyed.
- [ ] Every candidate has an asset ID.
- [ ] Every approved page is traceable to its source.
- [ ] Duplicate detection works at least at the perceptual-hash level.
- [ ] Production images are 300 DPI.
- [ ] PDF page dimensions are correct.
- [ ] PDF page count matches the manifest.
- [ ] Validation catches missing or malformed pages.

### Workflow

- [ ] New book setup takes minutes rather than hours.
- [ ] Candidate ingestion requires only dropping files into a folder.
- [ ] Review can be performed primarily with keyboard shortcuts.
- [ ] Final PDF can be rebuilt from the database/configuration.
- [ ] A second book can be created without changing application code.

---

# 69. Final Architecture

```text
                    BOOK DEFINITION
                          |
                          v
                 +------------------+
                 | Diversity Planner|
                 +------------------+
                          |
                          v
                 +------------------+
                 | Prompt Generator |
                 +------------------+
                          |
                          v
                 +------------------+
                 | Generation Queue |
                 +------------------+
                          |
                          v
                 +----------------------+
                 |     MIDJOURNEY       |
                 |   HUMAN GENERATION   |
                 +----------------------+
                          |
                    downloaded files
                          |
                          v
                 +------------------+
                 |   Folder Watcher |
                 +------------------+
                          |
                          v
                 +------------------+
                 |     Ingestion    |
                 +------------------+
                          |
                          v
                 +------------------+
                 |   Basic QC       |
                 +------------------+
                          |
                          v
                 +------------------+
                 | Similarity/QC    |
                 +------------------+
                          |
                          v
                 +------------------+
                 |   Review UI      |
                 +------------------+
                    |          |
                 reject      approve
                    |          |
                    v          v
                regenerate   normalize
                               |
                               v
                         +-----------+
                         |  Ordering |
                         +-----------+
                               |
                               v
                         +-----------+
                         | PDF Build |
                         +-----------+
                               |
                               v
                         +-----------+
                         | Validate  |
                         +-----------+
                               |
                               v
                        KDP-READY PDF
```

---

# 70. Decision Summary

### Use Midjourney?

**Yes.** It is a strong fit for the initial creative generation workflow.

### Automate Midjourney?

**No, not through unauthorized UI/Discord/browser automation.** Use the normal Midjourney interface and automate everything around it.

### Use Style References?

**Yes.** This is one of the primary mechanisms for maintaining consistent visual DNA.

### Use n8n?

**Eventually, yes.** Use it for orchestration, notifications, and workflow integration, not as the core image-processing engine.

### Use Python?

**Yes.** Python should own image processing, QC, metadata, similarity analysis, PDF generation, and CLI operations.

### Use a database?

**Yes.** SQLite for the MVP.

### Use a web UI?

**Yes.** A very small local review interface will provide enormous productivity gains.

### Use AI vision/QC?

**Yes, but after the basic pipeline works.**

### Build a provider abstraction?

**Yes.** This protects the system from becoming dependent on one generation provider.

### Target first?

**One real 40-page book.**

That book should be treated as the first production test of both the creative system and the publishing system.
