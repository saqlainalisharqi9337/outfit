# Milestone 4.4 — Mask R-CNN Dataset Audit and Improved Training Preparation

**MILESTONE 4.4 STATUS: PASS**

Audit and preparation only. Full-dataset training was **not** started. Mask R-CNN was **not** wired into FastAPI. The 15-class taxonomy was **not** changed. Production YOLO / gates / FastAPI were not modified.

The converted dataset is structurally suitable for a larger **controlled** experiment. It is not a reason to claim a production detector.

## 1. Objective

Determine whether the converted COCO set is fit for a bigger Mask R-CNN run, explain the M4.3 failure modes with evidence, and prepare a class-aware CPU experiment **without launching it**.

## 2. Existing M4.3 findings

- 100 train / 50 val images, 1 CPU epoch, first-N JSON order
- Train loss 2.65 → 1.76; val loss 1.69
- Score 0.5: 0 predictions. Score 0.05: precision 0.10, recall 0.39, mAP@50 0.043
- Only shoes and dress had useful signal in that slice
- Pipeline (smoke, checkpoint, eval, tests) already passed

## 3. Dataset size

| Split | Images | Annotations | Files on disk | Missing files | Zero-ann images |
|---|---:|---:|---:|---:|---:|
| train | 37887 | 115215 | 37887 | 0 | 0 |
| val | 1146 | 3800 | 1146 | 0 | 0 |
| test | 5227 | 15837 | 5227 | 0 | 0 |
| **total** | **44260** | **134852** | **44260** | **0** | **0** |

Every class has `num_boxes == num_masks == num_annotations`.

Image sizes (JSON): roughly 233–1024 px wide, 388–1024 px tall; train mean ≈ 749×986. Sampled files were all RGB, JSON size matched the file, mask shape matched the image, bbox vs mask was not disjoint (60 sampled loads: 30 train / 15 val / 15 test).

## 4. 15-class mapping

Source: `ml_service/taxonomy/unified_label_map.json` (`class_id = index + 1`). Background is separate.

| class_id | class_name |
|---:|---|
| 0 | background |
| 1 | shirt |
| 2 | jacket |
| 3 | sweater |
| 4 | trousers |
| 5 | shorts |
| 6 | skirt |
| 7 | dress |
| 8 | jumpsuit |
| 9 | shoes |
| 10 | bag |
| 11 | hat |
| 12 | belt |
| 13 | scarf |
| 14 | watch |
| 15 | sunglasses |

## 5–6. Per-class image and annotation counts (all splits)

| id | class | images | annotations | % of anns | avg box W×H | tiny boxes |
|---:|---|---:|---:|---:|---|---:|
| 1 | shirt | 6217 | 6263 | 4.64 | 281×394 | 3 |
| 2 | jacket | 11041 | 11244 | 8.34 | 347×464 | 4 |
| 3 | sweater | 1506 | 1515 | 1.12 | 424×517 | 1 |
| 4 | trousers | 12660 | 12728 | 9.44 | 235×350 | 2 |
| 5 | shorts | 2851 | 2862 | 2.12 | 224×186 | 1 |
| 6 | skirt | 5196 | 5208 | 3.86 | 256×308 | 1 |
| 7 | dress | 19172 | 19247 | 14.27 | 309×571 | 5 |
| 8 | jumpsuit | 943 | 943 | 0.70 | 259×571 | 0 |
| 9 | shoes | 24757 | 47929 | 35.54 | 64×89 | 329 |
| 10 | bag | 7112 | 7431 | 5.51 | 126×235 | 4 |
| 11 | hat | 2588 | 2592 | 1.92 | 153×118 | 0 |
| 12 | belt | 6823 | 7011 | 5.20 | 137×93 | 67 |
| 13 | scarf | 1410 | 1422 | 1.05 | 182×295 | 0 |
| 14 | watch | 3454 | 3472 | 2.57 | 40×36 | 33 |
| 15 | sunglasses | 4978 | 4985 | 3.70 | 92×44 | 10 |

Train still has every class (shirt 5397 anns … jumpsuit 809 … shoes 40775). Val also has every class (shirt 102, sweater 21, jumpsuit 21, scarf 48, shoes 1565).

## 7. Class imbalance analysis

**CONFIRMED**

- Severe imbalance: max/min annotation ratio **50.8** (shoes 47929 vs jumpsuit 943)
- High-frequency: **shoes** (35.5%), **dress** (14.3%)
- Medium: jacket, trousers, bag, belt, shirt, skirt, sunglasses
- Low: shorts, watch, hat, sweater, scarf
- Suspiciously few by the <1% rule: **jumpsuit only** (0.70%)
- Shirt (6263), trousers (12728), skirt (5208), bag (7431), hat (2592), belt (7011) are **not** scarce in the full set
- Shoes are small on average (64×89) and contribute most tiny boxes (329)

No class was deleted or duplicated.

## 8. Annotation quality findings

45 ground-truth overlays (3 per class) in `outputs/maskrcnn_dataset_audit/annotations/`.

**CONFIRMED (sample, not a full manual pass of 44k images)**

- Dress, skirt, bag, hat, belt, trousers, shoes, scarf, jumpsuit examples showed separate instances with matching boxes and masks (e.g. purple skirt + bag + two shoes; magenta dress + clutch; hat + shirt + belt + trousers + two shoes).
- Shoes are often two instances per image; boxes are small. That matches the count (≈1.9 shoes anns per shoes-image).
- Structural scan of **all** 134,852 annotations found **zero** invalid boxes, zero unknown class IDs, zero missing/empty masks, zero duplicate (image, class, rounded-bbox) rows.

**Observed in previews (do not silently “fix”)**

