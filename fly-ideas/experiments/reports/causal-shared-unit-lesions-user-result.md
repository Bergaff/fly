# Серия87: пользовательский результат causal shared-unit lesions

## Статус

Пользователь прислал `summary-21.json`, SHA-256:

`033a2fc502c99bfca0b17adee53386bfb9f7fdab989b14a04d6394f2e1c27fa6`.

Schema `causal-shared-unit-lesions-result-v1`, status `completed`. Exact fixed runner87 SHA `105f0c26e0b9fd5e0fa9a6060af48fe4fa900da09ff5e906116da1d12d7caa54`, runner86 и model84Z identities совпадают. Training false. Ровно516 unique cases:36 calibration и480 blocking evaluation.

`primary.passed = true`. Calibration-only ranking, shared-vs-random causal effect, observation/execution pathway effects, double-dissociation rule и no-collapse gate прошли. Это causal operational go87 для artificial pathways. По roadmap разрешена отдельно preregistered series88 actuator bridge.

## Независимая проверка

Из summary независимо пересчитаны:

- ordering selected groups из exported calibration ranking scores;
- baseline/private/observation-lesion identity counts;
- recognition margin losses;
- shared/random observation replay effects и30 paired comparisons;
- execution production effects и30 comparisons;
- aggregate primary logic;
- records, state и audit.

Все значения совпали. Calibration raw traces не экспортированы, поэтому сами ranking scores нельзя восстановить из raw traces, но selected groups однозначно следуют из сохранённых scores.

`unaffected_cross_routes_exact_by_design=true` является свойством конструкции intervention: observation-only mask не применяется production route, execution-only lesion не применяется recognition route. Это не отдельное эмпирическое измерение cross-route invariance и не должно интерпретироваться как биологическая double dissociation само по себе.

## Calibration-only groups

Все groups имеют budget2 semantic units.

- shared-selective: `left_proximal`, `left_middle`;
- observation-only: `left_middle`, `right_middle` feature blocks;
- execution-only: `left_proximal`, `left_distal` proprioceptive channels;
- random matched: `left_distal`, `right_proximal`.

Ranking использовал только motions498–506. Blocking motions507–536 не меняли groups.

Shared calibration correlations всех units были выше0,15; выбранные shared units имели два максимальных combined causal-impact scores:0,151728 и0,150165.

## Baseline recognition и observation-only lesion

- baseline correct `30/30`, требовалось20;
- private correct `30/30`;
- observation-lesion correct `18/30`;
- mean recognition margin loss `1,392230`;
- positive margin loss `30/30`, требовалось18.

По actions:

| Action | Baseline | Observation lesion | Mean margin loss |
|---|---:|---:|---:|
| foreleg rubbing |10/10|0/10|1,627283|
| head-directed grooming |10/10|8/10|0,567925|
| reach/withdraw |10/10|10/10|1,981482|

Observation-only lesion сильнее всего меняет categorical identity foreleg rubbing, хотя continuous margin уменьшается для всех30 motions. Это не uniform categorical collapse всех actions.

## Shared-selective против random matched lesion

Observation-triggered replay:

- intact mean RMSE `0,344635`;
- shared-lesion `0,366903`;
- random-lesion `0,351151`;
- shared degradation `0,022268`;
- random degradation `0,006517`;
- shared degradation примерно3,42× random;
- shared effect больше random `30/30`, требовалось18.

По actions:

| Action | Shared degradation | Random degradation |
|---|---:|---:|
| foreleg rubbing |+0,047317|+0,031176|
| head-directed grooming |+0,027406|+0,001965|
| reach/withdraw |−0,007919|−0,013591|

Для reach/withdraw обе lesions немного улучшают RMSE, но shared улучшает меньше random, поэтому paired inequality остаётся в пользу preregistered shared-vs-random effect. Нельзя утверждать, что shared lesion ухудшает каждый action по абсолютной величине. Aggregate и paired gate всё равно строго проходят.

## Execution-only effect

- intact execution replay RMSE `0,005167`;
- execution-lesion RMSE `0,191327`;
- degradation `0,186161`;
- degradation wins `30/30`, требовалось27;
- ratio около37,03× intact, требовалось1,20×.

По actions mean degradation:

- foreleg rubbing `0,230672`;
- head-directed grooming `0,298448`;
- reach/withdraw `0,029363`.

Execution effect устойчив во всех30 motions, но заметно слабее для reach/withdraw.

## Double dissociation и collapse

Reported и recomputed:

- observation-specific effect true;
- execution-specific effect true;
- unaffected cross-routes exact by design true;
- no total observation collapse true;
- double-dissociation gate true.

Shared-lesion observation RMSE `0,366903` остаётся ниже full-zero pooled evaluation RMSE `0,413328`, поэтому результат не является простым уничтожением всего output.

## State и overlap

- state immutable и SHA match516/516;
- minimum unique RGB frames50;
- minimum feature max std0,011000;
- accepted training candidates16 384;
- broad audit128/16 384, non-exhaustive;
- overlaps under0,001° =0;
- under1° =0;
- under5° =458.

## Научная интерпретация

В artificial system calibration-selected shared channels причинно важнее fixed random matched channels для observation-triggered replay. Mode-specific interventions дают заранее ожидаемый recognition/production pattern, а shared lesion не вызывает полный zero-collapse. Это усиливает функциональный causal claim по сравнению с корреляционными series85–86.

Но intervention classes реализованы различными computational operations: masking classifier features, zeroing proprioceptive channels и zeroing shared traces. Поэтому double dissociation частично обеспечена архитектурным разделением routes. Это causal evidence для engineered system, не доказательство biological shared neurons.

Нет natural vision, biological IDs, muscles, forces, actuators или closed-loop correction.

## Следующий допустимый шаг

Series88: actuator bridge prototype. Она должна заменить прямой kinematic qpos/replay на bounded actuators, использовать replay state как target policy, возвращать proprioception/contact в controller и проверять stability, limits, NaN и energy. Motions421–536 теперь раскрыты и запрещены для новых blocking evaluation.
