# Dataset Final Validation Report

**Date:** 2026-09-20T20:58:37Z
**Scope:** Milestone 3 close-out audit. No Mask R-CNN training. No production edits.

## Train JSON status

- Path: `d:\fyp project\adore\ml_service\datasets\sources\fashionpedia\instances_attributes_train2020.json`
- Size: **542193045** bytes (517.08 MB)
- JSON readable: **True**
- Source images: **45623**
- Source annotations: **333401**
- Source categories: 46

## Converter run

Command: `python -m training.prepare_detection_dataset --source-dir datasets/sources/fashionpedia --annotations-only`

| Split | Images | Instances | Origin |
|---|---:|---:|---|
| train | 37887 | 115215 | official Fashionpedia train minus 12% holdout |
| val | 1146 | 3800 | official Fashionpedia val |
| test | 5227 | 15837 | deterministic holdout of official train |

Present image files on disk: train 37887, val 1146, test 5227.

## Class distribution

| class | train instances | val instances | test instances | total | % of instances |
|---|---:|---:|---:|---:|---:|
| shirt | 5397 | 102 | 764 | 6263 | 4.644 |
| jacket | 9581 | 287 | 1376 | 11244 | 8.338 |
| sweater | 1295 | 21 | 199 | 1515 | 1.123 |
| trousers | 10939 | 314 | 1475 | 12728 | 9.438 |
| shorts | 2417 | 106 | 339 | 2862 | 2.122 |
| skirt | 4419 | 162 | 627 | 5208 | 3.862 |
| dress | 16481 | 508 | 2258 | 19247 | 14.273 |
| jumpsuit | 809 | 21 | 113 | 943 | 0.699 |
| shoes | 40775 | 1565 | 5589 | 47929 | 35.542 |
| bag | 6372 | 214 | 845 | 7431 | 5.51 |
| hat | 2210 | 74 | 308 | 2592 | 1.922 |
| belt | 6031 | 164 | 816 | 7011 | 5.199 |
| scarf | 1216 | 48 | 158 | 1422 | 1.054 |
| watch | 3002 | 84 | 386 | 3472 | 2.575 |
| sunglasses | 4271 | 130 | 584 | 4985 | 3.697 |

Smallest classes: jumpsuit (943), scarf (1422), sweater (1515)
Largest classes: shoes (47929), dress (19247), trousers (12728)

Attention classes:

| class | train | val | test | total |
|---|---:|---:|---:|---:|
| sweater | 1295 | 21 | 199 | 1515 |
| jumpsuit | 809 | 21 | 113 | 943 |
| scarf | 1216 | 48 | 158 | 1422 |
| hat | 2210 | 74 | 308 | 2592 |
| watch | 3002 | 84 | 386 | 3472 |
| shirt | 5397 | 102 | 764 | 6263 |
| shorts | 2417 | 106 | 339 | 2862 |

No class was duplicated or rebalanced.

## Annotation validation findings

### train

No integrity errors.

### val

No integrity errors.

### test

No integrity errors.

Geometry / id / taxonomy errors (excluding missing files): **0**
Missing image files (annotations-only conversion): **0**

Errors were **reported, not silently repaired**.

## Taxonomy verification

Approved detector classes remain exactly the 15 names listed in `unified_label_map.json`.

Forbidden mappings checked on every kept annotation (`original_category` → `unified_category`):

- dress → skirt
- skirt → dress
- jumpsuit → dress
- sweater → hoodie
- scarf → dupatta
- bag → hat / skirt
- top, t-shirt, sweatshirt → shirt
- head-covering → hijab
- shoe → footwear

Forbidden mapping hits: **0**

Outfit20 and binary gate folders were not inputs to this converter. Unexpected annotation sources: **0**.

## Duplicate / leakage findings

Image ids and filenames were compared across splits. Pixel hashing ran only on files that exist locally.

| Pair | shared image ids | shared filenames |
|---|---:|---:|
| train ↔ val | 0 | 0 |
| train ↔ test | 0 | 0 |
| val ↔ test | 0 | 0 |

