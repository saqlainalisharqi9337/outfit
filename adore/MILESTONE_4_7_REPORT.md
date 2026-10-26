# Milestone 4.7 — Class-Specific Error Analysis and Confidence Threshold Study

**MILESTONE 4.7 STATUS: PASS**

No retraining. FastAPI / YOLO / production inference / Flutter / taxonomy / dataset labels were **not** modified. Mask R-CNN was **not** integrated into the app.

This is an analysis of the frozen M4.6 best checkpoint. It is **not** a production-readiness claim.

## 1. Objective

Determine why several classes had 0 TP at confidence 0.5 in M4.6: whether they are (A) detected below 0.5, (B) assigned the wrong clothing class, or (C) completely missed. Also measure precision/recall across 0.50–0.10 and inspect confusion, small objects, and previews.

## 2. Checkpoint used

Identified from `checkpoints/maskrcnn/m4_6/history.json` (`best_epoch` 1) and confirmed by loading the file:

| field | value |
|---|---|
| path | `checkpoints/maskrcnn/m4_6/best_model.pth` |
| `best` | `True` |
| `epoch` | **1** |
| `val_loss` | 1.531695309082667 |
| `num_classes` | 16 |
| class names | shirt … sunglasses (15 foreground) |

`last_model.pth` is epoch 5 and was **not** evaluated.

Eval set: 150 first-N val images, IoU 0.5, same split as official M4.6. One forward pass collected 1716 raw model detections; metrics at each score were computed from that cache.

Artifacts: `checkpoints/maskrcnn/m4_6/m4_7_threshold_study.json`. Score≥0.1 overlays: `outputs/maskrcnn_m4_7/`. Existing M4.6 score≥0.3 overlays: `outputs/maskrcnn_preview_m4_6/`.

## 3. Threshold sweep

IoU = 0.5. Ground-truth count is 497 at every row.

**Operating-point columns** (P/R/TP/FP/FN/n_pred) count detections with score ≥ threshold, class-aware IoU match.

**mAP@50 / mAP@50:95 in this table** use only detections ≥ that threshold (so they *change* with the operating point). This is **not** the M4.6 headline AP.

M4.6 official mAP used **all ranked detections** (model outputs, typically score ≥ ~0.05). Recalculated here: **mAP@50 = 0.2879**, **mAP@50:95 = 0.1462**, 1716 predictions. That matches M4.6 exactly.

| score | n_pred | n_gt | TP | FP | FN | P | R | mAP@50 (filtered) | mAP@50:95 (filtered) | mean IoU TP |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 201 | 497 | 157 | 44 | 340 | **0.781** | **0.316** | 0.109 | 0.059 | 0.770 |
| 0.40 | 253 | 497 | 176 | 77 | 321 | 0.696 | 0.354 | 0.134 | 0.075 | 0.772 |
| 0.30 | 340 | 497 | 207 | 133 | 290 | 0.609 | 0.416 | 0.180 | 0.099 | 0.769 |
| 0.20 | 523 | 497 | 250 | 273 | 247 | 0.478 | 0.503 | 0.229 | 0.124 | 0.770 |
| 0.10 | 981 | 497 | 292 | 689 | 205 | 0.298 | 0.588 | 0.266 | 0.139 | 0.760 |

At score 0.50, P/R/n_pred match the official M4.6 eval (0.781 / 0.316 / 201). Mean IoU of true positives stays ~0.76–0.77 at every threshold: when a box matches, overlap is already decent.

Lowering the threshold recovers recall (0.32 → 0.59) and **destroys precision** (0.78 → 0.30). A global 0.10 operating point is not a substitute for better training.

## 4. Complete per-class threshold results

AP50 in these tables is **filtered** (detections ≥ that score). Ranking AP50 (all detections) is listed once per class in §5.

### Score 0.50

