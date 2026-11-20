# Frozen89C: пользовательский результат

Статус: **strict frozen replication no-go**. Series90 не разрешена.

## Аутентификация

- исходный `summary-30.json`: SHA-256 `63c4aaf8a982a44471f3a0677f38ef5b4b29831650fdcf4ed6b77362764375ea`;
- runner89C: `5f2c47ec8d4ce16c26e9a3c89026ea5aa1a071b9d74ca1d1bead974c234ea2ee`;
- runner89B6: `1d308cb1ff20a7f6934775c0da62df99bdf062b1fc5e1395328f4f94594c0cb6`;
-89B6 extract/summary: `88769591…` / `f1c36207…`;
- frozen89B6 model: `b8beb562d5a623d31ae7094fedfdb57b6a844f5f361c04092c0a641a7f5534f1`;
- frozen84Z model: `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`;
- boost4, `training_allowed=false`, `selection_allowed=false`.

Все pins совпали. Full mode, workers6. Motions819–836 и views721–732:216 уникальных cases,648 trials. Actions72/72/72, profiles216/216/216, все seeds уникальны.

## Независимый пересчёт

| Gate | Результат | Требование | Итог |
|---|---:|---:|---|
| Identity total |212/216 |≥195 | pass |
| Identity per action |foreleg70, head70, reach72 |≥65 каждый | pass |
| Safety |648/648 |648 | pass |
| Recovery |648/648 |≥584 | pass |
| Completion |648/648 |≥584 | pass |
| Angle wins |648/645/648/641/648 |≥584 каждый | pass |
| Contact vs angle-only |631/648 |≥584 | pass |
| Contact vs common |620/648 |≥584 | pass |
| Foreleg vs angle/common |210/194 |≥195/195 | **fail by1** |
| Head vs angle/common |210/210 |≥195/195 | pass |
| Reach vs angle/common |211/216 |≥195/195 | pass |
| Broad controls |6/8 |≥7/8 | **fail** |
| Mean candidate≤standard |0,1297995926≤0,1297995817 | обязательно | **fail** |
| Mean candidate≤soft |0,129800≤0,133907 | обязательно | pass |
| Mean candidate≤oracle+0,02 |0,129800≤0,145625 | обязательно | pass |

`identity_gate_passed=true`, `angle_gate_passed=true`, но `contact_gate_passed=false` и `primary.passed=false` воспроизводятся строго.

Broad contact wins:

- soft582, ниже584 на2;
- angle-only631;
- common620;
- uncalibrated557;
- zero642;
- shuffled642;
- open-loop636;
- lesion642.

Проходят6/8; soft и uncalibrated не проходят.

## Routing diagnostic

Обнаружены4/216 routing errors:

- два foreleg cases ошибочно направлены в reach;
- два head cases ошибочно направлены в reach;
- reach72/72.

Каждый visual case имеет три profiles, поэтому ошибки маршрутизации затрагивают12 trials. Oracle counterfactual для foreleg выиграл common200/216, тогда как deployable candidate194/216. То есть две foreleg routing errors полностью объясняют direct foreleg miss by1 на этом frozen наборе. Это диагностическое объяснение не меняет primary: candidate не имеет доступа к true action.

Candidate mean хуже standard-hard всего на `1,095×10⁻⁸`. Разница практически ничтожна, но preregistered inequality была строгой и не содержит tolerance или округления. Её нельзя задним числом считать tie/pass.

## Решение

-89B6 development go сохраняется как исторический результат;
- frozen89C: **no-go**;
- series90 остаётся blocked;
- нельзя округлить194 до195,582 до584, считать6/7, добавить tolerance к mean gate или заменить candidate oracle;
- данные motions819–836 теперь раскрыты и не могут использоваться как новый frozen holdout.

Следующий допустимый путь, если продолжать: отдельная preregistered development-серия на полностью новых motions/views, направленная на routing-margin robustness foreleg/head. Она не является повтором89C; после нового development go потребуется новый frozen holdout.

## Ограничения

Synthetic truth используется для scoring и oracle diagnostic. Reduced support/geometric contact proxy не являются collision force, muscles, natural vision или biological-neuron validation. Frozen model не refit; final coverage, metrics, routing, controls и decision пересчитаны независимо из648 trial records.