- Images hashed: 44260
- Exact duplicate groups (any split): 0
- Cross-split exact duplicates: 0
- Cross-split near-duplicates (aHash Hamming ≤ 4): 86844

No rows were deleted.

## Visual quality audit

Per-class overlays: `D:\fyp project\adore\evaluation_results\dataset_preview\by_class` (45 files).
Scene overlays: `D:\fyp project\adore\evaluation_results\dataset_preview`.

- Overlays draw instance boxes and polygons from the converted COCO files.
- Where pixels are missing, canvases are geometry-only and still show separate instances.

## Classes Requiring Attention Before Training

### sweater

- Train: 1295
- Val: 21
- Test: 199
- Annotation quality: Kept only from Fashionpedia sweater. Cardigan/hoodie/t-shirt-sweatshirt were excluded.
- Initial training: usable for initial training; extra real-world photos still advisable

### jumpsuit

- Train: 809
- Val: 21
- Test: 113
- Annotation quality: Kept as its own class; not merged into dress. Smallest detector class.
- Initial training: usable for initial training; extra real-world photos still advisable

### scarf

- Train: 1216
- Val: 48
- Test: 158
- Annotation quality: Neck scarf only. Dupatta/hijab/head-covering excluded.
- Initial training: usable for initial training; extra real-world photos still advisable

### watch

- Train: 3002
- Val: 84
- Test: 386
- Annotation quality: Small wrist instances; many tiny flags expected.
- Initial training: sufficient for initial Mask R-CNN training; real-world evaluation photos still needed later

### hat

- Train: 2210
- Val: 74
- Test: 308
- Annotation quality: Hat only. Head-covering/hair accessory excluded so hijab is not faked.
- Initial training: sufficient for initial Mask R-CNN training; real-world evaluation photos still needed later

### shirt

- Train: 5397
- Val: 102
- Test: 764
- Annotation quality: Only shirt, blouse. Mixed top/t-shirt/sweatshirt was excluded, so counts are conservative.
- Initial training: sufficient for initial Mask R-CNN training; real-world evaluation photos still needed later

### shoes

- Train: 40775
- Val: 1565
- Test: 5589
- Annotation quality: Dominant class; left and right shoes are separate instances. Sneakers/loafers/flats not distinguished.
- Initial training: sufficient for initial Mask R-CNN training; real-world evaluation photos still needed later

### dress

- Train: 16481
- Val: 508
- Test: 2258
- Annotation quality: One-piece dress masks. Not remapped to skirt.
- Initial training: sufficient for initial Mask R-CNN training; real-world evaluation photos still needed later

### skirt

- Train: 4419
- Val: 162
- Test: 627
- Annotation quality: Lowerwear skirt. Not remapped to dress.
- Initial training: sufficient for initial Mask R-CNN training; real-world evaluation photos still needed later

### bag

- Train: 6372
- Val: 214
- Test: 845
- Annotation quality: bag, wallet mapped to bag. Separate from clothing instances.
- Initial training: sufficient for initial Mask R-CNN training; real-world evaluation photos still needed later

## Training readiness decision

**READY_FOR_MILESTONE_4**

- COCO integrity checks passed.
- Approved 15-class taxonomy only.
- Official val intact; test holdout disjoint from train.
- Image files present: 44260.

Milestone 4 should use:

- `D:\fyp project\adore\ml_service\datasets\clothing_detection\annotations\instances_train.json`
- `D:\fyp project\adore\ml_service\datasets\clothing_detection\annotations\instances_val.json`
- `D:\fyp project\adore\ml_service\datasets\clothing_detection\annotations\instances_test.json`
- images under `D:\fyp project\adore\ml_service\datasets\clothing_detection\images` once pixels are present

## Confirmations

- Outfit20 was not converted.
- Binary gate folders were not converted.
- No Mask R-CNN / YOLO / specialist model was trained in this audit.
- Production inference, FastAPI, Flutter, and recommendation code were not modified.

