# Project Clothing Recognition Audit

**Milestone 1 of 8 — diagnostic only.**  
**Project:** Smart Cloth Advisor and Outfit Recommendation (Adore FYP)  
**Auditor role:** Lead Computer Vision Engineer / ML Systems Architect  
**Date:** 2026-09-20  
**Scope:** Inspect the repository. Do not train models, write production code, or delete files.

**Verdict:** The live engine is a **classification-first router with optional YOLO boxes**. It is not instance segmentation, not Mask R-CNN, and not a single unified detector. The failures listed in the project brief (silhouette mix-ups, label interference, colour over-generalization, dataset contamination) are consistent with this architecture. MMDetection is **not present** in application code.

---

## 1. What the system is today

```
Input image
  ├─ classify_clothing()          # whole-frame MobileNet/ResNet + ~15 binary gates
  ├─ object_detector (optional)   # COCO YOLOv8n person/bag + Fashionpedia YOLO boxes
  ├─ outfit20_detector (optional) # 20-class YOLO fine-tune OR Fashionpedia fallback
  ├─ region_proposals             # pose / person-box / hardcoded bands
  ├─ classify each crop again     # same specialists
  └─ color_analysis               # GrabCut/Lab flood + K-Means (not a class mask)
        └─ JSON via FastAPI POST /analyze-clothing
              └─ Flutter ImageAnalysisService + ClothingCatalog.resolvePrediction
                    └─ RecommendationService (rule-based; does not re-classify)
```

This is the inverse of the target pipeline. Target wants **detect instances first, then analyse each mask**. Today the system **guesses a class on the full frame first**, then uses boxes (when available) as an afterthought.

| Target (Milestone 4–7) | Current production |
|---|---|
| Mask R-CNN / ResNet-50-FPN via MMDetection | Not in repo. Torchvision Mask R-CNN exists only inside `.venv`. |
| Instance masks isolate each garment | No masks. YOLO boxes + rectangle crops + GrabCut. |
| One unified taxonomy model | 15+ specialist classifiers + a 2,400-line router |
| Flask `/api/detect-outfit` | **FastAPI** `http://127.0.0.1:8000` — `/analyze-clothing`, `/detect`, `/teach-clothing`, `/debug-colors`, `/analyze-skin-tone` |
| Per-mask colour array + pattern | Lab K-Means on a **crop**, not a class mask. Pattern is heuristic; Flutter still lets the user override. |

Honest pipeline label already documented in `ML_PIPELINE.md` and `DETECTION_LIMITATIONS.md`: pretrained YOLO **assists localisation**; garment **names come from classifiers**.

---

## 2. Inventory

### 2.1 Inference modules (`ml_service/app/`)

| File | Role |
|---|---|
| `main.py` | FastAPI app, warmup, health, endpoints |
| `outfit_parser.py` | Multi-item merge: full-frame classify + YOLO/outfit20 + regions + colour |
| `clothing_classifier.py` | Central router (~2,400 lines). Calls every gate. This is the interference surface. |
| `object_detector.py` | COCO YOLOv8n (`person`, backpack/handbag) + Fashionpedia YOLO accessory boxes |
| `outfit20_detector.py` | Optional 20-class YOLOv8 fine-tune; else Fashionpedia |
| `region_proposals.py` | Pose bands → person box bands → whole-image fallback rectangles |
| `fashionpedia_map.py` | Fashionpedia 46 names → Adore leaves (accessories + garment hints) |
| `outfit20_taxonomy.py` | 20 detector class IDs (`upperwear_shirt`, `one_piece_dress`, …) |
| `clothing_taxonomy.py` | Folder→class map, family rules, ImageNet preprocess |
| `garment_classifier.py` | Upperwear 6-class ResNet18 (shirt, t-shirt, hoodie, jacket, top, dress) |
| `lowerwear5.py` | Lowerwear 5-class ResNet18 (trousers, shorts, skirt, shalwar, leggings) |
| `silhouette_classifier.py` | dress vs skirt vs trousers (MobileNet) |
| `lowerwear_classifier.py` | trousers vs shorts vs skirt (MobileNet) |
| `accessory_classifier.py` | 8-class accessories (or legacy bag/hat/skirt/shoes) |
| `footwear_classifier.py` | shoes / flats / sneakers / heels |
| `dress_upperwear_gate.py` | Binary dress vs upperwear |
| `*_gate.py` (14 files) | Binary “lock or prefer” specialists |
| `color_analysis.py` | Per-crop K-Means in CIE Lab + pattern heuristic |
| `color_detection.py` | Older colour path (still imported in places) |
| `skin_tone.py` | ITA heuristic for `/analyze-skin-tone` |
| `teach.py` | Saves user labels; does not retrain live |
| `detection_schema.py` | BBox / proposal JSON contract |
| `config.py` | `ADORE_*` env knobs |

