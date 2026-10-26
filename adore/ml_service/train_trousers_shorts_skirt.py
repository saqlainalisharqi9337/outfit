"""Fine-tune MobileNetV2 to separate trousers, shorts, and skirt.

Reads existing Adore folders (does not rename or move files):

    bottomwear/pants    -> trousers   (jeans, palazzo, cargos live here)
    bottomwear/jeans    -> trousers   (optional; none in the current dataset)
    bottomwear/shorts   -> shorts
    bottomwear/skirt    -> skirt

There are no palazzo/mini/pleated subfolders. Those variants stay inside
the three leaf folders. This trainer never guesses labels from filenames.

Run from `ml_service` with the Python 3.12 venv:

    .venv\\Scripts\\python.exe train_trousers_shorts_skirt.py --audit-only
    .venv\\Scripts\\python.exe train_trousers_shorts_skirt.py

Outputs:
    models/trousers_shorts_skirt_mobilenetv2.keras
    models/trousers_shorts_skirt_labels.json
    models/trousers_shorts_skirt_eval.json
    models/trousers_shorts_skirt_confusion.png

Preprocess matches inference: on tall photos drop the top 28% so waist,
crotch, and hem dominate, then 224x224 RGB, x / 127.5 - 1.
Augmentation is training-only. No vertical flip. Extra lower-body zoom
keeps the hem (never crops the bottom). Color jitter is mild so the head
learns two-leg vs one-panel structure instead of fabric color.
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

from app.clothing_taxonomy import (
    IMAGE_SIZE,
    LOWER_BODY_TALL_RATIO,
    LOWER_BODY_TOP_FRAC,
)
from app.lowerwear_classifier import CLASS_ORDER, DISPLAY_NAME

DEFAULT_DATASET = Path(r"D:\fyp project\dataset")
MODELS_DIR = Path(__file__).resolve().parent / "models"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

SOURCE_FOLDERS: tuple[tuple[str, str, str], ...] = (
    ("bottomwear", "pants", "trousers"),
    ("bottomwear", "jeans", "trousers"),
    ("bottomwear", "shorts", "shorts"),
    ("bottomwear", "skirt", "skirt"),
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


def _file_digest(path: Path) -> str:
    return hashlib.md5(path.read_bytes()[:32768]).hexdigest()


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


def _drop_split_leakage(
    train: list[tuple[Path, str]],
    heldout: list[tuple[Path, str]],
) -> list[tuple[Path, str]]:
    blocked = {_file_digest(path) for path, _ in heldout}
    return [(path, label) for path, label in train if _file_digest(path) not in blocked]


def _shuffle_rows(rows: list[tuple[Path, str]], seed: int = 42) -> list[tuple[Path, str]]:
    rng = np.random.default_rng(seed)
    order = np.arange(len(rows))
    rng.shuffle(order)
    return [rows[i] for i in order]


def _tiny_or_bad(path: Path) -> str | None:
    try:
        size = path.stat().st_size
    except OSError:
        return "unreadable"
    if size < 2048:
        return "tiny_file"
    return None


def audit_dataset(root: Path) -> dict:
    report: dict = {
        "root": str(root),
        "task": "trousers vs shorts vs skirt",
        "class_order": list(CLASS_ORDER),
        "index": {name: i for i, name in enumerate(CLASS_ORDER)},
        "display": DISPLAY_NAME,
        "sources": [
            {"folder": f"{fam}/{leaf}", "class": label}
            for fam, leaf, label in SOURCE_FOLDERS
        ],
        "splits": {},
        "issues": [],
        "notes": [
            "No bottomwear/jeans folder today. Denim is inside bottomwear/pants "
            "and is trained as trousers.",
            "No palazzo/mini/pleated subfolders. Do not invent them. Variants "
            "stay in pants, shorts, or skirt.",
            "Do not invent palazzo/mini/pleated folders. Variants stay in "
            "pants, shorts, or skirt. Filenames are never used as labels.",
            "Do not vertically flip or crop the hem: crotch gap and hem "
            "length separate pants, shorts, and skirts.",
            "This specialist does not classify dresses. Long dress stays on "
            "the dress/pants/skirt silhouette head.",
        ],
    }
    split_hashes: dict[str, dict[str, str]] = {}
    for split in ("train", "val", "test"):
        rows = _collect_split(root, split)
        counts = Counter(label for _, label in rows)
        tiny = 0
        hashes: dict[str, str] = {}
        for path, label in rows:
            if _tiny_or_bad(path):
                tiny += 1
            hashes[_file_digest(path)] = f"{split}:{label}:{path.name}"
        split_hashes[split] = hashes
        report["splits"][split] = {
            "images": len(rows),
            "classes": {name: counts.get(name, 0) for name in CLASS_ORDER},
            "tiny_files": tiny,
        }
    leak_val = set(split_hashes["train"]) & set(split_hashes["val"])
    leak_test = set(split_hashes["train"]) & set(split_hashes["test"])
    report["leakage"] = {
        "train_val_prefix_overlap": len(leak_val),
        "train_test_prefix_overlap": len(leak_test),
    }
    if leak_val or leak_test:
        report["issues"].append(
            "Possible near-duplicate leakage across splits "
            f"(train/val={len(leak_val)}, train/test={len(leak_test)}). "
            "Trainer drops exact prefix duplicates inside a split only."
        )
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
    for name in CLASS_ORDER:
        if train.get(name, 0) == 0:
            report["issues"].append(f"No {name} images. The model cannot learn {name}.")
    report["issues"].append(
        "Folder labels are trusted. If palazzo pants were saved under skirt, "
        "move that file - this trainer does not guess from filenames."
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
        shape = tf.shape(image)
        height = shape[0]
        width = shape[1]
        tall = tf.cast(height, tf.float32) >= tf.cast(width, tf.float32) * LOWER_BODY_TALL_RATIO
        top = tf.cond(
            tall,
            lambda: tf.cast(tf.cast(height, tf.float32) * LOWER_BODY_TOP_FRAC, tf.int32),
            lambda: 0,
        )
        image = image[top:, :, :]
        if training:
            extra = tf.random.uniform([], 0.0, 0.18)
            extra_px = tf.cast(
                tf.cast(tf.shape(image)[0], tf.float32) * extra, tf.int32
            )
            image = image[extra_px:, :, :]
        image = tf.image.resize(image, [IMAGE_SIZE, IMAGE_SIZE], method="bilinear")
        image = tf.cast(image, tf.float32) / 127.5 - 1.0
        return image, label

    ds = ds.map(_load, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(32 if training else 48)
    return ds.prefetch(tf.data.AUTOTUNE)


def _build_model(num_classes: int):
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications import MobileNetV2

    augment = models.Sequential(
        [
            layers.RandomFlip("horizontal"),
            layers.RandomRotation(0.02),
            layers.RandomContrast(0.06),
            layers.RandomBrightness(0.04),
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
    outputs = layers.Dense(num_classes, activation="softmax", name="lowerwear")(x)
    model = models.Model(inputs, outputs, name="adore_trousers_shorts_skirt")
    return model, backbone


def _pair_errors(matrix, classes: list[str]) -> dict:
    pairs = {}
    names = list(classes)
    for i, src in enumerate(names):
        for j, dst in enumerate(names):
            if i == j:
                continue
            pairs[f"{src}_as_{dst}"] = int(matrix[i, j])
    off = [(k, v) for k, v in pairs.items() if v]
    worst = max(off, key=lambda row: row[1]) if off else ("none", 0)
    return {"counts": pairs, "most_confused": {"pair": worst[0], "errors": worst[1]}}


def _evaluate(model, dataset, classes: list[str], out_dir: Path, save_plot: bool = True) -> dict:
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
    y_prob: list[list[float]] = []
    for batch_x, batch_y in dataset:
        probs = model.predict(batch_x, verbose=0)
        y_true.extend(np.asarray(batch_y).astype(int).tolist())
        y_pred.extend(probs.argmax(axis=1).tolist())
        y_prob.extend(np.asarray(probs).tolist())
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
        "pair_errors": _pair_errors(matrix, classes),
    }
    payload["_y_true"] = y_true
    payload["_y_prob"] = y_prob
    if not save_plot:
        return payload
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
        ax.set_title("Trousers / shorts / skirt")
        fig.tight_layout()
        fig.savefig(out_dir / "trousers_shorts_skirt_confusion.png", dpi=140)
        plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        payload["plot_error"] = str(exc)
    return payload


def _pick_threshold(payload: dict, classes: list[str]) -> dict:
    """Pick min_confidence / min_gap on validation to cut trousers<->skirt swaps."""
    y_true = np.array(payload.pop("_y_true", []), dtype=int)
    y_prob = np.array(payload.pop("_y_prob", []), dtype=float)
    if y_true.size == 0 or y_prob.size == 0:
        return {"min_confidence": 0.42, "min_gap": 0.08, "source": "default"}
    idx = {name: i for i, name in enumerate(classes)}
    best = None
    best_key = (-1.0, -1.0, -1.0)
    for min_conf in (0.38, 0.42, 0.48, 0.55, 0.62):
        for min_gap in (0.05, 0.08, 0.12, 0.16):
            keep = []
            pred = []
            for i, probs in enumerate(y_prob):
                order = np.argsort(probs)[::-1]
                top, second = float(probs[order[0]]), float(probs[order[1]])
                if top < min_conf or (top - second) < min_gap:
                    continue
                keep.append(i)
                pred.append(int(order[0]))
            if len(keep) < max(int(0.55 * len(y_true)), 20):
                continue
            yt = y_true[keep]
            yp = np.array(pred)
            acc = float((yt == yp).mean())
            confuse = 0
            for a, b in (("trousers", "skirt"), ("skirt", "trousers"),
                         ("shorts", "skirt"), ("skirt", "shorts"),
                         ("trousers", "shorts"), ("shorts", "trousers")):
                if a in idx and b in idx:
                    confuse += int(np.logical_and(yt == idx[a], yp == idx[b]).sum())
            coverage = len(keep) / len(y_true)
            key = (acc - confuse / max(len(keep), 1), coverage, acc)
            if key > best_key:
                best_key = key
                best = {
                    "min_confidence": min_conf,
                    "min_gap": min_gap,
                    "accuracy": acc,
                    "coverage": coverage,
                    "confused_pairs": confuse,
                    "source": "validation_sweep",
                }
    return best or {"min_confidence": 0.42, "min_gap": 0.08, "source": "default"}


def train(dataset: Path, epochs_head: int, epochs_finetune: int, limit: int | None) -> None:
    try:
        import tensorflow as tf
        from tensorflow.keras.optimizers import Adam
    except ImportError as exc:
        raise SystemExit(
            "TensorFlow is not installed. Use Python 3.12:\n"
            "  ml_service\\.venv\\Scripts\\python.exe train_trousers_shorts_skirt.py\n"
            f"Original error: {exc}"
        ) from exc

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    audit = audit_dataset(dataset)
    print(json.dumps(audit, indent=2))
    (MODELS_DIR / "trousers_shorts_skirt_audit.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    if not audit["splits"].get("train", {}).get("images"):
        raise SystemExit("No training images found.")

    train_rows = _shuffle_rows(_skip_prefix_duplicates(_collect_split(dataset, "train")))
    val_rows = _collect_split(dataset, "val")
    test_rows = _collect_split(dataset, "test") or val_rows
    train_rows = _drop_split_leakage(train_rows, val_rows + test_rows)
    if limit:
        train_rows = _shuffle_rows(_stratified_cap(train_rows, limit), seed=7)
        val_rows = _stratified_cap(val_rows, max(limit // 6, 48))
        test_rows = _stratified_cap(test_rows, max(limit // 6, 48))

    classes = list(CLASS_ORDER)
    class_index = {name: i for i, name in enumerate(classes)}
    print("Classes:", class_index)
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
    pair_boost = {"trousers": 1.10, "shorts": 1.00, "skirt": 1.40}
    class_weight = {
        class_index[name]: (
            total / (len(classes) * max(counts.get(name, 0), 1))
        )
        * pair_boost.get(name, 1.0)
        for name in classes
    }

    model, backbone = _build_model(len(classes))
    model.compile(
        optimizer=Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    ckpt = MODELS_DIR / "trousers_shorts_skirt_mobilenetv2.keras"
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=4, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.4, patience=2, min_lr=1e-6
        ),
        tf.keras.callbacks.ModelCheckpoint(
            ckpt, monitor="val_accuracy", save_best_only=True
        ),
    ]
    print("Phase 1: train the trousers/shorts/skirt head (MobileNetV2 frozen).")
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs_head,
        class_weight=class_weight,
        callbacks=callbacks,
    )
    print("Phase 2: fine-tune the last 80 MobileNetV2 layers.")
    backbone.trainable = True
    for layer in backbone.layers[:-80]:
        layer.trainable = False
    model.compile(
        optimizer=Adam(8e-6),
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
    model.save(ckpt)

    print("Evaluating on the test split...")
    eval_report = _evaluate(model, test_ds, classes, MODELS_DIR)
    print("Selecting confidence threshold on validation...")
    val_eval = _evaluate(model, val_ds, classes, MODELS_DIR, save_plot=False)
    uncertain = _pick_threshold(val_eval, classes)
    eval_report.pop("_y_true", None)
    eval_report.pop("_y_prob", None)
    eval_report["uncertain"] = uncertain
    (MODELS_DIR / "trousers_shorts_skirt_eval.json").write_text(
        json.dumps(eval_report, indent=2), encoding="utf-8"
    )
    labels = {
        "classes": classes,
        "index": class_index,
        "display": DISPLAY_NAME,
        "image_size": IMAGE_SIZE,
        "color": "RGB",
        "normalization": "mobilenet_v2",
        "preprocess": "emphasize_lower_body (tall 28%) + lower_structure_crop, x / 127.5 - 1",
        "dataset": str(dataset),
        "sources": [
            {"folder": f"{fam}/{leaf}", "class": label}
            for fam, leaf, label in SOURCE_FOLDERS
        ],
        "uncertain": {
            "min_confidence": uncertain["min_confidence"],
            "min_gap": uncertain["min_gap"],
        },
        "threshold_search": uncertain,
    }
    (MODELS_DIR / "trousers_shorts_skirt_labels.json").write_text(
        json.dumps(labels, indent=2), encoding="utf-8"
    )
    print("Saved", ckpt)
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
            f"  {DISPLAY_NAME.get(name, name):16} p={row['precision']:.2f} "
            f"r={row['recall']:.2f} f1={row['f1']:.2f} acc={row['accuracy']:.2f} "
            f"n={int(row['support'])}"
        )
    print("pair errors", eval_report.get("pair_errors"))
    print("threshold", uncertain)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fine-tune MobileNetV2 for trousers vs shorts vs skirt"
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--epochs-head", type=int, default=6)
    parser.add_argument("--epochs-finetune", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--predict", type=Path, default=None)
    args = parser.parse_args()
    if args.audit_only:
        report = audit_dataset(args.dataset)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        (MODELS_DIR / "trousers_shorts_skirt_audit.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
        return
    if args.predict is not None:
        from PIL import Image

        from app.lowerwear_classifier import classify_lowerwear

        image = Image.open(args.predict).convert("RGB")
        result = classify_lowerwear(image)
        if result is None:
            raise SystemExit(
                "No trousers_shorts_skirt_mobilenetv2.keras yet. Train first:\n"
                "  .venv\\Scripts\\python.exe train_trousers_shorts_skirt.py"
            )
        print(json.dumps(result, indent=2))
        return
    train(
        dataset=args.dataset,
        epochs_head=args.epochs_head,
        epochs_finetune=args.epochs_finetune,
        limit=args.limit,
    )


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    sys.exit(main())
