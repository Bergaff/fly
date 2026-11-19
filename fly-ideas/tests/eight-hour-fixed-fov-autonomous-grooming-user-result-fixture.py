#!/usr/bin/env python3
"""Validate the attached series 83 result extract and exact corner-gate no-go."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
extract = ROOT / "experiments/reports/eight-hour-fixed-fov-autonomous-grooming-user-summary-extract.json"
d = json.loads(extract.read_text(encoding="utf-8"))

assert d["source_file_sha256"] == "0c0e321728a291eb70c942ea541203e8719812ed7b144bfd572522d3485c1540"
assert d["status"] == "completed" and d["protocol_mode"] == "long"
assert d["active_training_seconds"] >= 28800
assert d["candidates"] == d["accepted_candidates"] == 18686
assert d["training_frames"] == 915614
assert d["derived"]["test_records"] == 160
assert d["derived"]["distinct_test_ids"] == list(range(261, 271))
assert d["derived"]["distinct_corner_ids"] == list(range(1, 17))
assert d["derived"]["state_unchanged_cases"] == 160

p = d["primary"]
assert not p["passed"]
assert all(row["passed"] for row in p["axes"].values())
assert p["combined"]["wins_vs_zero"] == p["combined"]["cases"] == 160
assert p["combined"]["better_than_controls"] == 3
assert p["body_x_upper_safeguard"]["passed"]
assert all(row["passed"] for row in p["body_x_upper_safeguard"]["axes"].values())
assert p["corners_passed"] == 10 and p["corners_required"] == 12
assert sum(row["passed"] for row in p["corner_results"]) == 10

failed = d["derived"]["failed_corners"]
assert [row["corner_id"] for row in failed] == [1, 5, 6, 9, 13, 14]
assert all(row["view"]["body_x"] == 3.82 for row in failed)
assert [list(row["failed_axes"]) for row in failed] == [
    ["right_distal"], ["right_distal"], ["left_distal"],
    ["right_distal"], ["right_distal"], ["right_distal"],
]
for row in failed:
    for axis in row["failed_axes"].values():
        assert axis["normal"] < axis["zero"]
        assert axis["wins"] < 7

assert d["derived"]["normal_case_wins_vs_controls"] == {"shuffled": 160, "static": 160, "closed": 160}
assert d["derived"]["contact_cases"] == {"normal_better": 79, "equal": 72, "normal_worse": 9}
assert d["audit"]["accepted_total"] == 18686 and d["audit"]["audited_count"] == 128 and not d["audit"]["is_exhaustive"]
assert sum(x["under_0_001_deg"] for x in d["derived"]["unique_motion_overlap"].values()) == 0
assert sum(x["under_1_deg"] for x in d["derived"]["unique_motion_overlap"].values()) == 0
assert sum(x["under_5_deg"] for x in d["derived"]["unique_motion_overlap"].values()) == 115

print("Series 83 is internally consistent: pooled, control and body-X gates pass, but only 10/16 corners pass, so primary remains failed.")
