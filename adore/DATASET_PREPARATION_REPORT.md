# Dataset Preparation Report

**Milestone 3 of 8 — dataset conversion and validation only.**
**Date:** 2026-09-20T20:37:15Z
**Rule:** No Mask R-CNN training. No production inference edits.

---

## 1. Dataset sources

### Used

- **Fashionpedia** (2020 (CVDF / iFashionist release))
  - License: CC BY 4.0
  - Paper: Jia et al., ECCV 2020
  - Official images: 46781 (train 45623, val 1158, public test labels: none)
  - Annotation format: COCO instances + polygons/RLE + attributes
  - Destination of raw files: `ml_service/datasets/sources/fashionpedia/`
  - Converted dataset: `ml_service/datasets/clothing_detection/`

### Documented but not used

- **outfit20**: synthetic full-frame boxes (0.5 0.5 0.92 0.92)
- **binary_gates**: rivalry other/positive folders, no instance GT
- **local_adore_folders**: classification labels only
- **grigorev**: no boxes/masks
- **hf_fashion_product**: shop crops, no instance GT
- **secondhand**: background-removed crops, not garment masks
- **upperwear6_lowerwear5**: derived classification sets
- **deepfashion2**: academic non-commercial license; form+password required; not on disk; tops are not shirt/t-shirt

## 2–3. Versions and licenses

| Dataset | Version | License | Used? |
|---|---|---|---|
| Fashionpedia | 2020 CVDF/iFashionist | CC BY 4.0 | YES |
| DeepFashion2 | CVPR 2019 | Academic non-commercial; password form; no commercial license | NO |
| Local Adore / gates / outfit20 / Grigorev / HF crops | on-disk classification | mixed / private | NO as detector GT |

Fashionpedia attribution: Jia et al., *Fashionpedia: Ontology, Segmentation, and an Attribute Localization Dataset*, ECCV 2020.

## 4–7. Images and annotations processed

- Source images in JSON: **46781**
- Source annotations in JSON: **342182**
- Kept images: **44260**
- Kept instances: **134852**
- Images copied from zip/source: **44260**
- Missing image files after copy: **0**

### QC exclusion counts (annotations unless noted)

| Reason | Count |
|---|---:|
| rejected_taxonomy | 207314 |
| kept | 134852 |
| tiny_kept_flagged | 5754 |
| images_dropped_no_kept_instance | 2521 |
| degenerate_tiny_dropped | 15 |
| invalid_or_zero_bbox | 1 |

### Source classes kept (after mapping)

| Fashionpedia class | Instances kept |
|---|---:|
| shoe | 47929 |
| dress | 19247 |
| pants | 12728 |
| jacket | 8016 |
| bag, wallet | 7431 |
| belt | 7011 |
| shirt, blouse | 6263 |
| skirt | 5208 |
| glasses | 4985 |
| watch | 3472 |
| coat | 3228 |
| shorts | 2862 |
| hat | 2592 |
| sweater | 1515 |
| scarf | 1422 |
| jumpsuit | 943 |

### Ambiguous / DATA REQUIRED labels excluded (not remapped)

| Fashionpedia class | Instances excluded | Why |
|---|---:|---|
| top, t-shirt, sweatshirt | 17025 | mixed t-shirt/sweatshirt; not mapped to shirt |
| cardigan | 1119 | not sweater or hoodie |
| vest | 741 | not jacket or shirt |
| cape | 157 | not jacket |
| headband, head covering, hair accessory | 3579 | not hat, hijab, or dupatta |

Ambiguous labels excluded: **22621**
Garment-part / other non-detector classes excluded: **184693**

### Other excluded Fashionpedia classes (parts and out-of-vocab garments)

| Fashionpedia class | Instances excluded |
|---|---:|
| sleeve | 60890 |
| neckline | 35187 |
| pocket | 27720 |
| collar | 10377 |
| zipper | 8185 |
| lapel | 6107 |
| bead | 5191 |
| rivet | 5036 |
| tights, stockings | 4448 |
| applique | 3590 |
| buckle | 3367 |
| sock | 2669 |
| ruffle | 2483 |
| tie | 1460 |
| glove | 1416 |
| flower | 1404 |
| hood | 1258 |
| sequin | 942 |
| epaulette | 888 |
| fringe | 618 |
| bow | 534 |
| tassel | 374 |
| ribbon | 283 |
| umbrella | 140 |
| leg warmer | 126 |

## 8. Final detector classes

1. shirt
2. jacket
3. sweater
4. trousers
5. shorts
6. skirt
7. dress
8. jumpsuit
9. shoes
10. bag
11. hat
12. belt
13. scarf
14. watch
15. sunglasses

DATA REQUIRED (excluded from this detector dataset): t-shirt, hoodie, jeans, sneakers, loafers, flats, dupatta, hijab

## 9. Instances per class

