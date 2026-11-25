# Series109 genuine Windows result

## Integrity

The uploaded `summary-49.json` is preserved byte-for-byte as `frozen-nuisance-robustness-ablation-109-user-result.json`.

- result SHA-256: `e7cfc5068fb53ae69782d3d31ce03e16605c044699a3a41590193a5276c99f03`;
- status `completed`, mode `full`;
- runner SHA `691dbd14b76c1be975890236d1be81a9f8868b8825bb83846081730eaaf1f42b`;
- all18 IDs and144 rollout summaries are present;
- exact base/adapter and Series108 lineage match the frozen protocol;
- no training, selection or tuning occurred.

## Genuine robustness no-go

Series109 did not pass.

Successful gates included safety18/18, tracking0,061683rad, shuffled rejection17/18, action identity15/18, open-loop wins18/18 and aggregate adapter gain13/18.

The principal failure is domain-specific photometric sensitivity:

- dim candidate accepted0/3 and won0/3 against every repaired control;
- low-contrast candidate accepted0/3 and won0/3 against every repaired control;
- all six dim/low-contrast candidates fell back to the exact zero-input target, causing candidate/zero target equality and `targets_distinct=false`;
- overall candidate kept12/18 versus required15/18;
- aggregate wins were11/18 against neutral, reversed, repaired shuffled and zero versus required12/18.

Additional failures:

- sensor-noise foreleg was misclassified and its shuffled sequence was not rejected;
- adapter-gain by domain was only1/3 for sensor noise and1/3 for frame dropout versus required2/3;
- reach/withdraw action identity was4/6 versus the frozen per-action acceptance requirement implicit in the protocol.

The base candidate was often substantially better than the rejected repaired candidate under dim and low contrast, confirming that the failure is primarily the Series107 validity adapter's absolute-scale diagnostics rather than a total collapse of the trajectory experts. For example, dim grooming RMSE was0,1946 repaired/zero versus0,1444 base; low-contrast grooming was0,1939 repaired/zero versus0,0810 base.

## Decision and repair boundary

- `passed=false`;
- `robustness_candidate=false`;
- `scientific_result=false`.

Do not weaken the domain-balanced gate or reinterpret aggregate safety/open-loop success as robustness. Series108 remains a valid same-domain engineering physical pass, but does not generalize to dim/low-contrast inputs under the current adapter.

A separately preregistered Series110 is warranted. It should select among deterministic photometric/temporal normalization front ends on new nuisance development cases, preserve the exact base and adapter, and use a later untouched final. Series109 final IDs must not be used to fit or select that repair.
