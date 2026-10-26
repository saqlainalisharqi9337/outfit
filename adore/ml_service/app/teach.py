"""Save user-labeled photos so the detector can be fine-tuned later.

Photos are stored under datasets/user_labeled/<class>/. They do not change
the live model until prepare_outfit20_dataset.py + train_outfit20.py run.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from PIL import Image

from .outfit20_taxonomy import OUTFIT20_CLASSES, resolve_label

ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "datasets" / "user_labeled"


def class_count(class_name: str) -> int:
    folder = USER_DIR / class_name
    if not folder.is_dir():
        return 0
    return sum(1 for p in folder.iterdir() if p.is_file())


def save_example(image: Image.Image, label: str) -> dict[str, str | int]:
    class_name = resolve_label(label)
    if class_name is None:
        allowed = ", ".join(OUTFIT20_CLASSES)
        raise ValueError(
            f"Unknown clothing type {label!r}. Use a name like pants, tshirt, "
            f"or one of: {allowed}."
        )
    dest_dir = USER_DIR / class_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    rgb = image.convert("RGB")
    rgb.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    name = f"{class_name}_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
    path = dest_dir / name
    rgb.save(path, format="JPEG", quality=88)
    return {
        "class": class_name,
        "path": str(path),
        "saved": class_count(class_name),
        "note": (
            "Saved for training. The live model does not change until you run "
            "prepare_outfit20_dataset.py then train_outfit20.py and restart the ML service."
        ),
    }
