# Series108 genuine Windows result

## Integrity and completion

Uploaded `summary-48.json` is preserved byte-for-byte as `frozen-grooming-repair-physical-108-user-result.json`.

- result SHA-256: `9253e4bcb60ee9ea3d5fa990561e4807ee31eaf51b457fd198735b4d90ec0e64`;
- status: `completed`, mode: `full`;
- Series108 runner SHA: `7fd7efb4c6219834bafc2ca7b3098e5c1208dd036f5b46f4c2ac34fc911960d4`;
- Series107 runner/result, Series105D base-model and Series107 adapter SHAs exactly match the preregistration;
- training, selection and post-result tuning are all false;
- all fixed IDs1342–1359 are present, six per action;
- every case contains all six conditions, for108 physical rollout summaries.

This is a complete genuine run.

## Frozen primary result: pass

Every preregistered gate passed:

- candidate safe/contact:18/18;
- mean candidate tracking RMSE: `0.0603408 rad`, required≤0.20;
- candidate validity accepted:18/18;
- shuffled validity rejected:18/18, including6/6 in every action, required≥15/18 and≥4/6;
- action identity:18/18, including6/6 in every action, required≥15/18 and≥5/6;
- aggregate candidate truth-RMSE wins:
  - neutral visual:17/18, required≥12/18;
  - reversed visual:14/18, required≥12/18;
  - zero input:18/18, required≥12/18;
  - shuffled visual:18/18, required≥12/18;
  - true open loop:17/18, required≥15/18;
- candidate target distinct from every input-control target in all cases.

Class-balanced control wins:

| Action | Neutral | Reversed | Zero | Shuffled |
|---|---:|---:|---:|---:|
| foreleg rubbing |6/6|6/6|6/6|6/6|
| head-directed grooming |6/6|5/6|6/6|6/6|
| reach/withdraw |5/6|3/6|6/6|6/6|

The reach/withdraw reversed result is exactly the frozen minimum3/6 and should be retained as a limitation. It is a pass, not evidence of a large margin.

Mean physical truth RMSEs were candidate `0.0791502`, neutral `0.1394046`, reversed `0.1381516`, zero `0.1702706`, shuffled `0.1702706`, and open loop `0.1421249 rad`. Candidate RMSE by action was foreleg `0.0957774`, head-directed grooming `0.0903623`, and reach/withdraw `0.0513108 rad`.

## Decision and scope

- `passed=true`;
- `physical_development_candidate=true`;
- `scientific_result=false`.

Series108 establishes the intended class-balanced **engineering physical viability** claim for the exact supervised Series105D base plus Series107 temporal-validity adapter on new generated motions and official simulated MOTOR bodies. The repaired head-directed grooming line passed: candidate/identity/shuffled rejection were6/6, and candidate beat shuffled input6/6 physically.

This does not retroactively change the Series106 no-go. The difference is attributable to the separately trained and frozen Series107 adapter.

It is now reasonable to stop tuning this benchmark and move to a broader preregistered robustness/transfer phase. A credible next phase should change nuisance factors or domain conditions rather than generate another near-identical seed set—for example camera/lighting/body perturbations, action-duration variation, and a separately held cross-domain final. It must preserve the exact base and adapter artifacts and should include an adapter-ablation control.

No result here establishes biological learning, a living fly, real muscles, FlyVis/FlyWire/connectome mapping or mirror neurons. Those would require different data and experiments, not additional claims from this simulator result.
