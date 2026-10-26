# Milestone 4.10 — Read-Only Validation Audit

No retraining. `checkpoints/maskrcnn/m4_10/best_model.pth` was loaded and not written. FastAPI, YOLO, gates, outfit20, the taxonomy, Flutter, and production inference were not modified. M4.11 was not started.

## 1. Environment

Verified interpreter: `ml_service/.venv_m48/Scripts/python.exe`

| item | value |
|---|---|
| Python | 3.13.4 |
| PyTorch | 2.14.0+cpu |
| Torchvision | 0.29.0+cpu |
| CUDA | False |
| Mask R-CNN | `torchvision.models.detection.maskrcnn_resnet50_fpn` via `training/train_maskrcnn.py` `build_maskrcnn` |

Existing code reused: `training/train_maskrcnn.py` (`build_maskrcnn`, `load_checkpoint`, `apply_cpu_fast`), `training/dataset.py` (`ClothingDetectionDataset`), `training/label_map.py`, `training/evaluate_maskrcnn.py`, `training/analyze_maskrcnn_thresholds.py`, `training/preview_maskrcnn.py`.

## 2. Checkpoint verification

`checkpoints/maskrcnn/m4_10/best_model.pth` **loads successfully** on CPU.

| field | value |
|---|---|
| architecture | Mask R-CNN ResNet-50 FPN |
| `num_classes` | 16 (background + 15 foreground) |
| box predictor outputs | 16 |
| mask predictor outputs | 16 |
| epoch | 3 |
| `best` | true |
| val_loss | 1.0370639572143554 |
| device | cpu |
| `min_size` / `max_size` | 320 / 480 |

**CHECKPOINT CORRECT.**

## 3. Class mapping verification

Checkpoint `class_names` and `ml_service/taxonomy/unified_label_map.json` `detector_classes` are the same list, in the same order. `UnifiedLabelMap.class_id` is `index + 1`. Background is 0. Model label IDs therefore match:

| id | name |
|---:|---|
| 0 | background |
| 1 | shirt |
| 2 | jacket |
| 3 | sweater |
| 4 | trousers |
| 5 | shorts |
| 6 | skirt |
| 7 | dress |
| 8 | jumpsuit |
| 9 | shoes |
| 10 | bag |
| 11 | hat |
| 12 | belt |
| 13 | scarf |
| 14 | watch |
| 15 | sunglasses |

**Mapping match: yes.**

## 4. Inference verification

A live forward pass used the same dataset class and the same model builder as evaluation. It covered the first validation image that contains each of the 15 foreground classes: **11 images**, **94 raw predictions**. This subset is a behavior check. It is not a new mAP.

| check | result |
|---|---|
| images | 11 |
| predictions | 94 |
| score ≥ 0.5 | 22 |
| score 0.3–0.5 | 8 |
| score 0.1–0.3 | 34 |
| score < 0.1 | 30 |
| invalid boxes | 0 |
| empty masks | 0 |
| several objects in one image | yes (see §5) |

Every returned mask tensor has shape `[N, 1, H, W]` with `H, W` equal to the **original** image, which is what torchvision does after it pastes masks back. Boxes are finite and have positive area.

Predictions with score ≥ 0.05 on this subset existed for all 15 foreground names, including sweater (1) and jumpsuit (3). Most of those are below 0.5.

**INFERENCE CORRECT.** The model emits instance boxes, scores, labels, and masks. It is not a single whole-image classifier.

## 5. Multi-item detection results

Eight of these images have at least three ground-truth classes and at least two predictions at score ≥ 0.3.

| image | ground truth | separate predictions (highest scores) |
|---|---|---|
| val index 2 | jacket, trousers, shoes, belt | `shoes 0.98`, `trousers 0.95`, `jacket 0.80`, `belt 0.32`, extra `shoes 0.33` |
| val index 10 | shirt, trousers, shoes | `trousers 0.65`, `shoes 0.24`, `skirt 0.27`. Shirt is not in the top scores |
| val index 51 | jacket, trousers, shoes, belt, scarf, dress | `shoes 0.99`, `jacket 0.76`, `trousers 0.60`, `belt 0.36`, `scarf 0.12` |
| val index 0 | shirt, jacket, belt, sunglasses | `jacket 0.88`, `shirt 0.37`, `sunglasses 0.35`. Belt has no prediction at ≥ 0.05 |

