from pathlib import Path

from PIL import Image

from app.qc.basic import run_basic_qc


def _save(tmp_path: Path, name: str, color, size=(1200, 1500)) -> Path:
    path = tmp_path / name
    Image.new("RGB", size, color).save(path, "PNG")
    return path


def test_clean_line_art_like_image_passes(tmp_path):
    # Mostly white with a black border drawn via a thin rectangle approximation:
    # a nearly-all-white image should pass with no gray/color flags.
    path = _save(tmp_path, "white.png", (255, 255, 255))
    result = run_basic_qc(path)
    assert result.ok
    assert not result.color_detected
    assert not result.gray_detected


def test_mostly_solid_black_fails_hard(tmp_path):
    path = _save(tmp_path, "black.png", (5, 5, 5))
    result = run_basic_qc(path)
    assert not result.ok
    assert result.machine_decision == "qc_failed"


def test_gray_fill_is_flagged_not_failed(tmp_path):
    path = _save(tmp_path, "gray.png", (128, 128, 128))
    result = run_basic_qc(path)
    assert result.ok
    assert result.gray_detected


def test_color_fill_is_detected(tmp_path):
    path = _save(tmp_path, "red.png", (200, 30, 30))
    result = run_basic_qc(path)
    assert result.color_detected


def test_low_resolution_fails(tmp_path):
    path = _save(tmp_path, "tiny.png", (255, 255, 255), size=(200, 250))
    result = run_basic_qc(path)
    assert not result.ok


def test_corrupt_file_fails_gracefully(tmp_path):
    path = tmp_path / "corrupt.png"
    path.write_bytes(b"not a real png")
    result = run_basic_qc(path)
    assert not result.ok
    assert result.machine_decision == "qc_failed"
