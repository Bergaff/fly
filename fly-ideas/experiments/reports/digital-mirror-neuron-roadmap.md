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

## Серия 82D: distal observability diagnostic после no-go

Серия 82 завершилась no-go, поэтому перед 83 добавлена диагностическая ветвь, не меняющая нумерацию основного roadmap:

- standard48 level против high96 level, high96 edge и high96 level+edge на одном stream;
- независимая evaluation battery motions 221–226, seed 8222;
- controlled +10° perturbation каждой distal axis во всех 16 held corners;
- RGB/feature sensitivity и gain/correlation/bias/sign diagnostics против zero;
- заранее заданный routing в geometry/occlusion, новый representation prototype или decoder/temporal prototype.

82D всегда записывает `authorizes_series83=false`. Даже удачный diagnostic candidate должен пройти отдельный новый short prototype с six-axis gate.

## Серия 82G: scale-normalized camera prototype

После route `geometry_or_occlusion` сравниваются на новом stream:

- variable FOV edge representation;
- fixed FOV35 edge representation с сохранением остальных view coordinates;
- diagnostic-only body-relative tracked FOV35 camera.

Primary использует только fixed FOV35. Tracked camera не может спасти primary. Gate снова включает все шесть осей, zero, wins, FOV30/FOV70 safeguards, visibility и 12/16 corners.

Результат: полный `go_for_revised_long_training=true`. Все оси, FOV safeguards и visibility прошли; both-distal corners ровно 12/16. Все четыре failed corners имеют body X=4,18, поэтому серия 83 должна сохранить отдельный upper-body-X safeguard.

## Серия 83: восьмичасовое fixed-FOV35 edge обучение

После полного go серии 82G протокол подготовлен:

- две мухи, ровно 28 800 секунд active training, два worker;
- RGB96×64, FOV35, 576 gradient-energy history features;
- motion/view seeds 8301/8303;
- 50% всех 16 exact 4D geometry corners, 50% continuous interior;
- frozen evaluation seed8302, motions261–270 ×16 corners =160 cases;
- six-axis primary: ниже zero и минимум112/160 wins;
- bodyX4,18 safeguard: каждая ось ниже zero и минимум56/80 wins;
- минимум12/16 corners проходят все оси с минимум7/10 wins;
- 72-state, delay0,5s, shuffled/static/closed controls.

BAT `RUN-EIGHT-HOUR-FIXED-FOV-AUTONOMOUS-GROOMING.bat`; bounded fixture прошёл.

Результат long run: primary failed только по corner gate, 10/16 вместо 12/16. Все pooled axis, controls и bodyX4,18 safeguards прошли; отказ сосредоточен в distal repeatability при bodyX3,82. Не повторять training. Серия84 должна быть frozen read-only картой границы model83.

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

# Ближайшее действие после результата серии 83

Серия 83 завершилась `primary=false` только из-за corner gate 10/16 при пороге12. Gate post hoc не ослаблять и тот же 8-hour training не повторять.

Серия84 завершена как read-only stress map frozen model83 и дала no-go. Combined сигнал полезен, но left distal67/96 не достигает68, lower-X left distal32/48 не достигает34, uniform gate только2/16. По всей карте проходят9/72 cells, ни одной при cameraZ0,56; body X сам по себе не создаёт устойчивую область. Exact source probes36/36 совпали, поэтому отказ не объясняется сменой модели. Не повторять frozen slicing, не выбирать cells post hoc и не ослаблять thresholds.

Серия84R завершена близким, но строгим no-go. Новая model улучшила source83 по всем global axes, прошла обе distal comparator gates, controls, обе camera-Z groups и13/16 corners. Единственный blocking failure: lower bodyX3,82 right distal55/80 при пороге56. Это нельзя округлять до go. Кроме того, reported active elapsed34320,625с превысил budget28800с на92 минуты; перед следующим долгим обучением нужно прояснить time accounting.

Серия85 остаётся заблокированной. Техническая84T завершилась: QuickEdit был включён до защиты и отключён через WinAPI; fixed128 candidates рассчитаны без blocked batches, с устойчивыми post-startup batch times1,09–1,24с. Это сильно поддерживает console-selection explanation остановки84R и показывает, что wall elapsed нельзя считать полезным compute.

Серия84S завершена полным preregistered model go: fixed16384 candidates, lower-X right distal73/80 vs zero и62/80 vs frozen84R, обе X/Z groups и16/16 corners. Combined и все global axes прошли; QuickEdit/wall defect не изменил completion. Это первый uniform six-axis model go после серий83–84R.

Model84S теперь frozen; training/ridge/crop не менять и BAT не перезапускать. Следующий этап только независимая read-only replication на новых motions/seeds с теми же absolute, lower-X, X/Z и corner gates. Series85 shared observation/execution остаётся заблокированной до replication go.

