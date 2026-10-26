"""Fashionpedia category names -> Adore wardrobe leaves.

DeepFashion2 has 13 garment classes and **no accessories**, which is why a
bag became a skirt and a cap became a dress. Fashionpedia (Jia et al.,
CVPR 2020) labels glasses, hat, belt, bag, scarf and related items.

Index order matches the official 46-class Fashionpedia detection ontology
and the Hugging Face ``detection-datasets/fashionpedia`` ClassLabel list.
Garment *parts* (sleeve, zipper, …) are ignored so they cannot steal a
bag or hat box.
"""

from __future__ import annotations

FASHIONPEDIA_NAMES: tuple[str, ...] = (
    "shirt, blouse",
    "top, t-shirt, sweatshirt",
    "sweater",
    "cardigan",
    "jacket",
    "vest",
    "pants",
    "shorts",
    "skirt",
    "coat",
    "dress",
    "jumpsuit",
    "cape",
    "glasses",
    "hat",
    "headband, head covering, hair accessory",
    "tie",
    "glove",
    "watch",
    "belt",
    "leg warmer",
    "tights, stockings",
    "sock",
    "shoe",
    "bag, wallet",
    "scarf",
    "umbrella",
    "hood",
    "collar",
    "lapel",
    "epaulette",
    "sleeve",
    "pocket",
    "neckline",
    "buckle",
    "zipper",
    "applique",
    "bead",
    "bow",
    "flower",
    "fringe",
    "ribbon",
    "rivet",
    "ruffle",
    "sequin",
    "tassel",
)

# Detector may emit these leaves. Clothing/shoes stay on existing specialists
# so trousers/sneakers are not retrained.
ACCESSORY_FROM_FASHIONPEDIA: dict[str, str] = {
    "glasses": "sunglasses",
    "hat": "hat",
    "headband, head covering, hair accessory": "hat",
    "belt": "belt",
    "bag, wallet": "bag",
    "scarf": "scarf",
    "watch": "watch",
    "tie": "jewelry",
    "buckle": "belt",
}

# Allowed wardrobe labels when confirming a Fashionpedia accessory box.
ALLOWED_FROM_FASHIONPEDIA: dict[str, frozenset[str]] = {
    "glasses": frozenset({"sunglasses"}),
    "hat": frozenset({"hat"}),
    "headband, head covering, hair accessory": frozenset({"hat", "hijab"}),
    "belt": frozenset({"belt"}),
    "bag, wallet": frozenset({"bag"}),
    "scarf": frozenset({"scarf", "dupatta"}),
    "watch": frozenset({"jewelry", "watch"}),
    "tie": frozenset({"jewelry"}),
    "buckle": frozenset({"belt"}),
}

# Crops used to train the accessory classifier (Fashionpedia source name -> leaf).
TRAIN_CROP_FROM_FASHIONPEDIA: dict[str, str] = {
    "glasses": "sunglasses",
    "hat": "hat",
    "headband, head covering, hair accessory": "hijab",
    "belt": "belt",
    "bag, wallet": "bag",
    "scarf": "scarf",
    "watch": "jewelry",
    "tie": "jewelry",
}

ACCESSORY_LEAVES: tuple[str, ...] = (
    "bag",
    "belt",
    "scarf",
    "dupatta",
    "hat",
    "hijab",
    "jewelry",
    "sunglasses",
)


def name_for_index(index: int, model_names: dict | None = None) -> str:
    """Resolve a YOLO class index to a Fashionpedia category string."""
    if 0 <= index < len(FASHIONPEDIA_NAMES):
        mapped = FASHIONPEDIA_NAMES[index]
        # TorchScript exports sometimes keep numeric names; prefer ontology.
        if model_names:
            raw = str(model_names.get(index, mapped))
            if raw in ACCESSORY_FROM_FASHIONPEDIA or raw in TRAIN_CROP_FROM_FASHIONPEDIA:
                return raw
        return mapped
    if model_names:
        return str(model_names.get(index, index))
    return str(index)


def accessory_leaf(category: str | int | None) -> str | None:
    if category is None:
        return None
    if isinstance(category, int):
        category = name_for_index(category)
    key = str(category).strip().lower()
    for src, leaf in ACCESSORY_FROM_FASHIONPEDIA.items():
        if key == src.lower() or key == leaf:
            return leaf
    if key in ACCESSORY_LEAVES:
        return key
    return None


# Single-item wardrobe hints from the open-source Fashionpedia ontology
# (Jia et al., CVPR 2020). Pants are omitted on purpose so trousers_gate
# routing is not rewritten by the detector.
HINT_FROM_FASHIONPEDIA: dict[str, str] = {
    "dress": "dress",
    "jumpsuit": "dress",
    "shorts": "shorts",
    "skirt": "skirt",
    "hat": "hat",
    "headband, head covering, hair accessory": "hat",
    "belt": "belt",
    "watch": "watch",
    "bag, wallet": "bag",
    "scarf": "dupatta",
    "shoe": "shoes",
    "shirt, blouse": "shirt",
    "top, t-shirt, sweatshirt": "t-shirt",
    "jacket": "jacket",
    "coat": "jacket",
}


def hint_leaf(category: str | int | None) -> str | None:
    """Map a Fashionpedia class to an Adore leaf for routing hints."""
    if category is None:
        return None
    if isinstance(category, int):
        category = name_for_index(category)
    key = str(category).strip().lower()
    for src, leaf in HINT_FROM_FASHIONPEDIA.items():
        if key == src.lower() or key == leaf:
            return leaf
    return None


def outfit20_id(category: str | int | None) -> str | None:
    """Map a Fashionpedia class onto the 20-class detector id, or None."""
    from .outfit20_taxonomy import from_fashionpedia

    if category is None:
        return None
    if isinstance(category, int):
        category = name_for_index(category)
    return from_fashionpedia(str(category))


def allowed_leaves(category: str | int | None) -> frozenset[str] | None:
    if category is None:
        return None
    if isinstance(category, int):
        category = name_for_index(category)
    key = str(category).strip()
    if key in ALLOWED_FROM_FASHIONPEDIA:
        return ALLOWED_FROM_FASHIONPEDIA[key]
    leaf = accessory_leaf(key)
    if leaf:
        return frozenset({leaf})
    oid = outfit20_id(key)
    if oid is None:
        return None
    from .outfit20_taxonomy import SUBCATEGORY

    return frozenset({SUBCATEGORY[oid]})
