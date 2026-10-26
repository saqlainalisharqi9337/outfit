"""Shared clothing labels, family rules, and MobileNetV2 preprocessing.

Training (`train_clothing_mobilenet.py`) and inference (`clothing_classifier.py`)
must use the same image size, RGB order, and normalization.
"""

from __future__ import annotations

IMAGE_SIZE = 224

# Dataset folder leaf → model class. Optional folders are used only if present.
FOLDER_TO_CLASS: dict[tuple[str, str], str] = {
    ("accessories", "bag"): "bag",
    ("accessories", "hat"): "hat",
    ("accessories", "scarf"): "scarf",
    ("accessories", "belt"): "belt",
    ("accessories", "dupatta"): "dupatta",
    ("accessories", "hijab"): "hijab",
    ("accessories", "jewelry"): "jewelry",
    ("accessories", "jewellery"): "jewelry",
    ("accessories", "sunglasses"): "sunglasses",
    ("accessories", "glasses"): "sunglasses",
    ("accessories", "other"): "accessories",
    ("bottomwear", "pants"): "trousers",
    ("bottomwear", "jeans"): "jeans",
    ("bottomwear", "shorts"): "shorts",
    ("bottomwear", "skirt"): "skirt",
    ("bottomwear", "shalwar"): "shalwar",
    ("bottomwear", "leggings"): "leggings",
    ("footwear", "flats"): "flats",
    ("footwear", "heels"): "heels",
    ("footwear", "shoes"): "shoes",
    ("footwear", "sneakers"): "sneakers",
    ("one-piece", "dress"): "dress",
    ("upperwear", "jacket"): "jacket",
    ("upperwear", "shirt"): "shirt",
    ("upperwear", "tshirt"): "t-shirt",
    ("upperwear", "coat"): "coat",
    ("upperwear", "hoodie"): "hoodie",
    ("upperwear", "sweater"): "sweater",
    ("upperwear", "top"): "top",
    ("upperwear", "blouse"): "blouse",
}

CLASS_TO_CATEGORY: dict[str, str] = {
    "t-shirt": "upperwear",
    "shirt": "upperwear",
    "jacket": "upperwear",
    "coat": "upperwear",
    "sweater": "upperwear",
    "hoodie": "upperwear",
    "blazer": "upperwear",
    "cardigan": "upperwear",
    "kurta": "upperwear",
    "abaya": "upperwear",
    "top": "upperwear",
    "blouse": "upperwear",
    "dress": "dress",
    "gown": "dress",
    "jeans": "lowerwear",
    "trousers": "lowerwear",
    "shorts": "lowerwear",
    "skirt": "lowerwear",
    "shalwar": "lowerwear",
    "leggings": "lowerwear",
    "palazzo": "lowerwear",
    "hat": "accessories",
    "bag": "accessories",
    "scarf": "accessories",
    "jewelry": "accessories",
    "sunglasses": "accessories",
    "belt": "accessories",
    "watch": "accessories",
    "hijab": "accessories",
    "dupatta": "accessories",
    "accessories": "accessories",
    "shoes": "footwear",
    "sneakers": "footwear",
    "flats": "footwear",
    "heels": "footwear",
    "loafers": "footwear",
    "boots": "footwear",
    "sandals": "footwear",
    "unknown": "accessories",
}

ACCESSORY_CLASSES = {
    "hat",
    "bag",
    "scarf",
    "jewelry",
    "sunglasses",
    "belt",
    "watch",
    "hijab",
    "dupatta",
    "accessories",
}

HAT_NEVER = {
    "shirt",
    "t-shirt",
    "dress",
    "jeans",
    "trousers",
    "shorts",
    "skirt",
    "jacket",
    "coat",
    "hoodie",
    "sweater",
    "heels",
    "shoes",
    "sneakers",
    "flats",
    "boots",
    "sandals",
    "loafers",
}
# Primary upperwear must never be rewritten to hat by a weak ImageNet hat score.
UPPERWEAR_KEEP = {
    "shirt",
    "t-shirt",
    "hoodie",
    "jacket",
    "coat",
    "sweater",
    "blazer",
    "cardigan",
    "kurta",
    "abaya",
    "blouse",
    "top",
    "modest top",
}
DRESS_NEVER = {"jeans", "trousers", "shirt", "t-shirt", "hoodie"}
FOOTWEAR = {"shoes", "sneakers", "flats", "heels", "loafers", "boots", "sandals"}
PANTS_LABELS = {"trousers", "jeans", "shorts", "shalwar", "palazzo", "chinos"}
LOWERWEAR_KEEP = {
    "trousers",
    "jeans",
    "shorts",
    "skirt",
    "shalwar",
    "leggings",
    "palazzo",
    "chinos",
}

