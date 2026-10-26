# Adore — Testing Report

## Flutter (`flutter test`)

| File | Focus |
|---|---|
| `test/local_clothing_analysis_test.dart` | On-device clothing heuristics / catalog guards |
| `test/nlp_body_pattern_test.dart` | NLP parser + body type / pattern scoring |
| `test/demo_store_test.dart` | Offline demo store behaviour |
| `test/train_outfit_part_test.dart` | Outfit part helpers |
| `test/widget_test.dart` | Smoke / splash-related widgets |

Approximate suite size: **~130+** assertions across these files (run `flutter test` for the live count).

## Python ML (`pytest` from `ml_service/`)

| File | Focus |
|---|---|
| `tests/test_api.py` | Health, upload rejection, analyze smoke |
| `tests/test_detection.py` | Detector / region proposal contracts |
| `tests/test_regression_lowerwear_sneakers.py` | **Do not break** trousers/shorts/sneakers routing |
| `tests/test_recommendation_smoke.py` | Lightweight pairing / smoke helpers |
| `tests/conftest.py` | Shared fixtures |

Approximate suite size: **~40+** tests.

## Manual / product checks

- Web: `flutter run -d chrome` with ML on `:8000`
- Android: see `ANDROID_TEST_REPORT.md`
- Clothing accuracy smoke: `eval_confusion_fix_report.py --per-class 16`
- Production smoke: `production_smoke.py`

## Regression rule

Before merging ML routing changes:

1. `pytest` in `ml_service/` (especially lowerwear/sneakers).
2. `flutter test`
3. Optional 16-shot confusion report for hat / heels / jacket / bag
