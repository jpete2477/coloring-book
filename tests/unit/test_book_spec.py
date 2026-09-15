from pathlib import Path

from app.planning.book_spec import border_style_phrase, load_book_spec, parse_size
from app.planning.scaffold import render_book_yaml_from_spec
from app.config import BookConfig


def test_parse_size():
    assert parse_size("8.5x11") == (8.5, 11.0)
    assert parse_size("6X9") == (6.0, 9.0)


def test_border_style_phrase_combinations():
    assert border_style_phrase("solid,black,square") == "a solid black border with square corners"
    assert border_style_phrase("solid,square") == "a solid black border with square corners"  # color defaults to black
    assert border_style_phrase("solid,white,rounded") == "a solid white border with rounded corners"
    assert border_style_phrase("decorative") == "a decorative black border"
    assert border_style_phrase("") == "a solid black border"


def test_load_book_spec_from_file(tmp_path):
    spec_path = tmp_path / "book.json"
    spec_path.write_text(
        """
        {
            "audience": "Adult",
            "style": "stained glass window",
            "theme": "4 Seasons",
            "author": "Test Author",
            "page_count": 12,
            "border_type": "solid,square",
            "size": "8.5x11",
            "elements": ["flower", "leaf", "wave", "snowflake"]
        }
        """
    )
    spec = load_book_spec(spec_path)
    assert spec.style == "stained glass window"
    assert spec.theme == "4 Seasons"
    assert spec.page_count == 12
    assert spec.elements == ["flower", "leaf", "wave", "snowflake"]
    assert spec.create_cover is True  # default
    assert spec.margin_width_inches == 1.0  # default


def test_render_book_yaml_from_spec_produces_valid_config(tmp_path):
    spec_path = tmp_path / "book.json"
    spec_path.write_text(
        """
        {
            "style": "stained glass window",
            "theme": "4 Seasons",
            "author": "Test Author",
            "page_count": 12,
            "border_type": "solid,black,square",
            "size": "8.5x11",
            "margin_width_inches": 1.0,
            "elements": ["flower", "leaf", "wave", "snowflake"]
        }
        """
    )
    spec = load_book_spec(spec_path)
    yaml_text = render_book_yaml_from_spec(book_id="demo", title="Demo Book", spec=spec)

    import yaml as yaml_lib
    config = BookConfig.model_validate(yaml_lib.safe_load(yaml_text))

    assert config.book.theme == "4 Seasons"
    assert config.book.audience == "Adult"
    assert config.style.style_anchor == "stained glass window"
    assert config.style.border_style == "a solid black border with square corners"
    assert config.production.margin_inches == 1.0
    assert config.base_elements == ["flower", "leaf", "wave", "snowflake"]


def test_render_book_yaml_from_spec_requires_elements():
    from app.planning.book_spec import BookSpec

    spec = BookSpec(style="stained glass window")
    try:
        render_book_yaml_from_spec(book_id="demo", title="Demo", spec=spec)
        assert False, "expected ValueError for missing elements"
    except ValueError:
        pass
