# Series108: frozen grooming-repair physical validation

## Why one more test

Series107 repaired shuffled-sequence specificity on a supervised non-physical untouched final. That is not yet evidence that the repaired policy works through an official physical MOTOR body. Series108 is the decisive bridge before any broader claim: it exact-loads both frozen artifacts and performs one new class-balanced physical final without training, selection or tuning.

## Frozen artifacts

- Series108 runner SHA: `7fd7efb4c6219834bafc2ca7b3098e5c1208dd036f5b46f4c2ac34fc911960d4`;
- Series107 runner SHA: `822502bfc8a54d1511768f6922cf42429d17635f955ca142d0ea613acb2a2a20`;
- genuine Series107 result SHA: `6628a5f4d6655f926507e7b39591ea14208e8f4d4240dbec22bf5f86b211a5b6`;
- exact Series105D base model SHA: `1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1`;
- exact Series107 `global_linear_q00` adapter SHA: `4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57`.

Both original result folders are required. Summary JSON files do not contain the model arrays.

## Untouched physical design

- IDs1342–1359,18 new motions,6 per action;
- generated seeds108100–108152;
- amplitudes0,62–0,98 and speeds0,72–1,22;
- all hashes must be disjoint from every prior outcome;
- official demonstrator capture and official observer eyes;
- unchanged temporal pool, frozen classifier/experts and frozen validity adapter;
- accepted inputs use exact base target; rejected inputs use exact base zero-input target;
- official observer MOTOR body with the established closed-loop bridge.

Six conditions per case,108 physical rollouts total:

1. repaired candidate;
2. neutral visual;
3. reversed visual;
4. zero input;
5. deterministically shuffled visual;
6. true open loop using candidate target without q/dq feedback.

## Frozen primary gate

1. all18 candidate rollouts finite, ground-contacting and thorax z0,15–2,5mm;
2. mean candidate tracking RMSE≤0,20rad;
3. candidate validity accepted18/18;
4. shuffled input rejected≥15/18 and≥4/6 within every action;
5. action identity≥15/18 and≥5/6 within every action;
6. candidate truth-RMSE wins≥12/18 against neutral/reversed/zero/shuffled;
7. within every action candidate wins≥3/6 against each of those controls;
8. candidate wins≥15/18 against true open loop;
9. candidate target differs from neutral/reversed/zero/shuffled in every case.

No criterion may be weakened after outcome. Series106 remains a no-go regardless of Series108.

## Windows run

Double-click `experiments\RUN-FROZEN-GROOMING-REPAIR-PHYSICAL-108.bat`, then choose:

1. original Series105D run folder or its `result`;
2. original Series107 run folder or its `result`;
3. completed result89D;
4. production source84Z.

The GUI displays percentage/ETA and automatically opens the result or a copyable error report. A missing artifact, wrong SHA or dependency failure is operational, not a scientific no-go.

## Interpretation boundary

A pass establishes class-balanced engineering physical viability for this frozen supervised generated-action policy on new simulated bodies. It still does not establish biological learning, a living fly, real muscles, FlyVis/FlyWire/connectome mapping or mirror neurons. `scientific_result` remains false. A fail closes this frozen repaired-policy physical attempt without rerunning its final until pass.
