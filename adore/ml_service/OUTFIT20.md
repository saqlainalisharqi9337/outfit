# Outfit-20 detector — datasets, licenses, and training notes

## Existing model (kept)

| Item | Value |
|---|---|
| Framework | Ultralytics YOLOv8 |
| Checkpoint | `models/yolov8n-fashionpedia-1.torchscript` |
| Source | [louisJLN/yolo8-fashionpedia](https://huggingface.co/louisJLN/yolo8-fashionpedia) |
| Train data | [detection-datasets/fashionpedia](https://huggingface.co/datasets/detection-datasets/fashionpedia) (Jia et al., CVPR 2020) |
| Dataset license | CC BY 4.0 |
| Backup | `models/original/yolov8n-fashionpedia-1.torchscript` |

The original file is **never overwritten**. The improved 20-class weights go to `models/improved/outfit20_yolov8n.pt`.

## Why the old pipeline mixed items

Fashionpedia YOLO already predicted **many boxes** (shirt, pants, bag, watch, …). Adore then:

1. Dropped garment boxes (`allowed_leaves` returned None for dress/pants/shorts).
2. Classified the **whole image** with MobileNet specialists (one label).
3. Re-classified bag crops, which turned bags into skirts.

That is why a person wearing several items became a single Skirt/Hat/Dress.

## Class mapping (Fashionpedia → Adore 20)

| Fashionpedia | Adore |
|---|---|
| bag, wallet | accessories_bag |
| hat | accessories_hat |
| belt, buckle | accessories_belt |
| scarf | accessories_scarf |
| watch | accessories_watch |
| glasses | accessories_sunglasses |
| shirt, blouse | upperwear_shirt |
| top, t-shirt, sweatshirt | upperwear_tshirt |
| jacket, coat, cape | upperwear_jacket |
| pants | lowerwear_trousers |
| shorts | lowerwear_shorts |
| skirt | lowerwear_skirt |
| dress, jumpsuit | one_piece_dress |
| shoe | footwear_shoes |

Not forced (no equivalent leaf): sweater, cardigan, vest, glove, sock, headband, garment parts (sleeve, zipper, …).

Hijab, dupatta, flats, sneakers, loafers are **not** Fashionpedia classes. They come from local specialist folders and, after fine-tune, from the 20-class head. Shoe boxes are refined with the existing flats/sneakers/shoes gates.

## Local images (already on disk)

`D:\fyp project\dataset\train\train\…` plus gate test folders. Product photos use a near-full-frame box because the garment fills the image.

Heels images are mapped to `footwear_shoes` (heels is not in the 20-class list).

## Scripts

```text
python prepare_outfit20_dataset.py
python validate_outfit20_dataset.py
python train_outfit20.py
python eval_outfit20.py
python export_outfit20.py
```

API: `POST /analyze-clothing` now includes `detections` — one object per item (`class`, `category`, `confidence`, `bbox`).

## Teach by example (when the model is wrong)

Saving a photo into the wardrobe does **not** retrain the model by itself. Label examples, then fine-tune.

**In the app:** open Add clothing, pick the photo, set Type to the true item (Trousers, T-shirt, …), leave **Teach the model this type** on, then save. That stores the photo under `datasets/user_labeled/`.

**From folders or the command line** (same result):

```text
ml_service/datasets/user_labeled/lowerwear_trousers/my_pants.jpg
ml_service/datasets/user_labeled/upperwear_tshirt/my_tee.jpg
```

or:

```text
python teach_outfit.py --image photo.jpg --label pent
python teach_outfit.py --image photo.jpg --label tshirt
```

Aliases: `pent` / `pants` / `trousers` → trousers; `tshirt` / `t-shirt` / `tee` → t-shirt.

**Then actually train** (the live API does not learn until this):

```text
python prepare_outfit20_dataset.py
python train_outfit20.py
```

Restart the ML service so it loads `models/improved/outfit20_yolov8n.pt`. Aim for many photos per class (different lighting, angles, hanging vs worn), not one or two.
