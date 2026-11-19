# Серия89B: preregistration bounded policy calibration development

## Причина

Series89 дала strict no-go: normal хуже zero и shuffled во всех1296 angle pairs,1253/1296 trials достигли hard limits. Thresholds89 не ослабляются, failed trials не исключаются, motions421–602 раскрыты. Series90 остаётся blocked.

89B является новой supervised engineering development series, а не повтором89 и не replication.

## Frozen identities

- runner88 SHA `888778dd5771f740e142747f0bad2eb1cadff8147bf01c6b2fe480c6952daa30`;
- no-go89 extract SHA `8bc6a9b55621c984a7ba5dfd2977f33fe6f061354c5c3018a04c42b1fccf3d75`;
- no-go89 source SHA `0b44d61b58b374ac95037ba8a853e23b0c48a1b8510a0b0f4c323ebb509d1105`;
- source model84Z read-only, source training запрещён.

## Разделение данных

Development:

- motions603–620,6 replicates ×3 actions;
-8 views301–308;
-144 visual cases;
- development truth разрешён только для fit одного calibrator.

Untouched final:

- motions621–638,6 replicates ×3 actions;
-12 views321–332;
-216 visual cases;
-3 initial profiles;
-648 embodied trials;
- final data не участвуют в fit или выборе.

Всего360 visual cases. Fixture не является научным результатом.

## Единственный development package

1. Common action-agnostic ridge calibrator `13→6`: six decoded target positions, six first differences, intercept; ridge0,08.
2. Smooth projection `0,78 × ±55° × tanh` и slew≤0,11rad/frame.
3. Proprioceptive/contact controller получает soft joint barrier начиная с0,72 ×55°.

Calibrator общий для actions/views, не получает action label. Это supervised synthetic engineering calibration, не autonomous learning.

## Final controls

На каждом final trial:

- candidate: calibrated projected policy + barrier closed loop;
- uncalibrated: original observer policy и прежний controller без barrier;
- zero-state;
- shuffled-state через fixed coefficient permutation/phase roll, затем тот же calibrator;
- open-loop candidate policy;
- shared-lesion LP/LM перед calibrator.

Truth не участвует controller integration, только final metrics.

## Primary gate

Всего648 final trials, required584 (ceil90%). Все условия обязательны:

1. Candidate safety648/648: finite,0 hard-limit hits, torque≤0,35, energy≤4, tilt≤0,25, body-z≥0,30.
2. Recovery≤0,40с и completion≥0,65 минимум584/648.
3. Candidate truth-angle лучше каждого из uncalibrated, zero, shuffled, open и lesion минимум584 paired trials для каждого.
4. Candidate contact MAE лучше минимум4 из5 controls; каждый засчитанный comparator минимум584 wins.
5. Mean candidate angle≤0,90 mean uncalibrated и≤0,90 mean zero.

Near-miss является no-go. Final go разрешает только отдельную frozen read-only series89C на новых motions/views. Series90 остаётся blocked до replication go89C.

## Ограничения

Reduced six-joint support surrogate и geometric contact proxy, не FlyGym, мышцы или полноценное тело. Development использует synthetic truth labels. Natural vision, action invention и biological neurons отсутствуют. Даже go89B не является biological evidence и не разрешает прямой переход к90.
