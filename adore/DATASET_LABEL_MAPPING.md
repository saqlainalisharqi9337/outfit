# Dataset Label Mapping

**Milestone 2 of 8 — taxonomy only.**  
**Date:** 2026-09-20  
**Rule:** No dataset merge, no conversion, no training, no inference-code edits.

Machine-readable companion: `ml_service/taxonomy/unified_label_map.json`

---

## 0. How this document was built

Counts below were taken from disk on 2026-09-20 (`D:\fyp project\dataset` and `ml_service/datasets/`). Labels were read from folder names, CSV headers, YAML, and existing mapping modules — not guessed.

Existing mapping files inspected (do not treat them as the new source of truth):

| File | What it maps |
|---|---|
| `ml_service/app/fashionpedia_map.py` | Fashionpedia 46 names → Adore leaves (accessories + hints) |
| `ml_service/app/outfit20_taxonomy.py` | Fashionpedia / local folders → 20 YOLO ids |
| `ml_service/app/clothing_taxonomy.py` | Folder leaf → classifier class |
| `ml_service/prepare_upperwear6_dataset.py` | Grigorev + HF articleType → 6-class folders |
| `ml_service/expand_upperwear6.py` | Secondhand + HF extras → upperwear6 |
| `ml_service/prepare_lowerwear5_dataset.py` | HF / Grigorev → trousers/shorts/skirt/shalwar/leggings |
| `ml_service/prepare_outfit20_dataset.py` | Local folders → synthetic YOLO boxes |
| `DATASET_PLAN.md` | Fashionpedia download still **planning only** |
| `ml_service/OUTFIT20.md` | Fashionpedia YOLO license + 20-class map |

---

## 1. Datasets on disk

### 1.1 Local Adore product set

| Field | Value |
|---|---|
| Name | Adore local classification set |
| Location | `D:\fyp project\dataset` (outside git) |
| Format | Folder labels only (`train/train/{family}/{leaf}/*.jpg`) |
| Boxes | **No** |
| Masks | **No** |
| Attributes | **No** (no colour/pattern columns) |
| Splits | `train/train`, `val/val`, `test/test` plus parallel `*_gate/` trees |
| License | Private FYP product photos |
| Quality | **C** — classification / specialist training. **Not** Mask R-CNN GT. |

**Train / val / test leaf counts (images):**

| Family | Leaf | Train | Val | Test |
|---|---|---:|---:|---:|
| upperwear | shirt | 4567 | 531 | 558 |
| upperwear | tshirt | 5211 | 620 | 654 |
| upperwear | jacket | 3127 | 365 | 406 |
| upperwear | hoodie | **0** | **0** | **0** |
| upperwear | sweater | **0** | **0** | **0** |
| bottomwear | pants | 4932 | 556 | 600 |
| bottomwear | shorts | 4029 | 476 | 508 |
| bottomwear | skirt | 3314 | 398 | 412 |
| bottomwear | jeans | **0** | **0** | **0** |
| one-piece | dress | 3472 | 405 | 422 |
| one-piece | jumpsuit | **0** | **0** | **0** |
| footwear | flats | 3465 | 433 | 434 |
| footwear | heels | 3464 | 433 | 434 |
| footwear | shoes | 2091 | 260 | 261 |
| footwear | sneakers | 3512 | 439 | 440 |
| footwear | loafers | **0** | **0** | **0** |
| accessories | bag | 3184 | 398 | 399 |
| accessories | hat | 2383 | 280 | 293 |

Empty requested leaves on this disk: hoodie, sweater, jeans, jumpsuit, loafers, belt, scarf, dupatta, watch, hijab, sunglasses (those last accessories live in **gate / accessories_open** trees, not in `train/train/accessories`).

**Duplicates:** Gate folders (`shirt_gate`, `bag_gate`, …) reuse the same product photos as rivalry negatives. Same image can appear as `shirt` in the main set and as `other` in `jacket_gate`. Do not union them into one detector set without hash de-duplication (Milestone 3).

**outfit20 conversion note:** `prepare_outfit20_dataset.py` writes a **fake** box `class 0.5 0.5 0.92 0.92` (near-full frame). Confirmed on disk (`accessories_bag_0000.txt`). That is **not** instance annotation.

---

### 1.2 Binary gate datasets