- One street photo (`47cbe3ead1617a9971dccc438a8e8884`) draws a `shirt` box over a **blazer**; the same file was also selected as a jacket preview, so a jacket instance exists on that image. Possible overlapping shirt/jacket on one outer garment.
- A lace blouse above a correctly labeled skirt was unlabeled. **Hypothesis:** source class was a rejected Fashionpedia “top”, not a taxonomy bug.
- Gloves on a runway dress were unlabeled (rejected “glove”).

These are not integrity blockers and are **not** a reason to rename classes.

## 9. Train/validation split findings

**CONFIRMED**

- Filename overlap train∩val, train∩test, val∩test: **0**
- Image-id overlap across those pairs: **0**
- No class present in train but missing from val, or the reverse
- Val is shoe-heavier (41% of val anns vs 35% train) but still contains all 15 classes

Near-duplicates: exact filename/id leakage is absent. Pixel-level perceptual hashing of 44,260 files was not run (not needed after zero exact overlap).

## 10. Image/mask quality findings

**CONFIRMED**

- 0 missing image files
- Sampled PIL modes: RGB only
- 0 JSON vs file size mismatches in the sample
- 0 mask/image shape mismatches in the sample
- 0 bbox-vs-mask disjoint cases in the sample
- Dataset loader already converts via `exif_transpose` + RGB; no preprocessing change

## 11. Confirmed problems

1. **M4.3 subset was not representative.** `max_images` took the **first N JSON rows**. That slice had 139 shoes / 53 dresses / 9 shirts / 1 sweater. The full train set has 5397 shirts and 40775 shoes.
2. **Class imbalance is real** (shoes + dress = ~50% of annotations).
3. **Jumpsuit is the only class under 1%** (943 anns).
4. **Shoes and watches/belts include many small boxes** (tiny ≠ invalid).
5. **One-epoch random classification heads** plus score 0.5 produced zero detections in M4.3 — that is a training-budget/threshold issue, not a missing-annotation issue.

## 12. Suspected problems (hypotheses, not facts)

- M4.3 “shirt/trousers/skirt/bag/hat/belt failed” **because those classes were rare in the 100-image prefix**, not because the dataset lacks them.
- Score 0.5 is too high after 1 epoch of 100 images; ranking mAP@50 = 0.043 is consistent with underfitting, not empty GT.
- Dress/jacket overlap in predictions may partly reflect overlapping GT on layered outfits (coat + dress is valid; blazer-as-shirt is a possible source-label noise).
- Unlabeled tops on some skirt images may be rejected Fashionpedia “top, t-shirt, sweatshirt”.
- Architecture is **not** implicated by M4.3; the smoke test already proved finite mask/box/class losses.

## 13. Recommended training configuration

**Do not run this as part of M4.4.** CPU-only, class-aware subset, still capped.

```text
.\.venv\Scripts\python.exe -u training\train_maskrcnn.py --max-train-images 500 --max-val-images 100 --epochs 3 --batch-size 1 --num-workers 0 --class-aware-subset --lr 0.005 --seed 42 --score-threshold 0.3 --checkpoint-dir ..\checkpoints\maskrcnn
```

| Setting | Value | Why |
|---|---|---|
| train images | 500 | 5× M4.3; ~1 hour-scale on this CPU (M4.3 was ~6 min for 100×1) |
| val images | 100 | all 15 classes exist in official val |
| epochs | 3 | enough to see score>0.3 detections without a 44k run |
| subset | `--class-aware-subset` | round-robin from rarest class (jumpsuit/sweater/scarf first), seed 42, then fill |
| batch / workers | 1 / 0 | CPU |
| min/max size | 256 / 320 | existing CPU defaults |
| eval score | 0.3 | 0.5 was empty after 1×100; 0.3 is a diagnostic operating point |

`--allow-full` remains off. Smoke test is unchanged.

Subset algorithm (implemented in `training/dataset.py::class_aware_select`): group images by class, shuffle each group with the seed, repeatedly take the next unused image from the currently rarest class, then fill from leftovers.

## 14. Tests performed

```text
.\.venv\Scripts\python.exe -m pytest tests/test_maskrcnn_pipeline.py tests/test_maskrcnn_m43.py tests/test_maskrcnn_audit.py -q
.\.venv\Scripts\python.exe -u training\train_maskrcnn.py --smoke-test --no-preview
.\.venv\Scripts\python.exe -u training\audit_dataset.py
```

- **16 passed** (6 M4.2 + 5 M4.3 + 5 M4.4)
- **SMOKE TEST PASSED**
- Audit wrote JSON/CSV/markdown and 45 GT overlays

Larger training was not started.

## 15. Files created/modified

Created:

- `ml_service/training/audit_dataset.py`
- `ml_service/tests/test_maskrcnn_audit.py`
- `outputs/maskrcnn_dataset_audit/dataset_audit.json`
- `outputs/maskrcnn_dataset_audit/dataset_audit.csv`
- `outputs/maskrcnn_dataset_audit/DATASET_AUDIT_REPORT.md`
- `outputs/maskrcnn_dataset_audit/annotations/*.jpg` (45)
- `MILESTONE_4_4_REPORT.md`

Modified:

- `ml_service/training/dataset.py` — `class_aware_select` + `subset_mode`
- `ml_service/training/train_maskrcnn.py` — `--class-aware-subset`, `--score-threshold`
- `ml_service/training/README.md`

## 16. Ready for the next training experiment?

**Yes, for a capped class-aware run.** Not for full 44,260-image training on this CPU, and not for production integration.

No unresolved integrity failures (missing files, split leakage, unknown IDs, empty masks). Remaining issues are imbalance, small objects, occasional source-label noise, and the M4.3 first-N sampling bug — all documented and addressed by `--class-aware-subset`.
