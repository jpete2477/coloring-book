import numpy as np
from PIL import Image, ImageDraw

from app.config import BookConfig
from app.images.normalize import normalize_image


def make_config(**overrides) -> BookConfig:
    data = {
        "book": {"id": "test_book", "title": "Test", "bleed": False},
        "production": {
            "dpi": 300, "target_width_inches": 8.5, "target_height_inches": 11,
            "threshold": True, "threshold_value": 200, "margin_inches": 0.4, "border": True,
        },
    }
    data.update(overrides)
    return BookConfig.model_validate(data)


def test_normalize_produces_exact_production_dimensions_and_dpi(tmp_path):
    src = tmp_path / "source.png"
    Image.new("RGB", (1000, 1300), (240, 240, 240)).save(src, "PNG")

    dest = tmp_path / "out.png"
    geometry = normalize_image(src, dest, make_config())

    with Image.open(dest) as out:
        assert out.size == (2550, 3300)
        assert out.mode == "L"
        assert round(out.info["dpi"][0]) == 300
    assert geometry.page_width_px == 2550
    assert geometry.page_height_px == 3300


def test_normalize_thresholds_to_pure_black_and_white(tmp_path):
    src = tmp_path / "source.png"
    Image.new("RGB", (800, 1000), (128, 128, 128)).save(src, "PNG")

    dest = tmp_path / "out.png"
    normalize_image(src, dest, make_config())

    with Image.open(dest) as out:
        values = set(np.unique(np.asarray(out)).tolist())
    assert values <= {0, 255}


def test_normalize_never_modifies_source(tmp_path):
    src = tmp_path / "source.png"
    Image.new("RGB", (800, 1000), (10, 10, 10)).save(src, "PNG")
    original_bytes = src.read_bytes()

    normalize_image(src, tmp_path / "out.png", make_config())

    assert src.read_bytes() == original_bytes


def test_normalize_does_not_distort_content_with_a_large_margin(tmp_path):
    """Regression test: cropping to the full page's aspect ratio and then
    resizing into the margin-adjusted inner box (a different aspect ratio,
    since margin is a fixed pixel amount subtracted from unequal width and
    height) stretched every image - a perfect circle came out as an
    ellipse. Only visible with a big enough margin to matter (0.4in was too
    subtle to notice; 1in was obviously "squished"). Draw a circle, check it
    stays round."""
    src = tmp_path / "source.png"
    size = 1600
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)
    # A frame near the full canvas edge keeps _trim_to_content_bbox from
    # shrinking the working canvas here - this test is specifically about
    # the crop/resize aspect mismatch, not the content-bbox trim.
    draw.rectangle([4, 4, size - 4, size - 4], outline="black", width=4)
    r = 450  # small enough to fully survive the center-crop, not just distortion
    cx = cy = size // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", width=10)
    img.save(src, "PNG")

    dest = tmp_path / "out.png"
    config = make_config(production={
        "dpi": 300, "target_width_inches": 8.5, "target_height_inches": 11,
        "threshold": True, "threshold_value": 200, "margin_inches": 1.0, "border": True,
    })
    normalize_image(src, dest, config)

    with Image.open(dest) as out:
        arr = np.asarray(out)
    # cover-and-crop (unlike the old fit-within approach) crops the frame's
    # vertical edges away entirely on the tight axis and strips the rest via
    # EDGE_STRIP_FRACTION, so the only dark content left in the output is the
    # circle itself - safe to measure the whole canvas directly.
    dark_rows = np.where((arr < 128).any(axis=1))[0]
    dark_cols = np.where((arr < 128).any(axis=0))[0]
    bbox_height = dark_rows.max() - dark_rows.min()
    bbox_width = dark_cols.max() - dark_cols.min()
    aspect_ratio = bbox_width / bbox_height
    assert 0.97 < aspect_ratio < 1.03, (
        f"circle bounding box aspect ratio {aspect_ratio:.3f} - should stay ~1.0 (round), "
        f"got width={bbox_width} height={bbox_height} (distorted into an ellipse)"
    )


