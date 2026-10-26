"""Fine-tune MobileNetV2 to separate long dress, pants, and long skirt.

Reads the existing Adore dataset folders (does not rename or move files):

    one-piece/dress     → dress      (Long Dress)
    bottomwear/skirt    → skirt      (Long Skirt)
    bottomwear/pants    → trousers   (Pants/Trousers)
    bottomwear/jeans    → trousers   (no jeans folder today; mapped if added)

Run from `ml_service` with the Python 3.12 venv (TensorFlow needs 3.11/3.12):

    .venv\\Scripts\\python.exe -m pip install scikit-learn matplotlib
    .venv\\Scripts\\python.exe train_dress_pants_skirt.py --audit-only
    .venv\\Scripts\\python.exe train_dress_pants_skirt.py

Outputs (API loads these paths):
    models/dress_pants_skirt_mobilenetv2.keras
    models/dress_pants_skirt_labels.json
    models/dress_pants_skirt_eval.json
    models/dress_pants_skirt_confusion.png

Preprocess matches inference: 224×224 RGB, x / 127.5 - 1.
Augmentation is training-only (disabled at predict). No vertical flip,
no aggressive crop/rotation that would hide the crotch or waist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from app.clothing_taxonomy import IMAGE_SIZE
from app.silhouette_classifier import CLASS_ORDER, DISPLAY_NAME

DEFAULT_DATASET = Path(r"D:\fyp project\dataset")
MODELS_DIR = Path(__file__).resolve().parent / "models"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# (split-family, split-leaf) → specialist class
SOURCE_FOLDERS: tuple[tuple[str, str, str], ...] = (
    ("one-piece", "dress", "dress"),
    ("bottomwear", "skirt", "skirt"),
    ("bottomwear", "pants", "trousers"),
    ("bottomwear", "jeans", "trousers"),
)


def _collect_split(root: Path, split: str) -> list[tuple[Path, str]]:
    base = root / split / split
    rows: list[tuple[Path, str]] = []
    if not base.is_dir():
        return rows
    for family, leaf, label in SOURCE_FOLDERS:
        folder = base / family / leaf
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in EXTS:
                rows.append((path, label))
    return rows


def _skip_prefix_duplicates(rows: list[tuple[Path, str]]) -> list[tuple[Path, str]]:
    """Drop near-duplicate files (same first 32KB) so they are not trained twice."""
    seen: set[str] = set()
    kept: list[tuple[Path, str]] = []
    for path, label in rows:
        digest = hashlib.md5(path.read_bytes()[:32768]).hexdigest()
        key = f"{label}:{digest}"
        if key in seen:
            continue
        seen.add(key)
        kept.append((path, label))
    return kept


def _stratified_cap(rows: list[tuple[Path, str]], limit: int | None) -> list[tuple[Path, str]]:
    if not limit or limit <= 0:
        return rows
    buckets: dict[str, list[tuple[Path, str]]] = {name: [] for name in CLASS_ORDER}
    for row in rows:
        buckets.setdefault(row[1], []).append(row)
    per = max(limit // max(len(CLASS_ORDER), 1), 1)
    out: list[tuple[Path, str]] = []
    for name in CLASS_ORDER:
        out.extend(buckets.get(name, [])[:per])
    return out


def _shuffle_rows(rows: list[tuple[Path, str]], seed: int = 42) -> list[tuple[Path, str]]:
    rng = np.random.default_rng(seed)
    order = np.arange(len(rows))
    rng.shuffle(order)
    return [rows[i] for i in order]


def audit_dataset(root: Path) -> dict:
    report: dict = {
        "root": str(root),
        "task": "long_dress vs pants vs long_skirt",
        "class_order": list(CLASS_ORDER),
        "display": DISPLAY_NAME,
        "splits": {},
        "issues": [],
        "notes": [
            "There is no bottomwear/jeans folder. Denim lives in bottomwear/pants "
            "and is trained as trousers (Pants/Trousers).",
            "The general clothing_mobilenetv2.keras is not required. This specialist "
            "only learns the three silhouettes that ImageNet + geometry mix up.",
            "Do not vertically flip or heavily crop: that hides waist vs shoulders "
            "and the crotch gap between trouser legs.",
        ],
    }
    for split in ("train", "val", "test"):
        rows = _collect_split(root, split)
        counts = Counter(label for _, label in rows)
        report["splits"][split] = {
            "images": len(rows),
            "classes": {name: counts.get(name, 0) for name in CLASS_ORDER},
        }
    train = report["splits"].get("train", {}).get("classes", {})
    if not any(train.values()):
        report["issues"].append(f"No training images under {root}")
        return report
    values = [n for n in train.values() if n]
    if values and max(values) / max(min(values), 1) >= 1.8:
        report["issues"].append(
            "Class imbalance: "
            + ", ".join(f"{k}={v}" for k, v in train.items())
            + ". Training uses class weights."
        )
    if train.get("trousers", 0) == 0:
        report["issues"].append("No pants/jeans images. The model cannot learn Pants.")
    if train.get("dress", 0) == 0:
        report["issues"].append("No dress images. The model cannot learn Long Dress.")
    if train.get("skirt", 0) == 0:
        report["issues"].append("No skirt images. The model cannot learn Long Skirt.")
    report["issues"].append(
        "Folder labels are trusted. If a maxi skirt was saved under one-piece/dress "
        "(or palazzo pants under skirt), move that file — this trainer does not "
        "guess from filenames."
    )
    return report


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
        image = tf.image.resize(image, [IMAGE_SIZE, IMAGE_SIZE], method="bilinear")
        image = tf.cast(image, tf.float32) / 127.5 - 1.0
        return image, label

    ds = ds.map(_load, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(32 if training else 48)
    return ds.prefetch(tf.data.AUTOTUNE)


def _build_model(num_classes: int):
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications import MobileNetV2

    # Keep garment structure: no vertical flip, tiny rotation only.
    augment = models.Sequential(
        [
            layers.RandomFlip("horizontal"),
            layers.RandomRotation(0.03),
            layers.RandomContrast(0.12),
            layers.RandomBrightness(0.08),
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
    x = layers.Dropout(0.30)(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="silhouette")(x)
    model = models.Model(inputs, outputs, name="adore_dress_pants_skirt")
    return model, backbone


def _evaluate(model, dataset, classes: list[str], out_dir: Path) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )

    y_true: list[int] = []
    y_pred: list[int] = []
    for batch_x, batch_y in dataset:
        probs = model.predict(batch_x, verbose=0)
        y_true.extend(np.asarray(batch_y).astype(int).tolist())
        y_pred.extend(probs.argmax(axis=1).tolist())
    y_true_a = np.array(y_true)
    y_pred_a = np.array(y_pred)
    report = classification_report(
        y_true_a, y_pred_a, target_names=classes, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y_true_a, y_pred_a, labels=list(range(len(classes))))
    per_class_acc = {}
    for i, name in enumerate(classes):
        mask = y_true_a == i
        per_class_acc[name] = float((y_pred_a[mask] == i).mean()) if mask.any() else 0.0
    payload = {
        "accuracy": float(accuracy_score(y_true_a, y_pred_a)),
        "precision_macro": float(
            precision_score(y_true_a, y_pred_a, average="macro", zero_division=0)
        ),
        "recall_macro": float(
            recall_score(y_true_a, y_pred_a, average="macro", zero_division=0)
        ),
        "f1_macro": float(f1_score(y_true_a, y_pred_a, average="macro", zero_division=0)),
        "per_class": {
            name: {
                "precision": report[name]["precision"],
                "recall": report[name]["recall"],
                "f1": report[name]["f1-score"],
                "support": report[name]["support"],
                "accuracy": per_class_acc[name],
            }
            for name in classes
            if name in report
        },
        "confusion_matrix": matrix.tolist(),
        "labels": classes,
        "display": DISPLAY_NAME,
    }
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 5))
        ax.imshow(matrix, interpolation="nearest", cmap="Blues")
        ticks = [DISPLAY_NAME.get(n, n) for n in classes]
        ax.set_xticks(range(len(classes)), ticks, rotation=20, ha="right")
        ax.set_yticks(range(len(classes)), ticks)
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax.text(j, i, str(int(matrix[i, j])), ha="center", va="center")
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title("Long dress / pants / long skirt")
        fig.tight_layout()
        fig.savefig(out_dir / "dress_pants_skirt_confusion.png", dpi=140)
        plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        payload["plot_error"] = str(exc)
    return payload


def train(dataset: Path, epochs_head: int, epochs_finetune: int, limit: int | None) -> None:
    try:
        import tensorflow as tf
        from tensorflow.keras.optimizers import Adam
    except ImportError as exc:
        raise SystemExit(
            "TensorFlow is not installed. Use Python 3.12:\n"
            "  ml_service\\.venv\\Scripts\\python.exe -m pip install tensorflow "
            "scikit-learn matplotlib\n"
            f"Original error: {exc}"
        ) from exc

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    audit = audit_dataset(dataset)
    print(json.dumps(audit, indent=2))
    (MODELS_DIR / "dress_pants_skirt_audit.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    if not audit["splits"].get("train", {}).get("images"):
        raise SystemExit("No training images found.")

    train_rows = _shuffle_rows(_skip_prefix_duplicates(_collect_split(dataset, "train")))
    val_rows = _collect_split(dataset, "val")
    test_rows = _collect_split(dataset, "test") or val_rows
    if limit:
        train_rows = _shuffle_rows(_stratified_cap(train_rows, limit), seed=7)
        val_rows = _stratified_cap(val_rows, max(limit // 6, 48))
        test_rows = _stratified_cap(test_rows, max(limit // 6, 48))

    classes = list(CLASS_ORDER)
    class_index = {name: i for i, name in enumerate(classes)}
    print("Classes:", {name: DISPLAY_NAME[name] for name in classes})
    print(
        "counts train",
        Counter(label for _, label in train_rows),
        "val",
        Counter(label for _, label in val_rows),
    )

    train_ds = _tf_dataset(train_rows, class_index, training=True)
    val_ds = _tf_dataset(val_rows, class_index, training=False)
    test_ds = _tf_dataset(test_rows, class_index, training=False)

    counts = Counter(label for _, label in train_rows)
    total = max(sum(counts.values()), 1)
    class_weight = {
        class_index[name]: total / (len(classes) * max(counts.get(name, 0), 1))
        for name in classes
    }

    model, backbone = _build_model(len(classes))
    model.compile(
        optimizer=Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=3, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.4, patience=2, min_lr=1e-6
        ),
        tf.keras.callbacks.ModelCheckpoint(
            MODELS_DIR / "dress_pants_skirt_mobilenetv2.keras",
            monitor="val_accuracy",
            save_best_only=True,
        ),
    ]
    print("Phase 1: train the 3-class head (MobileNetV2 frozen).")
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs_head,
        class_weight=class_weight,
        callbacks=callbacks,
    )
    print("Phase 2: fine-tune the last 50 MobileNetV2 layers.")
    backbone.trainable = True
    for layer in backbone.layers[:-50]:
        layer.trainable = False
    model.compile(
        optimizer=Adam(1e-5),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs_finetune,
        class_weight=class_weight,
        callbacks=callbacks,
    )

    weights_path = MODELS_DIR / "dress_pants_skirt_mobilenetv2.keras"
    model.save(weights_path)
    labels = {
        "classes": classes,
        "index": class_index,
        "display": DISPLAY_NAME,
        "image_size": IMAGE_SIZE,
        "color": "RGB",
        "normalization": "mobilenet_v2",
        "preprocess": "x / 127.5 - 1",
        "dataset": str(dataset),
        "sources": [
            {"folder": f"{fam}/{leaf}", "class": label}
            for fam, leaf, label in SOURCE_FOLDERS
        ],
        "uncertain": {"min_confidence": 0.42, "min_gap": 0.08},
    }
    (MODELS_DIR / "dress_pants_skirt_labels.json").write_text(
        json.dumps(labels, indent=2), encoding="utf-8"
    )
    print("Saved", weights_path)

    print("Evaluating on the test split…")
    eval_report = _evaluate(model, test_ds, classes, MODELS_DIR)
    (MODELS_DIR / "dress_pants_skirt_eval.json").write_text(
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
            f"  {DISPLAY_NAME[name]:16} p={row['precision']:.2f} r={row['recall']:.2f} "
            f"f1={row['f1']:.2f} acc={row['accuracy']:.2f} n={int(row['support'])}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fine-tune MobileNetV2 for long dress vs pants vs long skirt"
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--epochs-head", type=int, default=6)
    parser.add_argument("--epochs-finetune", type=int, default=5)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap training images for a smoke run.",
    )
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument(
        "--predict",
        type=Path,
        default=None,
        help="Run inference on one image with the saved 3-class model.",
    )
    args = parser.parse_args()
    if args.audit_only:
        report = audit_dataset(args.dataset)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        (MODELS_DIR / "dress_pants_skirt_audit.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
        return
    if args.predict is not None:
        from PIL import Image

        from app.silhouette_classifier import classify_silhouette

        image = Image.open(args.predict).convert("RGB")
        result = classify_silhouette(image)
        if result is None:
            raise SystemExit(
                "No dress_pants_skirt_mobilenetv2.keras yet. Train first:\n"
                "  .venv\\Scripts\\python.exe train_dress_pants_skirt.py"
            )
        print(json.dumps(result, indent=2))
        return
    train(dataset=args.dataset, epochs_head=args.epochs_head, epochs_finetune=args.epochs_finetune, limit=args.limit)


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    sys.exit(main())
