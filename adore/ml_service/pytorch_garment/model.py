"""ResNet / EfficientNet backbones for 4-class garment classification."""

from __future__ import annotations

import torch
import torch.nn as nn
from torchvision import models


def build_model(
    backbone: str = "resnet18",
    num_classes: int = 4,
    *,
    pretrained: bool = True,
    freeze_backbone: bool = False,
) -> nn.Module:
    weights_map = {
        "resnet18": models.ResNet18_Weights.DEFAULT,
        "resnet50": models.ResNet50_Weights.DEFAULT,
        "efficientnet_b0": models.EfficientNet_B0_Weights.DEFAULT,
    }
    if backbone not in weights_map:
        raise ValueError(f"Unsupported backbone: {backbone}")

    weights = weights_map[backbone] if pretrained else None
    if backbone == "resnet18":
        model = models.resnet18(weights=weights)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
        backbone_params = [
            p for name, p in model.named_parameters() if not name.startswith("fc.")
        ]
    elif backbone == "resnet50":
        model = models.resnet50(weights=weights)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
        backbone_params = [
            p for name, p in model.named_parameters() if not name.startswith("fc.")
        ]
    else:
        model = models.efficientnet_b0(weights=weights)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, num_classes)
        backbone_params = [
            p
            for name, p in model.named_parameters()
            if not name.startswith("classifier.")
        ]

    if freeze_backbone:
        for param in backbone_params:
            param.requires_grad = False
    return model


def set_backbone_trainable(model: nn.Module, trainable: bool) -> None:
    for name, param in model.named_parameters():
        if name.startswith("fc.") or name.startswith("classifier."):
            param.requires_grad = True
        else:
            param.requires_grad = trainable
