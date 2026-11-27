# Series123 — local synthetic temporal closed-loop result

Result SHA-256: `a11cf2744fd2361abbf8a29947dbd03486739b480b2a1e68bd91d039db63549b`.

## Primary frozen result

| Model | Count | Clean RMSE ↓ | Success ↑ | Switch error ↓ | Local latency |
|---|---:|---:|---:|---:|---:|
| Memoryless ridge |560 | **0.20420** | **60.03%** | **0.22037** |15.96µs/step |
| History-4 ridge |2,216 |0.21547 |54.42% |0.23261 |20.62µs/step |
| Random reservoir61 |3,049 |0.20423 |59.97% |0.22204 |37.53µs/step |
| Graph reservoir61 |3,049 |0.20501 |59.17% |0.22225 |29.69µs/step |
| Privileged oracle* |0 fitted |0.17068 |78.33% |0.17353 |11.57µs/step |

`*` The oracle sees hidden future target and context and is not a deployable competitor.

## Stress summary

The graph reservoir reached57.50% success under stronger observation noise,59.33% under added partial observation,58.28% when the initial context cue was removed, and19.64% with two extra sensor/motor delay steps. The matched random reservoir reached54.14%,59.33%,58.97%, and19.25% respectively. Memoryless ridge reached57.86%,59.58%,61.86%, and23.19%.

## Decision

**Graph advantage: NO-GO.** All requested temporal/control ingredients are present, but the Series116 graph reservoir did not beat the matched random reservoir or even the smaller memoryless ridge on the primary clean metrics. The privileged oracle gap shows that additional task information can improve control, but this implementation did not extract that advantage from graph recurrence.

The cue-loss condition not hurting—and sometimes slightly improving—non-oracle models indicates that the learned controllers largely ignored or failed to exploit the short cue. This is a diagnostic limitation, not evidence that context is unnecessary. A future development series would need a preregistered context-decoding check and task construction in which remembering the cue is demonstrably necessary before another untouched final.

## Boundaries

This is a deterministic synthetic engineering benchmark seeded by frozen project artifacts. It is not a physical FlyGym/NeuroMechFly experiment, a living-neuron result, a whole-brain simulation, or evidence for general intelligence.
