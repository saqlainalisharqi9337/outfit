"""Fetch the public Fashionpedia YOLOv8n weights into models/.

Checkpoint: https://huggingface.co/louisJLN/yolo8-fashionpedia
Trained on detection-datasets/fashionpedia (bag, hat, glasses, belt, scarf, …).
"""

from __future__ import annotations

from pathlib import Path

DEST = Path(__file__).resolve().parent / "models" / "yolov8n-fashionpedia-1.torchscript"
REPO = "louisJLN/yolo8-fashionpedia"
FILE = "shared/yolov8n-fashionpedia-1.torchscript"


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.is_file() and DEST.stat().st_size > 1_000_000:
        print("already present", DEST)
        return 0
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(repo_id=REPO, filename=FILE)
    DEST.write_bytes(Path(path).read_bytes())
    print("saved", DEST, DEST.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