**There is no `feature_extractor.py`, no MMDetection config, and no `/api/detect-outfit`.**

### 2.2 Binary gates (preserve as baseline)

Each gate is a MobileNetV2 binary (or tiny multi-class) head whose job is to **steal** the label when a rival family is winning.

| Module | Weights | Typical rivalry |
|---|---|---|
| `bag_gate.py` | `bag_gate_mobilenetv2.keras` | bag vs skirt vs flats |
| `hat_gate.py` | `hat_gate_mobilenetv2.keras` | hat vs shirt/skirt |
| `watch_gate.py` | `watch_gate_mobilenetv2.keras` | watch vs bag |
| `watch_belt_gate.py` | `watch_belt_gate_mobilenetv2.keras` | belt vs bag |
| `dupatta_gate.py` | `dupatta_gate_mobilenetv2.keras` | dupatta vs bag |
| `trousers_gate.py` | `trousers_gate_mobilenetv2.keras` | trousers vs shirt/dress |
| `skirt_gate.py` | `skirt_gate_mobilenetv2.keras` | skirt vs dress |
| `shirt_gate.py` | `shirt_detector_mobilenetv2.keras` | shirt vs dress/hat |
| `tshirt_gate.py` | `tshirt_gate_mobilenetv2.keras` | t-shirt vs shirt |
| `jacket_gate.py` | `jacket_gate_mobilenetv2.keras` | jacket vs hoodie/shirt |
| `flats_gate.py` | `flats_gate_mobilenetv2.keras` | flats vs hat/shirt |
| `heels_gate.py` | `heels_gate_mobilenetv2.keras` | heels vs shirt/flats |
| `sneakers_gate.py` | `sneakers_gate_mobilenetv2.keras` | sneakers vs hat/flats |
| `shoes_gate.py` | `shoes_gate_mobilenetv2.keras` | oxfords vs heels/sneakers |

`clothing_classifier.py` evaluates **many of these on every image**, then returns the first lock that passes a stack of thresholds. Adding a class means adding another lock, which is why existing classes regress.

### 2.3 Training scripts (`ml_service/`)

Family trainers (classification, folder labels):

- `train_clothing_mobilenet.py` — unused unified 13-class path
- `train_dress_pants_skirt.py`, `train_trousers_shorts_skirt.py`, `train_bag_shoes.py`
- `train_accessories.py`, `train_upperwear_pytorch.py`, `train_upperwear6.py`
- `train_lowerwear5.py`, `train_footwear_pytorch.py`, `train_dress_upperwear_gate.py`
- `train_*_gate.py` for each binary gate
- `train_outfit20.py` / `export_outfit20.py` / `eval_outfit20.py` — YOLO 20-class (boxes, not masks)

Dataset builders: `prepare_*_dataset.py`, `prepare_upperwear6_dataset.py`, `expand_upperwear6.py`, `augment_upperwear6_unclear.py`, `prepare_outfit20_dataset.py`, `import_open_clothing_dataset.py`, `import_clothing_dataset_full.py`, `download_fashionpedia_yolo.py`, `download_wikimedia_weak_classes.py`.

**No Mask R-CNN trainer. No MMDetection config. No COCO mask JSON exporter.**

### 2.4 Weights (`ml_service/models/`)

Referenced at runtime (keep all of these as the **YOLO + specialist baseline**):