Серия84U завершена replication no-go без изменения model84S. Absolute reconstruction и controls устойчивы, обе camera-Z groups и16/16 corners прошли, combined84S немного ниже84R. Но целевая right distal хуже84R pooled global и выиграла лишь77/160 при пороге96; lower-X count44/80 не достиг48, несмотря на немного лучшую pooled RMSE. Значит, улучшение84S не является motion-invariant и не реплицировано.

Series85 остаётся заблокированной. Motions321–350 раскрыты; нельзя дообучать84S на341–350, исключать weak motions344/347 или запускать новые seeds в поиске go. Следующий допустимый шаг: новая preregistered model-development серия, адресующая motion-dependent distal consistency, с полностью новыми blocking holdouts и последующей отдельной frozen replication.

Серия84V завершена полным model-development go. Counterfactual view pairing при неизменных representation/ridge/count улучшил обе frozen models по всем осям; right distal135/160 vs84S и140/160 vs84R, lower-X61/80 и65/80, обе X/Z groups и16/16 corners прошли. Это поддерживает гипотезу motion/view confounding, но пока только на одной новой final battery361–370.

Candidate84V SHA `44b98c31…` теперь frozen; training84V не повторять и motions361–370 не использовать для tuning. Следующий этап только read-only replication на новых motions/seeds с теми же dual-comparator blocking gates. Series85 остаётся заблокированной до replication go.

Серия84W завершена строгим near-miss no-go. Улучшение84V над84S/84R реплицировано по всем global axes и combined; right distal129/160 и131/160 против comparators. Но lower-X absolute wins vs zero59/80 не достигли60/80, а corners9/13 дали right distal6/10. Порог нельзя округлять или заменять pooled RMSE.

Model84V остаётся frozen; motions381–390 нельзя использовать для tuning, и новый seed ради go запрещён. Series85 остаётся заблокированной. Следующий model-development шаг должен адресовать absolute lower-X right-distal failures, сохранив dual-comparator advantage, на полностью новых blocking motions.

Серия84X завершена model-development no-go. Шесть workers сократили полный fixed-count расчёт до2ч27м. Allocation3 lower-X+1 upper-X исправила lower-X target: RD73/80 vs zero и53/80 vs84V. Однако удалённый upper-X view ухудшил upper-X до28/80 wins vs84V; global RD81/160 вместо96 и combined candidate0,331909 хуже84V0,330785. Absolute X/Z и16/16 corners прошли, но balanced84V не превзойдена. Motions401–410 раскрыты;84X не повторять, series85 остаётся заблокированной.

Серия84Y завершена model-development no-go. Fixed20480 candidates рассчитаны за1ч56м. Дополнительный lower-X view не улучшил lower-X против84V: pooled0,404821 хуже0,404660, wins43/80 вместо48. Global RD53/160 вместо96, combined candidate0,302530 хуже84V0,300768; upper-X только10/80 wins vs84V. Exact84V examples сохранялись, но их относительный вес и единый ridge optimum изменились. Absolute X/Z и16/16 corners прошли. Motions411–420 раскрыты; простое view weighting/duplication в этой shared ridge модели исчерпано, series85 заблокирована.

Серия84Z завершена model-development go без утечки final. Development421–430 выбрал `ridge_0175` как единственный5/5-core вариант; ни один development strict полностью не прошёл, но selection rule была заранее фиксирована. На untouched431–440 selected model прошла всё: global RD149/160 vs84V, lower-X68/80 zero и77/80 vs84V, upper-X72/80 vs84V, combined лучше84V, X/Z и16/16 corners pass. Reported selected SHA `cb761051…` теперь frozen; motions421–440 раскрыты.

Серия84AA завершена independently verified strict frozen-replication go на seed8436 motions441–450. Exact frozen `ridge_0175` без training/selection прошёл global RD142/160 vs84V, lower-X68/80 zero и73/80 vs84V, combined ниже всех controls/comparators, обе X/Z и16/16 corners. State immutable160/160; audit128/16384 non-exhaustive. Независимый verifier пересчитал все gates из160 rows. Раскрытые motions421–450 нельзя использовать как новые blocking данные.

Серия85 завершена operational shared-population prototype go без нового training. На batteries451–460 и461–470 все6/6 semantic units dual-active; reported RSA0,749845/0,793694 выше shuffled p95; shared reconstruction немного лучше equal-budget private84V и ниже всех controls; state immutable320/320. Correlations/performance пересчитаны независимо. RSA signatures не экспортированы, поэтому RSA нельзя независимо пересчитать из summary. Это artificial operational mirror criterion, не biological claim; motions421–470 раскрыты.

