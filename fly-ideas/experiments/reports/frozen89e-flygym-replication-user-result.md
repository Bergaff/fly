# Series102: пользовательский результат frozen physical-adapter replication

## Статус

Полный Windows-запуск завершён. Неизменённый Series101 primary gate воспроизведён на24 новых cases: `primary.passed=true`. По протоколу результат остаётся `scientific_result=false`.

Исходный файл пользователя сохранён без изменения как `frozen89e-flygym-replication-user-result.json`.

- SHA-256 исходного JSON: `33795d582e9ac528304018300dc14c67db066d3452e1760df2bb74c9aef9a643`
- runner SHA-256: `16309bb094236e861fff6eeb1b4d24ce072d6f7ab55c8f88cd6f12e6d94d7a19`
- schema: `frozen89e-flygym-replication-result-v1`
- status: `completed`
- cases:24
- physical rollouts:120
- training/selection/post-result tuning: запрещены

## Frozen primary gate

| Проверка | Порог | Результат |
|---|---:|---:|
| Безопасные/contact candidate cases | 24/24 | 24/24 |
| Средний candidate tracking RMSE | ≤0,20 rad | 0,099839 rad |
| Candidate wins против zero state | ≥15/24 | 23/24 |
| Candidate wins против shuffled state | ≥15/24 | 24/24 |
| Candidate wins против true open loop | ≥20/24 | 24/24 |
| Candidate/state-control targets различаются | все cases | да |

Shared-lesion comparison также дал24/24 candidate wins, хотя он остаётся secondary diagnostic.

## Агрегированные физические показатели

| Условие | Mean truth RMSE, rad | Mean tracking RMSE, rad | Mean contact-frame fraction | Finite |
|---|---:|---:|---:|---:|
| candidate | 0,182590 | 0,099839 | 0,979592 | 24/24 |
| zero_state | 0,260322 | 0,027111 | 0,979592 | 24/24 |
| shuffled_state | 0,316677 | 0,127314 | 0,979592 | 24/24 |
| shared_lesion | 0,273135 | 0,146910 | 0,947279 | 24/24 |
| open_loop | 0,294741 | 0,194228 | 0,977891 | 24/24 |

Во всех условиях максимальная доля torque saturation равна0. Candidate minimum thorax z:0,707470mm; maximum:1,997548mm. Candidate и open loop имеют одинаковые target hashes во всех24 cases, поэтому их различие сохраняет Series101 изоляцию closed-loop q/dq feedback.

## Диагностические исключения

- Единственный проигрыш candidate против zero: motion899/view806, `reach_withdraw`; truth RMSE0,177246 против0,176403, разница0,000843rad. Это далеко не угрожает preregistered порогу15/24.
- Action classification:23/24. Единственная ошибка: motion898/view808, `head_directed_grooming → reach_withdraw`. Accuracy не входила в frozen primary.

## Вывод

Series102 независимо воспроизвела bounded technical viability fixed frozen89E→official FlyGym physical adapter на новых motions, seeds и camera coordinates без обучения или настройки после Series101. Candidate оставался finite/contact/stable, прошёл tracking threshold и устойчиво превзошёл state controls и q/dq-free open loop по truth RMSE.

Это усиливает только инженерный вывод о воспроизводимости adapter prototype. Результат не подтверждает official FlyGym visual observation между телами, FlyVis, FlyWire/connectome mapping, мышцы, живую муху, biological validity или mirror neurons. Он не открывает Stage97 и не возобновляет synthetic optimization.
