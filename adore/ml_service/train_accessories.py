"""Train the 8-class accessory MobileNetV2 on accessories_open.

Replaces the old bag/hat/skirt/shoes head. Skirt and shoes are not classes.

    .venv\\Scripts\\python.exe train_accessories.py --epochs 6 --max-per-class 280
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from app.accessory_classifier import CLASS_ORDER, DISPLAY_NAME
from app.clothing_taxonomy import IMAGE_SIZE

DEFAULT_DATA = Path(r"D:\fyp project\dataset") / "accessories_open"
MODELS_DIR = Path(__file__).resolve().parent / "models"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _collect(root: Path, split: str) -> list[tuple[Path, str]]:
    rows: list[tuple[Path, str]] = []
    base = root / split
    if not base.is_dir():
        return rows
    for label in CLASS_ORDER:
        folder = base / label
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in EXTS:
                rows.append((path, label))
    return rows


def _cap(rows: list[tuple[Path, str]], limit: int | None) -> list[tuple[Path, str]]:
    if not limit:
        return rows
    buckets: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    for row in rows:
        buckets[row[1]].append(row)
    out: list[tuple[Path, str]] = []
    for name in CLASS_ORDER:
        out.extend(buckets[name][:limit])
    return out


def _tf_dataset(rows: list[tuple[Path, str]], class_index: dict[str, int], training: bool):
    import tensorflow as tf

    paths = [str(path) for path, _ in rows]
    labels = [class_index[label] for _, label in rows]
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        ds = ds.shuffle(len(paths), reshuffle_each_iteration=True)

    def _load(path, label):
        raw = tf.io.read_file(path)
        image = tf.io.decode_image(raw, channels=3, expand_animations=False)
        image.set_shape([None, None, 3])
        hw = tf.shape(image)
        height, width = hw[0], hw[1]
        side = tf.maximum(height, width)
        pad_h = side - height
        pad_w = side - width
        image = tf.pad(
            image,
            [
                [pad_h // 2, pad_h - pad_h // 2],
                [pad_w // 2, pad_w - pad_w // 2],
                [0, 0],
            ],
            constant_values=114,
        )
        image = tf.image.resize(image, [IMAGE_SIZE, IMAGE_SIZE], method="bilinear")
        image = tf.cast(image, tf.float32) / 127.5 - 1.0
        return image, label

    return ds.map(_load, num_parallel_calls=tf.data.AUTOTUNE).batch(24 if training else 32).prefetch(
        tf.data.AUTOTUNE
    )


def _build_model(num_classes: int):
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications import MobileNetV2

    backbone = MobileNetV2(
        input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3),
        include_top=False,
        weights="imagenet",
        pooling="avg",
    )
    backbone.trainable = False
    inputs = layers.Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3))
    x = layers.RandomFlip("horizontal")(inputs)
    x = layers.RandomRotation(0.05)(x)
    x = layers.RandomContrast(0.15)(x)
    x = backbone(x, training=False)
    x = layers.Dropout(0.32)(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="accessory")(x)
    model = models.Model(inputs, outputs, name="adore_accessories8")
    return model, backbone


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--max-per-class", type=int, default=280)
    ap.add_argument("--fine-tune-epochs", type=int, default=2)
    args = ap.parse_args()
    train_rows = _cap(_collect(args.data, "train"), args.max_per_class)
    val_rows = _collect(args.data, "val") or train_rows[: max(16, len(train_rows) // 8)]
    test_rows = _collect(args.data, "test")
    if len(train_rows) < 24:
        raise SystemExit(f"Not enough accessory images in {args.data}. Run prepare_accessory_dataset.py first.")
    present = [name for name in CLASS_ORDER if any(label == name for _, label in train_rows)]
    class_index = {name: i for i, name in enumerate(present)}
    print("classes", present)
    print("train", dict(Counter(label for _, label in train_rows)))
    import tensorflow as tf

    train_ds = _tf_dataset(train_rows, class_index, True)
    val_ds = _tf_dataset(val_rows, class_index, False)
    model, backbone = _build_model(len(present))
    counts = Counter(label for _, label in train_rows)
    total = sum(counts.values())
    weights = {
        class_index[name]: total / (len(present) * max(counts[name], 1)) for name in present
    }
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        class_weight=weights,
        verbose=1,
    )
    if args.fine_tune_epochs > 0:
        backbone.trainable = True
        for layer in backbone.layers[:-24]:
            layer.trainable = False
        model.compile(
            optimizer=tf.keras.optimizers.Adam(1e-5),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=args.fine_tune_epochs,
            class_weight=weights,
            verbose=1,
        )
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    weights_path = MODELS_DIR / "accessories8_mobilenetv2.keras"
    model.save(weights_path)
    labels = {
        "classes": present,
        "index": class_index,
        "display": {name: DISPLAY_NAME.get(name, name) for name in present},
        "image_size": IMAGE_SIZE,
        "color": "RGB",
        "normalization": "mobilenet_v2",
        "preprocess": "letterbox + x / 127.5 - 1",
        "dataset": str(args.data),
        "sources": [
            "detection-datasets/fashionpedia",
            "local Adore bag/hat folders",
            "Wikimedia Commons",
        ],
        "uncertain": {"min_confidence": 0.38, "min_gap": 0.06},
    }
    (MODELS_DIR / "accessories8_labels.json").write_text(
        json.dumps(labels, indent=2), encoding="utf-8"
    )
    if test_rows:
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

        y_true, y_pred = [], []
        for batch_x, batch_y in _tf_dataset(test_rows, class_index, False):
            probs = model.predict(batch_x, verbose=0)
            y_true.extend(np.asarray(batch_y).astype(int).tolist())
            y_pred.extend(probs.argmax(axis=1).tolist())
        names = present
        report = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "report": classification_report(
                y_true, y_pred, target_names=names, output_dict=True, zero_division=0
            ),
            "confusion_matrix": confusion_matrix(
                y_true, y_pred, labels=list(range(len(names)))
            ).tolist(),
            "labels": names,
        }
        (MODELS_DIR / "accessories8_eval.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print("test accuracy", report["accuracy"])
    print("saved", weights_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
