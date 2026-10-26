"""Draw boxes and masks from the converted COCO set. Does not train."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from training.prepare_detection_dataset import DEFAULT_OUTPUT, DEFAULT_PREVIEW

PALETTE = {
    "shirt": (220, 20, 60),
    "jacket": (255, 127, 0),
    "sweater": (255, 215, 0),
    "trousers": (30, 144, 255),
    "shorts": (0, 191, 255),
    "skirt": (138, 43, 226),
    "dress": (199, 21, 133),
    "jumpsuit": (75, 0, 130),
    "shoes": (139, 69, 19),
    "bag": (46, 139, 87),
    "hat": (0, 128, 128),
    "belt": (112, 128, 144),
    "scarf": (255, 105, 180),
    "watch": (70, 130, 180),
    "sunglasses": (47, 79, 79),
}

SCENES = {
    "normal_outfit": None,
    "multiple_items": None,
    "dress": "dress",
    "skirt": "skirt",
    "bag": "bag",
    "trousers": "trousers",
    "upperwear": ("shirt", "jacket", "sweater"),
    "footwear": "shoes",
    "accessories": ("bag", "hat", "belt", "scarf", "watch", "sunglasses"),
}


def _font() -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", 16)
    except OSError:
        return ImageFont.load_default()


def _load_split(output_dir: Path, split: str) -> dict[str, Any]:
    path = output_dir / "annotations" / f"instances_{split}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _index(coco: dict[str, Any], split: str, output_dir: Path) -> list[dict[str, Any]]:
    cats = {int(c["id"]): c["name"] for c in coco["categories"]}
    anns_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ann in coco["annotations"]:
        anns_by_image[int(ann["image_id"])].append(ann)
    rows = []
    for image in coco["images"]:
        path = output_dir / "images" / split / Path(image["file_name"]).name
        anns = anns_by_image.get(int(image["id"]), [])
        names = [cats[int(a["category_id"])] for a in anns]
        rows.append({"split": split, "image": image, "path": path, "anns": anns, "names": names, "cats": cats})
    return rows


def _matches(row: dict[str, Any], need: str | tuple[str, ...] | None) -> bool:
    names = set(row["names"])
    if need is None:
        return len(names) >= 2
    if isinstance(need, tuple):
        return bool(names.intersection(need))
    return need in names


def draw_row(row: dict[str, Any], dest: Path) -> None:
    if row["path"].is_file():
        with Image.open(row["path"]) as im:
            rgb = im.convert("RGBA")
        source_note = ""
    else:
        image = row["image"]
        rgb = Image.new("RGBA", (int(image["width"]), int(image["height"])), (32, 32, 32, 255))
        source_note = "geometry-only (image file not copied yet)"
    overlay = Image.new("RGBA", rgb.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    box_draw = ImageDraw.Draw(rgb)
    font = _font()
    cats = row["cats"]
    for ann in row["anns"]:
        name = cats[int(ann["category_id"])]
        color = PALETTE.get(name, (255, 255, 255))
        x, y, w, h = ann["bbox"]
        box_draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
        box_draw.text((x + 2, max(0, y - 18)), name, fill=color, font=font)
        seg = ann.get("segmentation")
        if isinstance(seg, list) and seg:
            polys = seg if isinstance(seg[0], (list, tuple)) else [seg]
            for poly in polys:
                if len(poly) < 6:
                    continue
                pts = [(float(poly[i]), float(poly[i + 1])) for i in range(0, len(poly), 2)]
                draw.polygon(pts, fill=(*color, 70), outline=(*color, 200))
    if source_note:
        box_draw.text((8, 8), source_note, fill=(255, 220, 80), font=font)
    out = Image.alpha_composite(rgb.convert("RGBA"), overlay).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, quality=92)


def select_previews(rows: list[dict[str, Any]], per_scene: int, seed: int) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)
    chosen: dict[str, list[dict[str, Any]]] = {}
    used: set[int] = set()
    for scene, need in SCENES.items():
        pool = [r for r in rows if _matches(r, need) and int(r["image"]["id"]) not in used]
        rng.shuffle(pool)
        if scene == "multiple_items":
            pool = [r for r in pool if len(r["names"]) >= 3] or pool
        chosen[scene] = pool[:per_scene]
        for row in chosen[scene]:
            used.add(int(row["image"]["id"]))
    return chosen


def run(
    output_dir: Path,
    preview_dir: Path,
    per_scene: int,
    seed: int,
    report_path: Path | None = None,
) -> int:
    rows: list[dict[str, Any]] = []
    for split in ("train", "val", "test"):
        path = output_dir / "annotations" / f"instances_{split}.json"
        if path.is_file():
            rows.extend(_index(_load_split(output_dir, split), split, output_dir))
    if not rows:
        print("no annotated images in COCO json")
        return 0
    chosen = select_previews(rows, per_scene, seed)
    preview_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    index_lines = ["# Dataset preview", "", "Random Fashionpedia-mapped annotations. Not training output.", ""]
    for scene, items in chosen.items():
        index_lines.append(f"## {scene}")
        index_lines.append("")
        if not items:
            index_lines.append("No matching image with a copied file was available.")
            index_lines.append("")
            continue
        for i, row in enumerate(items):
            dest = preview_dir / f"{scene}_{i:02d}_{row['split']}_{row['image']['id']}.jpg"
            draw_row(row, dest)
            written += 1
            index_lines.append(f"- `{dest.name}` — classes: {', '.join(sorted(set(row['names'])))}")
        index_lines.append("")
    (preview_dir / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    stats_path = output_dir / "stats.json"
    if stats_path.is_file():
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        stats["preview_count"] = written
        stats["preview_dir"] = str(preview_dir)
        stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
        if report_path is not None:
            from training.prepare_detection_dataset import render_report

            render_report(stats, report_path)
    print(f"wrote {written} previews to {preview_dir}")
    return written


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW)
    p.add_argument("--report", type=Path, default=None, help="Optional markdown report to refresh")
    p.add_argument("--per-scene", type=int, default=3)
    p.add_argument("--seed", type=int, default=20)
    args = p.parse_args(argv)
    from training.prepare_detection_dataset import DEFAULT_REPORT

    report = args.report
    if report is None and args.output_dir.resolve() == DEFAULT_OUTPUT.resolve():
        report = DEFAULT_REPORT
    run(args.output_dir, args.preview_dir, args.per_scene, args.seed, report_path=report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
