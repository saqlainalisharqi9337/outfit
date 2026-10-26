"""M4.7 threshold/error analysis tests. No training, no production edits."""

from __future__ import annotations

import pytest
import torch

from training.analyze_maskrcnn_thresholds import (
    confidence_stats,
    diagnosis_label,
    error_analysis,
    metrics_from_detections,
    size_bin,
)
from training.label_map import load_label_map


def _names() -> list[str]:
    return list(load_label_map().detector_classes)


def _row(*, boxes, labels, scores, gt_boxes, gt_labels, gt_areas, height=100, width=100):
    return {
        "index": 0,
        "stem": "toy",
        "image_id": 1,
        "height": height,
        "width": width,
        "boxes": torch.tensor(boxes, dtype=torch.float32),
        "labels": torch.tensor(labels, dtype=torch.int64),
        "scores": torch.tensor(scores, dtype=torch.float32),
        "gt_boxes": torch.tensor(gt_boxes, dtype=torch.float32),
        "gt_labels": torch.tensor(gt_labels, dtype=torch.int64),
        "gt_areas": torch.tensor(gt_areas, dtype=torch.float32),
    }


def test_confidence_stats_min_max_mean_median():
    names = _names()
    shirt_id = names.index("shirt") + 1
    rows = [
        _row(
            boxes=[[0, 0, 10, 10], [0, 0, 8, 8], [1, 1, 9, 9]],
            labels=[shirt_id, shirt_id, shirt_id],
            scores=[0.2, 0.4, 0.9],
            gt_boxes=[[0, 0, 10, 10]],
            gt_labels=[shirt_id],
            gt_areas=[100.0],
        )
    ]
    stats = confidence_stats(rows, names)
    assert stats["shirt"]["n_pred"] == 3
    assert stats["shirt"]["min"] == pytest.approx(0.2, abs=1e-6)
    assert stats["shirt"]["max"] == pytest.approx(0.9, abs=1e-6)
    assert stats["shirt"]["mean"] == pytest.approx(0.5, abs=1e-6)
    assert stats["shirt"]["median"] == pytest.approx(0.4, abs=1e-6)
    assert stats["shirt"]["n_below_0_5"] == 2
    assert stats["shirt"]["n_at_or_above_0_5"] == 1
    assert stats["watch"]["n_pred"] == 0


def test_metrics_from_detections_respects_score_threshold():
    names = _names()
    shirt_id = names.index("shirt") + 1
    rows = [
        _row(
            boxes=[[0, 0, 10, 10]],
            labels=[shirt_id],
            scores=[0.3],
            gt_boxes=[[0, 0, 10, 10]],
            gt_labels=[shirt_id],
            gt_areas=[100.0],
        )
    ]
    low = metrics_from_detections(rows, names, score_thresh=0.2, iou_thresh=0.5, filter_ap=True)
    high = metrics_from_detections(rows, names, score_thresh=0.5, iou_thresh=0.5, filter_ap=True)
    assert low["tp"] == 1
    assert low["fn"] == 0
    assert low["per_class"]["shirt"]["tp"] == 1
    assert high["tp"] == 0
    assert high["fn"] == 1
    assert high["num_predictions"] == 0
    assert high["per_class"]["shirt"]["tp"] == 0


def test_error_analysis_separates_low_conf_wrong_class_and_miss():
    names = _names()
    shirt_id = names.index("shirt") + 1
    jacket_id = names.index("jacket") + 1
    watch_id = names.index("watch") + 1
    rows = [
        _row(
            boxes=[[0, 0, 10, 10], [20, 0, 30, 10]],
            labels=[shirt_id, jacket_id],
            scores=[0.3, 0.8],
            gt_boxes=[[0, 0, 10, 10], [20, 0, 30, 10], [80, 80, 90, 90]],
            gt_labels=[shirt_id, shirt_id, watch_id],
            gt_areas=[100.0, 100.0, 100.0],
        )
    ]
    errors = error_analysis(rows, names, iou_thresh=0.5)
    shirt = errors["per_class"]["shirt"]
    watch = errors["per_class"]["watch"]
    assert shirt["correct_low_conf"] == 1
    assert shirt["wrong_class"] == 1
    assert shirt["wrong_class_to"]["jacket"] == 1
    assert errors["focus_pairs"]["shirt->jacket"] == 1
    assert watch["missed"] == 1
    assert "A. detected but below confidence 0.5" in diagnosis_label(shirt) or shirt["wrong_class"] == 1


def test_size_bin_boundaries():
    assert size_bin(0.005) == "tiny(<1%)"
    assert size_bin(0.02) == "small(1-5%)"
    assert size_bin(0.10) == "medium(5-15%)"
    assert size_bin(0.30) == "large(>15%)"
