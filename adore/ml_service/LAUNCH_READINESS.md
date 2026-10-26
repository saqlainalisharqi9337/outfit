# Adore ML — launch readiness

## Data policy (important)

We do **not** scrape Google Images, shop sites, or other commercial pages.
That would violate terms of service and copyright.

What we did use instead (freely licensed / open):

1. Existing Adore folder dataset (`D:\fyp project\dataset`) — ~3–5k images per leaf class.
2. [clothing-dataset-small](https://github.com/alexeygrigorev/clothing-dataset-small) (CC0).
3. Full [clothing-dataset](https://github.com/alexeygrigorev/clothing-dataset) (CC0) — **+5,027** images imported (`fullopen_` prefix): hat, skirt, dress, shoes, tops, pants, shorts.
4. Optional: `download_wikimedia_weak_classes.py` for CC0/CC-BY Commons images (DNS may fail offline).
5. [Fashionpedia](https://huggingface.co/datasets/detection-datasets/fashionpedia) accessory crops + [YOLOv8n-Fashionpedia](https://huggingface.co/louisJLN/yolo8-fashionpedia) for bag/hat/glasses/belt/scarf. DeepFashion2 is **not** used for accessories (it has no bag/hat classes).

HuggingFace `nreimers/fashion-dataset` is **metadata only** (no images) — not usable for training.

## Production hardening (API)

- Upload size cap: **12 MB**
- Max resolution guard + thumbnail for huge images
- `/health/live` — liveness (no model load)
- `/health/ready` — readiness after warmup
- `/health` — full status including gate
- Startup warmup of classifiers
- Structured 4xx/5xx errors (no stack traces to clients)
- Latency + `serviceVersion` on analyze responses
- Optional `ADORE_CORS_ORIGINS` and `ADORE_API_KEY` (see `.env.example` / `DEPLOYMENT.md`)

## Model / routing status

Specialists are already strong offline (bag/hat/skirt/shoes ~90%, footwear4 heels F1 ~0.95, dress↔upperwear gate ~97%).
Live misses are mostly **routing** (bag stealing heels, tops↔dress, accessory↔skirt).

Lowerwear (pants/shorts) was intentionally left alone after earlier good results.

## Honest accuracy note

**No vision model is 100% error-free for thousands of users and every photo.**
Launch quality means: open training data, specialists, hardened API, and continuous eval — not a promise of zero mistakes.

Latest 8-shot smoke (test split, mixed with newly imported CC0 images):

| Class | Acc | Notes |
|---|---|---|
| t-shirt | ~88% | stable |
| shirt | ~100% | stable |
| jacket | ~100% | stable |
| bag | ~88% | improved vs ~62% |
| skirt | ~62% | improved vs ~12% |
| dress | ~50% | still confused with jacket/top |
| hat / heels | ~25–38% | still the weakest live classes |

Footwear4 specialist test: **94.6%** (heels F1 **0.97**).
Bag/hat/skirt/shoes specialist test: **80.5%** after CC0 import retrain.

Outfit pairing (`top+bottom+shoes`) smoke: OK.

## How to retrain (from `ml_service`)

```text
.\.venv\Scripts\python.exe download_fashionpedia_yolo.py
.\.venv\Scripts\python.exe prepare_accessory_dataset.py
.\.venv\Scripts\python.exe train_accessories.py --epochs 6 --max-per-class 160
.\.venv\Scripts\python.exe eval_accessories.py
.\.venv\Scripts\python.exe import_clothing_dataset_full.py
.\.venv\Scripts\python.exe train_footwear_pytorch.py --epochs 8 --max-per-class 450
.\.venv\Scripts\python.exe train_bag_shoes.py --limit 600
.\.venv\Scripts\python.exe train_dress_upperwear_gate.py --epochs 5 --max-per-class 800
.\.venv\Scripts\python.exe production_smoke.py
```

## How to run API

```text
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Flutter: `flutter run -d chrome` with ML URL `http://127.0.0.1:8000`.
