"""Duplicate detection, levels 1-2 (PRD section 18). Level 3 (embeddings) deferred."""
from __future__ import annotations

import hashlib
from pathlib import Path

import imagehash
from PIL import Image


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def phash_of(path: Path) -> str:
    with Image.open(path) as img:
        return str(imagehash.phash(img))


def hamming_distance(phash_a: str, phash_b: str) -> int:
    return imagehash.hex_to_hash(phash_a) - imagehash.hex_to_hash(phash_b)


def find_similar(phash: str, candidates: list[tuple[str, str]], threshold: int) -> list[tuple[str, int]]:
    """candidates: list of (asset_id, phash). Returns [(asset_id, distance), ...] within threshold, closest first."""
    hits = []
    for asset_id, other_phash in candidates:
        if not other_phash:
            continue
        dist = hamming_distance(phash, other_phash)
        if dist <= threshold:
            hits.append((asset_id, dist))
    hits.sort(key=lambda t: t[1])
    return hits
