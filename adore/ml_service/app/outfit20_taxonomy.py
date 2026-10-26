"""20-class Adore outfit detector taxonomy.

Fine-tunes the existing Ultralytics YOLOv8 Fashionpedia detector onto
wardrobe leaves. Fashionpedia part classes (sleeve, zipper, …) are skipped.
"""

from __future__ import annotations

OUTFIT20_CLASSES: tuple[str, ...] = (
    "accessories_bag",
    "accessories_hat",
    "accessories_belt",
    "accessories_scarf",
    "accessories_dupatta",
    "accessories_watch",
    "accessories_hijab",
    "accessories_sunglasses",
    "upperwear_tshirt",
    "upperwear_shirt",
    "upperwear_jacket",
    "lowerwear_trousers",
    "lowerwear_shorts",
    "lowerwear_skirt",
    "footwear_flats",
    "footwear_shoes",
    "footwear_sneakers",
    "footwear_loafers",
    "one_piece_dress",
)

# Fashionpedia (Jia et al., CVPR 2020, CC BY 4.0) -> Adore 20-class id.
# Unlisted source classes are not forced into a leaf.
FASHIONPEDIA_TO_OUTFIT20: dict[str, str] = {
    "bag, wallet": "accessories_bag",
    "hat": "accessories_hat",
    "belt": "accessories_belt",
    "buckle": "accessories_belt",
    "scarf": "accessories_scarf",
    "watch": "accessories_watch",
    "glasses": "accessories_sunglasses",
    "shirt, blouse": "upperwear_shirt",
    "top, t-shirt, sweatshirt": "upperwear_tshirt",
    "jacket": "upperwear_jacket",
    "coat": "upperwear_jacket",
    "cape": "upperwear_jacket",
    "pants": "lowerwear_trousers",
    "shorts": "lowerwear_shorts",
    "skirt": "lowerwear_skirt",
    "dress": "one_piece_dress",
    "jumpsuit": "one_piece_dress",
    "shoe": "footwear_shoes",
}

# Local folder leaf -> outfit20 id. Heels are dress shoes in this 20-class set.
LOCAL_FOLDER_TO_OUTFIT20: dict[str, str] = {
    "bag": "accessories_bag",
    "hat": "accessories_hat",
    "belt": "accessories_belt",
    "scarf": "accessories_scarf",
    "dupatta": "accessories_dupatta",
    "watch": "accessories_watch",
    "hijab": "accessories_hijab",
    "sunglasses": "accessories_sunglasses",
    "glasses": "accessories_sunglasses",
    "tshirt": "upperwear_tshirt",
    "t-shirt": "upperwear_tshirt",
    "shirt": "upperwear_shirt",
    "jacket": "upperwear_jacket",
    "coat": "upperwear_jacket",
    "pants": "lowerwear_trousers",
    "trousers": "lowerwear_trousers",
    "jeans": "lowerwear_trousers",
    "shorts": "lowerwear_shorts",
    "skirt": "lowerwear_skirt",
    "flats": "footwear_flats",
    "shoes": "footwear_shoes",
    "heels": "footwear_shoes",
    "sneakers": "footwear_sneakers",
    "loafers": "footwear_loafers",
    "dress": "one_piece_dress",
    "gown": "one_piece_dress",
    "modest dress": "one_piece_dress",
    "jumpsuit": "one_piece_dress",
    "kaftan": "one_piece_dress",
    "pent": "lowerwear_trousers",
    "pents": "lowerwear_trousers",
    "pant": "lowerwear_trousers",
    "shalwar": "lowerwear_trousers",
    "chinos": "lowerwear_trousers",
    "chino": "lowerwear_trousers",
    "palazzo": "lowerwear_trousers",
    "leggings": "lowerwear_trousers",
    "tee": "upperwear_tshirt",
    "teeshirt": "upperwear_tshirt",
    "t shirt": "upperwear_tshirt",
    "blouse": "upperwear_shirt",
    "top": "upperwear_shirt",
    "blazer": "upperwear_jacket",
}

PARENT: dict[str, str] = {
    "accessories_bag": "accessories",
    "accessories_hat": "accessories",
    "accessories_belt": "accessories",
    "accessories_scarf": "accessories",
    "accessories_dupatta": "accessories",
    "accessories_watch": "accessories",
    "accessories_hijab": "accessories",
    "accessories_sunglasses": "accessories",
    "upperwear_tshirt": "upperwear",
    "upperwear_shirt": "upperwear",
    "upperwear_jacket": "upperwear",
    "lowerwear_trousers": "lowerwear",
    "lowerwear_shorts": "lowerwear",
    "lowerwear_skirt": "lowerwear",
    "footwear_flats": "footwear",
    "footwear_shoes": "footwear",
    "footwear_sneakers": "footwear",
    "footwear_loafers": "footwear",
    "one_piece_dress": "dress",
}

SUBCATEGORY: dict[str, str] = {
    "accessories_bag": "bag",
    "accessories_hat": "hat",
    "accessories_belt": "belt",
    "accessories_scarf": "scarf",
    "accessories_dupatta": "dupatta",
    "accessories_watch": "watch",
    "accessories_hijab": "hijab",
    "accessories_sunglasses": "sunglasses",
    "upperwear_tshirt": "t-shirt",
    "upperwear_shirt": "shirt",
    "upperwear_jacket": "jacket",
    "lowerwear_trousers": "trousers",
    "lowerwear_shorts": "shorts",
    "lowerwear_skirt": "skirt",
    "footwear_flats": "flats",
    "footwear_shoes": "shoes",
    "footwear_sneakers": "sneakers",
    "footwear_loafers": "loafers",
    "one_piece_dress": "dress",
}


def class_id(name: str) -> int:
    return OUTFIT20_CLASSES.index(name)


def resolve_label(raw: str | None) -> str | None:
    """Map a user phrase (pants, pent, tshirt, …) onto an outfit-20 class."""
    if not raw:
        return None
    text = str(raw).strip().lower().replace("_", " ").replace("-", " ")
    text = " ".join(text.split())
    compact = text.replace(" ", "")
    if not text:
        return None
    underscored = text.replace(" ", "_")
    if underscored in OUTFIT20_CLASSES:
        return underscored
    if compact in OUTFIT20_CLASSES:
        return compact
    for src, leaf in LOCAL_FOLDER_TO_OUTFIT20.items():
        alias = src.replace("-", " ").replace("_", " ")
        if text == alias or compact == alias.replace(" ", ""):
            return leaf
    return None


def from_fashionpedia(name: str | None) -> str | None:
    if not name:
        return None
    key = str(name).strip().lower()
    for src, leaf in FASHIONPEDIA_TO_OUTFIT20.items():
        if key == src.lower() or key == leaf:
            return leaf
    return None
