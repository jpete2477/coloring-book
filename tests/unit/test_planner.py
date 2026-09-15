from app.config import BookConfig
from app.planning.ids import book_code, candidate_asset_id, page_spec_id, unassigned_asset_id
from app.planning.planner import plan_pages, summarize_plan


def make_config(**overrides) -> BookConfig:
    data = {
        "book": {"id": "test_book", "title": "Test Book", "target_pages": 20},
        "base_elements": ["flower", "wheel", "bird", "shell", "leaf"],
        "compositions": ["organic_all_over", "interlocking", "nested", "flowing_diagonal"],
        "constraints": ["no text", "no color"],
    }
    data.update(overrides)
    return BookConfig.model_validate(data)


def test_book_code():
    assert book_code("ornamental_forms") == "OF001"
    assert book_code("botanicals") == "BO001"


def test_page_spec_id_and_asset_ids():
    assert page_spec_id("OF001", 17) == "OF001-017"
    assert candidate_asset_id("OF001-017", 3) == "OF001-017-C03"
    assert unassigned_asset_id("20260913", 1) == "UNASSIGNED-20260913-0001"


def test_plan_pages_hits_target_count():
    config = make_config()
    pages = plan_pages(config, seed=42)
    assert len(pages) == config.book.target_pages


def test_plan_pages_reproducible_with_seed():
    config = make_config()
    a = plan_pages(config, seed=7)
    b = plan_pages(config, seed=7)
    assert [(p.element, p.composition) for p in a] == [(p.element, p.composition) for p in b]


def test_plan_respects_max_same_element_consecutive():
    config = make_config()
    config.diversity.max_same_element_consecutive = 1
    pages = plan_pages(config, seed=1)
    for prev, cur in zip(pages, pages[1:]):
        assert not (prev.element == cur.element), "no two consecutive pages should share an element"


def test_plan_respects_max_same_element_count():
    # 5 elements x cap 3 = 15 achievable slots, so a 15-page target is feasible
    # to satisfy exactly (unlike a higher target, which forces the planner to
    # relax the cap rather than come up short).
    config = make_config(book={"id": "test_book", "title": "Test Book", "target_pages": 15})
    config.diversity.max_same_element_count = 3
    pages = plan_pages(config, seed=1)
    counts = {}
    for p in pages:
        counts[p.element] = counts.get(p.element, 0) + 1
    assert all(c <= 3 for c in counts.values())


def test_summarize_plan_reports_duplicates():
    config = make_config()
    pages = plan_pages(config, seed=1)
    report = summarize_plan(pages)
    assert report.total_pages == len(pages)
    assert report.unique_combinations <= report.total_pages