| class | n_gt | TP | FP | FN | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 16 | 0 | 0 | 16 | 0.000 | 0.000 | 0.000 |
| jacket | 31 | 1 | 0 | 30 | 1.000 | 0.032 | 0.032 |
| sweater | 1 | 0 | 0 | 1 | 0.000 | 0.000 | 0.000 |
| trousers | 38 | 22 | 14 | 16 | 0.611 | 0.579 | 0.476 |
| shorts | 17 | 9 | 3 | 8 | 0.750 | 0.529 | 0.487 |
| skirt | 14 | 0 | 0 | 14 | 0.000 | 0.000 | 0.000 |
| dress | 67 | 6 | 0 | 61 | 1.000 | 0.090 | 0.090 |
| jumpsuit | 6 | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |
| shoes | 208 | 119 | 27 | 89 | 0.815 | 0.572 | 0.545 |
| bag | 24 | 0 | 0 | 24 | 0.000 | 0.000 | 0.000 |
| hat | 9 | 0 | 0 | 9 | 0.000 | 0.000 | 0.000 |
| belt | 30 | 0 | 0 | 30 | 0.000 | 0.000 | 0.000 |
| scarf | 8 | 0 | 0 | 8 | 0.000 | 0.000 | 0.000 |
| watch | 11 | 0 | 0 | 11 | 0.000 | 0.000 | 0.000 |
| sunglasses | 17 | 0 | 0 | 17 | 0.000 | 0.000 | 0.000 |

### Score 0.40

| class | n_gt | TP | FP | FN | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 16 | 0 | 0 | 16 | 0.000 | 0.000 | 0.000 |
| jacket | 31 | 4 | 2 | 27 | 0.667 | 0.129 | 0.129 |
| sweater | 1 | 0 | 0 | 1 | 0.000 | 0.000 | 0.000 |
| trousers | 38 | 24 | 19 | 14 | 0.558 | 0.632 | 0.508 |
| shorts | 17 | 9 | 9 | 8 | 0.500 | 0.529 | 0.487 |
| skirt | 14 | 2 | 1 | 12 | 0.667 | 0.143 | 0.119 |
| dress | 67 | 15 | 4 | 52 | 0.789 | 0.224 | 0.216 |
| jumpsuit | 6 | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |
| shoes | 208 | 122 | 42 | 86 | 0.744 | 0.587 | 0.556 |
| bag | 24 | 0 | 0 | 24 | 0.000 | 0.000 | 0.000 |
| hat | 9 | 0 | 0 | 9 | 0.000 | 0.000 | 0.000 |
| belt | 30 | 0 | 0 | 30 | 0.000 | 0.000 | 0.000 |
| scarf | 8 | 0 | 0 | 8 | 0.000 | 0.000 | 0.000 |
| watch | 11 | 0 | 0 | 11 | 0.000 | 0.000 | 0.000 |
| sunglasses | 17 | 0 | 0 | 17 | 0.000 | 0.000 | 0.000 |

### Score 0.30

| class | n_gt | TP | FP | FN | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 16 | 3 | 2 | 13 | 0.600 | 0.188 | 0.172 |
| jacket | 31 | 9 | 12 | 22 | 0.429 | 0.290 | 0.223 |
| sweater | 1 | 0 | 0 | 1 | 0.000 | 0.000 | 0.000 |
| trousers | 38 | 26 | 24 | 12 | 0.520 | 0.684 | 0.537 |
| shorts | 17 | 10 | 14 | 7 | 0.417 | 0.588 | 0.516 |
| skirt | 14 | 3 | 14 | 11 | 0.176 | 0.214 | 0.140 |
| dress | 67 | 26 | 6 | 41 | 0.812 | 0.388 | 0.353 |
| jumpsuit | 6 | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |
| shoes | 208 | 128 | 59 | 80 | 0.684 | 0.615 | 0.577 |
| bag | 24 | 0 | 0 | 24 | 0.000 | 0.000 | 0.000 |
| hat | 9 | 2 | 2 | 7 | 0.500 | 0.222 | 0.185 |
| belt | 30 | 0 | 0 | 30 | 0.000 | 0.000 | 0.000 |
| scarf | 8 | 0 | 0 | 8 | 0.000 | 0.000 | 0.000 |
| watch | 11 | 0 | 0 | 11 | 0.000 | 0.000 | 0.000 |
| sunglasses | 17 | 0 | 0 | 17 | 0.000 | 0.000 | 0.000 |

