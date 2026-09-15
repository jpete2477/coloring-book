"""Best-effort matching of a downloaded image to the page spec that produced it.

Midjourney web downloads often carry the prompt text in PNG metadata (e.g. a
"Description" or "parameters" text chunk). When present, we match it against
known planned prompts/elements; when absent or ambiguous, the asset is left
UNASSIGNED for manual assignment in the review UI (PRD section 14).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

MIN_MATCH_SCORE = 0.5


def extract_embedded_text(image_path: Path) -> str:
    try:
        with Image.open(image_path) as img:
            info = getattr(img, "info", {}) or {}
    except Exception:
        return ""
    parts = []
    for key in ("Description", "description", "parameters", "prompt", "Comment", "comment"):
        val = info.get(key)
        if isinstance(val, str):
            parts.append(val)
    return " ".join(parts)


def _score(embedded_text: str, element: str, composition: str) -> float:
    if not embedded_text:
        return 0.0
    text = embedded_text.lower()
    tokens = [element.lower(), composition.lower().replace("_", " ")]
    hits = sum(1 for t in tokens if t in text)
    return hits / len(tokens)


def match_page_spec(embedded_text: str, page_specs: list) -> tuple[str | None, float]:
    """page_specs: sqlite3.Row iterable with element/composition/id. Returns (page_spec_id, score)."""
    if not embedded_text:
        return None, 0.0
    best_id, best_score = None, 0.0
    for spec in page_specs:
        score = _score(embedded_text, spec["element"], spec["composition"])
        if score > best_score:
            best_id, best_score = spec["id"], score
    if best_score >= MIN_MATCH_SCORE:
        return best_id, best_score
    return None, best_score
