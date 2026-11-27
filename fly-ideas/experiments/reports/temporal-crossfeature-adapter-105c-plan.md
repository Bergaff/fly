# Series105C: temporal cross-feature official-eye adapter

## Frozen decision before outcome

Series104 direct transfer and Series105B diagonal adapter remain genuine no-go results. Series105C tests one new bounded hypothesis: official and synthetic72-dimensional cosine states may require mixing between axes and temporal coefficients, not independent scale/offset.

- Runner SHA-256: `60c74e44bca8c64ecc667e6eb8705f6163565cdd0509230ca8872d50ac4b206f`
- exact Series105A+B result SHA: `92715b54fde5fb259ce3947e35edf4f8ba178f659c5de01096546ca739af6a14`;
- exact Series105A+B runner SHA: `b070fff687dfcfd263c6868b59954283486dd84b5a4e07156816f333a13dae67`;
- required prior state: `development_candidate=false`, `scientific_result=false`;
- Series104/105B results are never overwritten or reinterpreted.

## Data split

All motions are generated and hash-checked before outcomes.

- train IDs1069–1098:30 motions,10 per action;
- held validation IDs1099–1107:9 motions,3 per action;
- training seeds105300–105392;
- validation seeds105500–105522;
- validation is never used for fit, ridge selection or threshold selection.

For each training motion the input is the official-eye72 coefficient state. The paired target is the mean frozen state of the same movement under synthetic views801–804. Action labels and actual trajectory truth are not used for fitting.

## Temporal cross-feature model

Official inputs and synthetic targets are standardized from train only. A full72×72 ridge matrix mixes six axes and12 temporal cosine coefficients. Candidate ridges are fixed:0,01;0,1;1;10;100.

Ridge selection uses five train-only folds grouped by replicate. Each fold contains two complete three-action replicates. Criterion is mean paired synthetic-state normalized RMSE; exact ties choose the larger ridge. The selected ridge is refit on all30 train pairs. No validation feedback or post-result tuning is allowed.

The old coordinate-wise diagonal transform is refit on the same new training pairs and retained only as a blocking control.

## Held non-physical development gate

On nine validation motions the cross-feature candidate must:

1. classify action correctly≥6/9;
2. win target-to-actual-demonstrator RMSE≥6/9 against each control: same-data diagonal adapter, raw frozen official state, neutral visual, reversed visual, zero state and shuffled state;
3. produce target hashes distinct from diagonal/neutral/reversed/zero/shuffled in all cases;
4. have lower mean truth RMSE than diagonal and raw frozen.

Pass sets only `development_candidate=true` and permits a separately frozen untouched physical Series106. It is not physical evidence. Fail closes this exact cross-feature hypothesis without weakening thresholds.

## Windows run

Double-click `experiments\RUN-TEMPORAL-CROSSFEATURE-ADAPTER-105C.bat`, then choose the completed result89D and production84Z folders. The GUI runs paired training, train-only CV and held validation sequentially, shows overall percentage and ETA, and automatically opens result or a copyable error report.

## Limitations

This is a newly trained engineering adapter. It is not unchanged frozen89E replication, a rescue of Series104/105B, biological observation-to-action, FlyVis/FlyWire mapping, living-animal evidence or mirror-neuron evidence. Physical Series106 remains blocked unless every frozen105C development criterion passes.

## Genuine Windows result

Run completed, selected ridge100 by train-only CV NRMSE0,146472, and evaluated all9 held cases. Cross-feature improved diagonal9/9 and raw9/9; mean RMSE0,160217 was below diagonal0,189996, raw0,495953 and zero0,169557. Nevertheless action correct4/9<6, neutral wins5/9<6 and zero wins3/9<6; reversed7/9 and shuffled9/9 passed. Eight cases were predicted reach/withdraw and no head-directed case was recognized. `passed=false`, `development_candidate=false`, `scientific_result=false`. Exact JSON SHA `d9f8c8400b4cff10ecc5b20132e06cb2ccb07f3cee3075d461a1c1622abcda39`; files `temporal-crossfeature-adapter-105c-user-result.json/.md`. Physical Series106 remains blocked.
