"""Build the M4.12 train-id list. Does not edit the original annotations or images."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANN = ROOT / "ml_service" / "datasets" / "clothing_detection" / "annotations" / "instances_train.json"
OUT = ROOT / "checkpoints" / "maskrcnn" / "m4_12"
FOCUS = ("shirt", "jacket", "sweater", "watch")
# Every sweater image, then matched shirt/jacket counts, then watches and a minority of other classes.
MAX_IMAGES = 3200
SHIRT_CAP = 700
JACKET_CAP = 700
LAYERING_CAP = 150
WATCH_CAP = 250
OTHER_CAP = 112


def scale_for(width: int, height: int) -> float:
    short = min(width, height)
    long = max(width, height)
    if short <= 0 or long <= 0:
        return 1.0
    return min(416.0 / short, 624.0 / long)


def main() -> int:
    coco = json.loads(ANN.read_text(encoding="utf-8"))
    names = {int(cat["id"]): str(cat["name"]) for cat in coco["categories"]}
    images = {int(row["id"]): row for row in coco["images"]}
    names_seen = [Path(str(row.get("file_name") or "")).name for row in coco["images"]]
    dup_names = [name for name, count in Counter(names_seen).items() if count > 1]
    by_image: dict[int, list[dict]] = defaultdict(list)
    bad_box = 0
    for ann in coco["annotations"]:
        bbox = ann.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            bad_box += 1
            continue
        if float(bbox[2]) <= 0 or float(bbox[3]) <= 0:
            bad_box += 1
            continue
        by_image[int(ann["image_id"])].append(ann)

    focus_images = {name: [] for name in FOCUS}
    watch_small = 0
    watch_boxes = 0
    shirt_only: list[int] = []
    jacket_only: list[int] = []
    shirt_not_jacket: list[int] = []
    jacket_not_shirt: list[int] = []
    both_ids: list[int] = []
    small_watches: list[int] = []
    larger_watches: list[int] = []
    other_ids: dict[str, list[int]] = defaultdict(list)
    for image_id, anns in by_image.items():
        meta = images.get(image_id)
        if meta is None:
            continue
        labels = {names.get(int(ann["category_id"]), "") for ann in anns}
        has_shirt = "shirt" in labels
        has_jacket = "jacket" in labels
        if has_shirt and has_jacket:
            both_ids.append(image_id)
        if labels == {"shirt"}:
            shirt_only.append(image_id)
        elif labels == {"jacket"}:
            jacket_only.append(image_id)
        if has_shirt and not has_jacket:
            shirt_not_jacket.append(image_id)
        if has_jacket and not has_shirt:
            jacket_not_shirt.append(image_id)
        for name in FOCUS:
            if name in labels:
                focus_images[name].append(image_id)
        for name in labels:
            if name not in FOCUS:
                other_ids[name].append(image_id)
        if "watch" not in labels:
            continue
        width = int(meta.get("width") or 0)
        height = int(meta.get("height") or 0)
        factor = scale_for(width, height)
        smallest = None
        for ann in anns:
            if names.get(int(ann["category_id"])) != "watch":
                continue
            watch_boxes += 1
            bw, bh = float(ann["bbox"][2]), float(ann["bbox"][3])
            side = min(bw, bh) * factor
            smallest = side if smallest is None else min(smallest, side)
            if side < 16:
                watch_small += 1
        if smallest is not None and smallest < 16:
            small_watches.append(image_id)
        elif smallest is not None:
            larger_watches.append(image_id)

    selected: list[int] = []
    used: set[int] = set()

    def take(ids: list[int], limit: int) -> int:
        added = 0
        for image_id in ids:
            if added >= limit or len(selected) >= MAX_IMAGES:
                break
            if image_id in used:
                continue
            used.add(image_id)
            selected.append(image_id)
            added += 1
        return added

    def take_mixed(left: list[int], right: list[int], limit: int) -> int:
        added = 0
        i = j = 0
        left_sorted = sorted(left)
        right_sorted = sorted(right)
        while added < limit and len(selected) < MAX_IMAGES and (i < len(left_sorted) or j < len(right_sorted)):
            if i < len(left_sorted):
                image_id = left_sorted[i]
                i += 1
                if image_id not in used:
                    used.add(image_id)
                    selected.append(image_id)
                    added += 1
                    if added >= limit or len(selected) >= MAX_IMAGES:
                        break
            if j < len(right_sorted):
                image_id = right_sorted[j]
                j += 1
                if image_id not in used:
                    used.add(image_id)
                    selected.append(image_id)
                    added += 1
        return added

    sweater_n = take(sorted(focus_images["sweater"]), 10_000)
    shirt_n = take(sorted(shirt_not_jacket), SHIRT_CAP)
    jacket_n = take(sorted(jacket_not_shirt), min(JACKET_CAP, shirt_n))
    layer_n = take(sorted(both_ids), LAYERING_CAP)
    watch_n = take_mixed(small_watches, larger_watches, WATCH_CAP)
    other_n = 0
    other_names = sorted(other_ids)
    while other_n < OTHER_CAP and len(selected) < MAX_IMAGES:
        progressed = False
        for name in other_names:
            if other_n >= OTHER_CAP:
                break
            pool = other_ids[name]
            if not pool:
                continue
            image_id = pool.pop(0)
            if image_id in used:
                continue
            used.add(image_id)
            selected.append(image_id)
            other_n += 1
            progressed = True
        if not progressed:
            break

    histogram: Counter[str] = Counter()
    for image_id in selected:
        labels = {names.get(int(ann["category_id"]), "") for ann in by_image[image_id]}
        for label in labels:
            if label:
                histogram[label] += 1

    OUT.mkdir(parents=True, exist_ok=True)
    audit = {
        "source": str(ANN),
        "images_in_json": len(images),
        "annotated_images": len(by_image),
        "duplicate_file_names": len(dup_names),
        "bad_boxes": bad_box,
        "shirt_images": len(focus_images["shirt"]),
        "jacket_images": len(focus_images["jacket"]),
        "sweater_images": len(focus_images["sweater"]),
        "watch_images": len(focus_images["watch"]),
        "shirt_only_images": len(shirt_only),
        "jacket_only_images": len(jacket_only),
        "shirt_without_jacket_images": len(shirt_not_jacket),
        "jacket_without_shirt_images": len(jacket_not_shirt),
        "shirt_and_jacket_same_image": len(both_ids),
        "watch_boxes": watch_boxes,
        "watch_boxes_under_16px_at_416": watch_small,
        "subset_size": len(selected),
        "subset_sweater_images_added": sweater_n,
        "subset_shirt_without_jacket_added": shirt_n,
        "subset_jacket_without_shirt_added": jacket_n,
        "subset_shirt_and_jacket_added": layer_n,
        "subset_watch_added": watch_n,
        "subset_other_added": other_n,
        "subset_histogram_images": dict(histogram),
        "note": "Original annotations were not modified. Shirt-only and jacket-only means the image has that one foreground label.",
    }
    (OUT / "data_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (OUT / "train_image_ids.json").write_text(json.dumps(selected), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
