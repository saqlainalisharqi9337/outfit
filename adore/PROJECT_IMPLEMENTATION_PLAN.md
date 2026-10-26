# Project Implementation Plan — Smart Cloth Advisor and Outfit Recommender

**Status:** Milestone 1 (repository audit) complete. No production code has been modified.
**Date of audit:** 31 August 2026
**Repository:** `d:\fyp project\adore`
**Dataset:** `D:\fyp project\dataset` (outside the repository)

This document records what the code *actually* does today, the problems found, and the
plan for the remaining milestones. Every claim below was verified by reading the file or
running the command. Nothing is assumed.

---

## A. Current Architecture

Three independent tiers, no shared code between them.

```
Flutter app (lib/)                    FastAPI service (ml_service/)         Supabase
─────────────────────                 ─────────────────────────────          ────────
23 screens                            POST /analyze-clothing                 Postgres (9 tables)
7 Provider stores          ── HTTP ─> POST /analyze-skin-tone                Auth (email/pw)
16 services                  multipart GET  /health                          Storage (2 buckets)
5 models                                                                     Realtime (4 tables)
on-device fallback analyser           MobileNetV2 ×4 (.keras/.h5)            RLS on every table
```

The Flutter app degrades gracefully: if the ML service is unreachable, every clothing
analysis silently falls back to `LocalImageAnalysis` (an on-device heuristic, not a CNN).

### Flutter layout (verified)

| Layer | Path | Count |
|---|---|---|
| Screens | `lib/screens/**` | 23 |
| Services | `lib/services/**` | 16 |
| Providers | `lib/providers/**` | 7 |
| Models | `lib/models/**` | 5 |
| Utils | `lib/utils/**` | 8 |
| Widgets | `lib/widgets/**` | 5 |

### FastAPI layout (verified)

| File | Role |
|---|---|
| `app/main.py` | 4 routes, wildcard CORS |
| `app/outfit_parser.py` | Region proposals + merge + precedence rules |
| `app/clothing_classifier.py` | ImageNet + specialist orchestration (32 KB, largest file) |
| `app/clothing_taxonomy.py` | Labels, family constraints, preprocessing |
| `app/accessory_classifier.py` | bag / hat / skirt / shoes head |
| `app/lowerwear_classifier.py` | trousers / shorts / skirt head |
| `app/silhouette_classifier.py` | dress / skirt / trousers head |
| `app/object_detector.py` | Optional YOLO wrapper — **inactive, no weights on disk** |
| `app/color_detection.py` | Dominant + secondary colour |
| `app/skin_tone.py` | ITA-based skin tone |

---

## B. Current ML Pipeline

```
image
 └─> classify_clothing(full image)          ImageNet MobileNetV2 + 3 specialist heads
 └─> detect_colors(full image)
 └─> object_detector.detect_objects()        returns [] — no .pt weights present
 └─> if _should_scan_regions():
       for each of 8 HARDCODED normalized boxes in outfit_parser.REGIONS:
         crop -> classify -> filter by `allowed` set -> colour -> item
 └─> _merge()  ~110 lines of hand-written precedence rules
 └─> JSON: {category, subcategory, confidence, color, items[], detected[], isolatedProduct}
```

**This is classification over fixed rectangles, not detection.** The eight regions in
`outfit_parser.REGIONS` are literal constants, for example `("lower", (0.14, 0.40, 0.86, 0.84))`.
They assume a centred, upright, full-length subject.

### Models on disk

| File | Size | Classes | Test accuracy |
|---|---|---|---|
| `dress_pants_skirt_mobilenetv2.keras` | 23.0 MB | dress, skirt, trousers | **0.9098** |
| `bag_shoes_mobilenetv2.keras` | 25.1 MB | bag, hat, skirt, shoes | **0.8973** |
| `trousers_shorts_skirt_mobilenetv2.keras` | 25.1 MB | trousers, shorts, skirt | **0.8690** |
| `mobilenet_v2_imagenet_1.0_224.h5` | 13.9 MB | 1000 ImageNet classes | n/a |

`clothing_mobilenetv2.keras` (the unified 13-class model) is referenced by
`train_clothing_mobilenet.py` and by `main.py`'s docstring but **has never been trained** —
neither it nor `labels.json`, `eval_report.json`, `dataset_audit.json` or
`confusion_matrix.png` exist on disk.

---

## C. Current Flutter → FastAPI Flow

