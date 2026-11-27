# Series101: пользовательский результат frozen89E → official FlyGym

## Статус

Полный Windows-запуск завершён. Предварительно зафиксированный development gate выполнен: `primary.passed=true`. Результат остаётся `scientific_result=false` по протоколу.

Исходный файл пользователя сохранён без изменения как `frozen89e-flygym-adapter-user-result.json`.

- SHA-256 исходного JSON: `9577d951090e4104326652a76ce31b387f82e13910cead1c4e2d477d9c3374ea`
- schema: `frozen89e-flygym-adapter-result-v1`
- status: `completed`
- cases: 24
- physical rollouts: 120
- workers: 1, безопасный последовательный visual phase
- training/selection: запрещены

## Первичный gate

| Проверка | Порог | Результат |
|---|---:|---:|
| Безопасные/contact candidate cases | 24/24 | 24/24 |
| Средний candidate tracking RMSE | ≤0,20 rad | 0,092774 rad |
| Candidate wins против zero state | ≥15/24 | 24/24 |
| Candidate wins против shuffled state | ≥15/24 | 24/24 |
| Candidate wins против true open loop | ≥20/24 | 24/24 |
| Candidate/state-control targets различаются | все cases | да |

Shared-lesion comparison также дал 24/24 candidate wins, хотя он не был отдельным порогом primary rule.

## Агрегированные физические показатели

| Условие | Mean truth RMSE, rad | Mean tracking RMSE, rad | Mean contact-frame fraction | Finite |
|---|---:|---:|---:|---:|
| candidate | 0,176922 | 0,092774 | 0,977891 | 24/24 |
| zero_state | 0,261524 | 0,027097 | 0,979592 | 24/24 |
| shuffled_state | 0,310272 | 0,128363 | 0,979592 | 24/24 |
| shared_lesion | 0,278502 | 0,150616 | 0,943878 | 24/24 |
| open_loop | 0,268021 | 0,189425 | 0,977891 | 24/24 |

Во всех условиях максимальная доля torque saturation равна 0. Candidate minimum thorax z по всем cases: 0,734272 mm; maximum: 1,997548 mm. Candidate правильно классифицировал действие в 23/24 cases; единственная ошибка: motion892, view804, `head_directed_grooming → reach_withdraw`. Классификационная точность не входила в blocking rule Series101.

## Вывод

Зафиксированный шестиканальный coordinate/readout adapter технически жизнеспособен на данном bounded наборе official FlyGym 2.1.1/MuJoCo rollouts. Candidate оставался finite/contact/stable, отслеживал заданную траекторию в пределах порога и во всех24 cases имел меньший truth RMSE, чем zero, shuffled и настоящий q/dq-free open loop. Различие candidate и open loop получено при одинаковых target hashes, поэтому оно изолирует пользу закрытого proprioceptive MOTOR-контура на этом протоколе.

Это не подтверждает FlyVis, FlyWire/connectome mapping, биологическую валидность, мышцы, живую муху или mirror neurons. Результат не переобучает frozen89E, не открывает Stage97 и не отменяет закрытие synthetic optimization. Он подтверждает только viability заранее объявленного physical adapter prototype.