### Score 0.20

| class | n_gt | TP | FP | FN | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 16 | 10 | 34 | 6 | 0.227 | 0.625 | 0.325 |
| jacket | 31 | 17 | 26 | 14 | 0.395 | 0.548 | 0.338 |
| sweater | 1 | 0 | 0 | 1 | 0.000 | 0.000 | 0.000 |
| trousers | 38 | 28 | 41 | 10 | 0.406 | 0.737 | 0.560 |
| shorts | 17 | 11 | 27 | 6 | 0.289 | 0.647 | 0.538 |
| skirt | 14 | 4 | 34 | 10 | 0.105 | 0.286 | 0.151 |
| dress | 67 | 41 | 14 | 26 | 0.745 | 0.612 | 0.544 |
| jumpsuit | 6 | 0 | 8 | 6 | 0.000 | 0.000 | 0.000 |
| shoes | 208 | 133 | 87 | 75 | 0.605 | 0.639 | 0.593 |
| bag | 24 | 1 | 0 | 23 | 1.000 | 0.042 | 0.042 |
| hat | 9 | 3 | 2 | 6 | 0.600 | 0.333 | 0.252 |
| belt | 30 | 1 | 0 | 29 | 1.000 | 0.033 | 0.033 |
| scarf | 8 | 0 | 0 | 8 | 0.000 | 0.000 | 0.000 |
| watch | 11 | 0 | 0 | 11 | 0.000 | 0.000 | 0.000 |
| sunglasses | 17 | 1 | 0 | 16 | 1.000 | 0.059 | 0.059 |

### Score 0.10

| class | n_gt | TP | FP | FN | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 16 | 12 | 104 | 4 | 0.103 | 0.750 | 0.339 |
| jacket | 31 | 25 | 74 | 6 | 0.253 | 0.806 | 0.421 |
| sweater | 1 | 0 | 6 | 1 | 0.000 | 0.000 | 0.000 |
| trousers | 38 | 30 | 71 | 8 | 0.297 | 0.789 | 0.579 |
| shorts | 17 | 12 | 71 | 5 | 0.145 | 0.706 | 0.554 |
| skirt | 14 | 10 | 83 | 4 | 0.108 | 0.714 | 0.207 |
| dress | 67 | 52 | 42 | 15 | 0.553 | 0.776 | 0.658 |
| jumpsuit | 6 | 2 | 74 | 4 | 0.026 | 0.333 | 0.026 |
| shoes | 208 | 137 | 130 | 71 | 0.513 | 0.659 | 0.604 |
| bag | 24 | 4 | 21 | 20 | 0.160 | 0.167 | 0.086 |
| hat | 9 | 3 | 8 | 6 | 0.273 | 0.333 | 0.252 |
| belt | 30 | 1 | 3 | 29 | 0.250 | 0.033 | 0.033 |
| scarf | 8 | 0 | 0 | 8 | 0.000 | 0.000 | 0.000 |
| watch | 11 | 0 | 0 | 11 | 0.000 | 0.000 | 0.000 |
| sunglasses | 17 | 4 | 2 | 13 | 0.667 | 0.235 | 0.235 |

Shirt first appears as TP at **0.30**. Jacket recall 0.03 → 0.81 from 0.50 to 0.10. Scarf and watch have **0 TP at every threshold**.

## 5. Confidence analysis

All 1716 model detections (TorchVision typically keeps score ≥ ~0.05).

