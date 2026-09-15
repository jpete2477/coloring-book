"""Generates placeholder black-on-white "line art" PNGs for local pipeline testing,
standing in for real Midjourney downloads. Not part of the production pipeline.

Usage: uv run python scripts/generate_placeholder_art.py <out_dir> <count> [--seed N] [--bad]
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw
from PIL.PngImagePlugin import PngInfo


def make_line_art(width: int, height: int, seed: int, *, bad: bool = False) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    if bad:
        # Deliberately fails QC: mostly solid black.
        draw.rectangle([0, 0, width, height], fill=(10, 10, 10))
        return img

    margin = int(min(width, height) * 0.08)
    draw.rectangle([margin, margin, width - margin, height - margin], outline="black", width=4)

    for _ in range(rng.randint(10, 20)):
        cx = rng.randint(margin, width - margin)
        cy = rng.randint(margin, height - margin)
        r = rng.randint(20, min(width, height) // 6)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", width=3)

    for _ in range(rng.randint(15, 30)):
        x1, y1 = rng.randint(margin, width - margin), rng.randint(margin, height - margin)
        x2, y2 = rng.randint(margin, width - margin), rng.randint(margin, height - margin)
        draw.line([x1, y1, x2, y2], fill="black", width=2)

    return img


def save(img: Image.Image, path: Path, description: str | None = None) -> None:
    info = None
    if description:
        info = PngInfo()
        info.add_text("Description", description)
    img.save(path, "PNG", dpi=(300, 300), pnginfo=info)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir")
    parser.add_argument("count", type=int)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--bad", action="store_true")
    parser.add_argument("--description", default=None)
    parser.add_argument("--width", type=int, default=2000)
    parser.add_argument("--height", type=int, default=2600)
    parser.add_argument("--prefix", default="placeholder")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(args.count):
        img = make_line_art(args.width, args.height, args.seed + i, bad=args.bad)
        save(img, out_dir / f"{args.prefix}_{i:03d}.png", description=args.description)
    print(f"Wrote {args.count} image(s) to {out_dir}")


if __name__ == "__main__":
    main()
