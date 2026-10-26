"""Dataset + collar-safe transforms for the 4-class garment model."""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

from .config import CLASS_ORDER, IMAGE_SIZE
from .organize_dataset import collect_split


def build_transforms(*, train: bool) -> transforms.Compose:
    """Augment without erasing collar / sleeve cues.

    - Mild rotation and flip keep garment upright enough to see collars.
    - RandomResizedCrop scale stays high (0.82+) so the top of the garment
      usually remains in frame.
    - No vertical flip, no strong perspective.
    """
    if train:
        return transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE + 32, IMAGE_SIZE + 32)),
                transforms.RandomResizedCrop(
                    IMAGE_SIZE,
                    scale=(0.82, 1.0),
                    ratio=(0.85, 1.15),
                ),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomRotation(degrees=12),
                transforms.ColorJitter(
                    brightness=0.18,
                    contrast=0.18,
                    saturation=0.15,
                    hue=0.02,
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=(0.485, 0.456, 0.406),
                    std=(0.229, 0.224, 0.225),
                ),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
        ]
    )


class GarmentDataset(Dataset):
    def __init__(
        self,
        rows: list[tuple[Path, str]],
        *,
        train: bool,
        max_per_class: int | None = None,
        seed: int = 42,
    ) -> None:
        self.class_to_idx = {name: i for i, name in enumerate(CLASS_ORDER)}
        grouped: dict[str, list[Path]] = {name: [] for name in CLASS_ORDER}
        for path, label in rows:
            if label in grouped:
                grouped[label].append(path)
        rng = random.Random(seed)
        self.samples: list[tuple[Path, int]] = []
        for label in CLASS_ORDER:
            paths = list(grouped[label])
            rng.shuffle(paths)
            if max_per_class is not None:
                paths = paths[:max_per_class]
            idx = self.class_to_idx[label]
            self.samples.extend((p, idx) for p in paths)
        rng.shuffle(self.samples)
        self.transform = build_transforms(train=train)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        path, target = self.samples[index]
        with Image.open(path) as img:
            image = img.convert("RGB")
        tensor = self.transform(image)
        return tensor, target, str(path)


def load_split_rows(root: Path, split: str) -> list[tuple[Path, str]]:
    return collect_split(root, split)
