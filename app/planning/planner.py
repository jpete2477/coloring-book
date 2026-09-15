"""Diversity planner (PRD sections 8, 55, 56).

Builds a page matrix that avoids accidental repetition: balances element and
composition usage counts, avoids immediate repeats, caps duplicate
(element, composition) combinations, biases density toward sparse/light
rather than moderate-or-denser (real user feedback: even "moderate" was too
detailed to color easily), and caps tiling/mirrored/rotational symmetry so
it doesn't dominate the book (that kind of symmetry reads as dense/ornate
regardless of the requested density level).
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from app.config import BookConfig
from app.planning.ids import book_code, page_spec_id

DENSITY_WEIGHTS = {1: 4, 2: 4, 3: 2, 4: 1, 5: 1}
"""Weighted toward sparse/light, moderate uncommon, dense rare. Shifted here
(from an earlier bell curve centered on "moderate") after real user
feedback: designs were too detailed to color easily even at moderate
density. 5 isn't in the default `densities` pool anymore (see config.py)
but keeps a weight here in case a book.yaml explicitly re-adds it."""

TILING_SYMMETRIES = {"four-way", "tiled", "rotational"}
MAX_TILING_FRACTION = 0.15
"""Repeated real generations showed that tiled/mirrored/rotational symmetry
multiplies apparent visual complexity regardless of the requested density -
a "moderate" motif repeated 4x with mirroring still reads as dense/ornate
overall. Capped low rather than eliminated (PRD section 8.5 asks to
"constrain", not remove, rotational-style symmetry)."""


@dataclass
class PlannedPage:
    id: str
    sequence: int
    element: str
    composition: str
    density: int
    symmetry: str
    scale: str
    border: str
    variation_seed: int


def _balanced_combo_sequence(
    elements: list[str],
    compositions: list[str],
    target_pages: int,
    *,
    max_same_element_count: int,
    max_same_composition_count: int,
    max_same_element_consecutive: int,
    max_same_composition_consecutive: int,
    max_duplicate_combination_count: int,
    rng: random.Random,
) -> list[tuple[str, str]]:
    all_pairs = list(itertools.product(elements, compositions))
    rng.shuffle(all_pairs)

    pool: list[tuple[str, str]] = []
    while len(pool) < target_pages * 2:
        batch = list(all_pairs)
        rng.shuffle(batch)
        pool.extend(batch * max_duplicate_combination_count)

    sequence: list[tuple[str, str]] = []
    element_count: dict[str, int] = {e: 0 for e in elements}
    composition_count: dict[str, int] = {c: 0 for c in compositions}
    element_run = (None, 0)
    composition_run = (None, 0)

    remaining = pool[:]
    while len(sequence) < target_pages and remaining:
        chosen_idx = None
        for idx, (e, c) in enumerate(remaining):
            if element_count[e] >= max_same_element_count:
                continue
            if composition_count[c] >= max_same_composition_count:
                continue
            if element_run[0] == e and element_run[1] >= max_same_element_consecutive:
                continue
            if composition_run[0] == c and composition_run[1] >= max_same_composition_consecutive:
                continue
            chosen_idx = idx
            break
        if chosen_idx is None:
            # Constraints too tight for remaining pool; relax by taking first available
            # element/composition pair even if it means exceeding a soft cap slightly.
            chosen_idx = 0
        e, c = remaining.pop(chosen_idx)
        sequence.append((e, c))
        element_count[e] += 1
        composition_count[c] += 1
        element_run = (e, element_run[1] + 1) if element_run[0] == e else (e, 1)
        composition_run = (c, composition_run[1] + 1) if composition_run[0] == c else (c, 1)

    return sequence


def plan_pages(config: BookConfig, *, seed: int | None = None) -> list[PlannedPage]:
    if not config.base_elements or not config.compositions:
        raise ValueError("book.yaml must define at least one base_element and one composition")

    rng = random.Random(seed if seed is not None else hash(config.book.id) & 0xFFFFFFFF)
    target_pages = config.book.target_pages
    div = config.diversity

    combos = _balanced_combo_sequence(
        config.base_elements,
        config.compositions,
        target_pages,
        max_same_element_count=div.max_same_element_count,
        max_same_composition_count=div.max_same_composition_count,
        max_same_element_consecutive=div.max_same_element_consecutive,
        max_same_composition_consecutive=div.max_same_composition_consecutive,
        max_duplicate_combination_count=div.max_duplicate_combination_count,
        rng=rng,
    )

    code = book_code(config.book.id)
    densities = config.densities
    symmetries = config.symmetries
    scales = config.scales
    borders = config.borders

    density_weights = [DENSITY_WEIGHTS.get(d, 1) for d in densities]
    tiling_symmetries_present = TILING_SYMMETRIES & set(symmetries)
    tiling_budget = max(1, round(target_pages * MAX_TILING_FRACTION)) if tiling_symmetries_present else 0
    tiling_used = 0

    pages: list[PlannedPage] = []
    for i, (element, composition) in enumerate(combos, start=1):
        density = rng.choices(densities, weights=density_weights, k=1)[0]

        symmetry_choices = symmetries
        if tiling_used >= tiling_budget:
            non_tiling = [s for s in symmetries if s not in TILING_SYMMETRIES]
            symmetry_choices = non_tiling or symmetries
        symmetry = rng.choice(symmetry_choices)
        if symmetry in TILING_SYMMETRIES:
            tiling_used += 1

        scale = rng.choice(scales)
        border = rng.choice(borders)
        variation_seed = rng.randint(0, 2**31 - 1)

        pages.append(
            PlannedPage(
                id=page_spec_id(code, i),
                sequence=i,
                element=element,
                composition=composition,
                density=density,
                symmetry=symmetry,
                scale=scale,
                border=border,
                variation_seed=variation_seed,
            )
        )
    return pages


@dataclass
class PlanReport:
    total_pages: int
    unique_combinations: int
    duplicate_combinations: int
    element_counts: dict[str, int]
    composition_counts: dict[str, int]


def summarize_plan(pages: list[PlannedPage]) -> PlanReport:
    combo_counts: dict[tuple[str, str], int] = {}
    element_counts: dict[str, int] = {}
    composition_counts: dict[str, int] = {}
    for p in pages:
        key = (p.element, p.composition)
        combo_counts[key] = combo_counts.get(key, 0) + 1
        element_counts[p.element] = element_counts.get(p.element, 0) + 1
        composition_counts[p.composition] = composition_counts.get(p.composition, 0) + 1
    duplicates = sum(1 for v in combo_counts.values() if v > 1)
    return PlanReport(
        total_pages=len(pages),
        unique_combinations=len(combo_counts),
        duplicate_combinations=duplicates,
        element_counts=element_counts,
        composition_counts=composition_counts,
    )
