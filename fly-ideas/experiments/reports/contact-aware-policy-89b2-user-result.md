# Серия89B2: пользовательский результат contact-aware policy development

## Статус

Пользователь прислал `summary-25.json`, SHA-256:

`6e3f9c224087bb2915034bf3017703a63afd8f2ad6e67966009a37faae2bb00b`.

Schema `contact-aware-policy-development-result-v1`, status `completed`. Exact runner89B2 SHA `ec46c681834c4dc13c30d66f07616546809c2f3b29242e134b7f0a004d95f1a3`, runner89B, no-go89B extract и selected model84Z identities совпадают. Source84Z training false; development training true; final used for fit false.

`primary.passed = false`. Это strict no-go89B2 из-за обязательного direct contact improvement против angle-only:525/648 при required584. Остальные safety, recovery, completion и angle gates прошли. Contact comparison прошёл для4 из6 controls, но direct angle-only condition была отдельным обязательным условием. Frozen89C и series90 остаются заблокированными.

## Development model

Angle model:

-7056 development frames;
- raw RMSE0,779068;
- calibrated0,244604;
- projected0,246127.

Contact predictor fit MAE0,163412. Development выбрал lambda1,0:

| Lambda | Angle RMSE | Contact MAE | Score |
|---:|---:|---:|---:|
|0|0,246127|0,173459|0,376221|
|0,25|0,245103|0,162393|0,366897|
|0,5|0,244776|0,157323|0,362768|
|1,0|0,244903|0,153693|0,360173|
|2,0|0,245621|0,152967|0,360346|
|4,0|0,246959|0,154319|0,362698|

Selected model SHA `136e98d32c353e3b0e92c81dc54eb9f8bd923e7b689b68efc4c5e77833cd1450`.

Development raw records и NPZ отсутствуют в summary, поэтому fit независимо не воспроизводится. Final decision пересчитан из exported records.

## Final coverage

- motions657–674;
- views421–432;
-216 unique visual cases;
-648 embodied trials;
-required584;
- unique state hashes216/216;
- state coefficients72;
- state before/after delay совпадает216/216.

## Primary

| Gate | Результат | Порог | Статус |
|---|---:|---:|---|
| Safety |648/648|648|pass|
| Recovery |645/648|≥584|pass|
| Completion |648/648|≥584|pass|
| Angle vs uncalibrated |648/648|≥584|pass|
| Angle vs zero |648/648|≥584|pass|
| Angle vs shuffled |648/648|≥584|pass|
| Angle vs open |639/648|≥584|pass|
| Angle vs lesion |648/648|≥584|pass|
| Contact vs angle-only |525/648|≥584|**fail**|
| Contact vs uncalibrated |446/648|≥584|fail|
| Contact vs zero |648/648|≥584|pass|
| Contact vs shuffled |648/648|≥584|pass|
| Contact vs open |589/648|≥584|pass|
| Contact vs lesion |640/648|≥584|pass|

Candidate проходит contact threshold для4 из6 comparators: zero, shuffled, open и lesion. Но protocol отдельно требует `contact['angle_only']>=584`;525 не достигает порога. Поэтому contact gate false независимо от count4/6.

## Mean final metrics

| Condition | Truth-angle RMSE | Contact MAE |
|---|---:|---:|
| candidate |0,251485|0,179762|
| angle-only |0,253725|0,204104|
| uncalibrated |0,729284|0,216757|
| zero-state |0,386651|0,442228|
| shuffled-state |0,549534|0,385146|
| open-loop |0,432454|0,266639|
| shared lesion |0,641088|0,359004|

Aggregate contact candidate улучшен относительно angle-only примерно на11,9%. Но paired wins только525/648, или81,0%, ниже preregistered90%. Aggregate mean не заменяет paired gate.

## По действиям

### Contact wins

| Action | Angle-only | Uncalibrated | Zero | Shuffled | Open | Lesion |
|---|---:|---:|---:|---:|---:|---:|
| foreleg rubbing |209|162|216|216|215|208|
| head grooming |181|82|216|216|158|216|
| reach/withdraw |135|202|216|216|216|216|

Direct benefit против angle-only неравномерен:

- foreleg209/216;
- head181/216;
- reach135/216.

Основной direct failure находится в reach/withdraw. Сравнение с uncalibrated особенно слабо для head grooming82/216, но оно не являлось отдельным mandatory direct condition; всё равно threshold не пройден.

### Angle wins

Foreleg и reach проходят216/216 против всех controls. Head проходит216/216 кроме open-loop207/216. Angle gate устойчиво выполнен.

## Safety и recovery

- limit violations0;
- NaN0;
- energy min/mean/max0,084731/1,031807/2,559843 при пороге4;
- max tilt0,069997rad;
- minimum body-z0,392969;
- max torque≤0,35.

Три unrecovered trials относятся к motion663, view432, foreleg rubbing, всем трём profiles; recovery0,44с при threshold0,40. Gate645/648 проходит.

## Независимая проверка

Из216 records/648 trials независимо пересчитаны coverage, safety, recovery, completion, all angle/contact wins, means и aggregate decision. Все совпало с reported primary с учётом машинного округления.

## Интерпретация

Contact-aware intervention улучшает aggregate contact и проходит zero/shuffled/open/lesion paired controls. Однако она не даёт preregistered uniform direct benefit над angle-only policy: примерно19% trials не улучшены, особенно reach/withdraw. Поэтому нельзя объявлять success на основании aggregate mean или count4/6, игнорируя обязательный direct test.

Это сильный, но недостаточно устойчивый development result. Frozen89C запускать нельзя.

## Следующий допустимый шаг

Только новая preregistered development89B3 на новых motions/views, адресующая action-conditional contact geometry без использования final657–674 для fit. Нельзя снижать direct threshold584, исключать reach/withdraw или выбирать только выигрышные cases. Motions421–674 раскрыты. Series90 blocked.
