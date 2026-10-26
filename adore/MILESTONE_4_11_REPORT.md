# Milestone 4.11 — Higher-Resolution Experiment

Epoch 3 was **not** run. Epoch 2 validation loss rose, so the saved best checkpoint is epoch 1. The same 1,146-image validation set as M4.9 and M4.10 was used. The app was not changed.

## 1. Baseline M4.10

Same 1,146 images, score 0.5, IoU 0.5. Input size 320 / 480.

| metric | M4.10 |
|---|---:|
| precision | 0.703 |
| recall | 0.476 |
| mAP@50 | 0.318 |
| mAP@50:95 | 0.178 |
| mean IoU | 0.803 |
| predictions / FP / FN | 2574 / 764 / 1990 |

## 2–6. Resolution

Resize is inside torchvision, not in the dataset loader. Scale is `min(min_size / short_side, max_size / long_side)`. Aspect ratio stays the same.

| | min_size | max_size | boxes with shorter side under 16 px |
|---|---:|---:|---:|
| M4.10 | 320 | 480 | **13,262** / 115,215 |
| tried first | 480 | 720 | 5,532 |
| **M4.11 used** | **416** | **624** | **7,842** / 115,215 |

480/720 was rejected. That process exited with code `3221225477` at epoch 1, step 1,200, and saved no checkpoint. 416/624 is the size that finished on this CPU. It removes 5,420 of the sub-16 px boxes.

## 7–11. Training

Initialized from `checkpoints/maskrcnn/m4_10/best_model.pth` (epoch 3). That file was not overwritten. Output is `checkpoints/maskrcnn/m4_11/`. Same 2,300-image weak-class subset as M4.10. Batch 1, workers 0, CPU, 15 foreground classes. No new labels and no duplicated images.

| epoch | train_loss | val_loss | seconds | kept |
|---:|---:|---:|---:|---|
| 1 | 1.289072 | **1.287146** | 17,975 | **best_model.pth** |
| 2 | 1.218617 | 1.310196 | 15,169 | last only |

**Best epoch: 1.** Train loss fell at epoch 2. Validation loss rose, so epoch 2 was not used for evaluation. Epoch 3 was stopped after epoch 2 was saved, to keep the run short.

Training time for the two finished epochs: **33,144 s** (about 9.2 hours). The working set during training was about **1.1 GB**.

## 12–16. Official metrics

Best checkpoint only. 1,146 images, 3,800 ground-truth instances, score 0.5, IoU 0.5. Inference took **1,540 s**. Ranking mAP uses all detections, the same rule as M4.10.

| metric | value |
|---|---:|
| precision | **0.729** |
| recall | **0.484** |
| mAP@50 | **0.357** |
| mAP@50:95 | **0.205** |
| mean IoU | **0.807** |
| predictions | 2,524 |
| TP / FP / FN | 1,840 / 684 / 1,960 |

## 17. Per-class at score 0.5

AP50 is ranking AP50.

| class | n_gt | TP | FP | FN | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 102 | 6 | 15 | 96 | 0.286 | 0.059 | 0.146 |
| jacket | 287 | 128 | 59 | 159 | 0.684 | 0.446 | 0.568 |
| sweater | 21 | 0 | 0 | 21 | 0.000 | 0.000 | 0.025 |
| trousers | 314 | 178 | 71 | 136 | 0.715 | 0.567 | 0.648 |
| shorts | 106 | 37 | 32 | 69 | 0.536 | 0.349 | 0.400 |
| skirt | 162 | 56 | 88 | 106 | 0.389 | 0.346 | 0.327 |
| dress | 508 | 247 | 55 | 261 | 0.818 | 0.486 | 0.732 |
| jumpsuit | 21 | 0 | 3 | 21 | 0.000 | 0.000 | 0.031 |
| shoes | 1565 | 988 | 181 | 577 | 0.845 | 0.631 | 0.690 |
| bag | 214 | 33 | 37 | 181 | 0.471 | 0.154 | 0.168 |
| hat | 74 | 44 | 66 | 30 | 0.400 | 0.595 | 0.529 |
| belt | 164 | 20 | 29 | 144 | 0.408 | 0.122 | 0.128 |
| scarf | 48 | 5 | 17 | 43 | 0.227 | 0.104 | 0.063 |
| watch | 84 | 17 | 5 | 67 | 0.773 | 0.202 | 0.243 |
| sunglasses | 130 | 81 | 26 | 49 | 0.757 | 0.623 | 0.663 |

