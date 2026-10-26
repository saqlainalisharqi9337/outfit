"""Train watch vs belt vs bag vs trousers.

    .venv\\Scripts\\python.exe train_watch_belt_gate.py --epochs 7 --max-per-class 500
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from app.clothing_taxonomy import IMAGE_SIZE

DATA = Path(r"D:\fyp project\dataset") / "watch_belt_gate"
MODELS = Path(__file__).resolve().parent / "models"
CLASSES = ("watch", "belt", "bag", "trousers")
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _collect(split: str) -> list[tuple[Path, str]]:
    rows: list[tuple[Path, str]] = []
    for label in CLASSES:
        folder = DATA / split / label
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in EXTS:
                rows.append((path, label))
    return rows


def _cap(rows: list[tuple[Path, str]], limit: int) -> list[tuple[Path, str]]:
    buckets: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    for row in rows:
        buckets[row[1]].append(row)
    out: list[tuple[Path, str]] = []
    for name in CLASSES:
        out.extend(buckets[name][:limit])
    return out


def _tf_ds(rows: list[tuple[Path, str]], index: dict[str, int], training: bool):
    import tensorflow as tf

    paths = [str(p) for p, _ in rows]
    labels = [index[n] for _, n in rows]
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
        pad_h, pad_w = side - height, side - width
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
        return tf.cast(image, tf.float32) / 127.5 - 1.0, label

    return ds.map(_load, num_parallel_calls=tf.data.AUTOTUNE).batch(
        24 if training else 32
    ).prefetch(tf.data.AUTOTUNE)


def _build(num: int):
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
    x = layers.RandomRotation(0.04)(x)
    x = layers.RandomContrast(0.16)(x)
    x = backbone(x, training=False)
    x = layers.Dropout(0.30)(x)
    outputs = layers.Dense(num, activation="softmax", name="watch_belt_gate")(x)
    return models.Model(inputs, outputs, name="adore_watch_belt_gate"), backbone


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=7)
    ap.add_argument("--fine-tune-epochs", type=int, default=3)
    ap.add_argument("--max-per-class", type=int, default=500)
    args = ap.parse_args()
    train = _cap(_collect("train"), args.max_per_class)
    val = _collect("val") or train[:40]
    test = _collect("test")
    if len(train) < 40:
        raise SystemExit("Run prepare_watch_belt_gate.py first.")
    index = {name: i for i, name in enumerate(CLASSES)}
    print("train", dict(Counter(n for _, n in train)), flush=True)
    import tensorflow as tf

    model, backbone = _build(4)
    counts = Counter(n for _, n in train)
    total = sum(counts.values())
    weights = {
        index["watch"]: 1.50 * total / (4 * max(counts["watch"], 1)),
        index["belt"]: 1.50 * total / (4 * max(counts["belt"], 1)),
        index["bag"]: total / (4 * max(counts["bag"], 1)),
        index["trousers"]: total / (4 * max(counts["trousers"], 1)),
    }
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(
        _tf_ds(train, index, True),
        validation_data=_tf_ds(val, index, False),
        epochs=args.epochs,
        class_weight=weights,
        verbose=1,
    )
    if args.fine_tune_epochs:
        backbone.trainable = True
        for layer in backbone.layers[:-28]:
            layer.trainable = False
        model.compile(
            optimizer=tf.keras.optimizers.Adam(8e-6),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        model.fit(
            _tf_ds(train, index, True),
            validation_data=_tf_ds(val, index, False),
            epochs=args.fine_tune_epochs,
            class_weight=weights,
            verbose=1,
        )
    MODELS.mkdir(parents=True, exist_ok=True)
    out = MODELS / "watch_belt_gate_mobilenetv2.keras"
    model.save(out)
    (MODELS / "watch_belt_gate_labels.json").write_text(
        json.dumps(
            {
                "classes": list(CLASSES),
                "index": index,
                "preprocess": "letterbox + x / 127.5 - 1",
                "dataset": str(DATA),
                "sources": [
                    "Fashionpedia watch and belt crops (open images)",
                    "Hugging Face fashion-product-images Watches/Belts",
                    "local bags and trousers as hard negatives",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if test:
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

        y_true, y_pred = [], []
        for batch_x, batch_y in _tf_ds(test, index, False):
            probs = model.predict(batch_x, verbose=0)
            y_true.extend(np.asarray(batch_y).astype(int).tolist())
            y_pred.extend(probs.argmax(axis=1).tolist())
        report = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "report": classification_report(
                y_true, y_pred, target_names=list(CLASSES), output_dict=True, zero_division=0
            ),
            "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1, 2, 3]).tolist(),
            "labels": list(CLASSES),
        }
        (MODELS / "watch_belt_gate_eval.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print("test accuracy", report["accuracy"], flush=True)
        print("watch as watch/belt/bag/trousers", report["confusion_matrix"][0], flush=True)
        print("belt as watch/belt/bag/trousers", report["confusion_matrix"][1], flush=True)
    print("saved", out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