Серия86 завершена operational multi-action/compositional go. Shared identity11/12 при private11/12; RSA0,792970 значительно выше shuffled p95; all six ordered pairs reported correct. Population5/6 dual-active: left proximal ниже threshold, поэтому uniform claim запрещён, но preregistered minimum4/6 выполнен. Reconstruction within private margin и ниже controls; state immutable324/324. Identity/RSA/population независимо пересчитаны, composition half-features не экспортированы. Это synthetic operational evidence без natural vision, action invention или actuators; motions421–497 раскрыты.

Серия87 завершена causal operational go. Calibration-only shared LP/LM lesion дала mean degradation0,022268 против0,006517 random matched и выиграла30/30 paired motions; execution lesion ухудшила30/30; observation lesion снизила margin30/30 и identity с30 до18. No-collapse pass. Reach absolute shared/random effects оба слегка улучшают RMSE, поэтому uniform harm claim запрещён. Cross-route invariance задана архитектурой interventions, а не независимо измерена. Это artificial causal evidence, не biological neurons. Series88 actuator bridge теперь разрешена; motions421–536 раскрыты.

Series88 завершена actuator bridge prototype go. На motions537–566 ×16 finite/limits/support/torque-energy gates прошли; closed/open target tracking0,053664/0,367405, wins480/480, completed479/480. Output-vs-truth остаётся0,295614/0,463626/0,287572 по actions, поэтому успех не означает solved visual/task accuracy. Reduced geometric contact/support surrogate нельзя называть FlyGym, мышцами или полноценным свободно стоящим телом. Series89 теперь разрешена отдельно; motions421–566 раскрыты.

Series89 завершена strict operational no-go. Recovery/completion1296/1296 прошли, но safety только43/1296 из-за hard-limit hits в1253 trials. Normal truth-angle0,793593 хуже zero0,391557 и shuffled0,596295 во всех1296 pairs; open-loop wins1233 pass, shared-lesion wins449 fail. Ни один contact comparator не достиг1167 wins. Failure широк по actions/profiles/views, не near-miss. Series90 blocked. Следующий допустимый путь только новая preregistered engineering development + отдельная frozen replication на новых motions/views;421–602 раскрыты.

Series89B завершена strict contact no-go. Calibrator снизил angle до0,257795, прошёл safety648/648, устранил limits и выиграл все angle gates. Но contact wins374/648/577/574/568 при required584; только zero comparator проходит вместо требуемых4/5. Нельзя округлять близкие577/574/568 или заменять paired gate aggregate means.89C и90 blocked. Следующий допустимый путь только новая contact-aware development89B2 на новых motions/views;421–638 раскрыты.

89B2 завершена strict direct-contact no-go. Safety и все angle gates прошли; candidate contact mean улучшен0,204104→0,179762 и4/6 controls проходят. Но mandatory paired benefit vs angle-only525/648 не достиг584; reach только135/216. Aggregate improvement не заменяет paired90%.89C/90 blocked. Следующий допустимый путь только new development89B3 на новых motions/views;421–674 раскрыты.

89B3 завершена strict contact no-go. Identity195/216 прошла ровно, все21 ошибки head; safety и angle прошли. Contact mean улучшена, angle-only590 проходит, но mandatory common579<584 и только3/7 controls проходят вместо5. Head contact остаётся слабым. Нельзя округлять579.89C/90 blocked; допустим только new head-focused development89B4 на новых motions/views;421–710 раскрыты.

89B4 завершена strict no-go. Identity216/216 устранила routing/head identity error; hard predicted и oracle совпали648/648. Safety/angle, direct angle-only624, common607 и6/9 contact controls прошли. Soft candidate mean contact0,127288 хуже mandatory hard0,122068 и выиграла hard/oracle только57/648: остаточное mixing разбавляет уже правильный expert. Нельзя постфактум заменить primary hard-policy.89C/90 blocked; motions421–746 раскрыты.

89B5 завершена strict no-go. Predicted hard routing identity216/216 и candidate=oracle648/648; mean contact0,121827 лучше soft0,126011. Safety/angle, total angle-only635/common617 прошли. Но foreleg vs common188/216<195 и только6/9 controls: soft561, uncal568, oracle ties0. Head common216 и reach213 сильны; узкое место теперь foreleg paired consistency. Нельзя заменить paired gates mean или исключить oracle.89C/90 blocked; motions421–782 раскрыты.

89B6 завершена full preregistered development go. Grouped-CV выбрал foreleg boost4; untouched final: identity216/216, safety/angle pass, contact soft587, angle638, common633, foreleg common201, head/reach216, broad7/8. Mean0,122611 едва лучше standard0,122644 и лучше soft0,126982; candidate=oracle648/648. Все gates independently reproduced. Эффект vs standard мал (~0,026%), но composite policy прошла полный preregistration.

Frozen89C подготовлена на motions819–836/views721–732. Exact result89B6 summary/model/manifest и source84Z обязательны; weights, lambdas, temperature, boost4 и decision frozen, обучение/selection запрещены. Near miss no-go;90 blocked до89C go.
