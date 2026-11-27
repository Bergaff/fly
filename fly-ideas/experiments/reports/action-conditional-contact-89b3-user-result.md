# Серия89B3: пользовательский результат action-conditional contact

## Статус

Пользователь прислал `summary-26.json`, SHA-256:

`dd16e35af84f5fe40d5319a9cc2720637639d51f7ac1c442af06cfd632bcccfb`.

Schema `action-conditional-contact-development-result-v1`, status `completed`. Exact runner89B3 SHA `b6252829d81ea92c106554f8413cae6b842868c06f69b18fdcd99e5d512ef259`, runner89B2, no-go89B2 extract и selected model84Z identities совпадают. Source84Z frozen, development training true, final used for fit false.

`primary.passed = false`. Identity, safety, recovery, completion и angle gates прошли. Contact gate failed: common-contact579/648 не достиг584 и всего3 из7 comparators достигли584 при требовании5. Frozen89C и series90 остаются blocked.

## Development

Angle raw/calibrated/projected RMSE:0,777397/0,247769/0,248804. Development identity134/144. Common model выбрал lambda1,0.

Все три action experts выбрали lambda4,0:

- foreleg development contact0,162867;
- head0,043242;
- reach0,103826.

Model SHA `5891db4dd5245c012a6e8192084b1c1dd3e0564e91134011ebd6af0e5198e558`.

Raw development records/NPZ отсутствуют, fit независимо не воспроизводится. Final aggregates пересчитаны из records.

## Final coverage

- motions693–710;
- views521–532;
-216 visual cases;
-648 trials;
-required identity195/216;
-required trials584/648.

## Identity

Predicted action correct195/216, ровно preregistered threshold.

Confusion:

- foreleg72/72 correct;
- reach72/72 correct;
- head51/72 correct;
-16 head classified reach;
-5 head classified foreleg.

Все21 ошибки относятся к head grooming. Identity gate проходит без запаса; результат нельзя называть uniform identity.

## Primary

| Gate | Результат | Порог | Статус |
|---|---:|---:|---|
| Identity |195/216|≥195|pass ровно|
| Safety |648/648|648|pass|
| Recovery |648/648|≥584|pass|
| Completion |648/648|≥584|pass|
| Angle vs uncalibrated |648/648|≥584|pass|
| Angle vs zero |642/648|≥584|pass|
| Angle vs shuffled |648/648|≥584|pass|
| Angle vs open |648/648|≥584|pass|
| Angle vs lesion |648/648|≥584|pass|
| Contact vs angle-only |590/648|≥584|pass by6|
| Contact vs common |579/648|≥584|fail by5|
| Contact vs uncalibrated |530/648|≥584|fail|
| Contact vs zero |648/648|≥584|pass|
| Contact vs shuffled |645/648|≥584|pass|
| Contact vs open |567/648|≥584|fail|
| Contact vs lesion |522/648|≥584|fail|

Проходят только3/7 contact comparators: angle-only, zero и shuffled. Требовались5/7, причём common-contact был обязательным. Поэтому no-go не сводится только к недобору5 common wins: total control count также не проходит.

## Mean metrics

| Condition | Angle RMSE | Contact MAE |
|---|---:|---:|
| candidate |0,253858|0,141665|
| angle-only |0,260069|0,187608|
| common-contact |0,258577|0,169858|
| uncalibrated |0,767555|0,214064|
| zero |0,380593|0,442121|
| shuffled |0,461144|0,356665|
| open |0,431745|0,222710|
| lesion |0,532511|0,265240|

Aggregate candidate contact примерно на24,5% ниже angle-only и16,6% ниже common-contact. Но paired common wins579/648=89,35%, ниже90%; aggregate mean не заменяет paired gate.

## По действиям

### Identity

| Action | Correct |
|---|---:|
| foreleg |72/72|
| head |51/72|
| reach |72/72|

### Contact wins

| Action | Angle-only | Common | Uncalibrated | Zero | Shuffled | Open | Lesion |
|---|---:|---:|---:|---:|---:|---:|---:|
| foreleg |203|211|201|216|216|214|216|
| head |171|162|113|216|213|153|90|
| reach |216|206|216|216|216|200|216|

Conditional experts хорошо работают для foreleg и reach. Head grooming является источником большей части contact failures, включая common, open и lesion. Это согласуется с identity errors, но summary не позволяет причинно отделить misclassification от качества head expert без counterfactual oracle-expert traces.

## Safety

- limit violations0;
- NaN0;
- max energy2,543195 при пороге4;
- max tilt0,069997rad;
- minimum body-z0,393069;
- recovery/completion648/648.

## Независимая проверка

Из216 records/648 trials пересчитаны identity, safety, recovery, completion, all angle/contact wins, means и aggregate decision. Все совпали с reported primary.

## Интерпретация

Action conditioning улучшило aggregate contact и прошло прямое сравнение с angle-only590/648. Однако доказательство дополнительной пользы относительно common-contact не достигло90% на5 pairs, а total controls прошли только3/7. Head identity и head contact остаются слабым местом.

Нельзя округлять579 до584, удалить head trials или использовать final693–710 для нового fit. Это strict no-go, хотя engineering trend положительный.

## Следующий допустимый шаг

Только новый preregistered development89B4 на новых motions/views, отдельно адресующий head identity и head contact. Нужен counterfactual oracle-vs-predicted expert diagnostic в development, но final inference по-прежнему не должен получать true action. Motions421–710 раскрыты. Frozen89C и series90 blocked.