| class | n_pred | min | max | mean | median | n below 0.5 | n at/above 0.5 | ranking AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| shirt | 200 | 0.051 | **0.398** | 0.136 | 0.116 | 200 | **0** | 0.348 |
| jacket | 171 | 0.051 | 0.663 | 0.158 | 0.115 | 170 | **1** | 0.440 |
| sweater | 74 | 0.050 | 0.169 | 0.073 | 0.065 | 74 | 0 | 0.031 |
| trousers | 151 | 0.051 | 0.928 | 0.297 | 0.186 | 115 | 36 | 0.586 |
| shorts | 146 | 0.050 | 0.882 | 0.182 | 0.119 | 134 | 12 | 0.554 |
| skirt | 151 | 0.050 | **0.452** | 0.151 | 0.125 | 151 | **0** | 0.220 |
| dress | 137 | 0.052 | 0.639 | 0.208 | 0.158 | 131 | 6 | 0.735 |
| jumpsuit | 135 | 0.050 | 0.254 | 0.117 | 0.111 | 135 | 0 | 0.038 |
| shoes | 337 | 0.050 | 0.968 | 0.449 | 0.378 | 191 | 146 | 0.608 |
| bag | 117 | 0.050 | **0.245** | 0.083 | 0.071 | 117 | **0** | 0.101 |
| hat | 14 | 0.069 | 0.367 | 0.180 | 0.120 | 14 | 0 | 0.252 |
| belt | 38 | 0.050 | 0.260 | 0.075 | 0.068 | 38 | 0 | 0.033 |
| scarf | 16 | 0.050 | **0.061** | 0.054 | 0.053 | 16 | 0 | **0.000** |
| watch | 7 | 0.055 | **0.096** | 0.071 | 0.062 | 7 | 0 | **0.000** |
| sunglasses | 22 | 0.052 | 0.241 | 0.097 | 0.075 | 22 | 0 | 0.372 |

Shirt, jacket, bag, hat, belt, scarf, watch, sunglasses **do** produce predictions, almost entirely below 0.5. That is not the same as “useful low-confidence detections”:

- Shirt/jacket/dress/skirt/sunglasses: ranking AP and GT-matched IoU≥0.5 at low score show a **real class signal**.
- Scarf max 0.061 and ranking AP 0.000: 16 boxes exist but they do **not** match scarf GT.
- Watch max 0.096, ranking AP 0.000, 0 TP at 0.10: the 7 watch boxes are not on the 11 watch GT instances.

## 6. Confusion / error analysis

Per ground-truth instance, the highest-IoU detection (any class) was classified as:

- **correct high-conf:** same class, IoU≥0.5, score≥0.5
- **correct low-conf:** same class, IoU≥0.5, score below 0.5
- **wrong class:** different class, IoU≥0.5
- **poor localization:** best IoU in [0.1, 0.5)
- **missed:** best IoU under 0.1

| class | n_gt | high≥0.5 | low below 0.5 | wrong | loc | miss |
|---|---:|---:|---:|---:|---:|---:|
| shirt | 16 | 0 | **14** | 1 | 1 | 0 |
| jacket | 31 | 1 | **27** | 2 | 1 | 0 |
| sweater | 1 | 0 | 1 | 0 | 0 | 0 |
| trousers | 38 | **22** | 9 | 2 | 5 | 0 |
| shorts | 17 | **9** | 3 | 1 | 3 | 1 |
| skirt | 14 | 0 | **12** | 0 | 1 | 1 |
| dress | 67 | 6 | **56** | 2 | 3 | 0 |
| jumpsuit | 6 | 0 | 4 | 2 | 0 | 0 |
| shoes | 208 | **116** | 24 | 0 | 37 | 31 |
| bag | 24 | 0 | 7 | 3 | **11** | 3 |
| hat | 9 | 0 | 3 | 0 | 1 | **5** |
| belt | 30 | 0 | 1 | 2 | 10 | **17** |
| scarf | 8 | 0 | 0 | **3** | 4 | 1 |
| watch | 11 | 0 | 0 | 0 | 0 | **11** |
| sunglasses | 17 | 0 | 8 | 0 | 3 | 6 |

### Hypothesized pairs (IoU≥0.5, wrong class)

All of the following were **0** on this 150-image set:

shirt→jacket, shirt→dress, jacket→shirt, shorts→skirt, skirt→shorts, trousers→shirt, dress→shirt, bag→hat/belt/scarf, hat→bag/scarf, belt→watch/scarf, scarf→belt/hat, watch→belt/sunglasses, sunglasses→watch/hat.

### Observed wrong-class matches (counts are small)

