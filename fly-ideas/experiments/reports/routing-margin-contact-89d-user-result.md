# Серия89D: пользовательский результат

Статус: **full preregistered development go**. Разрешена подготовка отдельной frozen89E на новых motions/views. Series90 остаётся blocked до frozen go.

## Аутентификация

- исходный `summary-31.json`: SHA-256 `fcde095ea33e523f912541183b4120879be8ae6f8ac1a503b9adfedb2bcfb97c`;
- runner89D: `ac85ba29b05535d48bf238ffb955f526b0c4b18419a7526e352afba86ae2304d`;
- runner89C: `5f2c47ec8d4ce16c26e9a3c89026ea5aa1a071b9d74ca1d1bead974c234ea2ee`;
-89C extract/upload: `9bafb373…` / `63c4aaf8…`;
- frozen84Z: `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`.

Все pins совпали. Full mode, workers6. Development837–854, untouched final855–872;36 уникальных motion hashes. Final:216 cases/648 trials, actions72/72/72, profiles216/216/216, все seeds уникальны.

## Development selection

Routing-margin grouped-CV выбрал ridge0,01:

- correct144/144;
- по actions48/48/48;
- mean true margin0,284613;
- minimum true margin положительный:0,021934.

Ridge0,001 дал142/144 и отрицательный minimum margin; остальные также имели меньше minimum-action accuracy. Выбор соответствует preregistered lexicographic rule.

Foreleg boost selection:

| Boost | Common wins | Standard wins | Contact MAE | Eligible common≥44/48 |
|---:|---:|---:|---:|---|
|1,5 |45 |20 |0,166212 |да |
|2 |45 |20 |0,166063 |да |
|4 |44 |21 |0,165763 |да |
|8 |43 |23 |0,165616 |нет |

Boost8 имел лучший mean, но не прошёл заранее установленную common eligibility. Среди eligible выбран boost4 по minimum contact MAE. Post-hoc замены не было.

## Независимый пересчёт final

| Gate | Результат | Требование | Итог |
|---|---:|---:|---|
| Identity total |216/216 |≥195 | pass |
| Identity per action |72/72 каждый |≥65 каждый | pass |
| Safety |648/648 |648 | pass |
| Recovery |645/648 |≥584 | pass |
| Completion |648/648 |≥584 | pass |
| Angle wins |648/648/648/646/648 |≥584 каждый | pass |
| Contact vs angle-only |630/648 |≥584 | pass |
| Contact vs common |639/648 |≥584 | pass |
| Foreleg angle/common |213/209 |≥195/195 | pass |
| Head angle/common |213/214 |≥195/195 | pass |
| Reach angle/common |204/216 |≥195/195 | pass |
| Broad controls |7/8 |≥7/8 | pass |
| Mean candidate≤standard |0,122980≤0,123237 | обязательно | pass |
| Mean candidate≤soft |0,122980≤0,128826 | обязательно | pass |
| Mean candidate≤oracle+0,02 |0,122980≤0,142980 | обязательно | pass |

`identity_gate_passed=true`, `angle_gate_passed=true`, `contact_gate_passed=true`, `primary.passed=true` независимо воспроизведены.

Contact wins: standard126, oracle0, soft587, angle630, common639, uncalibrated536, zero648, shuffled648, open647, lesion648. Broad fail только uncalibrated;7/8 пройдено.

## Интерпретация

На этом новом untouched final routing errors отсутствуют, candidate=oracle во всех648 trials. Mean candidate лучше standard на0,0002571, около0,209%, и лучше soft примерно4,54%. Это больше микроскопической разницы89B6/89C, но всё ещё небольшой эффект; крупный causal effect не заявляется.

Foreleg/common209 уверенно прошёл195; head/reach также прошли. Таким образом, новая composite policy устранила наблюдавшиеся в frozen89C routing и strict mean failures на development-stage untouched final.

Это не отменяет89C no-go и не разрешает series90 напрямую. Нужна новая frozen89E с точными89D model/policy/thresholds и полностью новыми motions/views. Данные89D нельзя использовать для изменения frozen policy.

## Ограничения

Development использует synthetic labels; oracle имеет label leakage. Reduced support/geometric contact proxy не являются collision force, muscles, natural vision или biological-neuron validation. Raw development trajectories/NPZ отсутствуют в summary, поэтому fit не воспроизводился заново; coverage, final metrics, routing, controls и decision пересчитаны независимо из648 trial records.
