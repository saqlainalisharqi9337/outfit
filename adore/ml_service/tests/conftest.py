"""Shared fixtures.

Nothing here may download a model. The detector is either loaded from the
local ``models/`` directory or explicitly disabled and faked.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image

SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app import config, object_detector  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Every test starts with unread settings and an unloaded detector.

    Mask R-CNN stays off here so the suite does not load the 336 MB checkpoint.
    The running API defaults it on.
    """
    monkeypatch.setenv("ADORE_MASKRCNN_ENABLED", "0")
    config.reset_settings()
    object_detector.reset()
    yield
    config.reset_settings()
    object_detector.reset()


@pytest.fixture
def detector_disabled(monkeypatch):
    monkeypatch.setenv("ADORE_DETECTOR_ENABLED", "0")
    config.reset_settings()
    object_detector.reset()
    return True


def make_image(width: int = 320, height: int = 480, color=(120, 90, 70)) -> Image.Image:
    return Image.new("RGB", (width, height), color)


def png_bytes(width: int = 320, height: int = 480) -> bytes:
    buffer = io.BytesIO()
    make_image(width, height).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeTensor:
    """Stands in for the torch tensors ultralytics returns."""

    def __init__(self, rows):
        self._rows = rows

    def tolist(self):
        return self._rows

    def __getitem__(self, index):
        return FakeScalar(self._rows[index])


class FakeScalar:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


class FakeBoxes:
    def __init__(self, xyxyn, cls, conf):
        self.xyxyn = FakeTensor(xyxyn)
        self.cls = FakeTensor(cls)
        self.conf = FakeTensor(conf)


class FakeRow:
    def __init__(self, boxes):
        self.boxes = boxes


class FakeYolo:
    """Minimal ultralytics stand-in with a fixed prediction."""

    def __init__(self, names, xyxyn, cls, conf):
        self.names = names
        self._rows = [FakeRow(FakeBoxes(xyxyn, cls, conf))]
        self.calls = 0

    def predict(self, *args, **kwargs):
        self.calls += 1
        return self._rows


@pytest.fixture
def fake_detector(monkeypatch):
    """Install a fake YOLO returning one person and one handbag."""

    def install(names=None, xyxyn=None, cls=None, conf=None):
        names = names or {0: "person", 26: "handbag"}
        xyxyn = xyxyn if xyxyn is not None else [
            [0.30, 0.05, 0.70, 0.95],
            [0.62, 0.40, 0.80, 0.62],
        ]
        cls = cls if cls is not None else [0, 26]
        conf = conf if conf is not None else [0.94, 0.71]
        model = FakeYolo(names, xyxyn, cls, conf)
        object_detector.reset()
        monkeypatch.setattr(object_detector, "_loaded", True)
        monkeypatch.setattr(object_detector, "_model", model)
        monkeypatch.setattr(object_detector, "_backend", "fake")
        monkeypatch.setattr(object_detector, "_model_name", "fake.pt")
        return model

    return install
