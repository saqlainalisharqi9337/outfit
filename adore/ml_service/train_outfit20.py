"""Fine-tune YOLOv8n onto the 20 Adore outfit classes.

Keeps the original Fashionpedia TorchScript in models/original/.
Saves the improved checkpoint to models/improved/outfit20_yolov8n.pt.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "datasets" / "outfit20" / "data.yaml"
OUT = ROOT / "models" / "improved"
PRETRAINED = ROOT / "models" / "yolov8n.pt"


def main() -> int:
    if not DATA.is_file():
        raise SystemExit("Run prepare_outfit20_dataset.py first.")
    OUT.mkdir(parents=True, exist_ok=True)
    from ultralytics import YOLO

    weights = str(PRETRAINED) if PRETRAINED.is_file() else "yolov8n.pt"
    model = YOLO(weights)
    model.train(
        data=str(DATA),
        epochs=5,
        imgsz=416,
        batch=8,
        patience=4,
        device="cpu",
        project=str(OUT),
        name="train",
        exist_ok=True,
        pretrained=True,
        hsv_h=0.015,
        hsv_s=0.4,
        hsv_v=0.3,
        fliplr=0.5,
        mosaic=0.8,
        close_mosaic=2,
        workers=0,
    )
    best = OUT / "train" / "weights" / "best.pt"
    dest = OUT / "outfit20_yolov8n.pt"
    if best.is_file():
        dest.write_bytes(best.read_bytes())
        print("saved", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
