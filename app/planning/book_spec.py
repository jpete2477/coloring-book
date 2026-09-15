"""Loads a book.json spec (simple, high-level book definition) and turns it
into book.yaml content. book.json is the "what is this book" layer for a
person; book.yaml remains the full, detailed config the rest of the
pipeline actually reads - book.json is a generator for it, not a
replacement.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class BookSpec(BaseModel):
    audience: str = "Adult"
    style: str
    theme: str = ""
    model: str = "Gemini"
    author: str = ""
    page_count: int = 40
    create_cover: bool = True
    border_type: str = "solid,black,square"
    size: str = "8.5x11"
    subtitle: str = "An Adult Coloring Collection"
    bleed: bool = False
    margin_width_inches: float = 1.0
    elements: list[str] = Field(default_factory=list)
    """Required in practice: theme -> element list is a curated judgment
    call (reviewed per book), not an automated mapping - see book.json."""
    compositions: list[str] = Field(default_factory=list)
    """Optional override; falls back to the standard proven-safe composition
    list (scaffold.DEFAULT_COMPOSITIONS) when empty."""
    notes: str = ""


def load_book_spec(path: Path) -> BookSpec:
    data = json.loads(path.read_text())
    return BookSpec.model_validate(data)


def parse_size(size: str) -> tuple[float, float]:
    w, h = size.lower().split("x")
    return float(w), float(h)


BORDER_COLORS = {"black", "white", "gray", "grey", "gold", "silver"}
BORDER_CORNERS = {"square": "square corners", "rounded": "rounded corners"}


def border_style_phrase(border_type: str) -> str:
    """"solid,black,square" -> "a solid black border with square corners".

    Color and corner style are parsed out separately from generic style
    descriptors (solid/dashed/decorative/...) rather than all three being
    mashed into one adjective string - an earlier version of this hardcoded
    "white border" regardless of input, which silently produced "solid black
    white border" once a color was added, and was arguably wrong even before
    that: a white border on a white page is invisible, whereas every other
    drawn element in this system (line_style) is black. Defaults to black
    for that reason when no color is specified."""
    parts = [p.strip().lower() for p in border_type.split(",") if p.strip()]
    corner = next((BORDER_CORNERS[p] for p in parts if p in BORDER_CORNERS), None)
    color = next((p for p in parts if p in BORDER_COLORS), "black")
    descriptors = [p for p in parts if p not in BORDER_CORNERS and p not in BORDER_COLORS]
    style_word = " ".join(descriptors) if descriptors else "solid"
    phrase = f"a {style_word} {color} border"
    if corner:
        phrase += f" with {corner}"
    return phrase