| Checkpoint | Framework | Classes / role |
|---|---|---|
| `yolov8n.pt` | Ultralytics | COCO person / bag boxes |
| `yolov8n-fashionpedia-1.torchscript` | Ultralytics | Fashionpedia accessory/garment **boxes** |
| `improved/outfit20_yolov8n.pt` | Ultralytics | Optional 20-class boxes |
| `upperwear6_resnet18.pt` | PyTorch ResNet18 | shirt, t-shirt, hoodie, jacket, top, dress (held-out ~90% acc, 2026-09) |
| `upperwear3_resnet18.pt` | PyTorch | shirt, t-shirt, jacket (fallback) |
| `lowerwear5_resnet18.pt` | PyTorch | trousers, shorts, skirt, shalwar, leggings |
| `footwear4_resnet18.pt` | PyTorch | shoes, flats, sneakers, heels |
| `dress_upperwear_gate.pt` | PyTorch | dress vs upperwear |
| `dress_pants_skirt_mobilenetv2.keras` | Keras | dress / skirt / trousers |
| `trousers_shorts_skirt_mobilenetv2.keras` | Keras | trousers / shorts / skirt |
| `accessories8_mobilenetv2.keras` | Keras | bag, belt, scarf, dupatta, hat, hijab, jewelry, sunglasses |
| `bag_shoes_mobilenetv2.keras` | Keras | legacy bag/hat/skirt/shoes |
| `*_gate_mobilenetv2.keras` | Keras | 14 binary gates |
| `mobilenet_v2_imagenet_1.0_224.h5` | Keras | ImageNet cues |

Eval JSON lives beside each specialist (`*_eval.json`, `*_live_eval.json`, `upperwear6_metrics.json`). `confusion_fix_report.json` is a **small live smoke**, not a detection mAP.

### 2.5 Datasets

| Location | Kind | Labels |
|---|---|---|
| `D:\fyp project\dataset` (outside git) | Primary classification folders | Family/leaf folders only. **No boxes, no masks.** |
| `ml_service/datasets/upperwear6` | Built train/val/test | shirt, t-shirt, hoodie, jacket, top, dress + unclear copies |
| `ml_service/datasets/lowerwear5` | Built train/val/test | trousers, shorts, skirt, shalwar, leggings + unclear copies |
| `ml_service/datasets/open_clothing` | Cached public images | Grigorev zip, fashion-product-small, secondhand crops |
| `ml_service/datasets/outfit20` | YOLO fine-tune set | 20 box classes (if prepared) |
| `ml_service/datasets/user_labeled` | Teach-by-example | User folder labels |

`DATASET_DOCUMENTATION.md` / `DATASET_PLAN.md`: local train historically ~40k images; **jeans, coat, hoodie, sweater, scarf, jewelry folders were empty** on the original disk layout. Hoodie/top were later filled from HuggingFace/Grigorev for upperwear6 only. Fashionpedia **instance** download is still “planning only” in `DATASET_PLAN.md` (YOLO Fashionpedia weights may exist even if the full COCO JSON was never curated here).

### 2.6 HTTP API (FastAPI, not Flask)

| Method | Path | Consumer |
|---|---|---|
| GET | `/health`, `/health/live`, `/health/ready` | Ops / Flutter readiness |
| POST | `/analyze-clothing` | **`lib/services/image_analysis_service.dart`** (wardrobe add) |
| POST | `/detect` | Detector-only debug (not used by Flutter wardrobe flow) |
| POST | `/teach-clothing` | Same Dart service (user correction) |
| POST | `/debug-colors` | Colour QA collage |
| POST | `/analyze-skin-tone` | Profile skin assist |

Base URL: `lib/utils/constants.dart` → `http://127.0.0.1:8000` (web) / `http://10.0.2.2:8000` (Android emulator).

Typical `/analyze-clothing` fields: `category`, `subcategory`, `confidence`, `source`, `usedFallback`, `color`, `secondaryColor`, `colorDistribution`, `pattern`, `items[]`, `detected[]`, `isolatedProduct`, `needsHumanReview`.

### 2.7 Flutter consumers

| File | Role |
|---|---|
| `lib/services/image_analysis_service.dart` | Calls ML; **second router** (pants vs dress, isolated shoe, local upperwear override) |
| `lib/utils/clothing_catalog.dart` | Canonical UI taxonomy + `resolvePrediction` **third router** |
| `lib/services/local_image_analysis.dart` | On-device fallback if ML is down |
| `lib/screens/wardrobe/add_clothing_screen.dart` | Shows ML guess; user confirms category / colour / **pattern** |
| `lib/models/wardrobe_item.dart` | Stores `color`, `colors`, `pattern`, `pattern_source` |
| `lib/services/recommendation_service.dart` | **Does not detect clothing.** Ranks outfits from stored labels + weather/culture/occasion |

