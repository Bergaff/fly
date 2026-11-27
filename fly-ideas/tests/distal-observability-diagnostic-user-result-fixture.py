#!/usr/bin/env python3
"""Validate the attached series 82D result extract and frozen routing."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runner = ROOT / "experiments/templates/82d_distal_observability_diagnostic.py"
runner82 = ROOT / "experiments/templates/82_high_resolution_distal_prototype.py"
extract = ROOT / "experiments/reports/distal-observability-diagnostic-user-summary-extract.json"
d = json.loads(extract.read_text(encoding="utf-8"))

assert d["source_file_sha256"] == "94f1142c79af42fb96d2c8c2446b1ccde4bcae55b9d28bb776acf1e235580e42"
assert hashlib.sha256(runner.read_bytes()).hexdigest() == d["protocol"]["script_sha256"]
assert hashlib.sha256(runner82.read_bytes()).hexdigest() == d["protocol"]["runner82_sha256"]
assert d["status"] == "completed" and d["protocol"]["mode"] == "diagnostic"
assert not d["protocol"]["scientific_result"] and not d["protocol"]["authorizes_long_training"]
assert d["derived"]["counts"] == {"training_diagnostics": 320, "visibility_records": 32, "evaluation_records": 96}

routing = d["routing"]
assert not routing["visibility"]["passed"]
assert routing["visibility"]["visible_cells_per_axis"] == {"left_distal": 8, "right_distal": 8}
assert routing["visibility"]["required_per_axis"] == 12
assert routing["visibility"]["by_fov"]["30"]["visible_cell_axis_pairs"] == 16
assert routing["visibility"]["by_fov"]["70"]["visible_cell_axis_pairs"] == 0
assert routing["candidate_representations"] == []
assert routing["route"] == "geometry_or_occlusion"
assert not routing["authorizes_series83"]

for model in routing["models"].values():
    assert not model["both_distal_below_zero"]
    for row in model["axes"].values():
        assert row["rmse"] > row["zero"]
edge = routing["models"]["high96_edge"]["axes"]
assert edge["left_distal"]["wins_vs_standard48"] == 58
assert edge["right_distal"]["wins_vs_standard48"] == 54

for axis in ("left_distal", "right_distal"):
    narrow = d["derived"]["visibility_ranges"]["30"][axis]
    wide = d["derived"]["visibility_ranges"]["70"][axis]
    assert narrow["changed_rgb48_min"] >= 20
    assert wide["changed_rgb48_max"] < 20
    assert wide["standard_feature_delta_min"] > 1e-4
    wide_combined = d["derived"]["distal_rmse_by_fov"]["high96_level_edge"]["70"][axis]
    wide_zero = d["derived"]["distal_rmse_by_fov"]["zero"]["70"][axis]
    assert wide_combined < wide_zero
    narrow_combined = d["derived"]["distal_rmse_by_fov"]["high96_level_edge"]["30"][axis]
    narrow_zero = d["derived"]["distal_rmse_by_fov"]["zero"]["30"][axis]
    assert narrow_combined > narrow_zero

print("Series 82D result is consistent: wide-FOV RGB guard fails, no representation passes pooled zero, and geometry/occlusion route stands.")
