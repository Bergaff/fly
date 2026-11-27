# Series123 — genuine user replication

The uploaded `summary-63.json` is archived unchanged. SHA-256: `297a6fb10db6a87f7f401bc88f8f2bb39e9983bde6f42cba185c2f3fb2e48ac4`.

## Reproduction

The user run exactly reproduced every deterministic RMSE, success-rate, switch-recovery, noise, partial-observation, cue-loss, and extra-delay value from the local Series123 result. This confirms the frozen seeds, inputs, model fitting, and closed-loop simulation are reproducible across the two runs.

| Model | Clean RMSE ↓ | Clean success ↑ | Switch error ↓ | User mean latency |
|---|---:|---:|---:|---:|
| Memoryless ridge |0.20420 |60.03% |0.22037 |30.10µs/step |
| History-4 ridge |0.21547 |54.42% |0.23261 |29.91µs/step |
| Random reservoir61 |0.20423 |59.97% |0.22204 |53.71µs/step |
| Graph reservoir61 |0.20501 |59.17% |0.22225 |49.47µs/step |
| Privileged oracle |0.17068 |78.33% |0.17353 |23.00µs/step |

Timings are platform-sensitive Python/NumPy wall measurements. The primary deterministic conclusion does not depend on them.

## Frozen decision

**Graph advantage remains NO-GO.** The graph reservoir did not beat either the matched random reservoir or the smaller memoryless ridge on clean RMSE/success. Under stronger noise it beat the random reservoir (57.50% versus54.14% success), but that isolated stress result cannot override the preregistered requirement to win against both controls across primary and stress metrics.

Cue loss again failed to hurt the learned controllers, confirming that the present task/model pair does not make effective use of the short context cue. The privileged-oracle gap remains real, but it does not demonstrate that the graph can recover the missing information.

## Boundary

This specific Series123 replication is a reproducible synthetic engineering NO-GO and does not rerun a body. Earlier Series100–112 used official FlyGym/NeuroMechFly, but their physical evidence cannot be transferred automatically to this new Graph reservoir. This remains neither living-neuron validation nor a whole-brain or general-intelligence result.
