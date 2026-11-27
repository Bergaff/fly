# Series106 genuine Windows result

## Integrity and completion

Uploaded `summary-46.json` is preserved byte-for-byte as `frozen-action-aware-physical-validation-106-user-result.json`.

- result SHA-256: `1eadcbcfea31c973f9993da16be7cd0b01998d2f4c6c7aa27c54b4c08da00be9`;
- status: `completed`, mode: `full`;
- Series106 runner SHA: `282a7a87ae43b3c6a5b2432c01495c564ee3dc3e1247c0230015917ada5ea5fa`;
- Series105D runner/result/model SHAs exactly match the preregistration;
- training, selection and post-result tuning are all `false`;
- all 12 fixed motion IDs 1234–1245 are present;
- every case contains all six physical conditions, for 72 recorded rollout summaries;
- all candidate/control target-distinctness checks pass.

This is a complete run, not a launcher or dependency failure.

## Frozen primary result: no-go

The preregistered primary gate did **not** pass:

- candidate safety/contact: 12/12, required 12/12;
- mean candidate tracking RMSE: `0.0605182 rad`, required at most `0.20`;
- action classification: 12/12, required at least 9/12;
- action classification by class: 4/4 for all three classes, required at least 3/4;
- aggregate candidate truth-RMSE wins:
  - neutral visual: 11/12, required at least 8/12;
  - reversed visual: 11/12, required at least 8/12;
  - zero input: 12/12, required at least 8/12;
  - shuffled visual: 9/12, required at least 8/12;
  - true open loop: 12/12, required at least 10/12;
- targets distinct: true.

The sole failed gate was the preregistered per-action specificity requirement. For `head_directed_grooming`, candidate beat shuffled visual in only **1/4** cases; the minimum was **2/4**. It won case 1235, but lost cases 1238, 1241 and 1244. Case 1241 was close (`0.104718` candidate versus `0.104437` shuffled), but the frozen rule is strict and cannot count it as a win.

All other per-action control gates passed:

| Action | Neutral | Reversed | Zero | Shuffled |
|---|---:|---:|---:|---:|
| foreleg rubbing | 4/4 | 4/4 | 4/4 | 4/4 |
| head-directed grooming | 4/4 | 3/4 | 4/4 | **1/4** |
| reach/withdraw | 3/4 | 4/4 | 4/4 | 4/4 |

Mean truth RMSEs were candidate `0.0803124`, neutral `0.1363493`, reversed `0.1356029`, zero `0.1649666`, shuffled `0.1246509`, and open loop `0.1386323` rad.

## Interpretation

Series106 is a genuine, narrow physical no-go under its frozen gate. The selected Series105D model transferred well enough for safety, tracking, action identity, aggregate specificity and feedback dependence, but it did not establish class-balanced visual specificity: head-directed grooming was insufficiently distinguishable from shuffled visual input.

Therefore:

- `passed=false`;
- `physical_development_candidate=false`;
- `scientific_result=false`;
- do not weaken the 2/4 per-class threshold;
- do not reinterpret the 9/12 aggregate shuffled win as a pass;
- do not rerun the same fixed final until it passes;
- do not describe this as physical confirmation, biological learning, FlyVis/FlyWire/connectome evidence, living-fly behavior or mirror neurons.

Any further work must be a separately preregistered development series with new training/selection data and a later untouched physical final. Series106 itself remains closed as a no-go.
