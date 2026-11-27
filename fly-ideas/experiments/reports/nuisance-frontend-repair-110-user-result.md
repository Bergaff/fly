# Series110 genuine Windows result

Result SHA-256: `e93208643c0c1229fe27d8ffabacd4680bb42153a05bcec89900e1deb97e1fd3`. The run is complete: all18 selection cases and all six declared front ends were evaluated. No front end passed, so the conditional final correctly remained untouched.

## What was fixed

Photometric normalization solved the main Series109 failure:

- `sequence_percentile` and `frame_percentile`: candidate kept18/18, shuffled rejected18/18, action17/18;
- `percentile_temporal`: kept18/18, rejected18/18, action18/18, candidate RMSE0,064890;
- `percentile_spatial`: kept17/18, rejected18/18, action18/18, candidate RMSE0,065865.

Thus dim and low-contrast acceptance recovered from0/3 to3/3 in all percentile variants.

## Why Series110 still failed

`percentile_temporal` was closest, but:

- reach/withdraw candidate beat neutral only3/6 versus required4/6;
- adapter-gain by domain was1/3 for sensor noise, horizontal shift and frame dropout versus required2/3.

`percentile_spatial` improved reach/neutral to4/6, but rejected one genuine horizontal-shift candidate and also had adapter-gain1/3 for noise and shift. Sequence/frame percentile variants had similar gain failures. Consequently no adapter was selected, final cases=0, `development_candidate=false`, `scientific_result=false`.

The adapter-gain metric asks the safe rejected-shuffle fallback to have larger truth RMSE than the base shuffled trajectory. That is not identical to operational validity: a safe abstention can correctly reject shuffled input without always making its trajectory numerically worse than an already-poor base shuffle. Series110 remains a valid no-go under its frozen rule; the rule cannot be removed retroactively.

A new series may preregister an operational robustness gate on fresh data: candidate acceptance, shuffled rejection, action identity, class/domain specificity and distinct targets. Base-shuffled RMSE gain should remain a reported ablation diagnostic rather than require intentionally harmful fallback behavior. A deterministic predicted-action route between temporal and spatial normalization is motivated because temporal is strongest overall while spatial repaired reach/neutral specificity.
