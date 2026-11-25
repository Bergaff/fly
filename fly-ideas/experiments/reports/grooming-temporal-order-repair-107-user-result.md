# Series107 genuine Windows result

## Integrity and completion

Uploaded `summary-47.json` is preserved byte-for-byte as `grooming-temporal-order-repair-107-user-result.json`.

- result SHA-256: `6628a5f4d6655f926507e7b39591ea14208e8f4d4240dbec22bf5f86b211a5b6`;
- status: `completed`;
- Series107 runner SHA: `822502bfc8a54d1511768f6922cf42429d17635f955ca142d0ea613acb2a2a20`;
- Series106 runner/result and Series105D base-model SHAs exactly match the preregistration;
- all 60 train and 18 selection motions are recorded;
- all eight declared adapters were evaluated on selection;
- a passing adapter was selected before the 18 untouched final cases were captured;
- final IDs1324–1341 are complete, six per action and five controls per case.

This is a complete run, not an early exit.

## Selection

Two adapters passed every frozen selection gate:

- `global_linear_q00`: candidate kept18/18, action18/18, wins neutral18/18, reversed17/18, zero18/18, shuffled18/18, candidate RMSE `0.041166`;
- `global_quadratic_q00`: identical selection metrics and candidate RMSE.

The preregistered tie-break by candidate RMSE then adapter name selected `global_linear_q00`. Its artifact SHA-256 is:

`4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57`

The six other adapters failed because one or more genuine candidate sequences were rejected (14–17/18 kept), which also caused target-distinctness failures. They were not eligible regardless of their control wins.

## Untouched final: pass

The selected adapter passed every frozen final gate:

- candidate accepted: 18/18;
- action identity: 18/18;
- aggregate truth-RMSE wins:
  - neutral visual: 17/18;
  - reversed visual: 17/18;
  - zero input: 18/18;
  - shuffled visual: 18/18;
- per-action wins:
  - foreleg rubbing: 6/6 against every control;
  - head-directed grooming: 6/6 against every control;
  - reach/withdraw: 5/6 neutral,5/6 reversed,6/6 zero and6/6 shuffled;
- candidate target distinct from every control target: true;
- mean candidate truth RMSE: `0.0457828 rad`;
- control means: neutral `0.139400`, reversed `0.153545`, zero `0.190738`, shuffled `0.190738 rad`.

For the selected adapter, all genuine candidate, neutral and reversed sequences were accepted in both selection and final; all shuffled sequences were rejected. Rejected shuffled sequences use the exact base model's zero-input target, explaining the identical zero/shuffled mean RMSE. This behavior is declared by the protocol rather than inferred after the result.

## Decision

- `passed=true`;
- `development_candidate=true`;
- `scientific_result=false`.

The grooming repair succeeded on the supervised non-physical development benchmark. In particular, head-directed grooming improved from the Series106 physical failure of1/4 versus shuffled input to6/6 on the new untouched Series107 non-physical final. This does **not** retroactively turn Series106 into a pass and is not yet physical confirmation.

A separately frozen Series108 is authorized, subject to exact loading of both:

1. the original Series105D `selected_action_aware_model.npz`, SHA `1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1`;
2. the original Series107 `selected_grooming_repair_adapter.npz`, SHA `4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57`.

The uploaded summary contains the adapter identity and SHA but not its arrays. Preserve the original Series107 result folder. Series108 must use new untouched physical motions, no retraining/selection/tuning, and retain class-balanced specificity gates. No outcome supports biological learning, FlyVis/FlyWire/connectome mapping, living-fly behavior or mirror-neuron claims.