Recommendation is rule-based scoring (`RECOMMENDATION_ENGINE.md`). Wrong ML labels poison outfits; the recommender cannot recover a missed instance.

### 2.8 Tests (baseline contracts)

`ml_service/tests/` — gate payload contracts, Fashionpedia mapping, colour analysis, upperwear6 routing, lowerwear/sneaker regression, API schema. Last full run in this project: **102 passed**.

Flutter: `test/local_clothing_analysis_test.dart` locks merge rules (hat must not become skirt, hoodie from `source=upperwear` must beat a local shirt, etc.).

---

## 3. Taxonomy gaps (current vs target)

Target hierarchy vs what the code actually predicts:

| Target family | Target leaves | Current production | Gap |
|---|---|---|---|
| UPPERWEAR | t-shirt, shirt, hoodie, jacket, sweater | upperwear6: t-shirt, shirt, hoodie, jacket, **top** (no sweater). Flutter also: kurta, blouse, coat, blazer, cardigan, kameez, abaya | **sweater untrained** in the 6-class head. Coat/blazer often collapsed to jacket. |
| LOWERWEAR | trousers, jeans, shorts, skirt | lowerwear5: trousers, shorts, skirt, **shalwar, leggings**. Jeans mapped into trousers | **jeans not a distinct class.** Extra South-Asian leaves not in the target list. |
| ONE-PIECE | dress, jumpsuit | Category `dress` with dress/gown; jumpsuit aliased to dress. outfit20 maps jumpsuit → `one_piece_dress` | **jumpsuit not a real class.** Flutter uses `ClothingCategory.dress`, not `one-piece`. |
| FOOTWEAR | shoes, sneakers, loafers, flats | shoes, sneakers, flats, **heels**, plus ImageNet boots/sandals. outfit20: loafers yes, heels collapsed to shoes | **heels exist in product but not in the target list.** Loafers weak. |
| ACCESSORIES | bag, hat, belt, scarf, dupatta, watch, hijab, sunglasses | Same plus jewelry. DeepFashion2 historically had **no accessories** (documented cause of bag→skirt, cap→dress) | Jewelry extra. Hijab/dupatta exist in gates, sparse in local folders. |

`CONFUSABLE_PAIRS` in `clothing_taxonomy.py` already names the chronic collisions: hat↔shirt, dress↔skirt, dress↔trousers, shirt↔t-shirt, jacket↔hoodie, jeans↔trousers, bag↔skirt.

---

## 4. Root-cause breakdown

### 4.1 Silhouette confusion (dress ↔ skirt/hat/shoes; bag ↔ clothing)

**Cause:** Whole-image classifiers see a hanging rectangle. A dress, skirt, tote, and baseball cap share similar aspect ratios. There is **no instance mask** to separate “this region is a bag” from “this region is a skirt panel”.

Evidence in code and docs:

- `DETECTION_LIMITATIONS.md`: COCO has no clothing classes; DeepFashion2 has no accessories.
- `bag_gate.py` docstring: tote reads as hanging rectangle → skirt or flats.
- `region_proposals.py`: fallback bands are **fixed fractions of the frame**. A close-up shoe lands in the “lower” band and becomes trousers.
- Live smoke (`models/confusion_fix_report.json`, n≈12/class): skirt **25%**, hat **42%**, heels **17%**, sneakers **25%**, sandals **0%**. These are routing/classifier failures on product photos, not mAP.

**Why Mask R-CNN is the right next architecture:** a bag instance gets its own mask; a dress instance gets a full-body mask; a cap is a small head instance. Classification on the **masked pixels** cannot see the rival silhouette.

### 4.2 Label interference (trousers as shirts; hoodie/jacket swap; new class breaks old ones)

**Cause:** Competing heads on the same pixels, winner-take-all router.

