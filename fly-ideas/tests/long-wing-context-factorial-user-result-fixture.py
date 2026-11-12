#!/usr/bin/env python3
"""Independent arithmetic checks for the compact user-pasted series 62 result."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "experiments/reports/long-user-wing-context-factorial-user-summary-extract.json"
AXES = ["left_x", "left_y", "left_z", "right_y", "right_z"]


def close(actual: float, expected: float, tolerance: float = 1e-12) -> None:
    assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance), (actual, expected)


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    rows = data["conditions_compact"]
    assert len(rows) == 32
    assert [row["mask"] for row in rows] == list(range(32))
    for row in rows:
        expected = [axis for bit, axis in enumerate(AXES) if row["mask"] & (1 << bit)]
        assert row["zeroed_axes"] == expected

    all_key = "new_all_frames_rmse_rad"
    segment_key = "new_segment_rmse_rad"
    best_all = min(rows, key=lambda row: row[all_key])
    best_segment = min(rows, key=lambda row: row[segment_key])
    assert best_all["condition"] == "zero_left_y_left_z_right_y"
    assert best_segment["condition"] == "zero_left_x_right_y"
    close(best_all[all_key], 0.18474897888095607)
    close(best_segment[segment_key], 0.13079011443545044)

    selected = data["selected_exact_metrics"]
    close(selected["zero_left_y_left_z_right_y_new_all_frames"]["sse_rad2"], best_all[all_key] ** 2 * 49)
    close(selected["zero_left_x_right_y_new_segment"]["sse_rad2"], best_segment[segment_key] ** 2 * 5)
    assert selected["zero_left_y_left_z_right_y_new_all_frames"]["opposite_sign_frames"] == 1
    assert selected["zero_left_x_right_y_new_segment"]["opposite_sign_frames"] == 0

    for model in ("old", "new"):
        for scope in ("all_frames", "segment"):
            result = data["shapley"][model][scope]
            values = result["sse_reduction_shapley_rad2"]
            shifts = result["mean_prediction_shift_shapley_rad"]
            assert [item["axis"] for item in values] == AXES
            assert [item["axis"] for item in shifts] == AXES
            close(sum(item["value"] for item in values), result["total_sse_reduction_rad2"])
            close(sum(item["value"] for item in shifts), result["total_mean_prediction_shift_rad"])

    baseline_sse = rows[0][segment_key] ** 2 * 5
    left_x_sse = rows[1][segment_key] ** 2 * 5
    right_y_sse = rows[8][segment_key] ** 2 * 5
    both_sse = rows[9][segment_key] ** 2 * 5
    overlap = (baseline_sse - left_x_sse) + (baseline_sse - right_y_sse) - (baseline_sse - both_sse)
    close(overlap, 2.6928927278642254, 1e-12)

    right_y = next(item["value"] for item in data["shapley"]["new"]["segment"]["sse_reduction_shapley_rad2"] if item["axis"] == "right_y")
    close(100.0 * right_y / data["shapley"]["new"]["segment"]["total_sse_reduction_rad2"], 63.648713857630426)
    print("series 62 compact result fixture: OK")


if __name__ == "__main__":
    main()
