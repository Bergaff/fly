# Series109: frozen visual-nuisance robustness and adapter ablation

## Purpose

Series108 established class-balanced physical viability on the original simulated visual domain. Series109 stops same-benchmark tuning and asks a different question: does the exact repaired policy survive declared visual-domain perturbations and does the Series107 adapter causally improve shuffled-input separation relative to a base-only ablation?

This remains a simulated engineering test. The nuisances are deterministic post-capture pixel/frame transformations, not physical camera hardware.

## Frozen lineage

- Series109 runner SHA: `691dbd14b76c1be975890236d1be81a9f8868b8825bb83846081730eaaf1f42b`;
- Series108 runner SHA: `7fd7efb4c6219834bafc2ca7b3098e5c1208dd036f5b46f4c2ac34fc911960d4`;
- genuine Series108 result SHA: `9253e4bcb60ee9ea3d5fa990561e4807ee31eaf51b457fd198735b4d90ec0e64`;
- exact base SHA: `1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1`;
- exact adapter SHA: `4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57`;
- no training, selection or post-result tuning.

## Cross-domain final

New IDs1360–1377, one case per action in each of six domains. Amplitude0,58–1,02 and speed0,56–1,34 also widen the action-duration envelope.

Declared visual domains:

1. dim: intensity×0,55;
2. bright: intensity×1,28 plus offset;
3. low contrast: deviations from per-frame mean×0,52;
4. sensor noise: deterministic Gaussian σ3,5% of range;
5. horizontal shift: deterministic3-pixel image shift;
6. frame dropout: every fifth frame repeats its predecessor.

Perturbations are applied after official-eye capture and before frozen edge/temporal processing. Demonstrator truth and official physical bodies are unchanged.

## Conditions and ablation

Eight physical conditions per case,144 rollouts:

- repaired candidate under nuisance;
- base candidate with adapter bypassed;
- repaired neutral visual;
- repaired reversed visual;
- repaired shuffled visual;
- base shuffled visual with adapter bypassed;
- zero input;
- true open loop.

The base-candidate ablation records whether candidate behavior differs when the adapter rejects a nuisance. The shuffled ablation is the causal repair control: adapter gain is counted only when repaired-shuffled truth RMSE is larger than base-shuffled RMSE, increasing candidate-versus-shuffle separation.

## Frozen primary gate

- all18 repaired candidates safe/contact and mean tracking≤0,20rad;
- candidate accepted, shuffled rejected and action correct each≥15/18;
- for each action, each of those three counts≥4/6;
- in each nuisance domain, candidate accepted and shuffled rejected≥2/3;
- candidate wins≥12/18 against neutral, reversed, repaired shuffled and zero;
- candidate wins≥3/6 within every action and≥2/3 within every domain against each control;
- candidate wins≥15/18 against true open loop;
- adapter gain≥12/18,≥3/6 within every action and≥2/3 within every domain;
- candidate targets distinct from neutral/reversed/repaired-shuffled/zero in every case.

No criterion may be weakened after outcome.

## Windows run

Double-click `experiments\RUN-FROZEN-NUISANCE-ROBUSTNESS-109.bat`, then choose the original Series105D run/result, original Series107 run/result, result89D and production source84Z. The GUI shows percentage/ETA and opens result or a copyable error report.

## Interpretation

A pass supports frozen engineering robustness to these six declared digital visual nuisances and demonstrates adapter contribution under the preregistered ablation metric. It is not hardware-camera transfer, biological vision, living-fly evidence, real muscles, FlyVis/FlyWire/connectome validation or mirror neurons. `scientific_result` remains false.
