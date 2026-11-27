#!/usr/bin/env python3
"""Validate the series 82 attached result extract and preregistered no-go."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runner = ROOT / "experiments/templates/82_high_resolution_distal_prototype.py"
extract = ROOT / "experiments/reports/high-resolution-distal-prototype-user-summary-extract.json"
d = json.loads(extract.read_text(encoding="utf-8"))

assert d["source_file_sha256"] == "cda09972ff536cd1789c6c858b4e08849ea31946ffb12181e3103581c24d8066"
assert hashlib.sha256(runner.read_bytes()).hexdigest() == d["protocol"]["script_sha256"]
assert d["status"] == "completed"
assert d["protocol"]["mode"] == "prototype" and not d["protocol"]["scientific_result"]
assert d["protocol"]["training_episodes"] == 320
assert d["protocol"]["evaluation_motions"] == 6
assert d["protocol"]["baseline"]["features"] == 576
assert d["protocol"]["high_resolution"]["features"] == 1152
assert not d["go_for_long_training"]

axes = d["axes"]
for axis in ("left_proximal", "left_middle", "right_proximal", "right_middle"):
    assert axes[axis]["passed"]
for axis in ("left_distal", "right_distal"):
    assert not axes[axis]["passed"]
    assert axes[axis]["highres"] > axes[axis]["zero"]
    assert axes[axis]["wins_vs_standard"] / axes[axis]["cases"] >= 0.60
assert axes["left_distal"]["highres"] > axes["left_distal"]["standard"]
assert axes["right_distal"]["highres"] < axes["right_distal"]["standard"]

assert d["combined"]["highres"] < d["combined"]["standard"] < d["combined"]["zero"]
assert all(group["passed"] for group in d["fov_safeguards"].values())
assert d["held_corners_both_distal_improved"] == 10 < 12
assert len(d["cell_results"]) == d["held_corners_total"] == 16
assert sum(cell["both_distal_improved"] for cell in d["cell_results"]) == 10
assert sum(cell["both_distal_improved"] for cell in d["cell_results"] if cell["view"]["fov_deg"] == 30) == 3
assert sum(cell["both_distal_improved"] for cell in d["cell_results"] if cell["view"]["fov_deg"] == 70) == 7

for fov in ("30", "70"):
    for axis in ("left_distal", "right_distal"):
        row = d["derived"]["distal_by_fov"][fov][axis]
        assert row["highres"] > row["zero"]
assert d["derived"]["distal_by_fov"]["30"]["left_distal"]["highres"] > d["derived"]["distal_by_fov"]["30"]["left_distal"]["standard"]
assert d["derived"]["distal_by_fov"]["30"]["right_distal"]["highres"] > d["derived"]["distal_by_fov"]["30"]["right_distal"]["standard"]
assert d["derived"]["distal_by_fov"]["70"]["left_distal"]["highres"] < d["derived"]["distal_by_fov"]["70"]["left_distal"]["standard"]
assert d["derived"]["distal_by_fov"]["70"]["right_distal"]["highres"] < d["derived"]["distal_by_fov"]["70"]["right_distal"]["standard"]

print("Series 82 result is internally consistent: combined improves, both distal axes fail zero, corner gate fails, no-go stands.")
