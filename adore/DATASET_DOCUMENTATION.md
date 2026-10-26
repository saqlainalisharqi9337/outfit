# Adore — Dataset Documentation

## Primary classification dataset

**Root (outside the git repo):** `D:\fyp project\dataset`

Layout (family / leaf folders under train/val/test splits as used by trainers):

| Family | Leaf classes |
|---|---|
| upperwear | jacket, shirt, t-shirt |
| bottomwear | pants/trousers, shorts, skirt |
| one-piece | dress |
| footwear | flats, heels, shoes, sneakers |
| accessories | bag, hat |

Folder labels only — **no bounding-box annotations**. That is why Stage B custom clothing YOLO is deferred (see `DATASET_PLAN.md`).

Approximate scale: thousands of images per leaf class (train order ~40k across classes historically).

## Licensed augmentations used

Documented in `ml_service/LAUNCH_READINESS.md`:

1. Existing Adore folder dataset.
2. [clothing-dataset-small](https://github.com/alexeygrigorev/clothing-dataset-small) (CC0).
3. Full [clothing-dataset](https://github.com/alexeygrigorev/clothing-dataset) (CC0) — imported with `fullopen_` prefix via `import_clothing_dataset_full.py` (~5k images).

**Not used:** commercial web scrape, shop crawls, Google Images bulk download.

**Planned but not downloaded:** Fashionpedia / iMaterialist (see `DATASET_PLAN.md`).

## Eval artefacts

- `ml_service/models/confusion_fix_report.json` — live routing smoke from `eval_confusion_fix_report.py`
- Specialist offline metrics printed by each `train_*.py` script
- `eval_photos/` — manual checklist scaffold (RESULTS not committed)

## Data policy

Training and demos must stay on openly licensed or project-owned images. See `ml_service/LAUNCH_READINESS.md` and `ML_DEPENDENCY_LICENSE.md`.