## 18. Comparison with M4.10

Same 1,146 images. This pair is comparable.

| | M4.10 | M4.11 | change |
|---|---:|---:|---|
| precision | 0.703 | 0.729 | up |
| recall | 0.476 | 0.484 | up |
| mAP@50 | 0.318 | 0.357 | up |
| mAP@50:95 | 0.178 | 0.205 | up |
| mean IoU | 0.803 | 0.807 | up |
| FP | 764 | 684 | down |
| FN | 1990 | 1960 | down |

## 19. Small objects

| class | M4.10 TP | M4.11 TP | M4.10 FP | M4.11 FP | M4.10 AP50 | M4.11 AP50 |
|---|---:|---:|---:|---:|---:|---:|
| bag | 25 | 33 | 43 | 37 | 0.130 | 0.168 |
| hat | 21 | 44 | 5 | 66 | 0.397 | 0.529 |
| belt | 16 | 20 | 29 | 29 | 0.084 | 0.128 |
| scarf | 1 | 5 | 5 | 17 | 0.052 | 0.063 |
| watch | 21 | 17 | 75 | 5 | 0.141 | 0.243 |
| sunglasses | 84 | 81 | 18 | 26 | 0.675 | 0.663 |

Hat, bag, belt, scarf, and watch AP rose. Hat recall rose and its precision fell because false positives went from 5 to 66. Watch true positives dipped, but false positives fell from 75 to 5, so watch AP rose. Sunglasses slipped slightly. Scarf is still 5/48.

## 20. Larger objects

| class | M4.10 TP | M4.11 TP | M4.10 AP50 | M4.11 AP50 |
|---|---:|---:|---:|---:|
| shirt | 5 | 6 | 0.145 | 0.146 |
| jacket | 159 | 128 | 0.548 | 0.568 |
| trousers | 183 | 178 | 0.596 | 0.648 |
| skirt | 58 | 56 | 0.299 | 0.327 |
| dress | 276 | 247 | 0.719 | 0.732 |
| shoes | 944 | 988 | 0.621 | 0.690 |

Shirt is almost unchanged and still fails at 0.5 (6/102). Jacket and dress have fewer true positives at 0.5, but their ranking AP rose and their false positives fell. Trousers, skirt, and shoes did not collapse. Shoes improved.

## 21–22. False positives and misses

At score 0.5, false positives fell by 80 and false negatives fell by 30. The extra false positives that remain are concentrated on hat (66) and scarf (17 versus 5). Shirt false positives rose from 5 to 15. Watch false positives fell from 75 to 5.

Misses are still the majority of ground truth: 1,960 of 3,800. Shirt still has 96 misses. Scarf has 43. Belt has 144. Watch has 67.

## 23–24. Time and machine

| item | value |
|---|---|
| finished training | 33,144 s on CPU |
| discarded 480/720 attempt | crashed at step 1,200, no checkpoint |
| evaluation | 1,540 s |
| memory while training | about 1.1 GB |

## 25. Conclusion

Higher resolution helped. On the same validation set, precision, recall, mAP@50, mAP@50:95, and mean IoU all rose, and false positives fell. Large classes did not collapse. Small-class AP rose for bag, hat, belt, scarf, and watch. Hat paid for its recall with many more false positives. Shirt and scarf are still poor at 0.5.

This checkpoint is **not** integrated and is **not** ready for the app. M4.12 was not started.

Previews: `outputs/maskrcnn_m4_11/`.

## Upload test

A local page, separate from FastAPI and Flutter, is in `ml_service/training/maskrcnn_upload_test.py`. From `ml_service`:

```text
.\.venv_m48\Scripts\python.exe -u -m training.maskrcnn_upload_test --checkpoint ..\checkpoints\maskrcnn\m4_11\best_model.pth --port 8765 --score-threshold 0.3
```

Open `http://127.0.0.1:8765`, choose a photo, and press Detect. Boxes are drawn at score 0.3 so low-confidence shirt, belt, and scarf boxes are visible. This does not write to the wardrobe or the app.
