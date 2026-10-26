"""Shared paths and class map for the 4-class garment model."""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ML_SERVICE_DIR = PACKAGE_DIR.parent
MODELS_DIR = ML_SERVICE_DIR / "models"
DEFAULT_DATASET = Path(r"D:\fyp project\dataset")
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# Fixed order — training, export, and inference must match.
CLASS_ORDER: tuple[str, ...] = ("shirt", "t-shirt", "jacket", "pants")

# Adore folder layout: {split}/{split}/{family}/{leaf}
# Hoodies (zip or pullover) are jacket when stored under jacket/hoodie leaves.
SOURCE_FOLDERS: tuple[tuple[str, str, str], ...] = (
    ("upperwear", "shirt", "shirt"),
    ("upperwear", "tshirt", "t-shirt"),
    ("upperwear", "t-shirt", "t-shirt"),
    ("upperwear", "jacket", "jacket"),
    ("upperwear", "hoodie", "jacket"),
    ("upperwear", "coat", "jacket"),
    ("upperwear", "blazer", "jacket"),
    ("bottomwear", "pants", "pants"),
    ("bottomwear", "trousers", "pants"),
    ("bottomwear", "jeans", "pants"),
    ("bottomwear", "chinos", "pants"),
    ("bottomwear", "joggers", "pants"),
)

DISPLAY_NAME = {
    "shirt": "Shirt",
    "t-shirt": "T-shirt",
    "jacket": "Jacket",
    "pants": "Pants/Trousers",
}

IMAGE_SIZE = 224
MODEL_NAME = "garment4_resnet18.pt"
LABELS_NAME = "garment4_labels.json"
METRICS_NAME = "garment4_metrics.json"
CONFUSION_NAME = "garment4_confusion.png"
ERRORS_DIR_NAME = "garment4_errors"
