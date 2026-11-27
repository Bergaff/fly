# Серия89B6: пользовательский результат

Статус: **full preregistered development go**. Это разрешает подготовить отдельную frozen89C на новых motions/views, но не заменяет её и не разрешает series90.

## Аутентификация

- исходный `summary-29.json`: SHA-256 `f1c362073c81f505a28ada36306bf51160ec9f3051ad3997b123c4777dc2fcc2`;
- runner89B6: `1d308cb1ff20a7f6934775c0da62df99bdf062b1fc5e1395328f4f94594c0cb6`;
- runner89B5: `6ebd6af6910ec1e5b30984d9247e3fc7374031393466e7959ad37cfd1fc697fc`;
-89B5 extract/upload: `0729aac3…` / `c14bbb13…`;
- frozen model84Z: `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`.

Все pins совпали. Full mode, workers6. Development783–800, untouched final801–818;36 уникальных motion hashes. Final:18 motions×12 views=216 cases и648 trials. Actions72/72/72, profiles216/216/216, все648 seeds уникальны.

## Development selection

Grouped-CV foreleg boost:

| Boost | Cases | Wins vs common | Wins vs standard | Contact MAE |
|---:|---:|---:|---:|---:|
|1,5 |48 |45 |24 |0,165097 |
|2 |48 |45 |24 |0,165088 |
|4 |48 |**46** |24 |0,165018 |
|8 |48 |45 |25 |**0,164798** |

По заранее заданному lexicographic rule сначала максимизировались wins vs common, поэтому выбран boost **4**, а не post-hoc лучший mean boost8. Identity grouped-CV для ridge0,01:144/144.

## Независимый пересчёт final

| Gate | Результат | Требование | Итог |
|---|---:|---:|---|
| Identity total |216/216 |≥195 | pass |
| Identity per action |72/72 каждый |≥65 каждый | pass |
| Safety |648/648 |648 | pass |
| Recovery |645/648 |≥584 | pass |
| Completion |648/648 |≥584 | pass |
| Angle wins |648/648/648/644/648 |≥584 каждый | pass |
| Mean angle vs angle-only |0,232303≤1,05×0,242685 | обязательно | pass |
| Contact vs angle-only |638/648 |≥584 | pass |
| Contact vs common |633/648 |≥584 | pass |
| Foreleg vs angle/common |214/201 |≥195/195 | pass |
| Head vs angle/common |213/216 |≥195/195 | pass |
| Reach vs angle/common |211/216 |≥195/195 | pass |
| Broad controls |7/8 |≥7/8 | pass |
| Mean candidate≤standard |0,122611≤0,122644 | обязательно | pass |
| Mean candidate≤soft |0,122611≤0,126982 | обязательно | pass |
| Mean candidate≤oracle+0,02 |0,122611≤0,142611 | обязательно | pass |

`identity_gate_passed=true`, `angle_gate_passed=true`, `contact_gate_passed=true` и `primary.passed=true` независимо воспроизведены.

Contact wins candidate:

- standard-hard126, diagnostic intervention comparison;
- oracle0, exact tie;
- soft587;
- angle-only638;
- common633;
- uncalibrated557, единственный broad fail;
- zero648;
- shuffled648;
- open-loop639;
- lesion648.

## Интерпретация

Оставшийся отказ89B5 устранён на новом untouched final: foreleg/common вырос с188/216 в предыдущей серии до201/216 здесь и прошёл195. Это сравнение между разными final наборами, поэтому оно показывает успешную свежую проверку, а не paired causal effect между сериями.

Robust candidate улучшила mean относительно standard-hard очень мало:0,0000323, около0,026%. Она выиграла standard в126/216 foreleg trials. Поэтому нельзя утверждать крупный эффект reweighting. Сильный вывод уже: полностью preregistered composite policy прошла все заранее заданные identity, safety, angle, action-specific contact и broad-control gates на untouched final.

Hard routing вновь совпал с truth-label oracle во всех648 records. Candidate не получала true action. Head/reach не были ослаблены: все их direct action gates прошли.

## Решение

-89B6: **development go**;
- теперь допустима отдельная frozen89C с полностью замороженными89B6 model/policy/thresholds на новых motions/views;
- данные89B6 нельзя использовать для изменения frozen policy;
- series90 остаётся blocked до успешной89C;
- near miss89C будет no-go.

## Ограничения

Development использует synthetic labels. Oracle имеет label leakage и только диагностический статус. Reduced support surrogate и geometric contact proxy не являются collision force, muscle dynamics, natural vision или biological-neuron validation. Raw development trajectories/NPZ отсутствуют в summary, поэтому fit не воспроизводился заново; coverage, final metrics, routing, controls и decision пересчитаны независимо из648 trial records.
