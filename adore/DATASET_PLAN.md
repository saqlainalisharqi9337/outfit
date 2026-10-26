# Dataset plan (Fashionpedia — not downloaded)

Status: **planning only**. Fashionpedia has not been downloaded.

## Current dataset

Root: `D:\fyp project\dataset`

13 classification folders (folder labels only, **no boxes**):
t-shirt, shirt, jacket, trousers, shorts, skirt, dress, bag, hat, flats,
heels, shoes, sneakers.

Train ~40,139 images. Optional folders with **zero** images:
jeans, coat, hoodie, sweater, scarf, jewelry.

## Future custom detector (Milestone 3+)

Fashionpedia (COCO instance annotations, CC BY 4.0)

Fashionpedia → class mapping → YOLO labels → fine-tune YOLOv8n → 13-class
taxonomy where a mapping exists.

### Proposed mapping (to be verified against the category list at download time)

| Project class | Likely Fashionpedia super-category / category |
|---|---|
| shirt / t-shirt | top, shirt, t-shirt |
| jacket | jacket, coat (coat has no project images — do not invent coat) |
| trousers | pants, trousers |
| shorts | shorts |
| skirt | skirt |
| dress | dress |
| bag | bag, wallet |
| hat | hat, headband (map conservatively) |
| shoes / sneakers / flats / heels | shoe (fine types still need the MobileNet heads) |

Classes with no project images must stay untrained.

### Conversion

COCO JSON → YOLO `class x_center y_center width height` (normalized), one
`.txt` per image, `data.yaml` with the mapped names.

### Storage / training (estimate)

- Fashionpedia images + JSON: several GB; confirm before download
- Train on a machine with a GPU if possible; CPU-only is slow
- Evaluate with mAP@0.5 plus per-class AP; never report classification
  accuracy as detection mAP

### License

Fashionpedia: CC BY 4.0 (attribution required). Ultralytics training code:
AGPL-3.0 (see `ML_DEPENDENCY_LICENSE.md`).
