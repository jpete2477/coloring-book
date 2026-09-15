"""Helpers for locating an asset's files on disk by ID (extension-agnostic)."""
from __future__ import annotations

from pathlib import Path


def find_candidate_file(book_dir: Path, asset_id: str) -> Path | None:
    matches = sorted((book_dir / "candidates").glob(f"{asset_id}.*"))
    matches = [m for m in matches if m.is_file()]
    return matches[0] if matches else None


def find_original_file(book_dir: Path, asset_id: str) -> Path | None:
    matches = sorted((book_dir / "originals").glob(f"{asset_id}.*"))
    matches = [m for m in matches if m.is_file()]
    return matches[0] if matches else None
