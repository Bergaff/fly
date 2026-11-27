# Серия89: пользовательский результат closed-loop surrogate embodied validation

## Статус

Пользователь прислал `summary-23.json`, SHA-256:

`0b44d61b58b374ac95037ba8a853e23b0c48a1b8510a0b0f4c323ebb509d1105`.

Schema `closed-loop-embodied-validation-result-v1`, status `completed`. Exact corrected runner89 SHA `e0412778b2e7e15c7c202241ededfa997bb6e8c0e39d5f3d3084940dc0d7e218`, runner88, go88 extract и selected model84Z identities совпадают. Training false. Ровно432 unique visual cases: motions567–602 × views101–112;3 initial profiles дают1296 embodied trials.

`primary.passed = false`. Это строгий operational no-go89. Safety, angle-control и contact-control gates не прошли. Recovery и completion прошли. Series90 остаётся заблокированной.

## Независимая проверка

Из1296 exported trial/control records независимо пересчитаны primary means, paired wins, safety, recovery, completion и aggregate decision. Coverage, frozen identities, immutable state markers и forbidden-access flags проверены. Все значения точно совпали с reported primary.

Trajectory/torque time series не экспортированы, поэтому numerical integration нельзя независимо повторить. Независимо проверено агрегирование runner-exported metrics, не сама dynamics simulation.

## Primary

| Gate | Результат | Требование | Статус |
|---|---:|---:|---|
| Normal safety |43/1296|1296/1296|fail|
| Recovery≤0,40с |1296/1296|≥1167|pass|
| Completion≥0,65 |1296/1296|≥1167|pass|
| Angle лучше zero |0/1296|≥1167|fail|
| Angle лучше shuffled |0/1296|≥1167|fail|
| Angle лучше open |1233/1296|≥1167|pass|
| Angle лучше shared lesion |449/1296|≥1167|fail|
| Contact лучше zero |938/1296|≥1167|fail|
| Contact лучше shuffled |951/1296|≥1167|fail|
| Contact лучше open |873/1296|≥1167|fail|
| Contact лучше shared lesion |723/1296|≥1167|fail|

Ни один contact comparator не достиг1167, тогда как требовались минимум три.

## Mean metrics

| Condition | Truth-angle RMSE | Contact MAE | Energy |
|---|---:|---:|---:|
| normal |0,793593|0,218181|0,938107|
| zero-state |0,391557|0,449293|0,010515|
| shuffled-state |0,596295|0,281702|5,691080|
| open-loop |0,880987|0,226482|0,752535|
| shared lesion |0,773247|0,231617|0,670218|

Normal closed-loop лучше open-loop aggregate angle и выигрывает1233/1296, но значительно хуже zero-state и shuffled-state во всех1296 paired trials. Shared lesion также имеет немного меньшую aggregate angle error, а normal выигрывает только449/1296.

Это не near-miss: центральные task/control gates не пройдены с большим запасом.

## Почему safety прошёл только43/1296

Единственная причина safety failure по exported metrics: hard joint-limit hits.

- cases без limit hits:43/1296;
- cases с limit hits:1253/1296;
- total sampled limit hits:13 949;
- максимум:30 hits в trial;
- NaN failures:0;
- torque failures:0;
- energy failures:0;
- tilt failures:0;
- body-z failures:0.

Normal extrema:

- energy0,312142–1,885243 при пороге4;
- max torque0,35;
- max tilt0,069998rad при пороге0,25;
- minimum body-z0,389148 при пороге0,30.

По actions число safe trials: foreleg17/432, head25/432, reach1/432. Порог нельзя post hoc переопределять: runner заранее считал sample at hard bound как limit violation.

## По действиям

| Action | Normal angle | Zero | Shuffled | Open | Lesion | Normal safe |
|---|---:|---:|---:|---:|---:|---:|
| foreleg rubbing |0,751990|0,389663|0,608510|0,887915|0,711365|17/432|
| head grooming |0,785689|0,494773|0,650544|0,835859|0,818055|25/432|
| reach/withdraw |0,843099|0,290235|0,529832|0,919187|0,790320|1/432|

Head grooming является единственным action, где normal angle стабильно лучше shared lesion:432/432. Для foreleg это17/432, для reach0/432. Normal не выигрывает у zero или shuffled ни на одном action trial.

## Initial profiles и views

Результат не объясняется одним initial profile:

- neutral normal angle0,792297, safe14/432;
- pose offset0,795221, safe16/432;
- velocity offset0,793260, safe13/432.

Во views102,103,105,106,108–111 safe trials отсутствуют полностью. Лучший view112 дал только18/108 safe. Значит, failure широк по profiles и held views.

## State и доступ

- unique state hashes432/432;
-72 coefficients во всех cases;
- state before/after delay совпадает432/432;
- teacher access false432/432;
- RGB access false432/432;
- framewise observer-buffer access false432/432;
-74 open-loop control trials корректно записали `recovery_s=null`, `recovered=false`; corrected JSON fix сработал.

## Научная интерпретация

Go88 показал хорошее отслеживание decoded target policy, но series89 проверила соответствие truth на новых views и initial conditions. Здесь observer-derived normal target оказался хуже неподвижного zero-state во всех1296 angle comparisons и часто доводил joints до hard limits. Следовательно, actuator controller способен следовать target, но target не является достаточно правильной embodied policy на этой blocking battery.

Contact normal mean лучше controls aggregate, кроме того что paired gate слишком слаб, но angle failure и limits сами по себе достаточны для no-go. Нельзя выбирать только contact или open-loop успех и объявлять embodied go.

## Ограничения

Это reduced six-joint support surrogate с geometric contact proxy, а не полноценное тело. Тем не менее failure внутри заявленного surrogate протокола реален. Нельзя:

- ослаблять thresholds после результата;
- переклассифицировать hard-bound hits как safety pass;
- исключать reach/withdraw, отдельные views или initial profiles;
- повторять те же motions/seeds после настройки;
- переходить к series90 как будто go89 состоялся.

## Следующий допустимый шаг

Series90 blocked. Допустим только новый preregistered engineering stage на новых development motions, направленный на visual target calibration, bounded policy projection и предотвращение limit saturation, после чего потребуется отдельная frozen blocking replication на ещё новых motions/views. Motions421–602 теперь раскрыты и запрещены для будущего blocking selection/evaluation.