```
add_clothing_screen.dart
  └─ PhotoPicker -> Uint8List
  └─ ImageAnalysisService.analyzeClothing(bytes)
       ├─ LocalImageAnalysis.analyzeClothing(bytes)        always runs first
       ├─ POST {mlServiceUrl}/analyze-clothing  (45 s timeout)
       ├─ non-200 or any exception -> return local result silently
       ├─ _parseDetected(json) -> List<DetectedClothingItem>   (bbox IS parsed)
       ├─ isolatedProduct footwear override
       ├─ _leadPantsOverDressOnCloseup
       ├─ isolatedProduct hat-over-skirt override
       └─ ClothingCatalog.resolvePrediction(local vs ml)    ~300 lines of if/else
  └─ user confirms in dropdowns -> WardrobeService.add()
```

`AppConstants.mlServiceUrl()` resolves to `http://10.0.2.2:8000` on Android,
`http://127.0.0.1:8000` elsewhere, overridable with `--dart-define=ML_SERVICE_URL=...`.

`DetectedClothingItem` already carries `bbox` and `region` fields
(`lib/models/product_model.dart:287`) and `fromJson` already parses them — **but no screen
ever renders them.** The plumbing for Phase 12 partially exists.

---

## D. Current Recommendation Pipeline

`RecommendationService.recommend()` is the single entry point.

```
weights (assets/data/recommendation_weights.json)
 └─> derive WeatherBand + effective Season (temperature overrides calendar)
 └─> build preferred / excludedTypes / excludedStyles sets
 └─> hard filter (6 rules: gender, excluded type, excluded style,
                  veryCold vs summer-only, hot vs winter outerwear, rain vs sandals)
 └─> partition by ClothingCategory
 └─> _topN per category using _itemSoftScore (6 hardcoded item weights)
 └─> combine (cap 160 combinations)
 └─> _score each outfit
 └─> sort, dedupe, apply excludeIds, _diversePick -> 5 outfits
```

**Outfit-level weights (sum = 1.00):**

| Component | Weight | Source |
|---|---|---|
| weather | 0.30 | JSON |
| culture | 0.20 | JSON |
| occasion | 0.15 | JSON |
| color | 0.15 | JSON |
| preference | 0.10 | JSON |
| wardrobe | 0.10 | JSON |
| trend bonus | ×0.04 | hardcoded, additive |
| personalization | ×0.05 | hardcoded, additive |

There is **no body-type component**. `genderScore` exists only at item pre-rank, not in the
outfit score. Explanations are already generated as a `List<String>` per outfit, so the
scoring system is already explainable — a body-type explanation slots in cleanly.

---

## E. Current Database Structure

Two migrations, both dated 2026-08-30. Nine tables, RLS enabled on all of them,
two public storage buckets (`avatars`, `wardrobe`).

`public.profiles` columns: `id, name, email, profile_image_url, gender, culture, skin_tone,
country, country_code, city, latitude, longitude, preferences (jsonb), onboarding_complete,
notifications_enabled, created_at, updated_at`.

`public.wardrobe_items` columns: `id, user_id, image_url, category, subcategory, color,
secondary_color, pattern (text default 'solid'), material, style, season (text[]), formality,
culture_compatibility (text[]), weather_suitability (text[]), occasion (text[]),
ai_confidence, created_at`.

Notable facts for planning:

- **No `body_type` column exists.** A migration is required.
- **`pattern` column already exists** with default `'solid'`. No migration needed to *store*
  a pattern; only `pattern_confidence` and `pattern_source` are new.
- There are **no CHECK constraints and no Postgres ENUM types** anywhere. All enum-like
  values are plain `text` / `text[]`. Adding a nullable text column is therefore low risk.

---

## F. Current Clothing Taxonomy

`FOLDER_TO_CLASS` in `clothing_taxonomy.py` declares 18 folder mappings, but only **13 have
images on disk**:

`bag, hat, trousers, shorts, skirt, flats, heels, shoes, sneakers, dress, jacket, shirt, t-shirt`

Declared but **zero images**: `jeans, scarf, accessories(other), coat, hoodie, sweater`.

Guard rails that already exist and must be preserved:

- `HAT_NEVER`, `DRESS_NEVER`, `FOOTWEAR`, `ACCESSORY_CLASSES` constant sets.
- `apply_family_constraints()` returns `"unknown"` when confidence is below threshold —
  unknown is genuinely propagated to Flutter as `subcategory: "unknown"`.
- `ClothingCatalog.unknownType` is filtered out of `_parseDetected` in Flutter.

The requirement "unknown must remain unknown" is **currently satisfied**; the work in later
milestones must not regress it.

---

## G. Current Model Files and Labels