Location: `D:\fyp project\dataset\{bag,hat,watch,dupatta,trousers,skirt,shirt,tshirt,jacket,flats,heels,sneakers,shoes,watch_belt}_gate/`

Format: folder labels (`positive` vs `other` or vs a rival leaf). No boxes/masks.

Quality: **D** for the unified detector (they encode rivalry, not a closed taxonomy). Keep them for the existing specialist baseline only.

Notable extra leaves (useful later as classification C, not as instance GT):

| Gate tree | Positive / extra | Pool images (approx.) |
|---|---|---:|
| `accessories_open` | bag, belt, dupatta, hat, hijab, jewelry, scarf, sunglasses | train hijab 316, dupatta 75, scarf 240, belt 389, sunglasses 365 |
| `dupatta_gate` | dupatta | pool 247 |
| `watch_gate` | watch | pool 700 |
| `skirt_gate` | belt (as rival) | belt pool 906 |

Jewelry is **not** in the target taxonomy → do not add as a detector class.

---

### 1.3 upperwear6 (derived classification)

| Field | Value |
|---|---|
| Location | `ml_service/datasets/upperwear6/{train,val,test}/{class}` |
| Format | Folder labels; includes synthetic `unclear_*` copies |
| Boxes / masks | No |
| Splits | train / val / test |
| Quality | **C** |

On-disk counts after expansion + unclear copies:

| Class | Train | Val | Test |
|---|---:|---:|---:|
| shirt | 1464 | 219 | 219 |
| t-shirt | 1464 | 219 | 219 |
| hoodie | 1544 | 229 | 229 |
| jacket | 1464 | 219 | 219 |
| top | 1544 | 229 | 229 |
| dress | 1464 | 219 | 219 |

**Contamination already in this set:** HF `sweaters` were mapped to **hoodie** in `prepare_upperwear6_dataset.py`. That mapping is **rejected** below. Do not reuse this folder as hoodie GT without filtering those files.

---

### 1.4 lowerwear5 (derived classification)

| Location | `ml_service/datasets/lowerwear5` |
| Format | Folder labels + unclear copies |
| Quality | **C** |

| Class | Train | Val | Test | Notes |
|---|---:|---:|---:|---|
| trousers | 1464 | 219 | 219 | Includes jeans/track pants/palazzos from HF |
| shorts | 1464 | 219 | 219 | |
| skirt | 1464 | 219 | 219 | |
| shalwar | 117 | 18 | 18 | **Severe undercount**; not in target taxonomy |
| leggings | 240 | 39 | 39 | Undercount; not in target taxonomy |

HF `jeans` → trousers here. That is why **jeans is not a learned class**.

---

### 1.5 outfit20 (YOLO fine-tune set)

| Field | Value |
|---|---|
| Location | `ml_service/datasets/outfit20` |
| Format | Ultralytics YOLO: `images/` + `labels/*.txt` + `data.yaml` |
| Boxes | Yes, but **synthetic full-frame** (`0.5 0.5 0.92 0.92`) |
| Masks | **No** |
| Splits | train 1924 / val 365 / test 368 images |
| Quality | **D** for Mask R-CNN. **C** only as a class-name experiment. |

`dataset_build.json` zeros: scarf 0, hijab 0, sunglasses 0, loafers 0; dupatta train 0.

---

### 1.6 Grigorev clothing-dataset

| Field | Value |
|---|---|
| Location | `ml_service/datasets/open_clothing/clothing-dataset-master/` |
| Format | `images.csv` (`image`, `sender_id`, `label`, `kids`) + `images/{id}.jpg` |
| Boxes / masks | **No** |
| Images | 5403 labeled rows (476 kids) |
| License | Free for any purpose including commercial (README) |
| Quality | **C** |

**Actual CSV labels (do not invent others):**

| Original label | Count | Unified keep? |
|---|---:|---|
| T-Shirt | 1011 | YES → t-shirt |
| Longsleeve | 699 | **NO** — shirt or sweater; ambiguous |
| Pants | 692 | YES → trousers (not jeans) |
| Shoes | 431 | YES → shoes (coarse; not sneaker/loafer/flat) |
| Shirt | 378 | YES → shirt |
| Dress | 357 | YES → dress |
| Outwear | 312 | weak YES → jacket (coats mixed in) |
| Shorts | 308 | YES → shorts |
| Not sure | 228 | **NO** |
| Hat | 171 | YES → hat |
| Skirt | 155 | YES → skirt |
| Polo | 120 | YES → shirt (collar) |
| Undershirt | 118 | **NO** |
| Blazer | 109 | YES → jacket |
| Hoodie | 100 | YES → hoodie (classification only; thin) |
| Body | 69 | **NO** (bodysuit / onesie; not jumpsuit with confidence) |
| Other | 67 | **NO** |
| Top | 43 | **NO** — too broad |
| Blouse | 23 | YES → shirt |
| Skip | 12 | **NO** |

