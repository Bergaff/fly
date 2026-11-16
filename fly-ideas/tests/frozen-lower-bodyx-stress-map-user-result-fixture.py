#!/usr/bin/env python3
"""Validate the persistent extract of the attached full series-84 result."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "experiments/reports/frozen-lower-bodyx-stress-map-user-summary-extract.json"
d = json.loads(p.read_text(encoding="utf-8"))

assert d["source_file_sha256"] == "7f187bed6f60d3136d21635bbfa84817fc3a00bb1d26118f16b5a83bb2fe2e11"
assert d["status"] == "completed"
proto = d["protocol"]
assert proto["mode"] == "full" and proto["no_retraining"]
assert proto["script_sha256"] == "0bbf0ef1d46a0896580b0fb887c26031fc6e6e4c96346dd87c03b14cc1093c40"
assert proto["runner83_sha256"] == "dac7ea443081aad92faed5c0986066a617fcd2e61735b9292d1979dc6a8fb931"
assert proto["source_model_sha256"] == "79ad0b29f904067d3b8ece3e81a395d66606ab7202015d5c47b254bfa484a9fd"
assert proto["new_motions"] == list(range(281, 287))
assert proto["x_values"] == [3.7, 3.76, 3.82, 3.88, 4.0, 4.12, 4.18, 4.24, 4.3]

x = d["derived"]
assert x["records"] == 432 and x["distinct_cells"] == 72
assert x["distinct_test_ids"] == list(range(281, 287))
assert x["state_unchanged_cases"] == 432
assert x["exact_probes"] == x["exact_probe_matches"] == 36
assert x["normal_case_wins"] == {"zero": 432, "shuffled": 431, "static": 410, "closed": 393}
assert x["empty_rgb_cases"] == 0 and x["min_changed_rgb_values"] > 0
assert x["all_cells_passed"] == 9
assert x["cells_passed_by_camera_z"] == {"0.36": 9, "0.56": 0}
assert x["axis_cells_passed"]["left_distal"] == 12
assert x["axis_cells_passed"]["right_distal"] == 22

primary = d["primary"]
assert not primary["passed"]
assert primary["combined"]["normal"] < primary["combined"]["zero"]
assert all(primary["combined"]["normal"] < primary["combined"][k] for k in ("shuffled", "static", "closed"))
assert primary["axes"]["left_distal"]["wins"] == 67
assert not primary["axes"]["left_distal"]["passed"]
assert all(row["passed"] for axis, row in primary["axes"].items() if axis != "left_distal")
assert not primary["body_x_lower_safeguard"]["passed"]
assert primary["body_x_lower_safeguard"]["axes"]["left_distal"]["wins"] == 32
assert primary["core_cells_passed"] == 2
assert primary["core_cells_total"] == 16 and primary["core_cells_required"] == 12

core = d["core_cells"]
assert len(core) == 16
assert [row["cell_id"] for row in core if row["passed"]] == [22, 54]
assert all(not row["failed_axes"] for row in core if row["passed"])
assert all(set(row["failed_axes"]).issubset({"left_distal", "right_distal"}) for row in core)

xs = d["x_summary"]
assert len(xs) == 9 and sum(row["cases"] for row in xs) == 432
assert xs[0]["body_x"] == 3.7
assert xs[0]["axes"]["left_distal"]["normal"] > xs[0]["axes"]["left_distal"]["zero"]
assert xs[0]["axes"]["right_distal"]["normal"] > xs[0]["axes"]["right_distal"]["zero"]
assert x["core_motion_axis_wins"]["284"] == {a: 16 for a in primary["axes"]}
assert x["core_motion_axis_wins"]["286"]["left_distal"] == 3
assert x["core_motion_axis_wins"]["286"]["right_distal"] == 1

print("Series 84 extract is consistent: pooled signal remains useful, but left-distal, lower-X and 2/16 core-cell gates make the preregistered result a strict no-go.")
