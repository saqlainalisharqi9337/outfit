"""Fine-tune MobileNetV2 to separate bags from hat, skirt, and shoes.

Reads existing Adore folders (does not rename or move files):

    accessories/bag          → bag
    accessories/hat          → hat   (hard negative: backpack vs cap)
    bottomwear/skirt         → skirt (hard negative: tote vs skirt)
    footwear/{flats,heels,shoes,sneakers,boots,sandals} → shoes

Hat and skirt images are hard negatives, not a label rewrite. The model
must learn a carrying container vs headwear vs a waist garment.

There is no jewellery/jewelry folder. Chain-strap bags stay Bag.

Run from `ml_service` with the Python 3.12 venv:

    .venv\\Scripts\\python.exe train_bag_shoes.py --audit-only
    .venv\\Scripts\\python.exe train_bag_shoes.py

Outputs:
    models/bag_shoes_mobilenetv2.keras
    models/bag_shoes_labels.json
    models/bag_shoes_eval.json
    models/bag_shoes_confusion.png

Preprocess matches inference: pad-to-square letterbox, then 224×224 RGB,
x / 127.5 - 1. Letterbox keeps tote/backpack aspect ratio.

Training-only augment: horizontal flip, small translation, mild rotation,
contrast/brightness/hue/saturation jitter. Color is randomized so the
head must use container/handle/strap structure. No vertical flip, no
heavy crop (handles and bag body stay in frame).

Loss up-weights bag→hat and bag→skirt mistakes. That is a training
signal, not an inference rewrite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from app.accessory_classifier import CLASS_ORDER, DISPLAY_NAME
from app.clothing_taxonomy import IMAGE_SIZE

DEFAULT_DATASET = Path(r"D:\fyp project\dataset")
MODELS_DIR = Path(__file__).resolve().parent / "models"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

SOURCE_FOLDERS: tuple[tuple[str, str, str], ...] = (
    ("accessories", "bag", "bag"),
    ("accessories", "hat", "hat"),
    ("bottomwear", "skirt", "skirt"),
    ("accessories", "jewelry", "jewelry"),
    ("accessories", "jewellery", "jewelry"),
    ("footwear", "flats", "shoes"),
    ("footwear", "heels", "shoes"),
    ("footwear", "shoes", "shoes"),
    ("footwear", "sneakers", "shoes"),
    ("footwear", "boots", "shoes"),
    ("footwear", "sandals", "shoes"),
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


def _cell(matrix, classes: list[str], src: str, dst: str) -> int:
    if src not in classes or dst not in classes:
        return 0
    return int(matrix[classes.index(src), classes.index(dst)])


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


def _balance_against_bag(rows: list[tuple[Path, str]], seed: int = 42) -> list[tuple[Path, str]]:
    """Keep rival classes near the bag count so shoes/skirts do not drown bags."""
    bags = [row for row in rows if row[1] == "bag"]
    if not bags:
        return rows
    target = int(len(bags) * 1.15)
    rng = np.random.default_rng(seed)
    kept: list[tuple[Path, str]] = list(bags)
    by_label: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    for path, label in rows:
        if label != "bag":
            by_label[label].append((path, label))
    for label, group in by_label.items():
        if len(group) <= target:
            kept.extend(group)
            continue
        by_leaf: dict[str, list[tuple[Path, str]]] = defaultdict(list)
        for path, name in group:
            by_leaf[path.parent.name].append((path, name))
        per = max(target // max(len(by_leaf), 1), 1)
        picked: list[tuple[Path, str]] = []
        for leaf_rows in by_leaf.values():
            rng.shuffle(leaf_rows)
            picked.extend(leaf_rows[:per])
        rng.shuffle(picked)
        kept.extend(picked[:target])
    return kept


def _shuffle_rows(rows: list[tuple[Path, str]], seed: int = 42) -> list[tuple[Path, str]]:
    rng = np.random.default_rng(seed)
    order = np.arange(len(rows))
    rng.shuffle(order)
    return [rows[i] for i in order]


def _stratified_cap(rows: list[tuple[Path, str]], limit: int | None) -> list[tuple[Path, str]]:
    if not limit or limit <= 0:
        return rows
    buckets: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    for row in rows:
        buckets[row[1]].append(row)
    names = [name for name in CLASS_ORDER if buckets[name]]
    per = max(limit // max(len(names), 1), 1)
    out: list[tuple[Path, str]] = []
    for name in names:
        out.extend(buckets[name][:per])
    return out


def audit_dataset(root: Path) -> dict:
    report: dict = {
        "root": str(root),
        "task": "bag vs hat vs skirt vs shoes (jewellery has no folder)",
        "class_order": list(CLASS_ORDER),
        "display": DISPLAY_NAME,
        "splits": {},
        "issues": [],
        "notes": [
            "accessories/bag exists and is large enough to train Bag.",
            "accessories/hat and bottomwear/skirt are hard negatives so a "
            "tote is not learned as a skirt and a backpack is not a hat.",
            "There is no accessories/jewelry folder. Jewellery cannot be a "
            "trained class until those photos are added. Chain-strap bags "
            "must not be labelled jewellery.",
            "Footwear is ~4× bags. Training caps rivals near the bag count "
            "and uses class weights.",
            "Do not vertically flip or heavily crop: that hides handles and "
            "the bag body vs a shoe sole or a skirt hem.",
        ],
    }
    for split in ("train", "val", "test"):
        rows = _collect_split(root, split)
        counts = Counter(label for _, label in rows)
        report["splits"][split] = {
            "images": len(rows),
            "classes": {
                "bag": counts.get("bag", 0),
                "hat": counts.get("hat", 0),
                "skirt": counts.get("skirt", 0),
                "shoes": counts.get("shoes", 0),
                "jewelry": counts.get("jewelry", 0),
            },
            "footwear_leaves": dict(
                Counter(
                    path.parent.name
                    for path, label in rows
                    if label == "shoes"
                )
            ),
        }
    train = report["splits"].get("train", {}).get("classes", {})
    if train.get("bag", 0) == 0:
        report["issues"].append("No bag images. The model cannot learn Bag.")
    if train.get("hat", 0) == 0:
        report["issues"].append("No hat images. Bag vs hat hard negatives are missing.")
    if train.get("skirt", 0) == 0:
        report["issues"].append(
            "No skirt images. Bag vs skirt hard negatives are missing."
        )
    if train.get("shoes", 0) == 0:
        report["issues"].append("No footwear images. The model cannot learn Shoes.")
    if train.get("jewelry", 0) == 0:
        report["issues"].append(
            "No jewellery folder. Chain-strap bags must stay Bag."
        )
    bags = train.get("bag", 0)
    for rival in ("hat", "skirt", "shoes"):
        n = train.get(rival, 0)
        if bags and n and n / max(bags, 1) >= 1.8:
            report["issues"].append(
                f"Class imbalance: bag={bags} {rival}={n}. "
                "Trainer caps rivals near the bag count and uses class weights."
            )
    return report


def _tf_dataset(
    rows: list[tuple[Path, str]],
    class_index: dict[str, int],
    training: bool,
    letterbox: bool = False,
):
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
        if letterbox:
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

    ds = ds.map(_load, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(32 if training else 48)
    return ds.prefetch(tf.data.AUTOTUNE)


def _bag_rival_loss(class_index: dict[str, int]):
    """Up-weight bag confused with hat or skirt so structure is learned.

    This is a training loss, not an inference rewrite.
    """
    import tensorflow as tf

    bag_i = class_index.get("bag")
    hat_i = class_index.get("hat")
    skirt_i = class_index.get("skirt")

    def loss(y_true, y_pred):
        y_true = tf.cast(tf.reshape(y_true, [-1]), tf.int32)
        ce = tf.keras.losses.sparse_categorical_crossentropy(y_true, y_pred)
        if bag_i is None:
            return tf.reduce_mean(ce)
        pred = tf.argmax(y_pred, axis=-1, output_type=tf.int32)
        is_bag = tf.equal(y_true, int(bag_i))
        rival = tf.zeros_like(is_bag)
        if hat_i is not None:
            rival = tf.logical_or(rival, tf.equal(pred, int(hat_i)))
        if skirt_i is not None:
            rival = tf.logical_or(rival, tf.equal(pred, int(skirt_i)))
        weight = 1.0 + 0.85 * tf.cast(tf.logical_and(is_bag, rival), tf.float32)
        return tf.reduce_mean(ce * weight)

    return loss


def _build_model(num_classes: int):
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications import MobileNetV2
    import tensorflow as tf

    class StructureColorJitter(layers.Layer):
        """Hue/saturation noise so color is not used as the bag cue."""

        def call(self, x, training=False):
            if not training:
                return x
            x01 = (x + 1.0) * 0.5
            x01 = tf.image.random_saturation(x01, 0.50, 1.50)
            x01 = tf.image.random_hue(x01, 0.10)
            return tf.clip_by_value(x01 * 2.0 - 1.0, -1.0, 1.0)

    augment = models.Sequential(
        [
            layers.RandomFlip("horizontal"),
            layers.RandomTranslation(0.06, 0.06, fill_mode="nearest"),
            layers.RandomRotation(0.04),
            layers.RandomContrast(0.18),
            layers.RandomBrightness(0.12),
            StructureColorJitter(name="structure_color_jitter"),
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
    outputs = layers.Dense(num_classes, activation="softmax", name="accessory")(x)
    model = models.Model(inputs, outputs, name="adore_bag_shoes")
    return model, backbone


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
        "display": {name: DISPLAY_NAME.get(name, name) for name in classes},
        "bag_as_shoes": _cell(matrix, classes, "bag", "shoes"),
        "bag_as_hat": _cell(matrix, classes, "bag", "hat"),
        "bag_as_skirt": _cell(matrix, classes, "bag", "skirt"),
        "shoes_as_bag": _cell(matrix, classes, "shoes", "bag"),
        "hat_as_bag": _cell(matrix, classes, "hat", "bag"),
        "skirt_as_bag": _cell(matrix, classes, "skirt", "bag"),
        "probs": None,
    }
    payload["_y_true"] = y_true
    payload["_y_prob"] = y_prob
    if not save_plot:
        return payload
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(5.5, 4.8))
        ax.imshow(matrix, interpolation="nearest", cmap="Blues")
        ticks = [DISPLAY_NAME.get(n, n) for n in classes]
        ax.set_xticks(range(len(classes)), ticks, rotation=15, ha="right")
        ax.set_yticks(range(len(classes)), ticks)
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax.text(j, i, str(int(matrix[i, j])), ha="center", va="center")
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title("Bag vs hat / skirt / shoes")
        fig.tight_layout()
        fig.savefig(out_dir / "bag_shoes_confusion.png", dpi=140)
        plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        payload["plot_error"] = str(exc)
    return payload


def _pick_threshold(payload: dict, classes: list[str]) -> dict:
    """Choose min_confidence / min_gap on held-out probs (bag recall + precision)."""
    y_true = np.array(payload.pop("_y_true", []), dtype=int)
    y_prob = np.array(payload.pop("_y_prob", []), dtype=float)
    if y_true.size == 0 or y_prob.size == 0 or "bag" not in classes:
        return {"min_confidence": 0.42, "min_gap": 0.08, "source": "default"}
    bag_i = classes.index("bag")
    best = None
    best_key = (-1.0, -1.0)
    for min_conf in (0.38, 0.42, 0.48, 0.55, 0.62):
        for min_gap in (0.05, 0.08, 0.12, 0.16):
            pred = []
            keep = []
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
            bag_true = yt == bag_i
            bag_pred = yp == bag_i
            tp = int(np.logical_and(bag_true, bag_pred).sum())
            fp = int(np.logical_and(~bag_true, bag_pred).sum())
            fn = int(np.logical_and(bag_true, ~bag_pred).sum())
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            if precision < 0.88:
                continue
            f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
            key = (f1, recall)
            if key > best_key:
                best_key = key
                best = {
                    "min_confidence": min_conf,
                    "min_gap": min_gap,
                    "bag_precision": precision,
                    "bag_recall": recall,
                    "bag_f1": f1,
                    "coverage": len(keep) / len(y_true),
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
            "  ml_service\\.venv\\Scripts\\python.exe train_bag_shoes.py\n"
            f"Original error: {exc}"
        ) from exc

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    audit = audit_dataset(dataset)
    print(json.dumps(audit, indent=2))
    (MODELS_DIR / "bag_shoes_audit.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    if not audit["splits"].get("train", {}).get("classes", {}).get("bag"):
        raise SystemExit("No bag training images found.")

    train_rows = _balance_against_bag(
        _shuffle_rows(_skip_prefix_duplicates(_collect_split(dataset, "train")))
    )
    val_rows = _collect_split(dataset, "val")
    test_rows = _collect_split(dataset, "test") or val_rows
    present = {label for _, label in train_rows}
    classes = [name for name in CLASS_ORDER if name in present]
    if "jewelry" in present and "jewelry" not in classes:
        classes.append("jewelry")
    if limit:
        train_rows = _shuffle_rows(_stratified_cap(train_rows, limit), seed=7)
        val_rows = _stratified_cap(val_rows, max(limit // 6, 48))
        test_rows = _stratified_cap(test_rows, max(limit // 6, 48))
        present = {label for _, label in train_rows}
        classes = [name for name in classes if name in present]

    class_index = {name: i for i, name in enumerate(classes)}
    print("Classes:", {name: DISPLAY_NAME.get(name, name) for name in classes})
    print(
        "counts train",
        Counter(label for _, label in train_rows),
        "val",
        Counter(label for _, label in val_rows),
    )

    train_ds = _tf_dataset(train_rows, class_index, training=True, letterbox=True)
    val_ds = _tf_dataset(val_rows, class_index, training=False, letterbox=True)
    test_ds = _tf_dataset(test_rows, class_index, training=False, letterbox=True)

    counts = Counter(label for _, label in train_rows)
    total = max(sum(counts.values()), 1)
    class_weight = {
        class_index[name]: total / (len(classes) * max(counts.get(name, 0), 1))
        for name in classes
    }
    if "bag" in class_index:
        class_weight[class_index["bag"]] *= 1.25

    model, backbone = _build_model(len(classes))
    rival_loss = _bag_rival_loss(class_index)
    model.compile(
        optimizer=Adam(1e-3),
        loss=rival_loss,
        metrics=["accuracy"],
    )
    ckpt = MODELS_DIR / "bag_shoes_mobilenetv2.keras"
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=3, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.4, patience=2, min_lr=1e-6
        ),
        tf.keras.callbacks.ModelCheckpoint(
            ckpt, monitor="val_accuracy", save_best_only=True
        ),
    ]
    print("Phase 1: train the bag/hat/skirt/shoes head (MobileNetV2 frozen).")
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
        optimizer=Adam(1e-5),
        loss=rival_loss,
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

    print("Evaluating on the test split…")
    eval_report = _evaluate(model, test_ds, classes, MODELS_DIR)
    print("Selecting confidence threshold on validation…")
    val_eval = _evaluate(model, val_ds, classes, MODELS_DIR, save_plot=False)
    uncertain = _pick_threshold(val_eval, classes)
    eval_report.pop("_y_true", None)
    eval_report.pop("_y_prob", None)
    eval_report["uncertain"] = uncertain
    (MODELS_DIR / "bag_shoes_eval.json").write_text(
        json.dumps(eval_report, indent=2), encoding="utf-8"
    )
    labels = {
        "classes": classes,
        "index": class_index,
        "display": {name: DISPLAY_NAME.get(name, name) for name in classes},
        "image_size": IMAGE_SIZE,
        "color": "RGB",
        "normalization": "mobilenet_v2",
        "preprocess": "letterbox + x / 127.5 - 1",
        "dataset": str(dataset),
        "uncertain": {
            "min_confidence": uncertain["min_confidence"],
            "min_gap": uncertain["min_gap"],
        },
        "threshold_search": uncertain,
    }
    (MODELS_DIR / "bag_shoes_labels.json").write_text(
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
    print(
        "threshold",
        uncertain,
        "bag->shoes",
        eval_report.get("bag_as_shoes"),
        "bag->hat",
        eval_report.get("bag_as_hat"),
        "bag->skirt",
        eval_report.get("bag_as_skirt"),
        "shoes->bag",
        eval_report.get("shoes_as_bag"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fine-tune MobileNetV2 for bag vs hat vs skirt vs shoes"
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--epochs-head", type=int, default=6)
    parser.add_argument("--epochs-finetune", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--predict", type=Path, default=None)
    args = parser.parse_args()
    if args.audit_only:
        print(json.dumps(audit_dataset(args.dataset), indent=2))
        return
    if args.predict is not None:
        from PIL import Image

        from app.accessory_classifier import classify_accessory

        image = Image.open(args.predict).convert("RGB")
        result = classify_accessory(image)
        if result is None:
            raise SystemExit(
                "No bag_shoes_mobilenetv2.keras yet. Train first:\n"
                "  .venv\\Scripts\\python.exe train_bag_shoes.py"
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