No jeans, no loafers, no dupatta, no hijab, no watch, no sunglasses, no sweater class (Longsleeve is not sweater).

---

### 1.7 HuggingFace fashion-product-small (cached crops)

| Location | `ml_service/datasets/open_clothing/fashion_product_small` and `fashion_product_lowerwear` |
| Source | `ashraq/fashion-product-images-small` (Kaggle fashion products) |
| Format | Already **re-foldered** by our importers; original label was `articleType` |
| Boxes / masks | **No** |
| Quality | **C** |

Cached files:

| Folder | Images |
|---|---:|
| hoodie | 685 (includes sweatshirts; **sweater→hoodie contamination**) |
| top | 800 |
| dress | 800 |
| jacket | 559 |
| shirt | 400 |
| t-shirt | 400 |
| trousers | 500 (includes jeans in the lowerwear harvest) |
| shorts | 500 |
| skirt | 128 |
| leggings | 220 |
| shalwar | 107 |

Original Myntra `articleType` values used in code (not all exist as folders): shirts, tshirts, dresses, jackets, tops, sweaters, sweatshirts, hoodies, tunics, kurtas, gowns, blazers, jeans, trousers, shorts, skirts, leggings, salwar, patiala, churidar.

---

### 1.8 Secondhand clothing (cached)

| Location | `ml_service/datasets/open_clothing/secondhand_upperwear` |
| Source | `wargoninnovation/clothingdatasetsecondhand` |
| Format | 224×224, background removed; re-foldered |
| Boxes / masks | **No** (empty background is not a garment mask) |
| Quality | **C** |
| Cached | hoodie 708, top 900, dress 500, jacket 300, shirt 200, t-shirt 200 |

Dataset also has a **Sweater** class that this project **did not save** (correct — do not merge into hoodie). Night gown was saved as dress (acceptable for dress, not for jumpsuit).

---

### 1.9 user_labeled

| Location | `ml_service/datasets/user_labeled/{outfit20_id}/` |
| Format | Folder labels; few files |
| Quality | **C** (tiny: 1–11 images per folder) |

---

## 2. Fashionpedia and DeepFashion2 (not fully downloaded)

### 2.1 Fashionpedia

| Status | **Not present as a local COCO dump.** `DATASET_PLAN.md` still says planning only. |
| Weights on disk | `ml_service/models/yolov8n-fashionpedia-1.torchscript` (boxes only) |
| HF cache | Streamed previously for gate crop harvest; not a complete instance dataset |
| Expected format (when downloaded) | COCO JSON: images + **segmentation polygons/RLE** + bboxes + **294 attributes** |
| License | CC BY 4.0 (Jia et al., CVPR 2020) |
| Size | ~48k images — **do not auto-download in this milestone** |
| Quality when downloaded | **A** — primary Mask R-CNN source |

**Official 46 detection names** (from `fashionpedia_map.py`, matching HF ClassLabel order). Apparel objects vs parts:

**Apparel (candidate instances):**  
shirt, blouse · top, t-shirt, sweatshirt · sweater · cardigan · jacket · vest · pants · shorts · skirt · coat · dress · jumpsuit · cape · glasses · hat · headband, head covering, hair accessory · tie · glove · watch · belt · leg warmer · tights, stockings · sock · shoe · bag, wallet · scarf · umbrella

**Parts (never clothing classes):**  
hood, collar, lapel, epaulette, sleeve, pocket, neckline, buckle, zipper, applique, bead, bow, flower, fringe, ribbon, rivet, ruffle, sequin, tassel

**Milestone 3 preparation (later):** download `detection-datasets/fashionpedia` or the official release; keep polygons; drop part categories; map apparel via the table in §5; use attributes for colour/pattern **not** as extra classes.

### 2.2 DeepFashion2

