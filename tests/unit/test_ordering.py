from app.config import OrderingConfig
from app.ordering.order import OrderItem, balanced_order, violation_count


def make_items():
    return [
        OrderItem("a1", "flower", "organic", 4),
        OrderItem("a2", "flower", "organic", 4),
        OrderItem("a3", "wheel", "lattice", 2),
        OrderItem("a4", "bird", "diagonal", 5),
        OrderItem("a5", "flower", "nested", 3),
        OrderItem("a6", "shell", "organic", 4),
    ]


def test_balanced_order_reduces_or_matches_naive_violation_count():
    config = OrderingConfig(avoid_adjacent_same_element=True, avoid_adjacent_same_composition=True)
    items = make_items()
    naive_violations = violation_count(items, config)
    ordered = balanced_order(items, config)
    ordered_violations = violation_count(ordered, config)
    assert ordered_violations <= naive_violations


def test_balanced_order_preserves_all_items():
    config = OrderingConfig()
    items = make_items()
    ordered = balanced_order(items, config)
    assert {it.asset_id for it in ordered} == {it.asset_id for it in items}
    assert len(ordered) == len(items)


def test_balanced_order_avoids_adjacent_same_element_when_possible():
    config = OrderingConfig(avoid_adjacent_same_element=True, avoid_adjacent_same_composition=False)
    items = [
        OrderItem("a1", "flower", "x", 3),
        OrderItem("a2", "flower", "y", 3),
        OrderItem("a3", "wheel", "z", 3),
    ]
    ordered = balanced_order(items, config)
    elements = [it.element for it in ordered]
    assert elements != ["flower", "flower", "wheel"]
