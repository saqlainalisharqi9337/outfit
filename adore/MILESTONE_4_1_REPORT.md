# Milestone 4.1 — Environment Setup and Verification

Verified on 2026-09-21 using `ml_service\.venv\Scripts\python.exe`.
No packages were installed or upgraded. No training was started. Production inference was not modified.

## Environment

Python: 3.12.10 (`D:\fyp project\adore\ml_service\.venv\Scripts\python.exe`)
PyTorch: 2.13.0+cpu
TorchVision: 0.28.0+cpu
CUDA: False
Device: CPU

## Mask R-CNN

Availability: `torchvision.models.detection.maskrcnn_resnet50_fpn` imports successfully.
TorchVision detection components: `FastRCNNPredictor` and `MaskRCNNPredictor` import successfully.

Also verified: `import torch`, `import torchvision`, `from PIL import Image`, `import numpy`.

## Dataset

Dataset was not modified. Image files counted under `ml_service/datasets/clothing_detection/images/`.

Train: 37887
Validation: 1146
Test: 5227
Total: 44260

These match the expected counts. `DATASET_FINAL_VALIDATION_REPORT.md` (2026-09-20T20:58:37Z) records **READY_FOR_MILESTONE_4** with 44260 image files present.

## Taxonomy

Source: `ml_service/taxonomy/unified_label_map.json`

Foreground classes: 15 — shirt, jacket, sweater, trousers, shorts, skirt, dress, jumpsuit, shoes, bag, hat, belt, scarf, watch, sunglasses
Total classes including background: 16

## Result

**READY for Milestone 4.2**

All environment, import, taxonomy, and on-disk image-count checks passed. Training remains CPU-only (`2.13.0+cpu`; CUDA unavailable). Do not start Mask R-CNN training until Milestone 4.2.