| Status | **Not downloaded. Not in HF cache as a training dump.** |
| Expected format | Per-item bbox, landmarks, **per-pixel mask**, occlusion/zoom attributes |
| License | Academic research (check CUHK download terms before M3) |
| Quality | **B** for garments only |

**Official 13 categories (do not invent more):**

1. short sleeve top  
2. long sleeve top  
3. short sleeve outwear  
4. long sleeve outwear  
5. vest  
6. sling  
7. shorts  
8. trousers  
9. skirt  
10. short sleeve dress  
11. long sleeve dress  
12. vest dress  
13. sling dress  

**Missing vs target:** all accessories, all footwear, hoodie, sweater (as named), jeans, t-shirt vs shirt (tops are sleeve-length, not collar type), jumpsuit.

DeepFashion2 is why bags became skirts historically — **do not use it to train accessory classes**.

---

## 3. Unified application taxonomy

Target families (product):

| Category | Subcategories |
|---|---|
| upperwear | t-shirt, shirt, hoodie, jacket, sweater |
| lowerwear | trousers, jeans, shorts, skirt |
| one-piece | dress, jumpsuit |
| footwear | shoes, sneakers, loafers, flats |
| accessories | bag, hat, belt, scarf, dupatta, watch, hijab, sunglasses |

Flutter currently uses `ClothingCategory.dress` instead of `one-piece`. Milestone 7 can alias `one-piece` ↔ `dress` in the API without renaming stored wardrobe rows. **Heels** stay a Flutter/specialist leaf; they are **not** in this detector taxonomy.

---

## 4. Semantic distinctions (do not collapse)

| Pair | Decision | Why |
|---|---|---|
| **Dress vs skirt** | Keep both | Fashionpedia has both. Dress = one-piece torso+skirt; skirt = lowerwear only. Local counts support both. |
| **Bag vs hat** | Keep both | Different Fashionpedia classes. Do not train on DeepFashion2 for either. |
| **Bag vs clothing** | Keep bag | Requires instance masks. Folder-level product photos of totes look like skirts — classification C only. |
| **Trousers vs shirt** | Keep both | Different families. Interference today is a **router** bug, not a label-map problem. |
| **T-shirt vs shirt** | Keep both **if** we refuse mixed sources | Fashionpedia class `top, t-shirt, sweatshirt` mixes tees and sweatshirts → **do not map that class to t-shirt**. Local `tshirt` vs `shirt` folders are usable for classification. |
| **Hoodie vs sweater** | Keep both; **do not merge** | Fashionpedia has `sweater` and **no hoodie**. HF `sweaters`→hoodie in upperwear6 is **wrong**. |
| **Shoes vs sneakers vs loafers vs flats** | Fashionpedia has one class `shoe` | Instance model: one **shoes** class. Subtypes = second-stage classifier on the shoe mask (existing footwear4). Loafers have **zero** local images. |
| **Hijab vs scarf** | Keep both if we get instance labels | Fashionpedia `headband, head covering, hair accessory` is a mix (headband/hijab/hair clip) → **NO** as hijab. `scarf` is a separate class. accessories_open has hijab **crops** (C). |
| **Dupatta vs scarf** | Keep both; do not map scarf→dupatta | Current `HINT_FROM_FASHIONPEDIA` maps scarf→dupatta. That is **rejected**. Dupatta is South-Asian drape; scarf is neck accessory. Dupatta instance masks: **DATA REQUIRED**. |
| **Jeans vs trousers** | Keep as product leaves; instance jeans **DATA REQUIRED** | No instance dataset names jeans. HF jeans were folded into trousers. |
| **Jumpsuit vs dress** | Keep both | Fashionpedia has `jumpsuit`. Current outfit20 map jumpsuit→dress is **rejected**. |
| **Jacket vs coat** | Map coat → jacket | Target has no coat. Silhouette overlap is acceptable for one outerwear class. Cape/vest: **NO**. |
| **Blouse vs shirt** | Map blouse → shirt | Collared/buttoned upper; target has no blouse. |
| **Top** | **NO** | Ambiguous (crop, tank, tunic, kurti). Not in the target list. |
| **Heels** | Out of detector taxonomy | Strong local classification data; keep specialist. Do not dump into `shoes` GT. |

---

## 5. Mapping tables