1. ImageNet MobileNetV2 emits a weak prior (`jersey`→t-shirt, `sweatshirt`→hoodie, `cowboy_hat`→hat).
2. Fourteen binary gates each try to **lock** their class.
3. Multi-class heads (upperwear6, lowerwear5) only win if thresholds and `usedFallback` allow it.
4. Flutter then re-routes (`image_analysis_service.dart` + `resolvePrediction`).

Observed failure modes already patched around, not eliminated:

- Shirt/jacket gates stole hoodies and gowns until upperwear6 was allowed to return at ≥0.38 (`test_upperwear6_routing.py`).
- `trousers_gate` has no hoodie class, so a hanging hoodie can lock as trousers or shirt depending on order.
- Adding `lowerwear5` required explicit “do not steal if upperwear6 owns the crop” — another threshold, another regression risk.
- Gate internals were frozen by user rule because retraining one binary head moved the lock boundary for every other class.

This is **catastrophic interference by construction**: each specialist is trained without the others in the loss. The router is the only place they meet.

### 4.3 Colour over-generalization

**Cause (historical):** Dominant-colour = brightest / largest blob in the full JPEG, including background and skin.

**Current mitigation (`color_analysis.py`):** crop → GrabCut or Lab border flood → gray-world → K-Means in CIE Lab (area, not brightness) → primary/secondary/accent by share → pattern from spatial cluster map (`solid`, `striped`, `checked`, `floral`, `printed`, …).

Remaining holes vs target:

- Isolation is **GrabCut on a box**, not a class mask. Background and adjacent garments leak into K.
- Colour still runs on the **person box or full frame** for the primary item when YOLO misses the garment (`outfit_parser.py`).
- Flutter `add_clothing_screen` stores a single `color` plus optional distribution; recommendation scoring mostly uses the primary name.
- Pattern CNN does not exist (`LIMITATIONS.md`). Heuristic floral/checked is easy to fool.

Milestone 6 should attach K-Means to **Mask R-CNN masks**, not invent a second colour stack. Reuse `color_analysis.py`.

### 4.4 Dataset contamination

**Cause:** Folder-label classification sets mixed from:

- Private Adore product photos (`D:\fyp project\dataset`)
- Grigorev clothing-dataset (shirt/t-shirt/outwear/hoodie/dress)
- `ashraq/fashion-product-images-small` (articleType strings: Sweatshirts mapped to hoodie, Kurtas to shirt, Gowns to dress)
- `wargoninnovation/clothingdatasetsecondhand` (background-removed; Hoodie/Top/Night gown)
- Fashionpedia **crops** for accessories (not full instance training set)

Unharmonized mappings:

- Sweaters → hoodie in one importer, skipped in another.
- Jeans → trousers everywhere; target wants jeans separate.
- Heels → `footwear_shoes` in outfit20; separate class in footwear4.
- Local hoodie/sweater folders were **empty** while Flutter already listed those leaves.

No instance-level train/val/test with a **single** label map. Images can appear in a gate dataset and a specialist dataset (leakage across heads, not necessarily within one split).

---

## 5. Why YOLO-as-classifier cannot be the long-term core

Keep YOLO as a **baseline benchmark** (Milestone 5: mAP vs Mask R-CNN). Do not promote it to the unified production model without masks.

| Constraint | Impact |
|---|---|
| COCO YOLOv8n classes | person + bags only |
| Fashionpedia YOLO | boxes, 46 ontology including **parts** (sleeve, zipper) that steal garment boxes if not filtered |
| outfit20 | 20 box classes; **no hoodie, no sweater, no jeans, no loafers/heels split, no jumpsuit** |
| Local data | folder labels, no polygons → cannot train Mask R-CNN until Milestone 3 curates COCO/MMDet annotations |
| Ultralytics license | AGPL-3.0 (`ML_DEPENDENCY_LICENSE.md`) — Fine for local FYP; document if the report claims “custom YOLO clothing detector” (it must not) |

---

## 6. File list — preserve vs modify later

### 6.1 Preserve (do not delete; use as baseline / regression)

Do not retrain or rewrite internals of working gates unless a later milestone explicitly replaces them behind a feature flag.

**Gates and weights**

- `ml_service/app/{hat,bag,watch,watch_belt,dupatta,trousers,skirt,shirt,tshirt,jacket,flats,heels,sneakers,shoes}_gate.py`
- Matching `ml_service/models/*_gate_mobilenetv2.keras` and `shirt_detector_mobilenetv2.keras`
- `ml_service/tests/test_*_gate.py`, `test_regression_lowerwear_sneakers.py`

