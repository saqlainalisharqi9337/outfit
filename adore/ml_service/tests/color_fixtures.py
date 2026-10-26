"""Synthetic garments for multi-colour tests (no copyrighted photos)."""

from __future__ import annotations

import random

import numpy as np
from PIL import Image, ImageDraw


def _blank(w: int, h: int, rgb: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (w, h), rgb)


def solid_black() -> Image.Image:
    img = _blank(240, 320, (245, 245, 245))
    ImageDraw.Draw(img).rectangle([40, 30, 200, 290], fill=(18, 18, 18))
    return img


def black_red_white_dress() -> Image.Image:
    img = _blank(240, 340, (236, 236, 236))
    draw = ImageDraw.Draw(img)
    draw.rectangle([36, 24, 204, 316], fill=(16, 16, 16))
    rng = random.Random(3)
    for _ in range(18):
        x, y = rng.randint(50, 180), rng.randint(50, 280)
        r = rng.randint(7, 12)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(198, 28, 36))
    for _ in range(16):
        x, y = rng.randint(50, 180), rng.randint(50, 280)
        r = rng.randint(9, 14)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(248, 248, 248))
    return img


def blue_white_striped_shirt() -> Image.Image:
    img = _blank(240, 300, (240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 28, 200, 272], fill=(36, 78, 176))
    for x in range(48, 196, 16):
        draw.rectangle([x, 28, x + 7, 272], fill=(248, 248, 248))
    return img


def navy_white_shirt() -> Image.Image:
    img = _blank(240, 300, (240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 28, 200, 272], fill=(18, 32, 78))
    for x in range(50, 196, 18):
        draw.rectangle([x, 28, x + 6, 272], fill=(246, 246, 246))
    return img


def black_gray_trousers() -> Image.Image:
    img = _blank(200, 340, (242, 242, 242))
    draw = ImageDraw.Draw(img)
    draw.rectangle([48, 20, 152, 320], fill=(20, 20, 20))
    for y in range(28, 312, 20):
        draw.rectangle([48, y, 152, y + 8], fill=(128, 128, 128))
    return img


def red_black_bag() -> Image.Image:
    img = _blank(260, 220, (248, 248, 248))
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 40, 128, 190], fill=(198, 28, 36))
    draw.rectangle([128, 40, 230, 190], fill=(16, 16, 16))
    return img


def green_gold_traditional() -> Image.Image:
    img = _blank(240, 340, (248, 244, 236))
    draw = ImageDraw.Draw(img)
    draw.rectangle([32, 22, 208, 318], fill=(24, 110, 52))
    rng = random.Random(9)
    for _ in range(40):
        x, y = rng.randint(48, 192), rng.randint(40, 300)
        r = rng.randint(3, 6)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(198, 158, 42))
    draw.rectangle([32, 22, 208, 48], fill=(198, 158, 42))
    return img


def pink_white_floral() -> Image.Image:
    img = _blank(240, 320, (236, 236, 236))
    draw = ImageDraw.Draw(img)
    draw.rectangle([36, 24, 204, 296], fill=(220, 118, 150))
    rng = random.Random(5)
    for _ in range(22):
        x, y = rng.randint(50, 180), rng.randint(50, 270)
        r = rng.randint(6, 11)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(248, 248, 248))
    return img


def black_shirt_blue_wall() -> Image.Image:
    img = _blank(280, 360, (40, 90, 210))
    ImageDraw.Draw(img).rectangle([70, 50, 210, 310], fill=(18, 18, 18))
    return img


def black_tiny_yellow_logo() -> Image.Image:
    img = _blank(240, 300, (244, 244, 244))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 30, 200, 270], fill=(16, 16, 16))
    draw.rectangle([112, 140, 128, 156], fill=(250, 220, 20))
    return img


