"""Shared interior page layout planning, used by both the PDF builder and
the KDP validator so their page-count math can never drift apart.
"""
from __future__ import annotations

from app.config import BookConfig


def interior_page_plan(config: BookConfig, image_count: int) -> list[bool]:
    """One entry per physical interior PDF page (not counting front/back
    matter): True for an actual image page, False for a blank filler page.

    When config.production.recto_only is set, every image must land on a
    right-hand (odd, counting page 1 as the first page after front matter)
    page - a leading blank is inserted if front matter left an odd count
    (which would otherwise put the first image on a left-hand page), and a
    blank follows every image so the next one also starts odd.
    """
    if not config.production.recto_only:
        return [True] * image_count
    plan: list[bool] = []
    if len(config.front_matter.pages) % 2 == 1:
        plan.append(False)
    for _ in range(image_count):
        plan.append(True)
        plan.append(False)
    return plan