Keep? **YES** = use in Milestone 3 conversion. **NO** = exclude. **AUX** = classification specialist only, not Mask R-CNN GT.

### 5.1 Fashionpedia (expected; dataset not on disk)

| Dataset | Original Label | Unified Category | Unified Subcategory | Keep? | Reason |
|---|---|---|---|---|---|
| Fashionpedia | shirt, blouse | upperwear | shirt | YES | Direct collared/blouse match |
| Fashionpedia | top, t-shirt, sweatshirt | — | — | NO | Mixes t-shirt, crop top, and sweatshirt |
| Fashionpedia | sweater | upperwear | sweater | YES | Direct named class |
| Fashionpedia | cardigan | — | — | NO | Not in target; looks like sweater/jacket |
| Fashionpedia | jacket | upperwear | jacket | YES | Direct match |
| Fashionpedia | coat | upperwear | jacket | YES | Outerwear; target has no coat |
| Fashionpedia | vest | — | — | NO | Not in target |
| Fashionpedia | cape | — | — | NO | Rare / not jacket |
| Fashionpedia | pants | lowerwear | trousers | YES | Direct; not jeans |
| Fashionpedia | shorts | lowerwear | shorts | YES | Direct match |
| Fashionpedia | skirt | lowerwear | skirt | YES | Direct match; keep distinct from dress |
| Fashionpedia | dress | one-piece | dress | YES | Direct match |
| Fashionpedia | jumpsuit | one-piece | jumpsuit | YES | Direct match; do not fold into dress |
| Fashionpedia | shoe | footwear | shoes | YES | Coarse footwear instance only |
| Fashionpedia | bag, wallet | accessories | bag | YES | Direct match |
| Fashionpedia | hat | accessories | hat | YES | Direct match |
| Fashionpedia | belt | accessories | belt | YES | Direct match |
| Fashionpedia | buckle | — | — | NO | Part, not a garment |
| Fashionpedia | scarf | accessories | scarf | YES | Direct; **not** dupatta |
| Fashionpedia | watch | accessories | watch | YES | Direct match |
| Fashionpedia | glasses | accessories | sunglasses | YES | Closest optical accessory |
| Fashionpedia | headband, head covering, hair accessory | — | — | NO | Mix of headband / hijab / hair clip |
| Fashionpedia | tie | — | — | NO | Jewelry-like; not in target |
| Fashionpedia | glove, sock, leg warmer, tights, stockings, umbrella | — | — | NO | Out of taxonomy |
| Fashionpedia | hood, collar, sleeve, zipper, … (all parts) | — | — | NO | Parts, not instances of clothing type |

### 5.2 DeepFashion2 (expected; not on disk)

| Dataset | Original Label | Unified Category | Unified Subcategory | Keep? | Reason |
|---|---|---|---|---|---|
| DeepFashion2 | short sleeve top | — | — | NO | Not shirt vs t-shirt |
| DeepFashion2 | long sleeve top | — | — | NO | Same ambiguity |
| DeepFashion2 | short/long sleeve outwear | upperwear | jacket | AUX | Weak; prefer Fashionpedia jacket |
| DeepFashion2 | vest | — | — | NO | Not in target |
| DeepFashion2 | sling | — | — | NO | Not in target |
| DeepFashion2 | shorts | lowerwear | shorts | YES | Direct (if downloaded) |
| DeepFashion2 | trousers | lowerwear | trousers | YES | Direct; not jeans |
| DeepFashion2 | skirt | lowerwear | skirt | YES | Direct |
| DeepFashion2 | * dress (all four) | one-piece | dress | YES | Sleeve variants are attributes |
| DeepFashion2 | *(no bag/hat/shoe)* | — | — | NO | Dataset does not contain these labels |

### 5.3 Local Adore folders

