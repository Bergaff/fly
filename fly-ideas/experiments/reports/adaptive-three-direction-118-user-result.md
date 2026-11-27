# Series118 — genuine four-hour Windows result

Exact uploaded `summary-57.json` SHA-256: `f1a5751b664e28f485f25cabb8949a266debb275aa8af8d9957b292108f0c5b1`.

## Execution integrity

- Status: `completed`; six workers; target four hours.
- Active wall time: 14,643.625 s = 4 h 4 min 3.625 s (1.69% above target).
- Development: 1,238 generations, 29,742 bundles and 713,808 bootstrap replicates.
- Untouched frozen final: 7,409 bundles and 177,816 replicates.
- Total: 37,151 bundles and 891,624 replicates.
- Adaptive development was allowed; final adaptation was explicitly false. Final used the selected configuration `alpha=.125, beta=.5, ridge=.01, subset=20, derivative=0`.
- All pinned Series116/117 source hashes match the preregistered protocol.

## Untouched final

| Direction / control | Result | Gate | Decision |
|---|---:|---:|---:|
| A mean stability | 0.998255 | >=0.90 | pass |
| A minimum stability | 0.995505 | >=0.70 | pass |
| B accuracy | 0.974546 | >=0.90 | pass |
| B shuffled accuracy | 0.672473 | <=0.75 | pass |
| C margin | 0.925103 | >=0.10 | pass |
| C advantage over strongest control | 0.414762 | >=0.02 | pass |
| C positive-advantage win rate | 0.986582 | >=0.80 | pass |

Final control margins: pairing -0.508228, retrained shuffled structure 0.451291, reversed identity 0.000222, shuffled label 0.234050 and zero approximately 0. The strongest mean control was structure, leaving a real-control margin difference of 0.473812; the reported mean per-replicate strongest-control advantage is 0.414762.

## Bounded conclusion

All three preregistered **digital** directions passed their untouched-final gates. This advances the computational pipeline beyond the Series117 no-go under the Series118 adaptive-development protocol. It does not retroactively change Series117, demonstrate same-neuron biological observation/execution responses, validate action labels in a living fly, or establish biological mirror neurons. The result itself correctly keeps `biological_claim=false` and `scientific_biological_result=false`.

The selected configuration had only one 24-replicate development bundle in `selected_development`; selection therefore has winner-noise risk. The very large untouched final gives a strong honest test of that frozen choice against the declared digital gates, but it does not remove the biological and model-construction limitations.