The model **does** separate large garments. It also **duplicates** shoes (two or three boxes on one pair) and **misses** the smaller piece in the same photo (belt on index 0, shirt on index 10, scarf kept only at 0.12).

## 6. Mask quality

From the existing overlays in `outputs/maskrcnn_m4_10/` (drawn by `training/preview_maskrcnn.py` at score ≥ 0.3) and the live mask tensors:

- Large garments can follow the item: trousers and shoes on index 2, dress on index 1 (`dress 0.84` live).
- Masks spill. On index 0 the jacket mask covers the pink shirt and the extended arm, while a separate shirt box still exists.
- Neighboring clothes get one mask. On index 51 the jacket mask paints the fur scarf; the scarf score is only 0.12, so the scarf has no usable mask at 0.3.
- Small objects often have no mask at the viewing threshold because the box itself is below 0.3 (watch 0.22 on index 28, bag absent on index 1).
- Returned masks are not empty. The problem is shape and class, not a missing mask head.

## 7. Small-object analysis

Live examples on the same validation images used for the M4.10 previews:

| class | example | what happened | category |
|---|---|---|---|
| belt | index 0, belt is in the ground truth | no belt prediction at ≥ 0.05 | A. absent |
| belt | index 2 | `belt 0.32` on the buckle | E. correct class, below 0.5 |
| belt | index 51 | `belt 0.36` | E. correct class, below 0.5 |
| watch | index 28, watch is in the ground truth | `watch 0.22` only | B / E. low confidence |
| scarf | index 51, fur scarf in the ground truth | `scarf 0.12`; jacket mask covers the fur | B, and the mask merges into the jacket |
| scarf | index 89 | `scarf 0.06` | B. very low confidence |
| bag | index 1, handbag in the ground truth | no bag prediction at ≥ 0.05; dress is 0.84 | A. absent |
| bag | index 13 | no bag prediction in the top scores | A. absent |
| sunglasses | index 37 | `sunglasses 0.95` with `shoes 0.96` | correct, above 0.5 |
| sunglasses | index 4 | no sunglasses prediction; top score is `dress 0.17` | A. absent |
| hat | index 7, red hat in the ground truth | `hat 0.19`; two `bag` boxes on the torso | B, plus wrong class on the body |

So small accessories are not one failure mode. Some are missing, some are the right class under 0.5, and some are covered by a neighboring mask. Sunglasses are the exception: they can score above 0.9.

This matches the M4.10 preprocessing audit: **13,262 / 115,215** training boxes have a shorter side under 16 px after the 320/480 scale. That audit was not re-run here. The live trace below shows the same scale rule is what inference uses.

## 8. Preprocessing trace

Dataset `__getitem__` does not resize. The first audited image is **683 × 1024**. Inside `GeneralizedRCNNTransform.resize`:

| item | value |
|---|---|
| scale | `min(320 / short_side, 480 / long_side)` = **0.4685** on this image |
| resized content | short side 320, long side at most 480 |
| batched tensor | **320 × 480** (also padded to a multiple of 32) |
| aspect ratio | preserved |
| normalization | mean `[0.485, 0.456, 0.406]`, std `[0.229, 0.224, 0.225]` |
| boxes | scaled with the image, then mapped back to original coordinates for the output |
| masks | resized with the image, then pasted back to original `H × W` |

No horizontal flip and no other augmentation exist in `ClothingDetectionDataset` or in this transform. Preprocessing was not changed.

## 9. Observed failure cases