| Dataset | Original Label | Unified Category | Unified Subcategory | Keep? | Reason |
|---|---|---|---|---|---|
| Local | upperwear/shirt | upperwear | shirt | AUX | Classification; no mask |
| Local | upperwear/tshirt | upperwear | t-shirt | AUX | Classification; no mask |
| Local | upperwear/jacket | upperwear | jacket | AUX | Classification; no mask |
| Local | bottomwear/pants | lowerwear | trousers | AUX | Folder is pants, not jeans |
| Local | bottomwear/shorts | lowerwear | shorts | AUX | Classification |
| Local | bottomwear/skirt | lowerwear | skirt | AUX | Classification |
| Local | one-piece/dress | one-piece | dress | AUX | Classification |
| Local | footwear/shoes | footwear | shoes | AUX | Classification |
| Local | footwear/sneakers | footwear | sneakers | AUX | Classification |
| Local | footwear/flats | footwear | flats | AUX | Classification |
| Local | footwear/heels | — | — | AUX | Not in detector taxonomy; keep specialist |
| Local | accessories/bag | accessories | bag | AUX | Classification |
| Local | accessories/hat | accessories | hat | AUX | Classification |
| accessories_open | belt | accessories | belt | AUX | Crops |
| accessories_open | scarf | accessories | scarf | AUX | Crops |
| accessories_open | dupatta | accessories | dupatta | AUX | Crops; thin |
| accessories_open | hijab | accessories | hijab | AUX | Crops; not instance |
| accessories_open | sunglasses | accessories | sunglasses | AUX | Crops |
| accessories_open | jewelry | — | — | NO | Not in target |
| Gate `*/other` | other | — | — | NO | Rivalry dump |
| outfit20 labels | `0.5 0.5 0.92 0.92` | — | — | NO | Fake boxes; not instances |

### 5.4 Grigorev

| Dataset | Original Label | Unified Category | Unified Subcategory | Keep? | Reason |
|---|---|---|---|---|---|
| Grigorev | T-Shirt | upperwear | t-shirt | AUX | Direct |
| Grigorev | Shirt | upperwear | shirt | AUX | Direct |
| Grigorev | Polo | upperwear | shirt | AUX | Collar |
| Grigorev | Blouse | upperwear | shirt | AUX | Equivalent |
| Grigorev | Hoodie | upperwear | hoodie | AUX | Direct; only 100 images |
| Grigorev | Blazer | upperwear | jacket | AUX | Outerwear |
| Grigorev | Outwear | upperwear | jacket | AUX | Weak mix of coats |
| Grigorev | Pants | lowerwear | trousers | AUX | Direct |
| Grigorev | Shorts | lowerwear | shorts | AUX | Direct |
| Grigorev | Skirt | lowerwear | skirt | AUX | Direct |
| Grigorev | Dress | one-piece | dress | AUX | Direct |
| Grigorev | Shoes | footwear | shoes | AUX | Coarse |
| Grigorev | Hat | accessories | hat | AUX | Direct |
| Grigorev | Top | — | — | NO | Ambiguous |
| Grigorev | Longsleeve | — | — | NO | Shirt vs sweater |
| Grigorev | Undershirt / Body / Other / Not sure / Skip | — | — | NO | Junk or underwear |

### 5.5 HF fashion-product / secondhand (articleType)

| Dataset | Original Label | Unified Category | Unified Subcategory | Keep? | Reason |
|---|---|---|---|---|---|
| HF fashion-product | tshirts | upperwear | t-shirt | AUX | Direct |
| HF fashion-product | shirts | upperwear | shirt | AUX | Direct |
| HF fashion-product | jackets / blazers / rain jacket / sports jackets / nehru jackets | upperwear | jacket | AUX | Outerwear |
| HF fashion-product | hoodies | upperwear | hoodie | AUX | Direct if present |
| HF fashion-product | sweatshirts | upperwear | hoodie | AUX | Kangaroo/crew sweatshirt ≈ hoodie family **only if hooded**; else NO — treat as hoodie only when filename/source is hoodies |
| HF fashion-product | sweaters | upperwear | sweater | YES* | *Must **not** map to hoodie (old importer was wrong) |
| HF fashion-product | dresses / gowns | one-piece | dress | AUX | Gown = long dress |
| HF fashion-product | jeans | lowerwear | jeans | AUX | Named jeans; still no boxes |
| HF fashion-product | trousers / track pants | lowerwear | trousers | AUX | Direct |
| HF fashion-product | shorts | lowerwear | shorts | AUX | Direct |
| HF fashion-product | skirts | lowerwear | skirt | AUX | Direct |
| HF fashion-product | tops / tunics / kurtis / shrugs | — | — | NO | Ambiguous “top” |
| HF fashion-product | kurtas | — | — | NO | Not in target (kurta ≠ shirt) |
| HF fashion-product | kurta sets | — | — | NO | Often two-piece |
| HF fashion-product | salwar / patiala / churidar | — | — | NO | Not in target |
| HF fashion-product | dupatta | accessories | dupatta | AUX | If harvested as itself, not discarded |
| Secondhand | Hoodie | upperwear | hoodie | AUX | Direct |
| Secondhand | Sweater | upperwear | sweater | AUX | Direct; was skipped (good) |
| Secondhand | T-shirt / Shirt / Jacket / Dress | (same) | (same) | AUX | Direct |
| Secondhand | Night gown / Nightgown | one-piece | dress | AUX | Dress-length; not jumpsuit |
| Secondhand | Top / Tank / Tunic / Blouse | — | — | NO | Top/tank/tunic ambiguous; blouse→shirt only if isolated |

