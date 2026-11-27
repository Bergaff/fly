# Series122 — local same-task baseline result

Result SHA-256: `8e29b0de5f4f5d09d05465dde1ce079d80cd5341958a572143dc94c1bfaf2054`.

## Protocol

- 2,000 train cases, 600 frozen test cases, and 600 disjoint new-seed cases.
- Four candidates per case; random expected accuracy25%.
- Exact-pinned Series116 61×8 paths.
- Test prefix matches Series121.
- Accuracy is the primary deterministic result. Timings are descriptive for this local Linux run and are platform-sensitive.

## Results

| Method | Count | Frozen test | New seed | Noise0.02 | Input dropout0.10 | Mean single-channel ablation | Local mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Exact dot | 4,214 project-core scalars* | 600/600 (100%) | 100% | 70.0% | 65.33% | 77.27% | 0.142µs/case |
| Max-weight-channel rule | 0 fitted | 343/600 (57.17%) | 57.33% | 53.67% | 53.33% | 53.0% | 0.085µs/case |
| Additive linear ridge | 17 | 243/600 (40.50%) | 40.17% | 26.17% | 30.67% | 34.69% | 0.064µs/case |
| Diagonal bilinear ridge | 9 | 600/600 (100%) | 100% | 70.0% | 65.33% | 77.27% | 0.094µs/case |
| Parameter-matched MLP | 4,213 | 547/600 (91.17%) | 90.0% | 69.33% | 64.33% | 67.81% | 6.450µs/case |
| Qwen2.5:7b, external Series121 | 7.616B | 21/60 (35%)* | not run | not run | not run | not run | 0.297s/case* |

`*` The4,214 count is the provenance accounting of the full project core, not the minimal parameter requirement of the isolated dot-product operation. Qwen used only the matching first60 test cases and end-to-end prompted wall time, so it is an external reference rather than a trained baseline.

## Main finding

A nine-parameter diagonal-bilinear model exactly expresses the benchmark operation and matched the exact solver on all frozen and new-seed cases. Therefore Series122 does **not** support a claim that the narrow Series121 operation requires the full4,214-scalar core. The parameter-matched MLP was larger, slower, and less accurate. The hand rule and additive linear model did not recover the interaction reliably.

All methods received the same frozen noise tensor and the same frozen dropout tensor. The exact and bilinear methods consequently match under perturbation and channel ablation because they compute the same function.

## Boundaries

This result characterizes one arithmetic ranking operation. It is not evidence about a closed-loop fly controller, graph-core superiority, a whole brain, living neurons, biology, or general intelligence. The strongest next test must use an actual temporal behavior/control task where the graph supplies information unavailable to a nine-parameter dot-product baseline.
