# Model evaluation (classifiers — not retrained in this milestone)

Source: `ml_service/models/*_eval.json` and `*_audit.json`.
These MobileNetV2 specialists were **not retrained** while adding YOLO assist.

## bag / hat / skirt / shoes

- accuracy 0.8973, precision_macro 0.8599, recall_macro 0.9290, f1_macro 0.8847
- bag precision **0.689** — 159 shoes predicted as bag (imbalance: ~11.9k shoes vs 3.2k bags)

## dress / skirt / trousers

- accuracy 0.9098, precision_macro 0.9079, recall_macro 0.9120, f1_macro 0.9082
- skirt ↔ dress and trousers ↔ skirt remain the main confusions

## trousers / shorts / skirt

- accuracy 0.8690, precision_macro 0.8758, recall_macro 0.8657, f1_macro 0.8674
- most confused: skirt as shorts (66)
- audit: train/val prefix overlap **101**, train/test prefix overlap **97**
  (only this trainer drops cross-split leakage)

## Unified 13-class model

`clothing_mobilenetv2.keras` is **not on disk**. ImageNet + specialists are live.

## Detector

Pretrained `yolov8n.pt` (COCO, 80 classes, ~6.2 MB). No clothing mAP is claimed.
