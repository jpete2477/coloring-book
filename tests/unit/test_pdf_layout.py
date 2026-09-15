from app.config import BookConfig
from app.pdf.layout import interior_page_plan


def make_config(front_matter_pages: list[str], recto_only: bool) -> BookConfig:
    return BookConfig.model_validate(
        {
            "book": {"id": "test_book", "title": "Test", "bleed": False},
            "production": {
                "dpi": 300, "target_width_inches": 8.5, "target_height_inches": 11,
                "recto_only": recto_only,
            },
            "front_matter": {"pages": front_matter_pages},
        }
    )


def test_recto_only_off_is_just_images_back_to_back():
    config = make_config([], recto_only=False)
    assert interior_page_plan(config, 5) == [True] * 5


def test_recto_only_inserts_leading_blank_when_front_matter_is_odd():
    config = make_config(["title_page"], recto_only=True)  # 1 front matter page
    plan = interior_page_plan(config, 2)
    assert plan == [False, True, False, True, False]


def test_recto_only_no_leading_blank_when_front_matter_is_even():
    config = make_config(["title_page", "belongs_to_page"], recto_only=True)  # 2 pages
    plan = interior_page_plan(config, 2)
    assert plan == [True, False, True, False]


def test_recto_only_every_image_lands_on_an_odd_global_page_number():
    for front_matter_len in range(0, 4):
        config = make_config([f"p{i}" for i in range(front_matter_len)], recto_only=True)
        plan = interior_page_plan(config, 4)
        for i, is_image in enumerate(plan):
            global_page_number = front_matter_len + i + 1
            if is_image:
                assert global_page_number % 2 == 1, (
                    f"image at plan index {i} (front_matter_len={front_matter_len}) "
                    f"landed on page {global_page_number}, should be odd"
                )