def test_normalize_fills_the_entire_margin_box_with_no_internal_gap(tmp_path):
    """The artwork must completely fill the bordered box edge-to-edge - no
    internal white gap between content and the (later, PDF-build-time)
    border, regardless of the source image's own aspect ratio. A "fit
    inside and letterbox" approach was tried and rejected for exactly this
    reason: whenever the source aspect didn't exactly match the box, it left
    a visible blank band on two sides."""
    src = tmp_path / "source.png"
    w, h = 1600, 1600  # square source, portrait box - aspect mismatch on purpose
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    for x in range(0, w, 80):
        draw.line([(x, 0), (x, h)], fill="black", width=6)
    for y in range(0, h, 80):
        draw.line([(0, y), (w, y)], fill="black", width=6)
    img.save(src, "PNG")

    dest = tmp_path / "out.png"
    config = make_config(production={
        "dpi": 300, "target_width_inches": 8.5, "target_height_inches": 11,
        "threshold": True, "threshold_value": 200, "margin_inches": 1.0, "border": True,
    })
    geometry = normalize_image(src, dest, config)
    margin_px = round(config.production.margin_inches * geometry.dpi)

    with Image.open(dest) as out:
        arr = np.asarray(out)
    dark_rows = np.where((arr < 128).any(axis=1))[0]
    dark_cols = np.where((arr < 128).any(axis=0))[0]
    out_h, out_w = arr.shape
    top_margin = dark_rows.min()
    bottom_margin = out_h - 1 - dark_rows.max()
    left_margin = dark_cols.min()
    right_margin = out_w - 1 - dark_cols.max()

    for name, measured in (
        ("top", top_margin), ("bottom", bottom_margin),
        ("left", left_margin), ("right", right_margin),
    ):
        assert abs(measured - margin_px) <= 3, (
            f"{name} margin should be exactly {margin_px}px (content fills the "
            f"box completely), got {measured}"
        )


def test_normalize_gives_uniform_margin_despite_asymmetric_source_padding(tmp_path):
    """Regression test: a source image with more blank padding on one axis
    than the other (very common - the AI doesn't frame its own border
    consistently) used to produce a bigger final margin on whichever axis
    _center_crop_to_aspect never crops (typically top/bottom), since that
    padding rode straight through untouched and stacked on top of our own
    deliberate margin. Content should be trimmed to its real bounding box
    first and then centered, so content never intrudes into the requested
    margin and sits symmetrically (left=right, top=bottom) regardless of how
    asymmetrically the source was framed. The border itself is no longer
    drawn here (moved to PDF-build time), so this checks the content
    placement directly rather than a drawn border line."""
    src = tmp_path / "source.png"
    w, h = 1800, 1800
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    # Deliberately asymmetric padding: only 20px left/right, 150px top/bottom.
    draw.rectangle([20, 150, w - 20, h - 150], outline="black", width=8)
    # Real actual artwork well inside the frame (not just the frame line
    # itself), so EDGE_STRIP_FRACTION - which strips a thin band right at
    # the trimmed content's own edge to remove the AI's own border - can't
    # accidentally strip away all of the content along with it.
    draw.ellipse([w // 2 - 400, h // 2 - 400, w // 2 + 400, h // 2 + 400], outline="black", width=10)
    img.save(src, "PNG")

    dest = tmp_path / "out.png"
    config = make_config(production={
        "dpi": 300, "target_width_inches": 8.5, "target_height_inches": 11,
        "threshold": True, "threshold_value": 200, "margin_inches": 1.0, "border": True,
    })
    geometry = normalize_image(src, dest, config)
    margin_px = round(config.production.margin_inches * geometry.dpi)

    with Image.open(dest) as out:
        arr = np.asarray(out)
    dark_rows = np.where((arr < 128).any(axis=1))[0]
    dark_cols = np.where((arr < 128).any(axis=0))[0]
    out_h, out_w = arr.shape
    top_margin = dark_rows.min()
    bottom_margin = out_h - 1 - dark_rows.max()
    left_margin = dark_cols.min()
    right_margin = out_w - 1 - dark_cols.max()

    assert abs(top_margin - bottom_margin) < 15, (
        f"content should be vertically centered, got top={top_margin} bottom={bottom_margin}"
    )
    assert abs(left_margin - right_margin) < 15, (
        f"content should be horizontally centered, got left={left_margin} right={right_margin}"
    )
    assert min(top_margin, bottom_margin, left_margin, right_margin) >= margin_px - 2, (
        f"content must never intrude into the {margin_px}px requested margin, "
        f"got top={top_margin} bottom={bottom_margin} left={left_margin} right={right_margin}"
    )