**YOLO baseline**

- `object_detector.py`, `outfit20_detector.py`, `fashionpedia_map.py`, `region_proposals.py`
- `yolov8n.pt`, `yolov8n-fashionpedia-1.torchscript`, `models/improved/outfit20_yolov8n.pt` if present
- `DETECTION_LIMITATIONS.md`, `ML_PIPELINE.md`

**Specialists (benchmark + fallback)**

- `garment_classifier.py` + `upperwear6_resnet18.pt`
- `lowerwear5.py` + `lowerwear5_resnet18.pt`
- `footwear_classifier.py`, `silhouette_classifier.py`, `lowerwear_classifier.py`, `accessory_classifier.py`
- `color_analysis.py` (reuse for Milestone 6)

**Product surface (do not break recommendation)**

- `lib/services/recommendation_service.dart`
- `lib/utils/clothing_catalog.dart` taxonomy lists (extend via mapping layer, do not silently rename stored wardrobe rows)
- Supabase `wardrobe_items` schema
- Flutter add-clothing confirm UI

### 6.2 Modify in later milestones (not now)

| Milestone | Files |
|---|---|
| 2 | New `DATASET_LABEL_MAPPING.md`; `clothing_taxonomy.py` / `outfit20_taxonomy.py` mapping tables only after approval |
| 3 | New dataset export scripts; **do not rmtree** existing `datasets/upperwear6` or gate folders |
| 4 | New MMDetection config + `COLAB_TRAINING_GUIDE.md`; `requirements.txt` (mmcv/mmdet) — additive |
| 5 | `MODEL_EVALUATION_REPORT.md`; eval vs YOLO baseline |
| 6 | New `feature_extractor.py` wrapping `color_analysis.py` on masks |
| 7 | `main.py` — **add** `/api/detect-outfit` (or alias) without removing `/analyze-clothing`; `image_analysis_service.dart` consume structured items |
| 8 | `evaluation_results/` visual debug; integration tests |

### 6.3 Highest-risk file if edited carelessly

`ml_service/app/clothing_classifier.py` — every specialist returns through this function. Milestone 7 should **bypass** it for Mask R-CNN detections (classify-on-mask path) rather than adding a 16th gate.

---

## 7. Alignment with the target pipeline

Recommended shape after later milestones (for planning only):

```
Image
  → Mask R-CNN (ResNet-50-FPN)  [instances: bbox, mask, class, score]
  → for each instance:
        crop × mask
        → colour K-Means (existing color_analysis)
        → pattern heuristic / later CNN
  → JSON items[]  → FastAPI (keep; Flask is not in this repo)
  → Flutter resolvePrediction only as a safety net, not a second classifier
```

**API note:** Replacing FastAPI with Flask is unnecessary for the FYP. Milestone 7 should keep uvicorn and add the structured outfit payload. If a report requires the path name `/api/detect-outfit`, add it as an alias of `/analyze-clothing`.

**Compute note:** This machine previously trained ResNet18 on CPU only (`torch.cuda.is_available() == False`). Mask R-CNN transfer learning belongs on Colab/GPU (Milestone 4 guide).

---

## 8. Milestone 1 exit criteria

Delivered:

1. Current models, trainers, weights, datasets, APIs, and Flutter consumers identified.
2. Failure modes mapped to architecture (not “need more epochs”).
3. Preserve vs modify file list for YOLO baseline + specialists.
4. Confirmed: **no MMDetection in application code**; **no instance masks in the local dataset**.

**Not done (by design):** training, production code, deletions, `DATASET_LABEL_MAPPING.md`, Colab guide, Flask rewrite.

---

## 9. Approval gate — stop here

Milestone 2 (taxonomy mapping DeepFashion2 / Fashionpedia → unified Adore labels) should start only after this audit is accepted.

Suggested Milestone 2 outputs (preview, not started):

- `DATASET_LABEL_MAPPING.md`
- Explicit handling of extras vs target: sweater, jeans, jumpsuit, heels, shalwar, jewelry, top/blouse
- Decision: keep Flutter `dress` category vs rename to `one-piece` in API only
