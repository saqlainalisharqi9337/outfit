# MobileNetV2 restoration

The live clothing API again uses the existing MobileNetV2 classifiers. Mask R-CNN is not loaded unless `ADORE_MASKRCNN_ENABLED=1`. No model was trained, and no checkpoint was deleted.

## Audit

| Item | Finding |
| --- | --- |
| Fine-tuned general checkpoint | `ml_service/models/clothing_mobilenetv2.keras` and `labels.json` are **not on disk**. Only `train_clothing_mobilenet.py` remains. |
| Specialist MobileNetV2 weights | Present in `ml_service/models/` as `.keras` files (shirt, t-shirt, jacket, trousers, skirt, dress silhouette, shoes, sneakers, heels, flats, bag, hat, watch, dupatta, and the 3-class heads). |
| ImageNet MobileNetV2 weights | `ml_service/models/mobilenet_v2_imagenet_1.0_224.h5` |
| Loader | `ml_service/app/clothing_classifier.py` loads a model once via `_ensure_loaded()`. |
| Preprocessing | `preprocess_mobilenet_v2` in `clothing_taxonomy.py`: RGB, bilinear resize to 224×224, `x / 127.5 - 1`, float32, shape `(1, 224, 224, 3)`. |
| Previous pipeline | `parse_outfit` in `outfit_parser.py`: full-image MobileNetV2 classify, then existing YOLO / region crops, then the same classifiers and color analysis. |
| Mask R-CNN live hook | `parse_outfit` called `maskrcnn_detector.detect_items` first when `maskrcnn_enabled` defaulted to true. That loaded `checkpoints/maskrcnn/m4_11/best_model.pth`. |
| API | `POST /analyze-clothing`, multipart field `file`. Flutter reads `category`, `subcategory`, `confidence`, `detected`, `color`, and `detectionStrategy`. The non-`maskrcnn` branch was already implemented in `image_analysis_service.dart`. |
| TensorFlow on this PC | The Keras venv (`.venv`) points at a missing Python 3.12 (`C:\Users\saqla\AppData\Local\Programs\Python\Python312\python.exe`). The working CPU venv (`.venv_m48`) is Python 3.13 with PyTorch and **no TensorFlow**. |

## What changed

Live default in `ml_service/app/config.py`: `ADORE_MASKRCNN_ENABLED` is now off. `detect_items` returns immediately and does not load the checkpoint. Warmup still calls `parse_outfit`, which now stays on the MobileNetV2 / YOLO crop path.

Backup: `ml_service/backups/config.py.before_mobilenet_restore`.

## Class mapping kept

Dataset folders in `FOLDER_TO_CLASS` still map to the same names (`shirt`, `t-shirt`, `jacket`, `hoodie`, `dress`, `trousers`, `jeans`, `shorts`, `skirt`, `shoes`, `sneakers`, `bag`, `hat`, and the other existing leaves). `CLASS_TO_CATEGORY` still maps those names to `upperwear`, `lowerwear`, `dress`, `footwear`, or `accessories`.

Specialist heads that are on disk keep their trained index order:

- `dress_pants_skirt_mobilenetv2.keras`: 0 dress, 1 skirt, 2 trousers
- `trousers_shorts_skirt_mobilenetv2.keras`: 0 trousers, 1 shorts, 2 skirt

MobileNetV2 does not find multiple objects by itself. The restored path still uses the existing YOLO and region crops, then classifies each crop.

## Files changed

- `ml_service/app/config.py`
- `ml_service/app/maskrcnn_detector.py` (module note only; inference code unchanged)
- `ml_service/tests/test_maskrcnn_api.py`
- `ml_service/backups/config.py.before_mobilenet_restore` (copy)
- this report

## Left untouched

Mask R-CNN training, evaluation, checkpoints, taxonomy, Flutter UI, recommendation, wardrobe, weather, and the MobileNetV2 `.keras` files.

## Tests

`ml_service` pytest with `.venv_m48`: **128 passed** before the extra default-off check. `tests/test_maskrcnn_api.py` then passed **3** tests, including that check: with no environment override, Mask R-CNN stays off and `detect_items` returns `None` without loading the checkpoint.

## Sample predictions

Not run. Loading any `.keras` file needs TensorFlow, and the only TensorFlow install is inside the broken Python 3.12 virtualenv. No predictions were invented.

Preview photos that can be used once that interpreter is available:

- shirt: `evaluation_results/dataset_preview/by_class/shirt_val_00_13557.jpg`
- dress: `evaluation_results/dataset_preview/by_class/dress_val_00_20056.jpg`
- jacket: `evaluation_results/dataset_preview/by_class/jacket_val_00_11658.jpg`
- bag: `evaluation_results/dataset_preview/by_class/bag_val_00_10566.jpg`
- hat: `evaluation_results/dataset_preview/by_class/hat_val_00_16896.jpg`

## Flutter

No Flutter change. `POST /analyze-clothing` still accepts the image file. When `detectionStrategy` is not `maskrcnn`, the app already reads `category`, `subcategory`, `confidence`, and `detected`.

## Limitations

- `clothing_mobilenetv2.keras` is missing, so the general fine-tune cannot run. The specialist MobileNetV2 files and the ImageNet weights are what the previous pipeline uses.
- This machine cannot execute those Keras models until the Python 3.12 environment that owns `.venv` is restored. Nothing was installed or trained to work around that.
