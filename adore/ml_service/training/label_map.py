"""Load Milestone 2 unified_label_map.json. Do not invent mappings here."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAP_PATH = ROOT / "ml_service" / "taxonomy" / "unified_label_map.json"

UNSAFE_PAIRS = (
    ("sweater", "hoodie"),
    ("dress", "skirt"),
    ("bag", "hat"),
    ("scarf", "dupatta"),
    ("jumpsuit", "dress"),
)


class UnifiedLabelMap:
    def __init__(self, data: dict[str, Any], path: Path) -> None:
        self.data = data
        self.path = path
        self.detector_classes: list[str] = list(data["detector_classes"])
        self.data_required: list[str] = list(data.get("data_required") or [])
        self.category_of: dict[str, str] = dict(data.get("category_of") or {})
        self.fashionpedia: dict[str, str] = dict(data["maps"]["fashionpedia"])
        self.fashionpedia_reject: set[str] = {
            str(name).strip().lower() for name in data["maps"]["fashionpedia_reject"]
        }
        self.deepfashion2: dict[str, str] = dict(data["maps"].get("deepfashion2") or {})
        self.deepfashion2_reject: set[str] = {
            str(name).strip().lower() for name in data["maps"].get("deepfashion2_reject") or []
        }
        self._assert_no_unsafe_maps()

    def _assert_no_unsafe_maps(self) -> None:
        mapped = dict(self.fashionpedia)
        mapped.update(self.deepfashion2)
        for src, dst in mapped.items():
            for banned_src, banned_dst in UNSAFE_PAIRS:
                if src.strip().lower() == banned_src and dst.strip().lower() == banned_dst:
                    raise ValueError(f"unsafe mapping {src} -> {dst}")

    def class_id(self, name: str) -> int:
        return self.detector_classes.index(name) + 1

    def coco_categories(self) -> list[dict[str, Any]]:
        cats = []
        for i, name in enumerate(self.detector_classes, start=1):
            cats.append(
                {
                    "id": i,
                    "name": name,
                    "supercategory": self.category_of.get(name, "clothing"),
                }
            )
        return cats

    def map_fashionpedia(self, original: str) -> tuple[str | None, str]:
        """Return (unified_name or None, reason_code)."""
        key = str(original).strip()
        lower = key.lower()
        if key in self.fashionpedia:
            unified = self.fashionpedia[key]
            if unified not in self.detector_classes:
                return None, "mapped_but_not_detector_class"
            if unified in self.data_required:
                return None, "data_required"
            return unified, "mapped"
        if lower in self.fashionpedia_reject:
            return None, "rejected_taxonomy"
        return None, "unmapped_excluded"


def load_label_map(path: Path | None = None) -> UnifiedLabelMap:
    map_path = path or DEFAULT_MAP_PATH
    data = json.loads(map_path.read_text(encoding="utf-8"))
    return UnifiedLabelMap(data, map_path)
