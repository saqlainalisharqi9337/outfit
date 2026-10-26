import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ml_service"))

import torch
from training.dataset import ClothingDetectionDataset, detection_paths
from training.label_map import load_label_map
from training.preview_maskrcnn import render_predictions
from training.train_maskrcnn import apply_cpu_fast, build_maskrcnn, load_checkpoint

focus = ["shirt", "scarf", "belt", "watch", "skirt", "bag", "hat", "sunglasses", "shoes", "dress", "trousers"]
paths = detection_paths()
ds = ClothingDetectionDataset(paths["val_images"], paths["val_ann"], load_label_map(), max_images=None, skip_invalid=True)
name_of = {i + 1: n for i, n in enumerate(ds.label_names)}
picked = {}
for i, rec in enumerate(ds.records):
    labels = set()
    for ann in rec["anns"]:
        lab = ds.cat_id_to_label.get(int(ann.get("category_id") or 0))
        if lab:
            labels.add(name_of[lab])
    for name in focus:
        if name in labels and name not in picked:
            picked[name] = i
    if len(picked) == len(focus):
        break
root = Path(__file__).resolve().parents[3]
ckpt = root / "checkpoints" / "maskrcnn" / "m4_10" / "best_model.pth"
meta = torch.load(ckpt, map_location="cpu", weights_only=False)
cfg = meta.get("config") or {}
model = build_maskrcnn(
    16,
    pretrained=False,
    min_size=int(cfg.get("min_size") or 320),
    max_size=int(cfg.get("max_size") or 480),
    smoke_rpn=True,
)
load_checkpoint(ckpt, model, map_location="cpu")
apply_cpu_fast(model)
model.eval()
dest = root / "outputs" / "maskrcnn_m4_10"
dest.mkdir(parents=True, exist_ok=True)
seen = set()
for name, index in picked.items():
    if index in seen:
        print("skip-dup", name, index)
        continue
    seen.add(index)
    image, _ = ds[index]
    with torch.no_grad():
        pred = model([image])[0]
    out = dest / f"{name}_{index:04d}_{ds.records[index]['path'].stem}.jpg"
    render_predictions(image, pred, ds.label_names, score_thresh=0.3).save(out, quality=90)
    print(name, index, out.name)
print("WROTE", len(seen))