| Class | Images | Instances | % of instances | train inst | val inst | test inst |
|---|---:|---:|---:|---:|---:|---:|
| shirt | 6217 | 6263 | 4.644 | 5397 | 102 | 764 |
| jacket | 11041 | 11244 | 8.338 | 9581 | 287 | 1376 |
| sweater | 1506 | 1515 | 1.123 | 1295 | 21 | 199 |
| trousers | 12660 | 12728 | 9.438 | 10939 | 314 | 1475 |
| shorts | 2851 | 2862 | 2.122 | 2417 | 106 | 339 |
| skirt | 5196 | 5208 | 3.862 | 4419 | 162 | 627 |
| dress | 19172 | 19247 | 14.273 | 16481 | 508 | 2258 |
| jumpsuit | 943 | 943 | 0.699 | 809 | 21 | 113 |
| shoes | 24757 | 47929 | 35.542 | 40775 | 1565 | 5589 |
| bag | 7112 | 7431 | 5.51 | 6372 | 214 | 845 |
| hat | 2588 | 2592 | 1.922 | 2210 | 74 | 308 |
| belt | 6823 | 7011 | 5.199 | 6031 | 164 | 816 |
| scarf | 1410 | 1422 | 1.054 | 1216 | 48 | 158 |
| watch | 3454 | 3472 | 2.575 | 3002 | 84 | 386 |
| sunglasses | 4978 | 4985 | 3.697 | 4271 | 130 | 584 |

## 10. Train / validation / test counts

| Split | Images | Instances | Origin |
|---|---:|---:|---|
| train | 37887 | 115215 | official Fashionpedia train minus test holdout |
| val | 1146 | 3800 | official Fashionpedia val (not reshuffled) |
| test | 5227 | 15837 | deterministic 12% holdout of official train image ids |

Reason for a train holdout: Fashionpedia does not publish test-set instance labels. Official val is kept intact. Holdout uses MD5(`adore-milestone3-fashionpedia-test-holdout:{image_id}`).

## 11. Duplicate detection

- Exact filename collisions: 0
- Perceptual near-duplicates across splits: 0
- Duplicates removed: 0

## 12. Invalid annotation results

See the QC table above. Problematic rows were **reported and excluded**, not silently rewritten into fake boxes.

- Invalid or zero-area boxes dropped: 1
- Degenerate tiny objects dropped: 15
- Tiny objects kept but flagged: 5754
- Images dropped because every instance was excluded: 2521


## 13. Difficult-class statistics

| Class | Images | Instances | % |
|---|---:|---:|---:|
| dress | 19172 | 19247 | 14.273 |
| skirt | 5196 | 5208 | 3.862 |
| bag | 7112 | 7431 | 5.51 |
| trousers | 12660 | 12728 | 9.438 |
| shirt | 6217 | 6263 | 4.644 |
| jacket | 11041 | 11244 | 8.338 |
| sweater | 1506 | 1515 | 1.123 |
| shoes | 24757 | 47929 | 35.542 |

Underrepresented (<200 instances): none at that threshold
Dominant classes: shoes (47929), dress (19247), trousers (12728)

## 14. Missing-data classes

Not in this instance dataset (DATA REQUIRED):

- t-shirt
- hoodie
- jeans
- sneakers
- loafers
- flats
- dupatta
- hijab

## 15. Visualization results

Preview directory: `D:\fyp project\adore\evaluation_results\dataset_preview`
Preview files written: 0

Scenes: normal outfit, multiple items, dress, skirt, bag, trousers, upperwear, footwear, accessories.
Current previews are **geometry-only** when pixels are not copied (`--annotations-only`).
They still show genuine instance masks/boxes: dress ≠ skirt, bag ≠ clothing, shoes as two instances.

Open those images before Milestone 4. If a box covers the whole person as one garment, do not train.

## 16. Known limitations

- HuggingFace `detection-datasets/fashionpedia` was **not** used as GT: it has Pascal VOC boxes and **no masks**.
- Official Fashionpedia val is small (~1.1k images). That split was kept official rather than inflating it.
- `top, t-shirt, sweatshirt` is excluded, so t-shirt is DATA REQUIRED.
- Footwear is a single `shoes` class; sneakers/loafers/flats stay on specialists.
- `glasses` maps to `sunglasses` (closest optical accessory); some eyeglasses will be labelled sunglasses.
- `coat` maps to `jacket`. Cape/vest/cardigan excluded.
- Attributes (colour/pattern) are not classes; Fashionpedia `attribute_ids` are not expanded here.
- Real-world Flutter photos are **not** in this training set. See `ml_service/datasets/clothing_detection/real_world_test/PLAN.md`.
- DeepFashion2 was not mixed in (license + ambiguous tops + no accessories).

## Reproducibility

```text
cd ml_service
.\.venv\Scripts\python.exe -m training.prepare_detection_dataset --download
.\.venv\Scripts\python.exe -m training.visualize_detection_dataset
```

No model was trained. Production inference was not modified.

