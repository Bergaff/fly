# Серия86: пользовательский результат multi-action compositional population

## Статус

Пользователь прислал `summary-20.json`, SHA-256:

`e66a6b52890bbf33b5071f7a2acb15d29a2e8051448a8dfae500df482b46da00`.

Schema `multiaction-compositional-population-result-v1`, status `completed`. Exact runner86 SHA `7dc5686028a2fe82d683f091a1f0a08deab25bcc2be41320b5d52e91de6d9714`, runner85 и selected model84Z identities совпадают. Training false. В summary ровно324 уникальных render cases:36 calibration,192 blocking identity,96 composition.

`primary.passed = true`. Action identity, exported cross-mode RSA, exact ordered composition и population safeguards прошли. Это operational multi-action/compositional go86. По roadmap разрешена отдельно preregistered series87 с causal shared-unit lesions.

## Независимая проверка

Из summary независимо пересчитаны:

- shared и private identity predictions из raw18-dimensional features, prototypes и scales;
- identity totals и per-action counts;
- все66 observation/execution RSA distances;
- RSA correlation;
- независимый1000-permutation RSA null с другим deterministic Python RNG;
- population correlations из sufficient statistics;
- dual-active classification;
- pooled reconstruction и controls;
- state immutability, records и audit.

Совпадение exported RSA distances до `1,78e-15`; recomputed RSA ровно `0,7929697692652838`. Независимый null p95 `0,214628`, тогда как runner-reported NumPy null p95 `0,233119`; observed RSA выше обоих.

Composition reported6/6 internally consistent, но first/second-half feature vectors не экспортированы. Поэтому exact composition classification нельзя независимо повторить из summary. Это новое export limitation, которое следует устранить в series87/следующем compositional audit; оно не меняет preregistered runner decision.

## Action identity

Shared correct `11/12`, требовалось8. Equal-budget private84V также `11/12`. Shuffled-label p95 `7/12`.

| Action | Correct | Cases |
|---|---:|---:|
| foreleg rubbing |4|4|
| head-directed grooming |3|4|
| reach/withdraw |4|4|

Единственная ошибка: motion484, head-directed grooming с amplitude0,85 и speed0,75, классифицирован как reach/withdraw. Та же ошибка есть у private84V, поэтому это не специфическая потеря shared path. Motion нельзя исключать post hoc.

## Cross-mode RSA

- correlation `0,792970`;
- runner shuffled p95 `0,233119`;
- independent Python shuffled p95 `0,214628`;
- permutations1000;
- required correlation0,30;
- gate pass.

RSA использует held identity motions480–491,18 normalized features и66 pair distances.

## Compositional order

Все шесть ordered pairs reported correct:

1. rubbing → head grooming;
2. head grooming → rubbing;
3. rubbing → reach;
4. reach → rubbing;
5. head grooming → reach;
6. reach → head grooming.

Result `6/6`, требовалось4/6. Засчитывался только полностью правильный ordered pair.

## Shared population

Dual-active5/6, требовалось4/6.

| Unit | Shared corr | Gate |
|---|---:|---|
| left proximal |0,102548|fail: ниже0,15|
| left middle |0,909469|pass|
| left distal |0,376081|pass|
| right proximal |0,552766|pass|
| right middle |0,844267|pass|
| right distal |0,183353|pass|

Left proximal честно не прошёл unit gate. Primary всё равно проходит заранее установленное правило минимум4/6. Нельзя post-hoc утверждать uniform6/6 multi-action population.

## Reconstruction safeguards

- shared observation `0,356667`;
- equal-budget private84V `0,355812`;
- execution mode `0,027302`;
- zero `0,416773`;
- shuffled `0,408693`;
- static `0,440186`;
- closed `0,474253`.

Shared хуже private84V примерно на0,240%, при preregistered допустимом margin5%. При этом shared ниже zero и всех temporal/static/closed controls.

## State, rendering и overlap

- state immutable и SHA match324/324;
- minimum unique RGB frames40;
- minimum feature max std0,009098;
- accepted training candidates16 384;
- broad audit128/16 384, non-exhaustive;
- overlaps under0,001° =0;
- under1° =0;
- under5° =295.

Exact motion hashes471–497 также были проверены против all training hashes и disclosed motions421–470 до evaluation.

## Научная интерпретация

Frozen RGB-only population сохраняет identity трёх заранее заданных synthetic motifs при held-out amplitude/speed, согласуется с execution representations и reported correctly identifies six unseen orders. Это сильнее series85, где был только один action family.

Однако actions и units инженерно заданы. Классификация может опираться на различия synthetic kinematics, а не на естественную action semantics. Результат не доказывает самостоятельное создание поведения, natural vision, biological mirror neurons, muscles, forces, actuators или closed-loop control.

## Следующий допустимый шаг

Series87 должна preregister causal lesions до просмотра lesion results:

- shared-selective units;
- observation-only units;
- execution-only units;
- random matched units;
- одинаковый lesion budget;
- ranking только по calibration/training data;
- новые motions и seeds;
- double-dissociation gates;
- общий collapse outputs не считается mirror-specific effect.

Motions421–497 теперь раскрыты и запрещены для новых blocking selection/evaluation. Следующий summary должен экспортировать любые feature vectors, используемые для lesion/composition decisions.