| case | evidence |
|---|---|
| low-confidence correct shirt | index 0: `shirt 0.37` under `jacket 0.88` |
| missed shirt | index 10: shirt is ground truth; top box is `trousers 0.65` |
| wrong class on shorts / hat | index 7: hat 0.19, shorts not at ≥ 0.3, torso labeled `bag 0.39` and `bag 0.32` |
| jumpsuit called dress | index 37: jumpsuit ground truth, `dress 0.90` |
| sweater not in the top scores | index 89: sweater is ground truth; top is sunglasses 0.98 and jacket 0.72 |
| duplicate shoes | index 2: `shoes 0.98` and `shoes 0.33`; index 28: `shoes 0.97` and `shoes 0.65` |
| overlapping garment labels | index 28: `dress 0.63`, `jacket 0.61`, and `skirt 0.45` on one outfit |
| poor mask | index 0 jacket mask covers shirt and arm |
| small-object miss | belt on index 0, bag on index 1, sunglasses on index 4 |

## 10. Comparison with M4.10 reported metrics

The official numbers in `MILESTONE_4_10_REPORT.md` come from `checkpoints/maskrcnn/m4_10/threshold_study.json` (1,146 images, 3,800 ground-truth instances, score 0.5, IoU 0.5). This audit did not recompute mAP. Those stored values are:

| metric | report | stored JSON |
|---|---:|---:|
| precision | 0.703 | 0.7032 |
| recall | 0.476 | 0.4763 |
| ranking mAP@50 | 0.318 | 0.3177 |
| ranking mAP@50:95 | 0.178 | 0.1780 |
| mean IoU | 0.803 | 0.8034 |
| predictions at 0.5 | — | 2,574 |
| TP / FP / FN | — | 1,810 / 764 / 1,990 |

The 11-image run agrees with that picture: many detections exist below 0.5 (34 between 0.1 and 0.3, 30 below 0.1), large classes clear 0.5, and shirt, belt, scarf, watch, and bag often do not. Mean IoU 0.803 says that **when a box matches, overlap is already good**. The gap is misses and low scores, not broken coordinates.

## 11. Pipeline correctness

| question | result |
|---|---|
| 1. Pipeline correct | **Yes.** Train, eval, preview, and this load all use one Mask R-CNN path. |
| 2. Checkpoint correct | **Yes.** Epoch 3, 16 classes, weights load. |
| 3. Inference correct | **Yes.** Separate instances, valid boxes, non-empty masks, labels on the taxonomy ids. |

Nothing in this audit shows a bug that would explain the M4.10 metrics. The metrics are measuring the model.

## 12. Model-quality assessment

**MODEL QUALITY NEEDS IMPROVEMENT.**

Not because mAP is moderate by itself. Because, on a working pipeline:

- shirt, scarf, belt, and watch still rarely clear 0.5 (M4.10: 5, 1, 16, and 21 true positives),
- watch false positives are 75 at 0.5,
- hat and bag are worse than M4.9,
- duplicates and overlapping class labels remain on shoes, dress, jacket, and skirt.

## 13. Production-readiness assessment

**NOT READY FOR INTEGRATION.**

Do not connect this checkpoint to FastAPI or Flutter. Large classes (jacket, trousers, dress, shoes, some sunglasses) are usable as research output. The 15-class detector is not.

## 14. Recommended next experiment

**The evidence supports proceeding to M4.11 higher-resolution training.**

Reasons from this audit, not from a new theory:

1. Implementation, checkpoint, class ids, boxes, and masks already work. A higher-resolution run would be training the same pipeline, not repairing a broken one.
2. Matched boxes already have mean IoU 0.803. Localization of the hits is not the main gap.
3. The objects that fail are the small ones, and inference uses the same 320/480 scale that leaves 13,262 training boxes under 16 px.
4. Live scores sit just under the line or disappear: belt 0.32 and 0.36, watch 0.22, scarf 0.12, bag absent. Those are the classes a larger input is aimed at.
5. M4.10 already showed that sampling more weak-class images, at the same resolution, does not fix them.

Keep M4.10 `best_model.pth` frozen and initialize M4.11 from it. Do not integrate either checkpoint until a full 1,146-image eval shows shirt, scarf, belt, and watch true positives rising **without** another hat/bag or dress-recall drop.

**M4.11 was not started.**
