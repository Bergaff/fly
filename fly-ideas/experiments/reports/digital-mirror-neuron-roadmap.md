# Roadmap функционального цифрового аналога зеркальных нейронов

## Текущее состояние

Оценочная готовность центральной цели: около 38%. Уже реализованы две мухи, visual observation, supervised six-axis decoding, compressed state, задержка 0,5 с, autonomous kinematic replay, temporal controls и ограниченный view transfer. Не реализованы общая observation/execution population, причинные lesions этой population, actuator closed loop и биологически reviewed mapping.

Термин «цифровые зеркальные нейроны» далее означает проверяемый функциональный аналог. Он не означает доказательство существования биологических mirror neurons у мухи.

## Общие правила

1. Каждая серия получает protocol, seeds, holdout и primary до просмотра результата.
2. Failed primary не переименовывается в успех и не исправляется исключением неудобных осей или cases.
3. Short prototype должен пройти blocking gate до long run.
4. Long model после обучения замораживается до transfer, lesion и embodiment tests.
5. Combined score никогда не заменяет осевые и population-level критерии.
6. Observation, execution, state и body-control outputs логируются раздельно.
7. Replay observed action не называется созданием нового поведения.
8. Kinematic qpos не называется actuator dynamics.
9. FlyVis/Shiu/FlyGym claims разрешены только после reviewed IDs, mappings и readouts.

# Этап I. Надёжное зрительное представление outer joints

## Серия 82: high-resolution distal representation prototype

Короткое сравнение на одном stream:

- baseline: RGB 48×32, текущие level-history features;
- high-resolution: RGB 96×64, coarse level плюс high-resolution gradient-energy history;
- одинаковые motions, views и labels;
- primary: обе distal axes лучше baseline и zero, минимум 60% wins;
- safeguards: proximal/middle и FOV30/FOV70 не ухудшаются более чем на закреплённый предел;
- минимум 12/16 held corners улучшают обе distal axes.

Fail: не запускать high-resolution long study; пересмотреть геометрию сегментов/occlusion или decoder class.

## Серия 83: восьмичасовое balanced high-resolution обучение

Только если 82 go=true.

- две мухи;
- 8 часов active training;
- balanced sampling multi-factor corners и continuous interior;
- high-resolution representation, замороженное после training;
- новые motion/view holdout;
- six-axis primary;
- 72-state delay/replay и controls.

Цель: устойчивость всех шести осей, не только middle.

## Серия 84: frozen high-resolution stress and replay map

Без обучения model83:

- новая stress grid;
- новые motions;
- outer/evaluation envelope;
- clipping, feature sensitivity, state and temporal controls;
- заранее заданная доля cells, прошедших six-axis rule.

Gate к следующему этапу: равномерная six-axis устойчивость на независимой grid, а не единичной батарее.

# Этап II. Общая observation/execution population

## Серия 85: shared latent population prototype

Создаётся явная population, используемая в двух режимах:

- observation encoder получает только RGB history;
- execution encoder получает только proprioceptive/body state;
- оба проецируются в одну shared latent population;
- один decoder формирует action/state coefficients;
- отдельные private observation и execution controls имеют равный budget.

Primary:

- shared units воспроизводимо активны в обоих режимах;
- action selectivity выше temporal/static controls;
- cross-mode representational similarity выше shuffled-label control;
- shared model не хуже private controls по заранее заданному margin.

Это всё ещё искусственные units, но впервые будет проверен центральный operational mirror criterion.

## Серия 86: несколько действий и compositional holdout

Добавляются минимум три различимых действия:

1. foreleg rubbing;
2. head-directed grooming;
3. reach/withdraw или другой кинематически отдельный motif.

Проверки:

- action identity, а не только phase/angle;
- observation и execution selectivity одной population;
- новый порядок знакомых motifs;
- held-out amplitude/speed;
- нельзя считать успехом простое копирование trajectory buffer.

Gate: shared population должна различать действия и переносить identity на новые trajectories.

# Этап III. Причинность

## Серия 87: preregistered shared-unit lesions

До lesion results фиксируются:

- ranking units только по training data;
- shared-selective, observation-only, execution-only и random matched groups;
- одинаковый lesion budget;
- десять или более независимых seeds/holdouts.

Primary causal pattern:

- shared lesion специфически ухудшает observation-triggered execution;
- random matched lesion слабее;
- observation-only lesion прежде всего нарушает recognition;
- execution-only lesion прежде всего нарушает production;
- общий collapse всех outputs не считается mirror-specific эффектом.

Без такого double dissociation термин mirror population остаётся только описательным.

# Этап IV. Embodied closed-loop execution

## Серия 88: actuator bridge prototype

- заменить прямое qpos assignment на ограниченные actuators;
- replay state задаёт target policy, а не poses;
- proprioception/contact возвращаются в controller;
- технические tests устойчивости, limits, NaN и energy.

Gate: тело должно завершать bounded grooming bout без падения и без прямого доступа к teacher trajectory.

## Серия 89: closed-loop embodied validation

- новые тела/initial poses;
- view shifts;
- contact objective;
- normal, zero-state, shuffled-state, open-loop и lesion controls;
- angle, contact, stability, effort и recovery metrics.

Успех поднимет систему до функционального embodied mirror-like agent, но не до биологического доказательства.

# Этап V. Биологическая привязка

## Серия 90: reviewed FlyVis/Shiu/FlyGym mapping gate

Только после функционального успеха:

- official FlyVis activity для visual types;
- reviewed type-to-FlyWire IDs;
- Shiu/FlyWire candidate pathways;
- preregistered descending/motor readout;
- mapping permutations и lesions;
- FlyGym API в отдельной закреплённой среде.

Если reviewed mapping отсутствует, серия заканчивается честным `mapping gate closed`, а artificial shared population остаётся основным результатом.

# Ожидаемые уровни готовности

| После этапа | Функциональная оценка при полном успехе |
|---|---:|
| Текущее состояние, серии 75–81 | около 38% |
| 82–84: устойчивое six-axis зрение | 50–55% |
| 85–86: shared observation/execution population | 65–70% |
| 87: причинные lesions | 75–80% |
| 88–89: actuator closed loop | 85–90% функционального аналога |
| 90: reviewed biological mapping | зависит от доступности mapping; не гарантируется кодом |

Проценты являются управленческой оценкой зрелости, а не измеренной научной вероятностью.

# Ближайшее действие после результата серии 82

Серия 82 завершилась `go=false`: обе distal axes остались хуже zero, а both-distal corner gate дал 10/16 вместо 12/16. Серию 83 не запускать и gate post hoc не ослаблять.

Перед продолжением roadmap требуется новая короткая preregistered distal-focused диагностика. Она должна разделить как минимум видимость distal сегментов и преимущество stationary zero, особенно в FOV30; нельзя сразу переходить к ещё одному восьмичасовому обучению. Точный новый protocol, seeds и gate должны быть записаны до запуска.
