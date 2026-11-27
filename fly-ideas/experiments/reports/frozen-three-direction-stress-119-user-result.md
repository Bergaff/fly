# Series119 — genuine frozen stress-replication result

Uploaded `summary-58.json` SHA-256: `2badd87b4efe717458782e71b865b8d426c4526b75893a91e784d43c1aa959d1`. The producing Series119 runner SHA was `cd1b98a387ff0e4c14a13f3e931d8de6316dbc8ea5fa770311c44cc3ab50aeba`.

## Runtime and workload

- Status: completed; six workers; no adaptive search or post-result tuning.
- Target:4 hours. Actual active wall time:51,653.062s =14h20m53.062s,3.587× target (258.7% over target).
- Cause: the original scheduler calibrated a small serial workload and multiplied by worker count. Concurrent NumPy/BLAS contention made actual throughput much lower. This is an engineering scheduling error, not a scientific protocol change.
-85,115 frozen bundles per profile;680,920 replicates per profile;2,042,760 total replicates.
- Exact genuine Series118 result/config and new `119900000+` seed namespace were retained.

## Overall frozen result

| Gate | Result | Required | Decision |
|---|---:|---:|---:|
| A mean stability |0.985471 |≥0.95 | pass |
| A minimum stability |0.877155 |≥0.85 | pass |
| B accuracy |0.867597 |≥0.85 | pass |
| B shuffled accuracy |0.630499 |≤0.75 | pass |
| B accuracy advantage |0.237098 |≥0.10 | pass |
| C margin |0.755749 |≥0.20 | pass |
| C strongest-control advantage |0.387098 |≥0.10 | pass |
| C positive-advantage win rate |0.944240 |≥0.80 | pass |

Overall control margins: pairing -0.421332, retrained shuffled structure0.328204, reversed identity0.001530, shuffled label0.140594 and zero approximately0.

## Severe-profile result

| Gate | Result | Required | Decision |
|---|---:|---:|---:|
| A mean stability |0.978089 |≥0.95 | pass |
| B accuracy |0.784869 |≥0.65 | pass |
| B advantage over shuffled |0.192198 |≥0.05 | pass |
| C margin |0.617366 |≥0.20 | pass |
| C strongest-control advantage |0.323383 |≥0.10 | pass |
| C positive-advantage win rate |0.897458 |≥0.70 | pass |

All preregistered overall and severe frozen stress gates pass. This materially strengthens the digital robustness conclusion and reduces Series118 winner-noise/generalization concern. It does not supply authoritative biological DN action labels, independent living-fly recordings, or same-neuron observation/execution evidence. The result correctly keeps `biological_claim=false` and `scientific_biological_result=false`.