def checked_black_gray() -> Image.Image:
    img = _blank(240, 320, (245, 245, 245))
    draw = ImageDraw.Draw(img)
    cell = 16
    for y in range(28, 292, cell):
        for x in range(44, 196, cell):
            fill = (18, 18, 18) if ((x // cell) + (y // cell)) % 2 == 0 else (128, 128, 128)
            draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=fill)
    return img


def light_cream_solid() -> Image.Image:
    img = _blank(220, 280, (90, 90, 90))
    ImageDraw.Draw(img).rectangle([30, 24, 190, 256], fill=(245, 236, 214))
    return img


def dark_navy_solid() -> Image.Image:
    img = _blank(220, 280, (230, 230, 230))
    ImageDraw.Draw(img).rectangle([30, 24, 190, 256], fill=(18, 32, 78))
    return img


CASES: list[dict] = [
    {
        "id": "solid_black",
        "builder": solid_black,
        "item": "dress",
        "primary": {"black"},
        "secondary": set(),
        "pattern": {"solid"},
        "kind": "solid-dark",
    },
    {
        "id": "black_red_white_dress",
        "builder": black_red_white_dress,
        "item": "dress",
        "primary": {"black"},
        "secondary": {"red", "white", "cream", "dark_red", "maroon"},
        "min_secondary": 2,
        "pattern": {"floral", "printed", "patterned", "multicolor"},
        "kind": "floral-three-colour",
    },
    {
        "id": "blue_white_striped_shirt",
        "builder": blue_white_striped_shirt,
        "item": "shirt",
        "primary": {"blue", "navy", "light_blue"},
        "secondary": {"white", "cream", "silver"},
        "pattern": {"striped", "patterned", "printed"},
        "kind": "striped",
    },
    {
        "id": "navy_white_shirt",
        "builder": navy_white_shirt,
        "item": "shirt",
        "primary": {"navy", "blue", "black"},
        "secondary": {"white", "cream", "silver"},
        "pattern": {"striped", "patterned", "printed"},
        "kind": "striped",
    },
    {
        "id": "black_gray_trousers",
        "builder": black_gray_trousers,
        "item": "trousers",
        "primary": {"black", "gray"},
        "secondary": {"gray", "black", "silver"},
        "pattern": {"striped", "patterned", "checked", "printed"},
        "kind": "two-colour",
    },
    {
        "id": "red_black_bag",
        "builder": red_black_bag,
        "item": "bag",
        "primary": {"red", "black", "dark_red", "maroon"},
        "secondary": {"black", "red", "dark_red", "maroon"},
        "pattern": {"patterned", "printed", "gradient", "checked"},
        "kind": "two-colour-bag",
    },
    {
        "id": "green_gold_traditional",
        "builder": green_gold_traditional,
        "item": "kurta",
        "primary": {"green", "dark_green"},
        "secondary": {"gold", "yellow", "beige", "orange"},
        "pattern": {"printed", "floral", "patterned", "embroidered"},
        "kind": "traditional",
    },
    {
        "id": "pink_white_floral",
        "builder": pink_white_floral,
        "item": "dress",
        "primary": {"pink", "red"},
        "secondary": {"white", "cream", "silver"},
        "pattern": {"floral", "printed", "patterned"},
        "kind": "floral",
    },
    {
        "id": "black_shirt_blue_wall",
        "builder": black_shirt_blue_wall,
        "item": "shirt",
        "primary": {"black"},
        "forbidden": {"blue", "navy", "light_blue"},
        "secondary": set(),
        "pattern": {"solid"},
        "kind": "background",
    },
    {
        "id": "black_tiny_yellow_logo",
        "builder": black_tiny_yellow_logo,
        "item": "t-shirt",
        "primary": {"black"},
        "forbidden_primary": {"yellow", "gold"},
        "secondary": set(),
        "pattern": {"solid"},
        "kind": "tiny-detail",
    },
    {
        "id": "checked_black_gray",
        "builder": checked_black_gray,
        "item": "shirt",
        "primary": {"black", "gray"},
        "secondary": {"gray", "black", "silver"},
        "pattern": {"checked", "patterned", "printed"},
        "kind": "checked",
    },
    {
        "id": "light_cream",
        "builder": light_cream_solid,
        "item": "shirt",
        "primary": {"cream", "white", "beige"},
        "secondary": set(),
        "pattern": {"solid"},
        "kind": "solid-light",
    },
    {
        "id": "dark_navy",
        "builder": dark_navy_solid,
        "item": "shirt",
        "primary": {"navy", "blue", "black"},
        "secondary": set(),
        "pattern": {"solid"},
        "kind": "solid-dark",
    },
]


def as_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGB"))
