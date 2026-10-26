# Adore 4-class garment classifier (PyTorch)

Fixes confusion between **shirt**, **t-shirt**, **jacket**, and **pants**.

Pants and formal trousers are **one class** (`pants`). Zip and pullover hoodies are labeled **jacket** when they live under `upperwear/jacket` (and any future hoodie folder mapped to jacket).

## Why this lives under `ml_service`

It trains from the same Adore dataset and exports weights the FastAPI app can load (`app/garment_classifier.py`). You do not maintain a second unrelated project.

## Classes

| Class     | Source folder(s)              |
|-----------|-------------------------------|
| `shirt`   | `upperwear/shirt`             |
| `t-shirt` | `upperwear/tshirt`            |
| `jacket`  | `upperwear/jacket` (+ hoodie) |
| `pants`   | `bottomwear/pants`            |

## CPU training (your machine)

Default backbone is **ResNet18** (fast enough on CPU). Use smaller `--max-per-class` for a first checkpoint, then full data overnight.

```bat
cd "d:\fyp project\adore\ml_service"
.venv\Scripts\python.exe -m pytorch_garment.organize_dataset --audit-only
.venv\Scripts\python.exe -m pytorch_garment.train --epochs 8 --max-per-class 800 --batch-size 16
.venv\Scripts\python.exe -m pytorch_garment.evaluate_errors
.venv\Scripts\python.exe -m pytorch_garment.infer path\to\image.jpg
```

Outputs go to `ml_service/models/`:

- `garment4_resnet18.pt`
- `garment4_labels.json`
- `garment4_metrics.json`
- `garment4_confusion.png`
- `garment4_errors/` (misclassified samples)

## Augmentations (collar/sleeve-safe)

Allowed: horizontal flip, mild rotation (±12°), color jitter, light translate.  
Avoided: vertical flip, heavy random resized crop that cuts off the collar, strong perspective warp.
