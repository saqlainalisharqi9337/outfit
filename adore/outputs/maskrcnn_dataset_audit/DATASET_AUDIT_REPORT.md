# Mask R-CNN dataset audit

Generated: 2026-09-20T22:11:23Z

Does not train. Does not modify production inference. Does not change the 15-class taxonomy.

## Class mapping

- background: `0`
- `1` → `shirt`
- `2` → `jacket`
- `3` → `sweater`
- `4` → `trousers`
- `5` → `shorts`
- `6` → `skirt`
- `7` → `dress`
- `8` → `jumpsuit`
- `9` → `shoes`
- `10` → `bag`
- `11` → `hat`
- `12` → `belt`
- `13` → `scarf`
- `14` → `watch`
- `15` → `sunglasses`

## Totals

- images: 44260
- annotations: 134852
- classes found: 15

## Per-class statistics

| id | class | images | anns | boxes | masks | % | min W×H | avg W×H | max W×H | invalid-image count | tiny boxes |
|---:|---|---:|---:|---:|---:|---:|---|---|---|---:|---:|
| 1 | shirt | 6217 | 6263 | 6263 | 6263 | 4.64 | 5.0×4.0 | 280.5×394.1 | 1022.0×1023.0 | 0 | 3 |
| 2 | jacket | 11041 | 11244 | 11244 | 11244 | 8.34 | 6.0×5.0 | 346.6×463.7 | 1023.0×1023.0 | 0 | 4 |
| 3 | sweater | 1506 | 1515 | 1515 | 1515 | 1.12 | 5.0×8.0 | 424.3×517.2 | 1023.0×1023.0 | 0 | 1 |
| 4 | trousers | 12660 | 12728 | 12728 | 12728 | 9.44 | 7.0×4.0 | 234.7×349.8 | 917.0×1023.0 | 0 | 2 |
| 5 | shorts | 2851 | 2862 | 2862 | 2862 | 2.12 | 10.0×6.0 | 224.4×185.7 | 1023.0×1016.0 | 0 | 1 |
| 6 | skirt | 5196 | 5208 | 5208 | 5208 | 3.86 | 7.0×11.0 | 255.9×307.5 | 1023.0×1023.0 | 0 | 1 |
| 7 | dress | 19172 | 19247 | 19247 | 19247 | 14.27 | 3.0×6.0 | 308.8×571.4 | 1022.0×1023.0 | 0 | 5 |
| 8 | jumpsuit | 943 | 943 | 943 | 943 | 0.70 | 39.0×85.0 | 259.2×570.7 | 747.0×1023.0 | 0 | 0 |
| 9 | shoes | 24757 | 47929 | 47929 | 47929 | 35.54 | 2.0×2.0 | 63.7×89.4 | 506.0×621.0 | 0 | 329 |
| 10 | bag | 7112 | 7431 | 7431 | 7431 | 5.51 | 3.0×13.0 | 125.7×234.9 | 671.0×1022.0 | 0 | 4 |
| 11 | hat | 2588 | 2592 | 2592 | 2592 | 1.92 | 15.0×10.0 | 152.7×117.5 | 651.0×614.0 | 0 | 0 |
| 12 | belt | 6823 | 7011 | 7011 | 7011 | 5.20 | 3.0×2.0 | 137.0×92.6 | 685.0×793.0 | 0 | 67 |
| 13 | scarf | 1410 | 1422 | 1422 | 1422 | 1.05 | 8.0×9.0 | 181.8×295.0 | 1023.0×950.0 | 0 | 0 |
| 14 | watch | 3454 | 3472 | 3472 | 3472 | 2.57 | 4.0×4.0 | 39.6×36.1 | 126.0×151.0 | 0 | 33 |
| 15 | sunglasses | 4978 | 4985 | 4985 | 4985 | 3.70 | 5.0×3.0 | 91.7×44.1 | 339.0×351.0 | 0 | 10 |

## Class imbalance

- high-frequency: dress, shoes
- medium-frequency: shirt, jacket, trousers, skirt, bag, belt, sunglasses
- low-frequency: sweater, shorts, jumpsuit, hat, scarf, watch
- suspiciously few (<1% or zero): jumpsuit
- max/min annotation ratio: 50.8

## Integrity errors (counts)


## Train / validation split

- overlap counts: `{'train_val_filename': 0, 'train_val_image_id': 0, 'train_test_filename': 0, 'train_test_image_id': 0, 'val_test_filename': 0, 'val_test_image_id': 0}`
- class gaps: `{'in_train_not_val': [], 'in_val_not_train': []}`

## Recommended next experiment (not launched)

- train images: 500
- val images: 100
- epochs: 3
- subset: `class_aware`
- selection: Scan every train/val image that has a file on disk, group by the 15 detector classes, shuffle each group with seed 42, then greedily round-robin from the rarest class so a 500-image CPU subset still contains shirt/skirt/bag/hat/belt/accessories rather than the first 500 JSON rows (which over-represent shoes/dress).