| GT → pred | count |
|---|---:|
| scarf → dress | 2 |
| scarf → shirt | 1 |
| shirt → scarf | 1 |
| jacket → dress | 1 |
| jacket → bag | 1 |
| dress → jacket | 1 |
| dress → skirt | 1 |
| shorts → trousers | 1 |
| trousers → shoes | 2 |
| jumpsuit → shorts | 1 |
| jumpsuit → trousers | 1 |
| bag → shirt / jacket / sweater | 1 each |
| belt → trousers / shorts | 1 each |

Class confusion exists but is **not** the main failure for shirt/jacket/dress. Those garments are usually boxed as the **correct** class with score 0.10–0.40.

Shoes → non-clothing: not a GT confusion (shoes have 0 wrong-class). It appears as **false positives** in previews (plaid hip as `shoes 0.35` in M4.6 `pred_04`; door region as `shorts 0.13` at score 0.1 in M4.7 `pred_00`). The M4.5 door-handle-as-shoes did **not** repeat at 0.3.

## 7. Small-object analysis

Relative box area = GT area / image area. **Observed** (not assumed causes):

| class | tiny under 1% | small 1–5% | notes |
|---|---|---|---|
| watch | 11/11 GT, **11 missed** | 0 | every watch is tiny; 0 IoU≥0.1 to any detection |
| belt | 26/30 GT; 17 missed, 8 poor loc | 4 GT, 2 wrong class | almost no correct belt boxes |
| sunglasses | 16/17 tiny; 8 correct low-conf, 6 missed | 1 | some tiny sunglasses *are* localized below 0.5 |
| hat | 5 tiny: 4 missed, 1 poor loc | 4 GT: 3 correct | tiny hats fail; slightly larger hats can match |
| bag | 8 tiny: 0 correct, 5 loc, 2 miss | 15: 6 correct, 6 loc | even 1–5% bags often fail IoU |
| scarf | 1 tiny miss | 6: 3 wrong, 3 loc | no correct scarf match at IoU 0.5 |
| shoes | **203/208 tiny**; 138 correct, 34 loc, 31 miss | 5 | tiny does not prevent shoes from scoring ≥0.5 |

**Evidence:** watches are 100% tiny and 100% missed. Belts are mostly tiny and mostly missed or poorly localized. Hats that are tiny miss; hats that are 1–5% can match.

**Hypothesis (not proven):** CPU `min_size=256` / `max_size=320` plus tiny GT area makes watch/belt features too small after resize. Shoes contradict a blanket “tiny ⇒ undetectable” claim: they are tiny *and* the strongest class. So size is associated with accessory failure, but class frequency / pretraining (COCO shoes-like objects) also matter.

Occlusion was not measured separately. Preview `pred_06` shows a large straw bag that is still missed at 0.3; that is **not** explained by tiny size.

## 8. Preview observations

M4.6 overlays (`outputs/maskrcnn_preview_m4_6/`, score ≥ 0.3) plus M4.7 overlays (`outputs/maskrcnn_m4_7/`, score ≥ 0.1) on the same eight val images.

- **Missed pieces at 0.3:** jacket/shirt/sunglasses/belt on `pred_00`; bag on `pred_01` and `pred_06`; beanie on `pred_07`; second shoe on `pred_02`/`pred_03`.
- **Low-confidence correct boxes:** at 0.1, `pred_00` gains `jacket 0.23`; `pred_02` gains `jacket 0.26` plus overlapping `shirt`; `pred_05` gains `shirt 0.22` / `jacket 0.19` on the open shirt. These were absent or weaker at 0.5.
- **Duplicates / overlap:** two `trousers` (0.39 and 0.64) in `pred_02`; at 0.1, `pred_05` stacks shorts/skirt/trousers; `pred_01` stacks dress/jumpsuit/skirt/shorts on one garment.
- **Incorrect labels:** `hat 0.33` on hair in `pred_00` (no hat); `pred_04` `shoes 0.35` on a plaid jacket, not the boots; `pred_05` at 0.1 adds `hat 0.14` (headband/hair) and `skirt` on shorts.
- **Poor masks:** trousers leak into the audience (`pred_02`); jacket masks incomplete (`pred_06`).
- **Background FP:** `shorts 0.13` on the door at 0.1 (`pred_00`). Lowering the threshold reintroduces this noise.
- **Small accessories:** sunglasses visible in `pred_00`/`pred_04` still unlabeled; belt on the runway jacket unlabeled; straw bag unlabeled.

