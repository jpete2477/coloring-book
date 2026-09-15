import pymupdf
from PIL import Image

from app.config import BookConfig
from app.pdf.build import build_interior_pdf


def make_config(**overrides) -> BookConfig:
    data = {
        "book": {"id": "test_book", "title": "Test", "author": "Author", "bleed": False},
        "production": {
            "dpi": 300, "target_width_inches": 8.5, "target_height_inches": 11,
            "threshold": True, "border": True, "margin_inches": 1.0,
        },
        "front_matter": {"pages": ["title_page"]},
        "back_matter": {"pages": []},
    }
    data.update(overrides)
    return BookConfig.model_validate(data)


def make_pages(tmp_path, n: int) -> list[dict]:
    pages = []
    for i in range(n):
        path = tmp_path / f"page_{i}.png"
        Image.new("L", (2550, 3300), 255).save(path)
        pages.append({"asset_id": f"asset_{i}", "normalized_path": path})
    return pages


def _page_is_blank(page) -> bool:
    return len(page.get_text().strip()) == 0 and not page.get_images()


def test_recto_only_puts_every_image_on_an_odd_page(tmp_path):
    """front_matter has 1 page (odd), so without adjustment the first image
    would land on page 2 (left/even) - a leading blank page should push it
    to page 3 (right/odd), and a blank should follow every image so the
    next one is odd too."""
    config = make_config(production={
        "dpi": 300, "target_width_inches": 8.5, "target_height_inches": 11,
        "threshold": True, "border": True, "margin_inches": 1.0, "recto_only": True,
    })
    pages = make_pages(tmp_path, 3)
    out_path = build_interior_pdf(tmp_path, config, pages)

    doc = pymupdf.open(out_path)
    image_page_numbers = [i + 1 for i in range(doc.page_count) if doc[i].get_images()]
    assert all(n % 2 == 1 for n in image_page_numbers), (
        f"every image page must be odd (right-hand), got {image_page_numbers}"
    )
    assert len(image_page_numbers) == 3


def test_recto_only_off_keeps_images_back_to_back(tmp_path):
    config = make_config()
    pages = make_pages(tmp_path, 3)
    out_path = build_interior_pdf(tmp_path, config, pages)

    doc = pymupdf.open(out_path)
    # front matter (1) + 3 images, no blanks inserted
    assert doc.page_count == 4
