# Detection limitations

The clothing pipeline is:

**pretrained YOLO detection-assisted clothing analysis with MobileNetV2
classification/refinement and fallback region proposals.**

It is **not** a trained 13-class YOLO clothing detector. There are no
bounding-box annotations in `D:\fyp project\dataset`.

## What pretrained COCO YOLO can detect

Relevant COCO classes used here:

| COCO class | How it is used |
|---|---|
| person | box used to place garment bands on the actual subject |
| backpack, handbag, suitcase | bag candidate crops, then confirmed by MobileNetV2 |
| (optional pose weights) | shoulder/hip/knee/ankle bands if `ADORE_POSE_WEIGHTS` is set |

## Clothing classes COCO does not have

t-shirt, shirt, jacket, trousers, shorts, skirt, dress, hat, flats, heels,
shoes, sneakers.

Those labels still come from ImageNet MobileNetV2 and the three specialist
heads (`dress_pants_skirt`, `trousers_shorts_skirt`, `bag_shoes`).

## What still uses fallback regions

- Detector weights missing or `ADORE_DETECTOR_ENABLED=0`
- Isolated product close-ups (region scan is skipped by design)
- Garments COCO cannot box (almost all clothing)

Person-relative bands replace whole-image percentages **when a person box
exists**. Otherwise the original frame-relative regions remain.
