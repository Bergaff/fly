#!/usr/bin/env python3
"""Validate the attached series 82G result extract and full fixed-FOV go."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runner = ROOT / "experiments/templates/82g_scale_normalized_camera_prototype.py"
runner82 = ROOT / "experiments/templates/82_high_resolution_distal_prototype.py"
extract = ROOT / "experiments/reports/scale-normalized-camera-prototype-user-summary-extract.json"
d = json.loads(extract.read_text(encoding="utf-8"))

assert d["source_file_sha256"] == "9bed977b784bc5ab05bf1313ca7fa410af3d9b4f08d6b0a66e044ad2ac9dd4e1"
assert hashlib.sha256(runner.read_bytes()).hexdigest() == d["protocol"]["script_sha256"]
assert hashlib.sha256(runner82.read_bytes()).hexdigest() == d["protocol"]["runner82_sha256"]
assert d["status"] == "completed" and d["protocol"]["mode"] == "prototype"
assert not d["protocol"]["scientific_result"]
assert d["protocol"]["primary_candidate"] == "fov35_edge"
assert not d["protocol"]["tracked_camera_can_rescue_primary"]
assert d["go_for_revised_long_training"]
assert d["derived"]["counts"] == {"training_diagnostics": 320, "visibility_records": 32, "cell_results": 16, "evaluation_records": 96}

for axis, row in d["axes"].items():
    assert row["passed"]
    assert row["fov35_edge"] < row["zero"]
    if axis.endswith("distal"):
        assert row["fov35_edge"] < row["variable_edge"]
        assert row["fov35_wins_vs_variable"] >= 0.60 * row["cases"]
    else:
        assert row["fov35_edge"] <= 1.05 * row["variable_edge"]
assert d["combined"]["fov35_edge"] < d["combined"]["variable_edge"] < d["combined"]["zero"]
assert all(row["passed"] for row in d["original_fov_safeguards"].values())
assert d["visibility"]["passed"]
assert d["visibility"]["visible_cells_per_axis"] == {"left_distal": 16, "right_distal": 16}
assert d["held_corners_both_distal_improved"] == 12
assert len(d["cell_results"]) == d["held_corners_total"] == 16
assert sum(c["both_distal_improved"] for c in d["cell_results"] if c["view"]["fov_deg"] == 30) == 5
assert sum(c["both_distal_improved"] for c in d["cell_results"] if c["view"]["fov_deg"] == 70) == 7
failed = [c for c in d["cell_results"] if not c["both_distal_improved"]]
assert [c["cell_id"] for c in failed] == [4, 6, 8, 12]
assert all(c["view"]["body_x"] == 4.18 for c in failed)

for fov in ("30", "70"):
    for axis in ("left_distal", "right_distal"):
        row = d["derived"]["distal_by_original_fov"][fov][axis]
        assert row["fov35_edge"] < row["variable_edge"]
        assert row["fov35_edge"] < row["zero"]
for row in d["derived"]["fov35_visibility_ranges"].values():
    assert row["changed_rgb_min"] >= 40
    assert row["feature_delta_min"] >= 1e-4

print("Series 82G result is consistent: fixed FOV35 passes every preregistered gate and authorizes revised long-run design.")
