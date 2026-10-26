"""Export the improved 20-class detector for serving."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "models" / "improved" / "outfit20_yolov8n.pt"


def main() -> int:
    if not SRC.is_file():
        raise SystemExit("Train first: python train_outfit20.py")
    from ultralytics import YOLO

    model = YOLO(str(SRC))
    model.export(format="onnx", imgsz=416)
    print("exported beside", SRC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
