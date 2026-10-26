# Adore clothing analysis API

The Flutter cupboard screen already calls this service. Keep the UI as-is.
What changed is the **model and how labels are merged**.

## Why caps became shirts and dresses became jeans

1. The on-device helper is **not** a CNN. It is 41 shape/color numbers plus a
   linear softmax. A centered cap looks like a small dark square, which the
   old fallback called **shirt**. A long navy dress looks like a column, which
   the jeans rule could steal.
2. The Python API used **ImageNet** MobileNetV2 (1000 everyday objects), then
   mapped a few names onto clothes. ImageNet has no baseball-cap class. Any
   unmapped label was forced to **shirt**.
3. Flutter **threw away** the API label and kept the on-device guess. Even a
   correct server prediction never reached the dropdowns.

## Dataset issues (`D:\fyp project\dataset`)

| Class | Train images | Notes |
| --- | ---: | --- |
| trousers (`bottomwear/pants`) | 3929 | Includes denim. There is **no jeans folder**. |
| shorts | 3574 | Easy to mix with skirt |
| sneakers | 3512 | |
| flats / heels | ~3464 each | Overlap with shoes |
| t-shirt / shirt | 3431 / 3406 | Visually similar |
| bag | 3184 | |
| skirt | 3079 | |
| dress | 2953 | |
| jacket | 2510 | No coat/hoodie/sweater folders |
| hat | 2125 | Enough, but fewer than tops |
| shoes | 1507 | Imbalanced vs other footwear |

Missing from the dataset (the model cannot learn these until you add folders):
**jeans, coat, sweater, hoodie, scarf, generic accessories**.

How that causes mistakes:

- **Incorrect labels** — if a cap sits in `upperwear/shirt`, MobileNetV2 will
  learn “cap = shirt”.
- **Class imbalance** — shoes have less than half the flats/heels images.
  Training uses class weights so rare classes are not ignored.
- **Overlapping categories** — `pants` mixes jeans and trousers; shirt and
  t-shirt share collars and sleeves. Fine-grained errors stay until folders
  are cleaned.

To add a class, create:

```
train/train/<family>/<leaf>
val/val/<family>/<leaf>
test/test/<family>/<leaf>
```

Examples: `bottomwear/jeans`, `upperwear/coat`, `upperwear/hoodie`,
`upperwear/sweater`, `accessories/scarf`. Then re-run training. The folder map
lives in `app/clothing_taxonomy.py` (`FOLDER_TO_CLASS`).

If you only have broad folders (`upperwear`, `lowerwear`, `accessories`),
split them into the leaf folders above and change the last Dense layer to
`softmax(num_leaf_classes)`. Do not train one head on “upperwear” and then
expect it to say “cap”.

## Train the clothing MobileNetV2

TensorFlow does **not** install on Python 3.14. Use **3.11 or 3.12**.

```bash
cd ml_service
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install tensorflow scikit-learn matplotlib
python train_clothing_mobilenet.py --audit-only
python train_clothing_mobilenet.py
```

That script:

- Loads every image as **224×224 RGB**
- Normalizes with MobileNetV2 `x / 127.5 - 1` (same as inference)
- Applies flip / rotation / zoom / shift / contrast on the training split only
- Freezes MobileNetV2, trains a new softmax head, then fine-tunes the last 40
  layers
- Writes accuracy, precision, recall, F1, per-class scores, and a confusion
  matrix

Outputs (leave these names — the API loads them):

| File | Place |
| --- | --- |
| `models/clothing_mobilenetv2.keras` | `ml_service/models/` |
| `models/labels.json` | `ml_service/models/` |
| `models/eval_report.json` | `ml_service/models/` |
| `models/confusion_matrix.png` | `ml_service/models/` |

A smoke run on a few hundred images:

```bash
python train_clothing_mobilenet.py --limit 400 --epochs-head 1 --epochs-finetune 1
```

## ImageNet MobileNetV2 for accessories

The API loads this ImageNet head for hats, bags, watches, sunglasses,
jewelry, belts, and scarves (ImageNet has those classes; the clothing
dataset mostly does not):

`ml_service/models/mobilenet_v2_imagenet_1.0_224.h5`

That file is the Keras MobileNetV2 1.0 224 weights **with** the 1000-class
top (`tf_dim_ordering_tf_kernels`). Copy it from
`D:\fyp project\outfit\mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224 (1).h5`
if it is missing.

`GET /health` reports `model.imagenet` as `tensorflow-local` when these
weights loaded.

## Run the API

```bash
cd ml_service
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Then open Adore (Chrome already uses `http://127.0.0.1:8000`).

| File | Place | Role |
| --- | --- | --- |
| `app/main.py` | `ml_service/app/` | `/analyze-clothing` |
| `app/clothing_classifier.py` | `ml_service/app/` | Loads the fine-tuned model first |
| `app/clothing_taxonomy.py` | `ml_service/app/` | Shared labels + preprocess |
| `train_clothing_mobilenet.py` | `ml_service/` | Training + metrics |
| `lib/services/image_analysis_service.dart` | Flutter | Uses API labels + family vetoes |
| `lib/services/local_image_analysis.dart` | Flutter | Offline fallback only |

`GET /health` reports whether the fine-tuned weights loaded.

If the top two classes are different families and both are plausible, the API
returns `items[]`. The cupboard screen stays single-item; the extra names are
appended to the status text.

If confidence is low, the API returns `subcategory: "unknown"` instead of
guessing shirt.

## Flutter

No new screens. Analyze with AI still fills Category / Type / Color. If the
model is uncertain, those dropdowns are left alone so a wrong shirt is not
saved.
