# Series122 — same-task Graph Core baseline benchmark

## Question

On the exact narrow four-candidate weighted61-to-8 routing operation used in Series121, how do the exact dot-product solver, a hand rule, additive linear ridge, a minimal diagonal-bilinear model, and a parameter-matched MLP compare on accuracy, latency, new-seed cases, input noise, dropout, and channel ablation?

## Frozen scope

- Exact-pinned Series116 61×8 paths SHA-256: `4186bb6fdbe0a0e81f8626469027976ade1d416ff0549af94b85fb1b07aa3ca1`.
- Disjoint train seed: `122000001`.
- Test seed: `121000001`, so the test prefix matches Series121.
- New-seed generalization: `122000003`.
- Default train/test sizes: 2,000/600 cases.
- Four candidates per case; random expected accuracy25%.
- The exact solver is an oracle by task definition.
- Qwen Series121 is imported only as an external prompted reference when the genuine60-case report is present.

## Models

1. exact weighted dot product; project provenance core is reported as4,214 scalars, although the isolated operation consumes supplied vectors;
2. max-weight-channel hand rule, zero fitted coefficients;
3. additive linear ridge over the16 raw vector/weight inputs,17 fitted coefficients including intercept;
4. diagonal bilinear ridge over the8 elementwise interactions,9 fitted coefficients including intercept;
5. one-hidden-layer ReLU MLP with width234 and4,213 trainable parameters, approximately matching the4,214-scalar project-core accounting.

## Boundaries

This is a same-task arithmetic baseline benchmark. It is not a closed-loop controller comparison, whole-brain model, biological validation, or general-intelligence benchmark. A tiny bilinear model can exactly express a dot product, so it may match the oracle; if it does, that is evidence that the narrow operation does not require the full graph-core capacity.

Run `experiments\RUN-GRAPH-CORE-BASELINES-122.bat` and return `summary.json`.