| Artefact | Exists | Notes |
|---|---|---|
| 3 specialist `.keras` models | Yes | with `_labels.json`, `_eval.json`, `_audit.json`, `_confusion.png` |
| ImageNet `.h5` | Yes | 13.9 MB |
| Unified 13-class model | **No** | trainer exists, never run |
| YOLO `.pt` weights | **No** | zero `.pt` files anywhere under `D:\fyp project` |
| Bounding-box annotations | **No** | see Section I |

Confidence thresholds are per-model and stored in the labels JSON: bag_shoes and
dress_pants_skirt use `min_confidence 0.42 / min_gap 0.08` (default); trousers_shorts_skirt
uses `0.62 / 0.05` derived from a real validation sweep.

---

## H. Existing Tests

`flutter test` baseline, run 31 Aug 2026: **99 passed, 1 skipped, 2 failed.**

| File | Content |
|---|---|
| `test/local_clothing_analysis_test.dart` | ~90 tests: label normalisation, `resolvePrediction` precedence, silhouette heuristics |
| `test/train_outfit_part_test.dart` | outfit-part weight training helper |
| `test/demo_store_test.dart` | demo mode store |
| `test/widget_test.dart` | 1 test: splash screen |

**There are no Python tests at all.** No `pytest`, no `ml_service/tests/`.
There are no tests for the recommendation engine, weather scoring, occasion scoring,
diversity/rotation, or API contract.

### The two failing tests (both pre-existing, both real bugs)

1. **`local hat is not overwritten by accessory shoes`** — a genuine regression.
   `lib/utils/clothing_catalog.dart:444` added an accessory-footwear override during the
   previous "shoes recognised as trousers" fix. Its only guard is
   `!dressLabels.contains(local.$2)`; it does not exclude `hatLabels` or `bagLabels`, so a
   local **hat** + ML **shoes** now resolves to shoes. Fixing the shoe bug broke the hat case.

2. **`splash branding is visible`** — `SplashScreen` starts a timer/animation that is still
   pending when the widget tree is disposed, so the test framework asserts. A test-harness
   problem, not a product bug.

---

## I. Existing Problems

### I.1 Critical — no bounding-box data exists anywhere

This was checked exhaustively across both `D:\fyp project\dataset` and the repository:

| Artefact | Count found |
|---|---|
| Pascal VOC `*.xml` | 0 |
| YOLO `*.txt` label files | 0 |
| COCO JSON containing `annotations` + `bbox` | 0 |
| `data.yaml` / `classes.txt` | 0 |
| `labels/` or `annotations/` directories | 0 |

The 40,139 training images are **single-object classification images with folder labels
only**. `bbox` appears in the code solely as *output* geometry.

**Consequence: a custom 13-class clothing detector cannot be trained from the current
dataset.** Any claim otherwise would be false. This governs the entire Milestone 2 design.

### I.2 Detection depends on fixed image percentages

`outfit_parser.REGIONS` hardcodes 8 rectangles. A person off-centre, seated, cropped, or
photographed at an angle breaks every region. This is exactly the dependency the brief
requires removing.

### I.3 Precedence logic has become unmaintainable

Item routing is now decided in **five** places: `clothing_taxonomy.apply_family_constraints`,
`clothing_classifier`, `outfit_parser._merge`, `image_analysis_service`, and
`clothing_catalog.resolvePrediction`. Each past fix added another special case, and the
failing hat test is the direct result. Real detection removes the *need* for most of these.

### I.4 Measured model weaknesses (from the eval JSONs)

| Confusion | Count | Rate |
|---|---|---|
| shoes → bag | 159 / 1497 | 10.6% of shoes |
| skirt → shorts | 66 / 384 | 17.2% of skirts |
| trousers → shorts | 46 / 476 | 9.7% of trousers |
| shorts → skirt | 27 / 453 | 6.0% |
| skirt → trousers (dress head) | 36 / 384 | 9.4% |

`bag` precision is only **0.689** — nearly a third of bag predictions are wrong, driven by
shoes leaking into bag. This is the single worst metric in the project and it is caused by
class imbalance: the bag_shoes trainer sees `shoes 11,948` vs `bag 3,184`.

### I.5 Confirmed data leakage

`trousers_shorts_skirt_audit.json` reports `train_val_prefix_overlap: 101` and
`train_test_prefix_overlap: 97`. Only `train_trousers_shorts_skirt.py` implements
cross-split leakage removal; `train_bag_shoes.py` and `train_dress_pants_skirt.py` drop
duplicates **within** train only. Their reported accuracies are therefore mildly optimistic.

### I.6 Feature gaps