---

## 6. Category vs attributes (colour / pattern)

These must **never** become detector classes:

- red shirt, blue shirt, black shirt  
- striped shirt, floral shirt, checked shirt  
- red-black shirt, graphic tee  

**Instance class** = garment type only (`shirt`, `bag`, …).

**Attributes** (per instance, after the mask exists):

```json
{
  "category": "upperwear",
  "subcategory": "shirt",
  "colors": ["black", "red"],
  "pattern": "striped"
}
```

Existing colour stack to reuse in Milestone 6: `color_analysis.py` (CIE Lab K-Means, not brightest pixel). Future payload:

```json
"colors": [
  { "name": "black", "hex": "#161616", "share": 0.62 },
  { "name": "red", "hex": "#c42028", "share": 0.24 }
]
```

Drop clusters below ~4% share (logos/buttons). Do not return only the brightest cluster.

**Allowed colour names** (Flutter catalog + Lab palette, mapped):  
black, white, grey, red, blue, green, yellow, orange, brown, beige, pink, purple, navy, maroon, cream, olive, gold, teal  
(internal Lab extras `dark_red`→maroon, `dark_green`→olive, `light_blue`→blue, `silver`→grey)

**Allowed patterns** (detector must not classify these as types):

| Pattern | Source later |
|---|---|
| solid | K-Means: one dominant cluster |
| striped | spatial row/col transitions |
| checked | both axes high transition |
| floral | many small non-primary components |
| printed | ≥3 colour clusters, not striped/checked |
| dotted | **not implemented**; add when we have attribute labels |
| geometric | **not implemented**; Fashionpedia attributes if downloaded |

Flutter also stores `multicolor`, `gradient`, `patterned`, `polka dot`, `graphic`, `embroidered` as **user-selectable** tags. Those stay UI attributes, not classes.

Fashionpedia **attributes** (294) should be parsed in Milestone 3/6 for colour/texture when the JSON is downloaded. Until then, attributes come from pixels on the mask, not from folder names like `red_floral_dress/`.

---

## 7. Dataset quality grades

| Dataset | Grade | Why |
|---|---|---|
| Fashionpedia (full COCO, **to download**) | **A** | Instance masks + boxes + attributes; accessories and shoes exist |
| DeepFashion2 (**to download if license OK**) | **B** | Masks for garments only; no bag/hat/shoe; top classes are not shirt/t-shirt |
| Local Adore folders | **C** | Strong classification volume; no masks; empty hoodie/sweater/jeans/loafers |
| Grigorev | **C** | Clean single-item photos; no boxes; Longsleeve/Top junk |
| HF fashion-product / secondhand | **C** | Shop crops; no boxes; sweater/hoodie contamination risk |
| accessories_open / Wikimedia crops | **C** | Useful hijab/dupatta/scarf **classification** |
| upperwear6 / lowerwear5 | **C** | Derived; unclear copies; some wrong maps |
| user_labeled | **C** | Too few images |
| outfit20 YOLO labels | **D** | Fake full-frame boxes |
| Binary `*_gate` trees | **D** | Rivalry `other` class; duplicates |
| DeepFashion2 for accessories | **D** | Labels do not exist |

**Mask R-CNN GT must be grade A (Fashionpedia), optionally B (DeepFashion2 garments).** Do not train Mask R-CNN on C/D folder labels.

---

## 8. Class balance (approximate, where counted)

**Severe underrepresentation (instance-ready = no):**

