# Series107: grooming temporal-order repair tournament

## Why this is a new series

Series106 remains a frozen physical no-go. Its aggregate shuffled-input result passed 9/12, but head-directed grooming passed only 1/4 against the required2/4. Series107 does not alter that threshold, reuse those final cases for fitting, or rerun IDs1234–1245. It is a separately preregistered supervised development series intended to repair temporal-order specificity before any new physical final.

## Frozen inputs

- Series107 runner SHA-256: `822502bfc8a54d1511768f6922cf42429d17635f955ca142d0ea613acb2a2a20`;
- Series106 runner SHA: `282a7a87ae43b3c6a5b2432c01495c564ee3dc3e1247c0230015917ada5ea5fa`;
- genuine Series106 no-go SHA: `1eadcbcfea31c973f9993da16be7cd0b01998d2f4c6c7aa27c54b4c08da00be9`;
- unchanged base model SHA: `1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1`.

The Series105D classifier and trajectory experts remain unchanged. Series107 may train only a temporal-order validity adapter. It uses generated validity/action labels and actual demonstrator trajectories, so all outcomes are supervised engineering evidence.

## New split

All generated motion hashes must be disjoint from prior outcomes and from each other.

- train: IDs1246–1305,60 cases,20/action;
- selection: IDs1306–1323,18 cases,6/action;
- untouched conditional final: IDs1324–1341,18 cases,6/action;
- each official-eye capture is checkpointed;
- final remains untouched unless an adapter passes selection.

## Eight declared ideas

Every detector receives deterministic temporal-order diagnostics: lag1/2/4/8 absolute-change moments and cosine continuity, second differences and temporal energy statistics. A rejected visual sequence uses the exact base model's zero-input target; an accepted sequence uses the unchanged base output.

The tournament crosses three frozen choices: global versus action-specific detector, linear versus fixed quadratic diagnostics, and train-minimum (`q00`) versus 5th-percentile (`q05`) valid threshold. This gives eight declared adapters. `q00` prioritizes retaining genuine sequences; `q05` is the more aggressive shuffled-sequence rejection rule.

Train data fit detector ridges and thresholds only. Selection chooses among the eight fixed ideas. No selection/final row is used for fitting.

## Frozen selection and final gate

For every18-case split:

- action identity at least12/18;
- every candidate sequence accepted,18/18;
- candidate truth-RMSE wins at least12/18 against neutral, reversed, zero and shuffled input;
- within each action, wins at least4/6 against each control;
- candidate target distinct from every control target.

Among passing selection adapters, choose minimum candidate RMSE, then adapter name. The same gate is applied once to untouched final. No threshold may be changed after outcome.

## Run

Double-click `experiments\RUN-GROOMING-TEMPORAL-ORDER-REPAIR-107.bat`. Choose:

1. the original Series105D run folder or its `result` folder;
2. completed result89D;
3. production source84Z.

The GUI supports new run and checkpoint continuation, displays percentage/ETA and opens result or a copyable error report. A dependency/model/path failure is not a scientific no-go.

## Decision boundary

A pass means only that a supervised temporal-order adapter is a development candidate. It authorizes preparation of a separately frozen Series108 with new untouched physical motions and exact base-model plus adapter loading. It is not a Series106 pass and not physical, biological, FlyVis/FlyWire, connectome, living-fly or mirror-neuron evidence. A no-go closes this declared repair tournament without threshold weakening.
