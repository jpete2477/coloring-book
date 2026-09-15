from app.config import BookConfig
from app.production_geometry import page_geometry


def make_config(bleed: bool) -> BookConfig:
    return BookConfig.model_validate(
        {
            "book": {"id": "test_book", "title": "Test", "bleed": bleed},
            "production": {"dpi": 300, "target_width_inches": 8.5, "target_height_inches": 11},
        }
    )


def test_no_bleed_matches_trim_size_at_300dpi():
    geo = page_geometry(make_config(bleed=False))
    assert geo.page_width_px == 2550
    assert geo.page_height_px == 3300


def test_bleed_adds_kdp_bleed_margins():
    geo = page_geometry(make_config(bleed=True))
    # KDP bleed: +0.125in outside edge (width), +0.125in top and bottom (height)
    assert round(geo.page_width_in, 3) == 8.625
    assert round(geo.page_height_in, 3) == 11.25
    assert geo.page_width_px == 2588
    assert geo.page_height_px == 3375
