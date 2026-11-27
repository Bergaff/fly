# Series119 — frozen out-of-family stress replication of A/B/C

## Why this is next

Series118 passed all three digital gates, but its selected configuration had only one24-replicate development bundle and all final cases remained inside the same generator family. Series119 addresses winner-noise/generalization risk without reopening adaptation. It cannot resolve absent biological action labels or same-neuron living-fly evidence.

## Frozen contract

The runner exact-loads genuine Series118 SHA `f1a5751b…` and runner SHA `d75169f8…`. Configuration is fixed before execution: `alpha=.125`, `beta=.5`, `ridge=.01`, `subset=20`, `derivative=0`. There is no development, fitting of configuration, selection, threshold change or post-result tuning. New seeds start at `119900000`.

Every bundle tests three predeclared out-of-family profiles, eight replicates each:

| Profile | edge dropout | edge log-noise sigma | dropped DN channels | case noise sigma |
|---|---:|---:|---:|---:|
| mild |5% |0.12 |0 |0.18 |
| medium |10% |0.18 |1 |0.22 |
| severe |15% |0.24 |2 |0.28 |

Pairing, independently retrained shuffled structure, reversed identity, shuffled label and zero controls remain. A measures stressed structural rank stability; B measures action readout versus shuffled structure; C measures observe/execute margin against the strongest control.

## Preregistered gate

Overall: A mean≥.95 and minimum≥.85; B accuracy≥.85, shuffled≤.75 and difference≥.10; C margin≥.20, strongest-control advantage≥.10 and positive-advantage win rate≥.80.

Severe profile must additionally retain A mean≥.95; B accuracy≥.65 and difference≥.05; C margin≥.20, advantage≥.10 and win rate≥.70. All clauses are required.

The default GUI targets about four active hours using calibration, SQLite checkpoints, Start new/Continue/Pause, workers2/4/6/Max, percentage and ETA. The genuine first run exposed a scheduler-only defect: serial calibration overestimated six-worker NumPy/BLAS throughput and produced14h20m53s instead of4h. Future runs now calibrate concurrent full bundles under the selected worker load; the completed frozen result and gates are unchanged. Regardless of outcome, biological and scientific-biological flags remain false.

Run: `experiments\RUN-FROZEN-THREE-DIRECTION-STRESS-119-4H.bat`.