| Class | What exists | Gap |
|---|---|---|
| hoodie | 100 Grigorev + 708 secondhand + 685 HF (contaminated with sweaters) | No instance masks; local folder empty |
| sweater | Fashionpedia class (not downloaded); HF sweaters exist | Local folder empty; must un-merge from hoodie |
| jeans | HF articleType only (folded into trousers) | No instance name; local folder empty |
| jumpsuit | Fashionpedia class only | Local folder empty |
| loafers | **0 images** on disk | DATA REQUIRED |
| dupatta | accessories_open train 75; gate pool 247 | No instance masks |
| hijab | accessories_open train 316 | Mixed FP head-covering class; no clean instance GT |
| t-shirt (instance) | Local 5211 classification images | Fashionpedia class is mixed with sweatshirt |
| sneakers / flats | Strong **classification** counts (~3.5k train each) | Fashionpedia only `shoe` |

**Healthy classification volume (still no masks):** shirt, t-shirt, jacket, trousers/pants, shorts, skirt, dress, bag, hat, shoes, sneakers, flats.

---

## 9. Final class list for Milestone 3

Two lists. Milestone 3 must **not** dump postponed classes into Mask R-CNN GT.

### 9.1 Detector classes (instance GT plan = Fashionpedia)

Use these **15** names as the Mask R-CNN vocabulary once Fashionpedia is downloaded and converted:

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

### 9.2 Target product leaves that are **DATA REQUIRED** for the instance model

Keep them in the **app taxonomy** and in **specialists / classification AUX**. Do not add to Mask R-CNN until real boxes+masks exist.

16. t-shirt — DATA REQUIRED (need instance labels that are not mixed with sweatshirt)  
17. hoodie — DATA REQUIRED (no Fashionpedia class; local folder empty)  
18. jeans — DATA REQUIRED (no instance dataset names jeans)  
19. sneakers — DATA REQUIRED (subtype of `shoe` mask; use footwear specialist until then)  
20. loafers — DATA REQUIRED (zero images)  
21. flats — DATA REQUIRED (same as sneakers)  
22. dupatta — DATA REQUIRED (no Fashionpedia class)  
23. hijab — DATA REQUIRED (FP head-covering is mixed)

**Explicitly excluded from the detector (not postponed, rejected):**  
top, blouse-as-its-own-class, coat-as-its-own-class, cape, vest, cardigan, heels, jewelry, shalwar, leggings, kurta, longsleeve, unknown_top, garment parts, colour/pattern as classes.

Heels remain a **Flutter + heels_gate** leaf only.

---

## 10. Recommended datasets for Milestone 3 (conversion, not merge-now)

1. **Download Fashionpedia** (COCO instance) — primary GT. Map with §5.1. Drop parts.  
2. **Optional DeepFashion2** — garment masks only, §5.2. Never for bag/hat/shoe.  
3. **Do not** convert outfit20 synthetic YOLO labels into Mask R-CNN.  
4. **Do not** mix gate `other` folders into GT.  
5. Keep local/Grigorev/HF as **AUX classification** for specialists and for a future t-shirt/hoodie/jeans campaign.  
6. Fix the known bad map before any reuse of upperwear6 hoodie: HF `sweaters` must be sweater or dropped.

Annotation conversion required later (not this milestone):

- Fashionpedia COCO polygons → MMDetection COCO (`category_id` remapped to the 15-class list)  
- Attribute JSON → `colors[]` / `pattern` (not extra classes)  
- Train/val/test **by image id** (Fashionpedia official splits) to avoid leakage  
- Hash-dedupe if any local image is added as AUX

---

## 11. Labels rejected (summary)

Fashionpedia parts; `top, t-shirt, sweatshirt` as t-shirt; headband mix as hijab; scarf as dupatta; jumpsuit as dress; sweater as hoodie; jeans as trousers **for the jeans class**; Longsleeve; Top; Not sure; Skip; Other; Body; Undershirt; vest; cape; cardigan; buckle as belt; DeepFashion2 tops as shirt/t-shirt; kurta; tank/tunic as shirt; jewelry; gate `other`; fake YOLO full-frame boxes.

---

## 12. Milestone 2 exit

- Datasets inspected: local Adore, 14 gate trees, accessories_open, upperwear6, lowerwear5, outfit20, Grigorev, HF fashion-product caches, secondhand cache, user_labeled; Fashionpedia/DeepFashion2 **schemas** without downloading.  
- No datasets merged or converted.  
- No model trained.  
- No production inference file modified.
