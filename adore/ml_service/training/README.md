# Clothing detection dataset preparation

Milestone 3 only: convert genuine instance annotations into a 15-class COCO set
for a future Mask R-CNN. This directory does **not** train models and is not
imported by FastAPI production code.

## Source of truth

- `DATASET_LABEL_MAPPING.md`
- `ml_service/taxonomy/unified_label_map.json`

Unsafe maps that this pipeline will refuse:

- sweater → hoodie
- dress → skirt
- bag → hat
- scarf → dupatta
- jumpsuit → dress
- generic top → shirt

## What is used

| Source | Why |
|---|---|
| **Fashionpedia** official COCO (Jia et al., ECCV 2020) | Grade A: instance masks + boxes + attributes. CC BY 4.0. |

## What is not used

| Source | Why |
|---|---|
| DeepFashion2 | Academic non-commercial license; download form + unzip password; no commercial license; tops are not shirt vs t-shirt; no bag/hat/watch/sunglasses/belt |
| outfit20 | Synthetic full-frame boxes `0.5 0.5 0.92 0.92` |
| Binary `*_gate` trees | Rivalry labels, not a closed instance taxonomy |
| Local Adore folders / Grigorev / HF crops / secondhand / upperwear6 / lowerwear5 | No instance masks |

HuggingFace `detection-datasets/fashionpedia` is **not** the GT source: it stores Pascal VOC boxes and **drops segmentation**.

## Fashionpedia download (explicit, not silent)

Source files (CVDF / iFashionist):

| File | URL | Role |
|---|---|---|
| `instances_attributes_train2020.json` | https://s3.amazonaws.com/ifashionist-dataset/annotations/instances_attributes_train2020.json | Train instances + polygons/RLE |
| `instances_attributes_val2020.json` | https://s3.amazonaws.com/ifashionist-dataset/annotations/instances_attributes_val2020.json | Official val |
| `train2020.zip` | https://s3.amazonaws.com/ifashionist-dataset/images/train2020.zip | Train images |
| `val_test2020.zip` | https://s3.amazonaws.com/ifashionist-dataset/images/val_test2020.zip | Val/test images |

- License: **CC BY 4.0** (attribution: Jia et al., ECCV 2020)
- Expected size: several GB of images; annotation JSON is hundreds of MB
- Destination: `ml_service/datasets/sources/fashionpedia/`
- Converted output: `ml_service/datasets/clothing_detection/`

Public test labels do not exist. This pipeline keeps official val intact and holds out 12% of official **train** image ids for a labeled test split (stable MD5, salt `adore-milestone3-fashionpedia-test-holdout`).

## Pipeline

```text
Fashionpedia COCO JSON
  → map names via unified_label_map.json
  → drop rejected / part / DATA REQUIRED / invalid rows
  → write COCO instances_{train,val,test}.json
  → copy only images that still have an instance
  → hash duplicates
  → draw preview overlays
```

## Commands (from `ml_service`, Python 3.12 venv)

```text
# Convert annotations only (current Milestone 3 run):
.\.venv\Scripts\python.exe -m training.prepare_detection_dataset --source-dir datasets\sources\fashionpedia --annotations-only
.\.venv\Scripts\python.exe -m training.visualize_detection_dataset
.\.venv\Scripts\python.exe -m training.audit_detection_dataset
.\.venv\Scripts\python.exe -m pytest tests/test_prepare_detection_dataset.py -q

# Later, when disk allows, copy pixels from official zips (still no training):
.\.venv\Scripts\python.exe -m training.prepare_detection_dataset --download
```

`--download` is required to fetch Fashionpedia. Without it, the script only runs if the JSON files are already in `--source-dir`.

`--annotations-only` converts JSON and writes statistics without copying images (useful if disk is tight).

Packages already used: Python 3.12, Pillow, (stdlib urllib/json/hashlib/zipfile). No MMDetection install is required for this milestone.

## Output layout

```text
ml_service/datasets/clothing_detection/
  images/train|val|test/
  annotations/instances_train.json
  annotations/instances_val.json
  annotations/instances_test.json
  stats.json
  reports/
  real_world_test/PLAN.md
  README.md
evaluation_results/dataset_preview/
DATASET_PREPARATION_REPORT.md
```

Images are copied out of the zip **only for kept file names**. The zip itself stays in `datasets/sources/` and is not duplicated by a full extract.

## Detector classes written into COCO

1. shirt  2. jacket  3. sweater  4. trousers  5. shorts
6. skirt  7. dress  8. jumpsuit  9. shoes  10. bag
11. hat  12. belt  13. scarf  14. watch  15. sunglasses

DATA REQUIRED (not in COCO): t-shirt, hoodie, jeans, sneakers, loafers, flats, dupatta, hijab.

## Milestone 4.2 training pipeline

Mask R-CNN training lives in this package and is **not** wired into FastAPI.

```text
# From ml_service — smoke test only (one batch, then exit):
.\.venv\Scripts\python.exe -m training.train_maskrcnn --smoke-test
.\.venv\Scripts\python.exe -m pytest tests/test_maskrcnn_pipeline.py -q
```

Do **not** run the entire 37,887-image train split on CPU. Use a capped small run:

```text
.\.venv\Scripts\python.exe -m training.train_maskrcnn --max-train-images 500 --max-val-images 100 --epochs 3 --batch-size 1 --num-workers 0 --class-aware-subset
.\.venv\Scripts\python.exe -m training.audit_dataset
.\.venv\Scripts\python.exe -m training.evaluate_maskrcnn --checkpoint ..\checkpoints\maskrcnn\best_model.pth --max-images 100
```

`--allow-full` is required to disable the image cap. Production FastAPI inference is unchanged.

## Current conversion status (Milestone 3)

Official train + val JSON are converted. No Mask R-CNN was trained.

| Split | Images | Instances |
|---|---:|---:|
| train | 37887 | 115215 |
| val | 1146 | 3800 |
| test | 5227 | 15837 |
| **total** | **44260** | **134852** |

Annotation JSON sizes: train `542193045` bytes, val `14533475` bytes.

Image pixels: **not fully copied** (`--annotations-only`). Official zips or `--images-from-hf` are required before training. Duplicate hashing waits for pixels. Previews are geometry overlays until then.

Do not convert outfit20 or gate folders.

## Do not

- Train Mask R-CNN from these scripts
- Modify `clothing_classifier.py`, gates, YOLO, FastAPI, Flutter, or the recommendation engine
- Feed outfit20 or gate folders into this converter