# Visually similar groups — trainer up-weights these and eval reports them.
CONFUSABLE_PAIRS = (
    ("hat", "shirt"),
    ("hat", "t-shirt"),
    ("dress", "jeans"),
    ("dress", "trousers"),
    ("dress", "skirt"),
    ("shirt", "t-shirt"),
    ("jacket", "coat"),
    ("jacket", "hoodie"),
    ("jeans", "trousers"),
    ("trousers", "shorts"),
    ("trousers", "skirt"),
    ("shorts", "skirt"),
    ("shorts", "jeans"),
    ("shoes", "sneakers"),
    ("flats", "heels"),
    ("bag", "dress"),
    ("bag", "heels"),
    ("bag", "shoes"),
    ("bag", "skirt"),
    ("bag", "hat"),
)


def _as_rgb_image(rgb_uint8):
    import numpy as np
    from PIL import Image

    if hasattr(rgb_uint8, "convert"):
        return rgb_uint8.convert("RGB")
    return Image.fromarray(np.asarray(rgb_uint8).astype("uint8")).convert("RGB")


def preprocess_mobilenet_v2(rgb_uint8):
    """Resize to 224×224 RGB and apply MobileNetV2 `preprocess_input`.

    Formula: x / 127.5 - 1  →  float32 in [-1, 1], shape (1, 224, 224, 3).
    Stretch-resize matches the dress and trousers heads.
    """
    import numpy as np
    from PIL import Image

    image = _as_rgb_image(rgb_uint8).resize((IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR)
    arr = np.asarray(image, dtype=np.float32)
    arr = arr / 127.5 - 1.0
    return np.expand_dims(arr, 0)


def letterbox_mobilenet_v2(rgb_uint8):
    """Pad to a square, then 224 RGB `x / 127.5 - 1`.

    Keeps bag aspect ratio so a hanging tote is not stretched into a
    skirt-like panel and a backpack is not squashed into a cap oval.
    Use only with weights trained the same way.
    """
    import numpy as np
    from PIL import Image

    image = _as_rgb_image(rgb_uint8)
    width, height = image.size
    side = max(width, height, 1)
    canvas = Image.new("RGB", (side, side), (114, 114, 114))
    canvas.paste(image, ((side - width) // 2, (side - height) // 2))
    canvas = canvas.resize((IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR)
    arr = np.asarray(canvas, dtype=np.float32)
    arr = arr / 127.5 - 1.0
    return np.expand_dims(arr, 0)


LOWER_BODY_TALL_RATIO = 1.28
LOWER_BODY_TOP_FRAC = 0.28


def is_full_length_frame(image) -> bool:
    """True when the frame is tall enough to show shoulders and hem together."""
    if not hasattr(image, "size"):
        return False
    width, height = image.size
    return height >= int(width * 1.18)


def is_isolated_product_shot(image) -> bool:
    """True when one compact object sits on a table or studio background.

    A phone photo of a cap is often portrait, so ``is_full_length_frame``
    is the wrong test — that flag is for outfits, not a single accessory.
    """
    if not hasattr(image, "convert") or not hasattr(image, "size"):
        return False
    width, height = image.size
    if width < 16 or height < 16:
        return True
    import numpy as np
    from PIL import Image as PILImage

    rgb = image.convert("RGB")
    thumb = rgb.resize((64, 64), PILImage.BILINEAR)
    arr = np.asarray(thumb, dtype=np.float32)
    corners = np.concatenate(
        [
            arr[:8, :8].reshape(-1, 3),
            arr[:8, -8:].reshape(-1, 3),
            arr[-8:, :8].reshape(-1, 3),
            arr[-8:, -8:].reshape(-1, 3),
        ]
    )
    bg = np.median(corners, axis=0)
    dist = np.linalg.norm(arr - bg, axis=2)
    mask = dist > 26.0
    occ = float(mask.mean())
    if occ < 0.015:
        return True
    ys, xs = np.where(mask)
    if ys.size < 6:
        return True
    hfrac = float(ys.max() - ys.min() + 1) / 64.0
    wfrac = float(xs.max() - xs.min() + 1) / 64.0
    aspect = wfrac / max(hfrac, 1e-6)
    # Cropped beanie / cap filling the frame is still one product, not an outfit.
    # A standing person is a thin column (aspect well below 0.72).
    if occ > 0.52:
        return aspect >= 0.72 and wfrac >= 0.48
    # A standing person fills most of the height. A cap on a bed does not.
    if hfrac <= 0.68 and occ <= 0.38 and 0.40 <= aspect <= 2.60:
        return True
    if not is_full_length_frame(image) and occ <= 0.42 and hfrac <= 0.78:
        return True
    return False


def is_closeup_item_frame(image) -> bool:
    """Square close-ups and tall table-top product shots both count."""
    return (not is_full_length_frame(image)) or is_isolated_product_shot(image)


def is_hanging_body_garment(image) -> bool:
    """True for a hanging / laid-out shirt or pants panel — not a compact cap.

    Hanging button-downs often score ImageNet ``cowboy_hat``. Use silhouette
    geometry so those crops are not early-returned as accessories/hat.
    """
    if not hasattr(image, "convert") or not hasattr(image, "size"):
        return False
    width, height = image.size
    if width < 16 or height < 16:
        return False
    import numpy as np
    from PIL import Image as PILImage

    # Portrait hanging garments are usually taller than wide.
    if height >= int(width * 1.05):
        rgb = image.convert("RGB")
        thumb = rgb.resize((64, 64), PILImage.BILINEAR)
        arr = np.asarray(thumb, dtype=np.float32)
        corners = np.concatenate(
            [
                arr[:8, :8].reshape(-1, 3),
                arr[:8, -8:].reshape(-1, 3),
                arr[-8:, :8].reshape(-1, 3),
                arr[-8:, -8:].reshape(-1, 3),
            ]
        )
        bg = np.median(corners, axis=0)
        dist = np.linalg.norm(arr - bg, axis=2)
        mask = dist > 26.0
        occ = float(mask.mean())
        if occ < 0.10:
            return False
        ys, xs = np.where(mask)
        if ys.size < 8:
            return False
        hfrac = float(ys.max() - ys.min() + 1) / 64.0
        wfrac = float(xs.max() - xs.min() + 1) / 64.0
        aspect = wfrac / max(hfrac, 1e-6)
        # Caps are compact (low height frac or near-square crown). Shirts
        # and trousers fill a tall column.
        if hfrac >= 0.58 and aspect <= 0.95 and occ >= 0.14:
            return True
        if hfrac >= 0.70 and aspect <= 1.10 and occ >= 0.18:
            return True
    return False


def crop_foreground_occupancy(image) -> float:
    """Fraction of the crop that differs from corner background (0..1).

    Empty cream side-bands used for bag proposals score near 0.
    """
    if not hasattr(image, "convert") or not hasattr(image, "size"):
        return 1.0
    width, height = image.size
    if width < 8 or height < 8:
        return 0.0
    import numpy as np
    from PIL import Image as PILImage

    rgb = image.convert("RGB")
    thumb = rgb.resize((48, 48), PILImage.BILINEAR)
    arr = np.asarray(thumb, dtype=np.float32)
    corners = np.concatenate(
        [
            arr[:6, :6].reshape(-1, 3),
            arr[:6, -6:].reshape(-1, 3),
            arr[-6:, :6].reshape(-1, 3),
            arr[-6:, -6:].reshape(-1, 3),
        ]
    )
    bg = np.median(corners, axis=0)
    dist = np.linalg.norm(arr - bg, axis=2)
    return float((dist > 22.0).mean())


def emphasize_lower_body(image):
    """On tall photos, drop the upper frame so waist, crotch, and hem dominate.

    Isolated product shots stay almost unchanged. This is not a detector;
    full-body photos with several items still need a later detection stage.
    Training (`train_trousers_shorts_skirt.py`) uses the same 0.28 / 1.28 rule.
    """
    if not hasattr(image, "convert"):
        return image
    rgb = image.convert("RGB")
    width, height = rgb.size
    if height >= int(width * LOWER_BODY_TALL_RATIO):
        top = int(height * LOWER_BODY_TOP_FRAC)
        rgb = rgb.crop((0, top, width, height))
    return rgb


def lower_structure_crop(image):
    """Second view: keep the bottom 68% so crotch gap and hem stay in frame."""
    if not hasattr(image, "convert"):
        return image
    rgb = image.convert("RGB")
    width, height = rgb.size
    top = int(height * 0.32)
    if height - top < 36:
        return rgb
    return rgb.crop((0, top, width, height))


def family_of(label: str) -> str:
    return CLASS_TO_CATEGORY.get(label, "accessories")


def apply_family_constraints(
    ranked: list[tuple[str, float]],
) -> tuple[str, float, bool, str]:
    """Never allow a cap to become a shirt, or a dress to become jeans.

    `ranked` is (class, probability) high-to-low, already softmaxed.
    Returns (label, confidence, uncertain, message).
    """
    if not ranked:
        return "unknown", 0.0, True, "No class scores. Please select the type."

    label, confidence = ranked[0]
    forced = False

    hat = next((row for row in ranked if row[0] == "hat"), None)
    bag = next((row for row in ranked if row[0] == "bag"), None)
    # Do not promote skirt over the softmax winner. That rewrite turned
    # pants, shorts, dresses, and bags into skirts. Specialists decide
    # trousers/shorts/skirt and dress/skirt/pants from pixels.
    if label in FOOTWEAR and bag is not None:
        # Heels/sandals often get weak bag noise; only steal with a strong bag.
        if label in {"heels", "sandals", "boots"}:
            strong_bag = bag[1] >= 0.32 and bag[1] >= confidence * 0.85
            if strong_bag:
                label, confidence = bag
                forced = True
        elif bag[1] >= 0.06:
            label, confidence = bag
            forced = True
    elif label in UPPERWEAR_KEEP:
        # A hanging shirt often scores a little cowboy_hat noise. Keep the shirt.
        pass
    elif label in PANTS_LABELS:
        # Never rewrite trousers/jeans/shorts to hat.
        pass
    elif (
        label in HAT_NEVER
        and label not in {"skirt", "bag", "dress", "gown"}
        and hat is not None
    ):
        # Heels must not flip to hat on tiny cowboy_hat noise.
        if label in {"heels", "sandals", "boots"}:
            heel_swap = (
                hat[1] >= 0.32
                and hat[1] >= confidence * 0.90
                and confidence < 0.45
            )
        else:
            heel_swap = label in FOOTWEAR and hat[1] >= 0.06
        strong_hat = (
            hat[1] >= 0.28
            and hat[1] >= confidence * 0.90
            and confidence < 0.45
        )
        if heel_swap or strong_hat:
            label, confidence = hat
            forced = True
    # ImageNet must never rewrite trousers/jeans/shorts as a one-piece.
    pants_row = next(
        (row for row in ranked if row[0] in PANTS_LABELS),
        None,
    )
    if label in {"dress", "gown", "modest dress"} and pants_row is not None:
        if pants_row[1] >= 0.06:
            label, confidence = pants_row
            forced = True
    # Weak hat must not beat a real upperwear score in the ranked list.
    shirt_row = next(
        (row for row in ranked if row[0] in UPPERWEAR_KEEP),
        None,
    )
    # DRESS_NEVER: never keep dress when shirt/t-shirt/hoodie/pants scored.
    if label in {"dress", "gown", "modest dress"}:
        never_row = next(
            (row for row in ranked if row[0] in DRESS_NEVER),
            None,
        )
        if never_row is not None and never_row[1] >= 0.08:
            label, confidence = never_row
            forced = True
        elif shirt_row is not None and shirt_row[1] >= 0.10:
            label, confidence = shirt_row
            forced = True
    if label == "hat" and shirt_row is not None:
        if shirt_row[1] >= 0.10 and shirt_row[1] + 0.02 >= confidence:
            label, confidence = shirt_row
            forced = True
    if label == "hat" and pants_row is not None:
        if pants_row[1] >= 0.08:
            label, confidence = pants_row
            forced = True

    gap = confidence - (ranked[1][1] if len(ranked) > 1 else 0.0)
    if label in ACCESSORY_CLASSES:
        # ImageNet accessory scores are often split across several nearby classes.
        uncertain = not forced and confidence < 0.12
    elif label in UPPERWEAR_KEEP or label in PANTS_LABELS:
        # Shirt/trousers scores are often split with cowboy_hat noise.
        # Keep them when clearly ahead of accessories; do not force unknown.
        uncertain = not forced and confidence < 0.28
    else:
        uncertain = not forced and (
            confidence < 0.38 or (confidence < 0.50 and gap < 0.08)
        )
    if uncertain:
        return (
            "unknown",
            confidence,
            True,
            "Uncertain. Please select the type instead of accepting a guess.",
        )
    return label, confidence, False, f"Detected {label}."


def extra_items(ranked: list[tuple[str, float]], primary: str) -> list[dict[str, object]]:
    """Other high-scoring items from a multi-item photo."""
    items: list[dict[str, object]] = []
    seen = {primary, "unknown"}
    for name, score in ranked:
        min_score = 0.12 if name in {"bag", "jewelry"} or name in FOOTWEAR else 0.18
        if name in seen or score < min_score:
            continue
        if family_of(name) == family_of(primary) and score < 0.28:
            continue
        seen.add(name)
        items.append(
            {
                "category": family_of(name),
                "subcategory": name,
                "confidence": round(float(score), 4),
            }
        )
        if len(items) >= 3:
            break
    return items
