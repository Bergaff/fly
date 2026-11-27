#!/usr/bin/env python3
"""Arithmetic check for the user-transcribed series 69 result."""
import json
import math
from pathlib import Path

P = Path(__file__).parents[1] / "experiments/reports/matched-encoder-ablation-user-summary-extract.json"
d = json.loads(P.read_text(encoding="utf-8"))
h = d["normal_rmse_by_holdout"]
a = d["aggregate"]
mean = lambda key: sum(x[key] for x in h) / len(h)

assert d["transcription"]["status"] == "completed"
p = d["protocol"]
assert p["training_stream_episodes"] == p["compact_training_episodes"] == 60_000
assert p["compact_optimizer_steps"] == 1_875
assert p["compact"]["units"] == 24 and p["compact"]["features"] == 240
assert p["compact"]["projection_seed"] == 6601
assert p["rich"]["spatial_units"] == 96 and p["rich"]["features"] == 1_920
assert p["adam"] == {"learning_rate": .002, "weight_decay": 1e-6}
assert p["matched_targets_and_adam_settings"] is True

# Displayed holdout values are stored to ten decimals, so compare at their precision.
assert math.isclose(mean("compact"), a["compact"]["normal"], abs_tol=5e-11)
assert math.isclose(mean("rich"), a["rich"]["normal"], abs_tol=5e-11)
delta = a["rich"]["normal"] - a["compact"]["normal"]
assert math.isclose(delta, a["rich_minus_compact_normal_rmse_rad"], abs_tol=2e-10)
wins = sum(x["rich"] < x["compact"] for x in h)
assert wins == a["rich_better_than_compact"] == 4
assert all(x["winner"] == ("rich" if x["rich"] < x["compact"] else "compact") for x in h)
relative = (a["compact"]["normal"] - a["rich"]["normal"]) / a["compact"]["normal"] * 100
assert math.isclose(relative, a["rich_relative_normal_rmse_reduction_percent"], abs_tol=1e-8)

for model in ("compact", "rich"):
    m = a[model]
    temporal = all(m["normal"] < m[k] for k in ("static", "shuffled", "reversed", "closed"))
    assert temporal == m["temporal_primary_pass"] is True
assert a["rich"]["normal"] < a["compact"]["normal"] and wins >= 4
assert a["rich"]["temporal_primary_pass"] and a["primary_pass"] is True

# Rich is not uniformly superior: movement 55 and all non-zero aggregate controls favor compact.
assert h[-1]["holdout"] == 55 and h[-1]["winner"] == "compact"
for condition in ("static", "shuffled", "reversed", "closed"):
    assert a["compact"][condition] < a["rich"][condition]
print("matched encoder ablation user-result fixture: OK")