## 9. Weak-class diagnosis

| class | A below 0.5 | B wrong class | C missed | Dominant evidence |
|---|---|---|---|---|
| shirt | **yes (14/16)** | 1 (→scarf) | 0 | max score 0.398; TP 0→12 from 0.5 to 0.1 |
| jacket | **yes (27/31)** | 2 | 0 | 170/171 preds below 0.5; recall 0.03→0.81 |
| sweater | 1/1 low-conf | 0 | 0 | n_gt=1 only |
| skirt | **yes (12/14)** | 0 | 1 | max 0.452; no pred ≥ 0.5 |
| dress | **yes (56/67)** | 2 | 0 | high ranking AP, conservative scores |
| bag | 7 low-conf | 3 | 3 | **11 poor loc** — mixed A + localization |
| hat | 3 low-conf | 0 | **5** | tiny hats missed; others low-conf |
| belt | 1 | 2 | **17** | tiny + poor loc |
| scarf | 0 correct | **3** | 1 | 4 loc; 16 noise boxes, AP=0 |
| watch | 0 | 0 | **11/11** | C + tiny |
| sunglasses | **8 low-conf** | 0 | 6 | max 0.241; ranking AP 0.372 |

Shirt/jacket 0 TP at 0.5 is **not** “the detector cannot see them.” It is **under-confident correct localizations**.

## 10. Recommended next training change

Do **not** ship a 0.10 global threshold (P 0.30). Do **not** train more epochs on the same 1000-image subset (M4.6 val loss already rose after epoch 1). Do **not** change the 15-class taxonomy. Do **not** wire this into FastAPI.

Training-side next step (isolated M4.8):

1. **More images, fewer epochs**, resume from this best file, new directory:
   `2000 train / 200 val / 2–3 epochs / class-aware / --resume checkpoints/maskrcnn/m4_6/best_model.pth / --checkpoint-dir checkpoints/maskrcnn/m4_7` (or `m4_8`).
2. If a GPU (or a longer CPU budget) is available, **raise `min_size`** above 256. Watch/belt failure is concentrated in tiny boxes; 256-px training is a plausible limiter.
3. Keep evaluating at **0.5 and 0.3**. Success for shirt/jacket is TP at 0.5, not just ranking AP.
4. Optional: class-aware **val** eval so watch/scarf are not judged only on the first-N JSON prefix.

Lowering score at inference can be a later **analysis** tool. It is not the training fix.

## 11. Decision for M4.8

The evidence supports:

**5. Mixed problem**

Breakdown:

1. **Low-confidence (primary for garments):** shirt, jacket, skirt, dress, and many sunglasses/hats are localized as the correct class with IoU≥0.5 but score below 0.5. This is the M4.6 “0 TP at 0.5” story for shirt/jacket.
2. **Class-confusion (secondary, not the hypothesized pairs):** scarf→dress/shirt; jumpsuit→bottoms; a few bag/jacket swaps. shirt→jacket, shorts→skirt, and dress→shirt were **0** at IoU 0.5 on this slice. Preview overlap at score 0.1 is mostly duplicate low-score tags on one object, not the main GT failure mode.
3. **Localization/segmentation:** bags (11/24 poor IoU), belts (10/30), leftover shoes of a pair (37 poor loc, 31 miss). Mean IoU of TPs is already ~0.77, so this is unmatched instances, not sloppy matched boxes.
4. **Small-object/data:** **watches are completely missed** (11/11 tiny, 0 TP at 0.10, ranking AP 0). Belts are mostly tiny and missed. Scarf has no correct match.

M4.8 should treat this as mixed: raise confidence of already-localized garments (more/varied data, not 5 more overfit epochs) **and** add small-object capacity for watch/belt. Confusion-only fixes (taxonomy merges) are **not** supported by the counts.

**MILESTONE 4.7 STATUS: PASS**
