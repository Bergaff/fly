# Серия89B: пользовательский результат bounded policy calibration

## Статус

Пользователь прислал `summary-24.json`, SHA-256:

`f4351c05599a059090310452857887da096fbff79699c407ec4bf1c8a8028664`.

Schema `bounded-policy-calibration-result-v1`, status `completed`. Exact runner89B SHA `99e0ccd01e9ae0ba27d61c4391e6cdff675793c8b10cbea41a4237a5b398a920`, runner88, no-go89 extract и selected model84Z identities совпадают. Source84Z training false. Development fit разрешён protocol.

`primary.passed = false`. Это strict no-go89B только из-за preregistered contact gate. Safety, recovery, completion, все angle-control gates и mean-margin gate прошли. Frozen replication89C и series90 остаются заблокированными.

## Calibrator development

Development содержит7056 frames. Reported diagnostics:

- raw RMSE0,810772;
- calibrated RMSE0,247240;
- projected RMSE0,248161;
- calibrator SHA `fe618e736365769627a63454e0191dcf76afa4acbd7db35a6134791612b6c154`;
- ridge0,08.

Это сильное снижение development error, но development raw rows и NPZ не входят в summary. Поэтому calibrator fit и его SHA нельзя независимо воспроизвести из присланного файла. Final metrics проверяются независимо по exported records.

## Final coverage

- motions621–638;
- views321–332;
-216 unique visual cases;
-3 initial profiles;
-648 embodied trials;
-required584.

Development motions603–620 и final motions621–638 разделены в protocol. `final_used_for_fit=false` reported и pinned runner подтверждают конструкцию, но raw development stream в summary отсутствует.

## Primary

| Gate | Результат | Порог | Статус |
|---|---:|---:|---|
| Candidate safety |648/648|648|pass|
| Recovery≤0,40с |645/648|≥584|pass|
| Completion≥0,65 |648/648|≥584|pass|
| Angle vs uncalibrated |648/648|≥584|pass|
| Angle vs zero |630/648|≥584|pass|
| Angle vs shuffled |648/648|≥584|pass|
| Angle vs open |637/648|≥584|pass|
| Angle vs lesion |648/648|≥584|pass|
| Contact vs uncalibrated |374/648|≥584|fail|
| Contact vs zero |648/648|≥584|pass|
| Contact vs shuffled |577/648|≥584|fail by7|
| Contact vs open |574/648|≥584|fail by10|
| Contact vs lesion |568/648|≥584|fail by16|
| Mean angle margin |pass|≤90% uncalibrated и zero|pass|

Contact gate требовал проход минимум4 из5 comparators. Прошёл только zero-state. Поэтому aggregate no-go обязателен. Нельзя округлять577/574/568 до584 или post hoc снизить threshold.

## Mean final metrics

| Condition | Truth-angle RMSE | Contact MAE |
|---|---:|---:|
| candidate |0,257795|0,191640|
| uncalibrated |0,763503|0,214114|
| zero-state |0,390803|0,444075|
| shuffled-state |0,661314|0,258912|
| open-loop |0,449437|0,271385|
| shared lesion |0,600663|0,281887|

Candidate mean angle:

- примерно66,2% ниже uncalibrated;
- примерно34,0% ниже zero-state;
- ниже каждого control aggregate.

Mean contact candidate также ниже каждого control aggregate. Но preregistered gate был paired90%, а не aggregate mean. Aggregate superiority не заменяет paired requirement.

## По действиям

### Angle wins

| Action | Uncalibrated | Zero | Shuffled | Open | Lesion |
|---|---:|---:|---:|---:|---:|
| foreleg rubbing |216|216|216|216|216|
| head grooming |216|216|216|205|216|
| reach/withdraw |216|198|216|216|216|

Angle improvement широкое и не зависит от одного action.

### Contact wins

| Action | Uncalibrated | Zero | Shuffled | Open | Lesion |
|---|---:|---:|---:|---:|---:|
| foreleg rubbing |111|216|183|199|205|
| head grooming |47|216|178|159|216|
| reach/withdraw |216|216|216|216|147|

Contact failure имеет action-specific структуру:

- candidate часто хуже uncalibrated для head grooming;
- lesion comparison слабее для reach/withdraw;
- shuffled/open shortfall сосредоточен прежде всего в head grooming.

Нельзя исключать эти actions после просмотра.

## Safety и recovery

Candidate:

- limit violations0;
- NaN0;
- energy min/mean/max0,107543/1,033700/2,595085 при пороге4;
- max tilt0,069997rad при пороге0,25;
- minimum body-z0,392729 при пороге0,30;
- max torque0,35.

Bounded projection/barrier полностью устранили hard-limit failure series89 на этой final battery.

Три unrecovered trials относятся к одному visual case: motion627, view325, foreleg rubbing, все три profiles. Recovery0,48с при threshold0,40. Поскольку645/648 выше584, recovery gate проходит.

## Независимая проверка

Из216 records/648 trials независимо пересчитаны:

- safety, recovery и completion;
- все angle/contact paired wins;
- means и mean-margin;
- aggregate decision;
- coverage, state hashes и immutable delay markers.

Все значения совпали с reported primary с учётом машинного округления mean.

## Интерпретация

89B успешно исправила две главные проблемы89:

1. truth-angle policy значительно лучше zero и uncalibrated;
2. hard-limit saturation устранена648/648.

Однако contact objective не переносится с требуемой paired устойчивостью. Результат является сильным engineering improvement, но строгим no-go по заранее установленному правилу. Frozen89C запускать нельзя, потому что candidate89B не прошёл собственный final gate.

## Следующий допустимый шаг

Допустима новая development series89B2 с заранее описанным contact-aware objective, использующая только новые development motions/views и отдельный untouched final. Нельзя дообучать на motions621–638, выбирать failed contact cases или ослаблять584 threshold. Motions421–638 теперь раскрыты. Series90 остаётся blocked.
