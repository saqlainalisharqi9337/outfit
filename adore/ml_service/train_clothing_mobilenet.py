"""Fine-tune MobileNetV2 on the Adore clothing dataset.

Run from the `ml_service` folder with Python 3.11 or 3.12 (TensorFlow does
not install on Python 3.14):

    python -m venv .venv
    .venv\\Scripts\\activate
    pip install -r requirements.txt
    pip install tensorflow scikit-learn matplotlib
    python train_clothing_mobilenet.py

Outputs (do not rename — the API loads these paths):
    models/clothing_mobilenetv2.keras
    models/labels.json
    models/eval_report.json
    models/confusion_matrix.png
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from app.clothing_taxonomy import (
    CONFUSABLE_PAIRS,
    FOLDER_TO_CLASS,
    IMAGE_SIZE,
    preprocess_mobilenet_v2,
)

DEFAULT_DATASET = Path(r"D:\fyp project\dataset")
MODELS_DIR = Path(__file__).resolve().parent / "models"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _collect_split(root: Path, split: str) -> list[tuple[Path, str]]:
    base = root / split / split
    rows: list[tuple[Path, str]] = []
    if not base.is_dir():
        return rows
    for (family, leaf), label in FOLDER_TO_CLASS.items():
        folder = base / family / leaf
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in EXTS:
                rows.append((path, label))
    return rows


def audit_dataset(root: Path) -> dict:
    report: dict = {"root": str(root), "splits": {}, "issues": []}
    for split in ("train", "val", "test"):
        rows = _collect_split(root, split)
        counts = Counter(label for _, label in rows)
        report["splits"][split] = {
            "images": len(rows),
            "classes": dict(sorted(counts.items())),
        }
    train = report["splits"].get("train", {}).get("classes", {})
    if not train:
        report["issues"].append(f"No training images under {root}")
        return report

    present = set(train)
    recommended = {
        "t-shirt",
        "shirt",
        "dress",
        "jeans",
        "trousers",
        "shorts",
        "skirt",
        "jacket",
        "coat",
        "hoodie",
        "sweater",
        "hat",
        "bag",
        "scarf",
        "shoes",
    }
    missing = sorted(recommended - present)
    if missing:
        report["issues"].append(
            "Missing folders for: "
            + ", ".join(missing)
            + ". Add them as train/train/<family>/<leaf> using FOLDER_TO_CLASS "
            "in app/clothing_taxonomy.py. Until then the model cannot learn those labels."
        )
    if "jeans" not in present and "trousers" in present:
        report["issues"].append(
            "There is no jeans folder. Denim photos sit in bottomwear/pants and "
            "are trained as trousers. That is why a dress can be called jeans "
            "on-device (color heuristic) and why trousers/jeans stay confused."
        )
    values = list(train.values())
    if values and max(values) / max(min(values), 1) >= 1.8:
        report["issues"].append(
            "Class imbalance: largest class has "
            f"{max(values)} images vs {min(values)} for the smallest. "
            "Training uses class weights so rare classes (often shoes/hat) are not ignored."
        )
    report["issues"].append(
        "Overlapping categories: shirt vs t-shirt, jacket vs coat, pants vs jeans, "
        "flats vs shoes vs sneakers. MobileNetV2 can separate these only if the "
        "folders are clean. Misfiled images teach the wrong class."
    )
    return report


def _load_xy(rows: list[tuple[Path, str]], class_index: dict[str, int]):
    xs = []
    ys = []
    for path, label in rows:
        try:
            image = Image.open(path).convert("RGB")
        except OSError:
            continue
        xs.append(preprocess_mobilenet_v2(image)[0])
        ys.append(class_index[label])
    return np.stack(xs), np.array(ys, dtype=np.int32)


def _build_tf_model(num_classes: int):
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications import MobileNetV2

    augment = models.Sequential(
        [
            layers.RandomFlip("horizontal"),
            layers.RandomRotation(0.08),
            layers.RandomZoom(0.12),
            layers.RandomTranslation(0.08, 0.08),
            layers.RandomContrast(0.15),
        ],
        name="augment",
    )
    backbone = MobileNetV2(
        input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3),
        include_top=False,
        weights="imagenet",
        pooling="avg",
    )
    backbone.trainable = False

    inputs = layers.Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3))
    x = augment(inputs)
    x = backbone(x, training=False)
    x = layers.Dropout(0.25)(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="clothing")(x)
    model = models.Model(inputs, outputs, name="adore_clothing_mobilenetv2")
    return model, backbone


def _evaluate(model, x, y, classes: list[str], out_dir: Path) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )

    probs = model.predict(x, batch_size=32, verbose=0)
    pred = probs.argmax(axis=1)
    report = classification_report(
        y, pred, target_names=classes, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y, pred, labels=list(range(len(classes))))
    payload = {
        "accuracy": float(accuracy_score(y, pred)),
        "precision_macro": float(precision_score(y, pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y, pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y, pred, average="macro", zero_division=0)),
        "per_class": {
            name: {
                "precision": report[name]["precision"],
                "recall": report[name]["recall"],
                "f1": report[name]["f1-score"],
                "support": report[name]["support"],
            }
            for name in classes
            if name in report
        },
        "confusion_matrix": matrix.tolist(),
        "labels": classes,
        "confusable": {},
    }
    index = {name: i for i, name in enumerate(classes)}
    for a, b in CONFUSABLE_PAIRS:
        if a not in index or b not in index:
            continue
        ia, ib = index[a], index[b]
        support_a = max(int(matrix[ia].sum()), 1)
        support_b = max(int(matrix[ib].sum()), 1)
        payload["confusable"][f"{a}->{b}"] = int(matrix[ia, ib]) / support_a
        payload["confusable"][f"{b}->{a}"] = int(matrix[ib, ia]) / support_b

    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(matrix, interpolation="nearest")
        ax.set_xticks(range(len(classes)), classes, rotation=45, ha="right")
        ax.set_yticks(range(len(classes)), classes)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title("Clothing MobileNetV2 — test confusion matrix")
        fig.tight_layout()
        fig.savefig(out_dir / "confusion_matrix.png", dpi=140)
        plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        payload["plot_error"] = str(exc)
    return payload


def train(dataset: Path, epochs_head: int, epochs_finetune: int, limit: int | None) -> None:
    try:
        import tensorflow as tf
        from tensorflow.keras.optimizers import Adam
        from tensorflow.keras.utils import to_categorical
    except ImportError as exc:
        raise SystemExit(
            "TensorFlow is not installed. Use Python 3.11 or 3.12, then:\n"
            "  pip install tensorflow scikit-learn matplotlib\n"
            f"Original error: {exc}"
        ) from exc

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    audit = audit_dataset(dataset)
    print(json.dumps(audit, indent=2))
    (MODELS_DIR / "dataset_audit.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    if not audit["splits"].get("train", {}).get("images"):
        raise SystemExit("No training images found.")

    train_rows = _collect_split(dataset, "train")
    val_rows = _collect_split(dataset, "val")
    test_rows = _collect_split(dataset, "test")
    if limit:
        train_rows = train_rows[:limit]
        val_rows = val_rows[: max(limit // 8, 50)]
        test_rows = test_rows[: max(limit // 8, 50)]

    classes = sorted({label for _, label in train_rows})
    class_index = {name: i for i, name in enumerate(classes)}
    print("Classes:", classes)

    print("Loading and preprocessing images (224 RGB, MobileNetV2 [-1, 1])…")
    x_train, y_train = _load_xy(train_rows, class_index)
    x_val, y_val = _load_xy(val_rows, class_index) if val_rows else (x_train[:1], y_train[:1])
    x_test, y_test = _load_xy(test_rows, class_index) if test_rows else (x_val, y_val)

    counts = Counter(int(v) for v in y_train)
    total = len(y_train)
    class_weight = {
        i: total / (len(classes) * max(counts[i], 1)) for i in range(len(classes))
    }
    for name in ("hat", "dress", "shirt", "t-shirt", "jeans", "trousers"):
        if name in class_index:
            class_weight[class_index[name]] *= 1.25

    model, backbone = _build_tf_model(len(classes))
    model.compile(
        optimizer=Adam(1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    y_train_oh = to_categorical(y_train, len(classes))
    y_val_oh = to_categorical(y_val, len(classes))

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=3, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.4, patience=2, min_lr=1e-6
        ),
    ]
    print("Phase 1: train the new classification layer (backbone frozen).")
    model.fit(
        x_train,
        y_train_oh,
        validation_data=(x_val, y_val_oh),
        epochs=epochs_head,
        batch_size=32,
        class_weight=class_weight,
        callbacks=callbacks,
    )

    print("Phase 2: unfreeze the last 40 MobileNetV2 layers and fine-tune.")
    backbone.trainable = True
    for layer in backbone.layers[:-40]:
        layer.trainable = False
    model.compile(
        optimizer=Adam(1e-5),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(
        x_train,
        y_train_oh,
        validation_data=(x_val, y_val_oh),
        epochs=epochs_finetune,
        batch_size=16,
        class_weight=class_weight,
        callbacks=callbacks,
    )

    weights_path = MODELS_DIR / "clothing_mobilenetv2.keras"
    model.save(weights_path)
    labels = {
        "classes": classes,
        "image_size": IMAGE_SIZE,
        "color": "RGB",
        "normalization": "mobilenet_v2",
        "preprocess": "x / 127.5 - 1",
        "dataset": str(dataset),
    }
    (MODELS_DIR / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    print("Saved", weights_path)

    print("Evaluating on the test split…")
    eval_report = _evaluate(model, x_test, y_test, classes, MODELS_DIR)
    (MODELS_DIR / "eval_report.json").write_text(
        json.dumps(eval_report, indent=2), encoding="utf-8"
    )
    print(
        "accuracy={:.3f}  precision={:.3f}  recall={:.3f}  f1={:.3f}".format(
            eval_report["accuracy"],
            eval_report["precision_macro"],
            eval_report["recall_macro"],
            eval_report["f1_macro"],
        )
    )
    for name, row in eval_report["per_class"].items():
        print(
            f"  {name:10} p={row['precision']:.2f} r={row['recall']:.2f} "
            f"f1={row['f1']:.2f} n={int(row['support'])}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune MobileNetV2 for Adore")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--epochs-head", type=int, default=8)
    parser.add_argument("--epochs-finetune", type=int, default=6)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on training images for a smoke run.",
    )
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    if args.audit_only:
        print(json.dumps(audit_dataset(args.dataset), indent=2))
        return
    train(args.dataset, args.epochs_head, args.epochs_finetune, args.limit)


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    sys.exit(main())
