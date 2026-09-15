"""Book/page/asset ID helpers (PRD sections 10 and 14)."""
from __future__ import annotations

import re


def book_code(book_id: str) -> str:
    """e.g. 'ornamental_forms' -> 'OF001'."""
    words = [w for w in re.split(r"[_\-]", book_id) if w]
    initials = "".join(w[0] for w in words).upper()
    if len(initials) < 2:
        initials = (book_id[:2]).upper()
    return f"{initials}001"


def page_spec_id(code: str, sequence: int) -> str:
    return f"{code}-{sequence:03d}"


def candidate_asset_id(page_id: str, candidate_number: int) -> str:
    return f"{page_id}-C{candidate_number:02d}"


def unassigned_asset_id(date_str: str, counter: int) -> str:
    return f"UNASSIGNED-{date_str}-{counter:04d}"
