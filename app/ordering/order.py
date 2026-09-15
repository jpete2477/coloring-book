"""Book ordering (PRD section 24): manual sequence or automatic balanced order."""
from __future__ import annotations

from dataclasses import dataclass

from app.config import OrderingConfig


@dataclass
class OrderItem:
    asset_id: str
    element: str
    composition: str
    density: int


def manual_order(items: list[OrderItem], sequence_by_asset_id: dict[str, int]) -> list[OrderItem]:
    """Order items by an explicit user-provided sequence map; unlisted items go last, input order."""
    return sorted(
        items,
        key=lambda it: (sequence_by_asset_id.get(it.asset_id, 10**9), items.index(it)),
    )


def balanced_order(items: list[OrderItem], config: OrderingConfig) -> list[OrderItem]:
    """Greedy interleave that avoids adjacent repeats of element/composition and
    nudges density to alternate, per PRD section 24.2/24.3."""
    remaining = list(items)
    element_counts = {}
    composition_counts = {}
    for it in remaining:
        element_counts[it.element] = element_counts.get(it.element, 0) + 1
        composition_counts[it.composition] = composition_counts.get(it.composition, 0) + 1

    ordered: list[OrderItem] = []
    last_element = None
    last_composition = None
    last_density = None

    while remaining:
        def score(it: OrderItem) -> tuple:
            element_violation = (
                config.avoid_adjacent_same_element and it.element == last_element
            )
            composition_violation = (
                config.avoid_adjacent_same_composition and it.composition == last_composition
            )
            density_bonus = 0
            if config.target_density_variation and last_density is not None:
                density_bonus = -abs(it.density - last_density)
            return (
                element_violation,
                composition_violation,
                -element_counts[it.element],
                -composition_counts[it.composition],
                -density_bonus,
            )

        remaining.sort(key=score)
        chosen = remaining.pop(0)
        ordered.append(chosen)
        element_counts[chosen.element] -= 1
        composition_counts[chosen.composition] -= 1
        last_element, last_composition, last_density = chosen.element, chosen.composition, chosen.density

    return ordered


def violation_count(items: list[OrderItem], config: OrderingConfig) -> int:
    violations = 0
    for prev, cur in zip(items, items[1:]):
        if config.avoid_adjacent_same_element and prev.element == cur.element:
            violations += 1
        if config.avoid_adjacent_same_composition and prev.composition == cur.composition:
            violations += 1
    return violations