- `body_type` — absent from enums, model, schema, onboarding, and scoring.
- `pattern` — `add_clothing_screen.dart:33` is `final String _pattern = 'solid';` with no UI
  control, so every wardrobe item is `solid`. (`style` on line 35 *does* have a dropdown.)
- NLP — no parser of any kind.
- `bbox` — parsed in Flutter, never displayed.

### I.7 Deployment blockers

`allow_origins=["*"]`, no auth, no rate limiting, no logging, no request-size cap, model
paths hardcoded relative to `__file__`, no `.env` handling. `/health` exists and already
reports `model_status()` and `detector_status()` — a good foundation to extend.

---

## Proposed Solution

### The central decision: how to deliver honest object detection

Because no bounding-box annotations exist, Milestone 2 is split into two stages. Stage A is
implementable immediately with pretrained weights and no new data; Stage B requires the
dataset decision in Milestone 3.

**Stage A — anatomy-driven proposals (no new training data).**
Use pretrained COCO YOLOv8 for `person`, `backpack`, `handbag`, `suitcase`, `tie`, plus
COCO-pose keypoints (shoulders, hips, knees, ankles) to derive garment regions from the
subject's actual anatomy instead of fixed percentages. Each proposal is then classified by
the existing MobileNetV2 specialists, which remain untouched.

This genuinely removes the fixed-percentage dependency, produces real per-item bounding
boxes, and handles off-centre, seated and partially-cropped subjects. It will be documented
precisely as what it is: **detection-assisted region proposals refined by classification**,
not an end-to-end trained clothing detector.

**Stage B — a real trained clothing detector.**
Fine-tune YOLOv8 on an externally annotated fashion detection dataset mapped onto the
existing 13-class taxonomy. Recommended dataset: **Fashionpedia** (COCO-format instance
annotations, CC BY 4.0, contains `shoe`, `bag/wallet`, `hat` and `glasses` alongside
garments, so it covers accessories and footwear that garment-only datasets omit).
DeepFashion2 is the main alternative but has no footwear/bag/hat classes; ModaNet maps well
but its images depend on the deprecated PaperDoll distribution. No dataset will be
downloaded until size, licence and class mapping are confirmed in `DATASET_PLAN.md`.

**Dependency risk to approve before Milestone 2:** `ultralytics` is AGPL-3.0 and pulls
PyTorch (roughly 2–2.5 GB into `ml_service/.venv`, which already contains TensorFlow).
Both stages depend on it. The detector will remain strictly optional at runtime — if
weights or the package are absent, the service must keep working through the existing
region path, exactly as `object_detector.py` does today.

### Milestone summary

| # | Goal | Depends on |
|---|---|---|
| 2 | Stage A detection + `/detect` endpoint + structured detections | ultralytics approval |
| 3 | `DATASET_PLAN.md`, taxonomy stabilisation, fix hat regression | — |
| 4 | Body type: enum, migration, onboarding, scoring, explanations | — |
| 5 | Pattern: user-selectable + confidence/source + extension point | — |
| 6 | NLP request parser + ≥10 unit tests | — |
| 7 | FastAPI config, CORS, logging, auth, `DEPLOYMENT.md` | — |
| 8 | Flutter detection UI, error handling, Android testing | 2, 4, 5, 6 |
| 9 | Final documentation set | all |

---

## Files That Will Be Modified

Nothing outside this list will be touched without reporting it first.

**Milestone 2**
- `ml_service/app/object_detector.py` — extend (do not duplicate) with person + pose backends
- `ml_service/app/outfit_parser.py` — consume proposals; keep region path as fallback
- `ml_service/app/main.py` — add `POST /detect`; extend `/health`
- `ml_service/requirements.txt` — record optional detector extras

**Milestone 3**
- `lib/utils/clothing_catalog.dart` — add `hatLabels`/`bagLabels` guards to the line-444 rule
- `ml_service/app/clothing_taxonomy.py` — only if confusion analysis requires it
- `test/local_clothing_analysis_test.dart` — extend, never weaken existing assertions

**Milestone 4**
- `lib/utils/enums.dart` — `BodyType` enum + label extension
- `lib/models/user_model.dart` — `bodyType` field, read `body_type`/`bodyType`, write `body_type`
- `lib/screens/onboarding/profile_setup_screen.dart` — body type control
- `lib/screens/profile/edit_profile_screen.dart` — editable after onboarding
- `lib/services/recommendation_service.dart` — `bodyTypeScore` component + explanation
- `lib/utils/clothing_catalog.dart` — silhouette compatibility table
- `assets/data/recommendation_weights.json` — add `bodyType`, rebalance to 1.00

