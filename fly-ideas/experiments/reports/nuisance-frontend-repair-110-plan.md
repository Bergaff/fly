# Series110: nuisance normalization front-end repair

## Frozen reason

Series109 failed because the Series107 adapter rejected every genuine dim and low-contrast candidate. The base model often remained better than the zero fallback, so Series110 repairs the front end rather than retraining the base trajectory experts or weakening Series109 gates.

- Series110 runner SHA: `1d15c85d5969d20f82798249f302cd5f0728a3ad74d7d233c2a26c90588316c1`;
- Series109 runner SHA: `691dbd14b76c1be975890236d1be81a9f8868b8825bb83846081730eaaf1f42b`;
- exact Series109 no-go SHA: `e7cfc5068fb53ae69782d3d31ce03e16605c044699a3a41590193a5276c99f03`;
- exact base SHA: `1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1`;
- exact adapter SHA: `4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57`.

Series109 IDs1360–1377 are outcome data and cannot be used for selection.

## New split

- selection IDs1378–1395:18 cases, one per action×domain;
- untouched conditional final IDs1396–1413:18 cases;
- same six nuisance families but new motions/seeds and slightly wider speed envelope;
- final is captured only if at least one declared front end passes selection.

## Six declared deterministic front ends

1. raw baseline;
2. sequence-level2nd–98th percentile stretch;
3. per-frame2nd–98th percentile stretch;
4. sequence z-score mapped to fixed mean/range;
5. sequence percentile stretch plus three-frame temporal smoothing;
6. sequence percentile stretch plus fixed cross-shaped spatial smoothing.

No neural/model weights are refit. Selection uses generated action/truth outcomes and therefore remains supervised engineering development.

## Frozen gate

On each18-case selection/final split:

- candidate accepted, shuffled rejected and action correct each≥15/18;
- candidate/shuffled validity and adapter gain each≥2/3 within every nuisance domain;
- candidate wins≥12/18 against neutral, reversed, zero and repaired shuffled;
- wins≥4/6 within every action and≥2/3 within every nuisance domain against every control;
- adapter gain≥12/18 and≥2/3/domain;
- candidate targets distinct from those four controls.

Among passing selection front ends, choose minimum candidate RMSE then name. Apply the same gate once to untouched final. No threshold changes after outcome.

## Run

Double-click `experiments\RUN-NUISANCE-FRONTEND-REPAIR-110.bat`, then choose original Series105D run/result, original Series107 run/result, result89D and source84Z.

A pass is non-physical development authorization for a separately frozen physical validation. It does not rewrite the Series109 no-go and is not hardware-camera, biological, FlyVis/FlyWire, living-fly or mirror-neuron evidence.

## Genuine outcome

Complete result SHA `e93208643c0c1229fe27d8ffabacd4680bb42153a05bcec89900e1deb97e1fd3` is a selection no-go; final remained untouched. Percentile normalization repaired dim/low-contrast acceptance. `percentile_temporal` achieved kept/rejected/action18/18 and RMSE0,064890 but failed reach-neutral3/6<4 and gain1/3<2 for noise/shift/dropout. No threshold is weakened. Series111 prospectively defines an operational safe-abstention gate on fresh data, retaining validity/specificity while reporting—not incentivizing—fallback RMSE harm.
