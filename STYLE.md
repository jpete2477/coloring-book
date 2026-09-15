# Style Bible — Ornamental Forms

Product line: **Ornamental Forms**, an adult coloring collection by MBOQ
Colors. This is the persistent style reference for the product line (PRD
section 7) — treat it as product IP and keep it version-controlled.

## Design intent: anxiety reduction

This book is meant to reduce anxiety, not just to be pretty. That has a
concrete consequence: subjects must stay abstract/ornamental rather than
representational. A realistic bird, butterfly, or fish carries an implicit
"correct" reference in the colorer's head, and coloring toward (or missing)
that reference can itself become a source of anxiety and self-judgment.
Abstract patterns have no wrong answer. For that reason `base_elements` is
deliberately restricted to forms with no real-world "correct" appearance
(flower, wheel, shell, spiral, lattice, gear, etc. — see `book.yaml`), and
density is weighted toward light-to-moderate rather than maximum intricacy,
since tightly packed tiny regions can frustrate rather than calm.

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

## Style reference

No image style reference exists yet (`style/` starts empty). Once a first
round of Midjourney generations comes back, pick 2-4 strong, representative
pages, save them under `style/`, and point `book.yaml`'s
`style.style_reference` at them for subsequent generation rounds (PRD
sections 12.1/12.2/54). Keep the text prompt content-focused once a style
reference is in use — don't fight it with contradictory style instructions.