**Milestone 5**
- `lib/models/wardrobe_item.dart` — `patternConfidence`, `patternSource`
- `lib/screens/wardrobe/add_clothing_screen.dart` — replace the hardcoded `_pattern`
- `lib/utils/clothing_catalog.dart` — reuse the existing `patterns` list (line 775)

**Milestone 7**
- `ml_service/app/main.py` — env-driven CORS, logging, handlers, request limits

**Milestone 8**
- `lib/screens/wardrobe/add_clothing_screen.dart` — render detections and boxes
- `lib/services/image_analysis_service.dart` — typed error handling

## Files That Will Be Created

| Path | Milestone |
|---|---|
| `ml_service/app/region_proposals.py` | 2 |
| `ml_service/app/detection_schema.py` | 2 |
| `DATASET_PLAN.md` | 3 |
| `MODEL_EVALUATION.md` | 3 |
| `supabase/migrations/<ts>_add_body_type.sql` | 4 |
| `test/body_type_scoring_test.dart` | 4 |
| `supabase/migrations/<ts>_add_pattern_metadata.sql` | 5 |
| `ml_service/app/pattern_analysis.py` | 5 (heuristic, clearly labelled) |
| `lib/services/nlp_request_parser.dart` | 6 |
| `test/nlp_request_parser_test.dart` | 6 |
| `ml_service/app/config.py` | 7 |
| `ml_service/.env.example` | 7 |
| `ml_service/tests/test_api.py` | 7 |
| `DEPLOYMENT.md` | 7 |
| `ANDROID_TEST_REPORT.md` | 8 |
| `PROJECT_ARCHITECTURE.md`, `ML_PIPELINE.md`, `DATASET_DOCUMENTATION.md`, `RECOMMENDATION_ENGINE.md`, `NLP_DOCUMENTATION.md`, `API_DOCUMENTATION.md`, `TESTING_REPORT.md`, `LIMITATIONS.md` | 9 |

## Database Changes

Two additive, nullable, backward-compatible migrations. No column is renamed or dropped, and
no existing row is rewritten.

```sql
-- Milestone 4
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS body_type text;

-- Milestone 5
ALTER TABLE public.wardrobe_items ADD COLUMN IF NOT EXISTS pattern_confidence double precision;
ALTER TABLE public.wardrobe_items ADD COLUMN IF NOT EXISTS pattern_source text;
```

`body_type` is nullable so every existing profile stays valid and `bodyTypeScore` returns a
neutral value when it is unset. RLS is unaffected: existing `profiles_own` and
`wardrobe_own` policies are `FOR ALL` and already cover new columns.

## Testing Plan

**Baseline to protect:** 99 passing Dart tests. The 2 known failures are fixed in
Milestone 3 (hat regression) and Milestone 8 (splash timer), and must not be masked by
deleting or weakening assertions.

| Milestone | Added tests | Command |
|---|---|---|
| 2 | detection parsing, empty-detection fallback, health payload | `pytest ml_service/tests` |
| 3 | hat-vs-accessory-shoes regression, unknown stays unknown | `flutter test` |
| 4 | body-type scoring per silhouette, null body type is neutral, weights sum to 1.0 | `flutter test` |
| 5 | pattern default, pattern round-trip, source/confidence persistence | `flutter test` |
| 6 | ≥10 natural-language sentences → structured filters | `flutter test` |
| 7 | `/health` shape, invalid input 400, oversized upload rejected | `pytest ml_service/tests` |
| 8 | full Android journey, manually recorded | `ANDROID_TEST_REPORT.md` |

Regression rule for every milestone: run the full `flutter test` suite before reporting, and
report the pass/fail delta against the 99-test baseline.

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| `ultralytics` + PyTorch install (~2–2.5 GB, AGPL-3.0) | Blocks Milestone 2 | Get approval first; keep detector optional at runtime so absence never breaks the service |
| Stage B needs an external dataset download | Time and disk | `DATASET_PLAN.md` decided before any download |
| Adding `bodyType` weight rebalances existing weights | Could change current recommendations | Introduce at low weight, keep JSON-configurable, assert weights sum to 1.0 in a test |
| Precedence rules are entangled across 5 files | Fixing one case breaks another (already happened once) | Add the failing case as a test *before* changing the rule |
| No Python test infrastructure exists | API regressions invisible | Create `ml_service/tests/` in Milestone 7 |
| Detector changes could regress the 99 passing Dart tests | Loss of working behaviour | Region path retained as fallback; full suite run each milestone |
| Android device/emulator availability unverified | Milestone 8 cannot complete | Confirm `flutter devices` before starting Milestone 8 |
