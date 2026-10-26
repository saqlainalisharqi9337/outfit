# Adore — ML Pipeline

## Honest pipeline label

**Pretrained YOLO detection-assisted clothing analysis** with MobileNetV2 / ResNet specialists, a dress-vs-upperwear gate, colour extraction, and fallback fixed-region proposals.

It is **not** a custom-trained 13-class clothing detector. Garment labels come from classifiers, not from YOLO class names.

## End-to-end flow

```
upload image
  ├─ classify_clothing (full frame)
  │    ├─ ImageNet MobileNetV2
  │    ├─ accessory / lowerwear / silhouette MobileNet heads
  │    ├─ upperwear3 / footwear4 / garment / dress-upperwear gate (PyTorch)
  │    └─ routing rules (isolated product, hanging body, tall frame)
  ├─ detect_colors
  ├─ object_detector (optional YOLO Stage A)
  ├─ if region scan warranted:
  │     person/bag proposals or hardcoded REGIONS → crop → classify → filter
  └─ merge precedence → JSON
       {category, subcategory, confidence, color, items[], detected[],
        isolatedProduct, needsHumanReview, latencyMs, serviceVersion}
```

## Specialists on disk (`ml_service/models/`)

| Weights | Classes / role |
|---|---|
| `mobilenet_v2_imagenet_1.0_224.h5` | ImageNet hints (hat, bag, footwear cues, …) |
| `bag_shoes_mobilenetv2.keras` | bag, hat, skirt, shoes |
| `trousers_shorts_skirt_mobilenetv2.keras` | trousers, shorts, skirt |
| `dress_pants_skirt_mobilenetv2.keras` | dress, skirt, trousers |
| `upperwear3_resnet18.pt` | shirt, t-shirt, jacket |
| `footwear4_*.pt` (or footwear3) | flats, heels, shoes, sneakers |
| `garment4_*.pt` | multi-garment support |
| `dress_upperwear_gate*.pt` | dress vs upperwear |
| `yolov8n.pt` | Stage A COCO person / bag proposals |

`clothing_mobilenetv2.keras` (unified 13-class) is referenced by a trainer but is not required when specialists are present.

## Routing highlights

- **Isolated product** close-ups skip full-body region scans and prefer accessory / footwear specialists.
- **Hat lock** runs before lowerwear on compact product shots so hats do not become shorts/skirt.
- **Footwear forced path** recovers heels/sneakers wrongly labelled bag by the 4-class accessory head.
- **Jacket preference** inside upperwear when ImageNet/outerwear evidence is present.
- **Lowerwear and sneaker contracts** are protected by regression tests — do not change those heads casually.
- **Human review:** predictions below `ADORE_HUMAN_REVIEW_MIN_CONF` (default `0.45`) set `needsHumanReview`.

## Skin tone

`POST /analyze-skin-tone` uses an ITA-based heuristic (`skin_tone.py`), with a fallback message when face skin is uncertain.

## Pattern

Wardrobe pattern is **user-selectable** in the Flutter UI and stored with `pattern_source` / `pattern_confidence`. There is no automatic `pattern_analysis.py` pixel model yet.

## Retrain pointers

See `ml_service/LAUNCH_READINESS.md` and `ml_service/README.md` for import/retrain commands. Dataset root: `D:\fyp project\dataset`.
