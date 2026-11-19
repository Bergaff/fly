# Серия89B4: пользовательский результат

Статус: **strict primary no-go**. Frozen89C и series90 не разрешены.

## Аутентификация

- исходный `summary-27.json`: SHA-256 `334c4a89a87a9cbbac357cc533b99863caa25e9045fba5e8f9ac50c57aff975f`;
- runner89B4: `1f86189bc11e1822c81c488e1c85a377247ffd2d6d8286589d780e729cf07c2f`;
- runner89B3: `b6252829d81ea92c106554f8413cae6b842868c06f69b18fdcd99e5d512ef259`;
- runner89B2: `ec46c681834c4dc13c30d66f07616546809c2f3b29242e134b7f0a004d95f1a3`;
-89B3 extract/upload: `99e07b32…` / `dd16e35a…`;
- frozen model84Z: `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`.

Все pins совпали с preregistration. Режим full, workers6. Development711–728, final729–746; final содержит18 motions ×12 views=216 cases и648 trials. Actions сбалансированы72/72/72, profiles216/216/216, все648 seeds уникальны.

## Независимый пересчёт

| Gate | Результат | Требование | Итог |
|---|---:|---:|---|
| Identity |216/216 |≥195 | pass |
| Safety |648/648 |648 | pass |
| Recovery |645/648 |≥584 | pass |
| Completion |648/648 |≥584 | pass |
| Angle gate | все пять wins648; mean0,226607≤1,05×0,235574 | preregistered | pass |
| Contact vs angle-only |624/648 |≥584 | pass |
| Contact vs common |607/648 |≥584 | pass |
| Contact controls |6/9 |≥6/9 | pass |
| Candidate mean≤hard expert |0,127288≤0,122068 | обязательно | **fail** |
| Candidate mean≤oracle+0,02 |0,127288≤0,142068 | обязательно | pass |

Поэтому `contact_gate_passed=false`, `primary.passed=false` воспроизводятся строго.

Contact wins candidate:

- angle-only624;
- common607;
- hard57;
- oracle57;
- uncalibrated559;
- zero648;
- shuffled648;
- open635;
- lesion648.

## Что объяснила oracle-диагностика

Identity на final идеальна: foreleg72/72, head72/72, reach72/72. Hard predicted expert и oracle expert совпали во всех648 trial records. Значит на этом final слабое место уже **не routing** и не head identity: predicted action всегда равен true action.

Soft mixture проиграла соответствующему hard/oracle expert по mean contact на `0,0052204`, примерно4,28% относительно hard. Она выиграла hard только57/648 раз; по actions: foreleg4/216, head0/216, reach53/216. Вероятностное смешивание разбавило правильный expert остаточной вероятностью других experts, хотя argmax route уже был верен.

При этом head intervention сработала по абсолютной ошибке: head mean contact candidate0,092397, hard/oracle0,085853; candidate выиграла angle-only207/216 и common210/216. Но по заранее установленному gate soft candidate должна была быть не хуже hard. Near miss или остальные проходы не заменяют этот обязательный критерий.

Post-hoc hard-expert counterfactual выглядит сильнее по contact, но не является зарегистрированным primary candidate и не может задним числом превратить89B4 в go. Если продолжать, допустим отдельный preregistered development/final этап с predicted hard routing на полностью новых motions/views. Frozen89C и series90 остаются blocked до полного нового go.

## Ограничения

Synthetic action/contact labels использовались в development; oracle имеет label leakage и только диагностическая. Reduced-body surrogate и geometric contact proxy не являются collision force, muscle dynamics, natural vision или biological neuron validation. Raw development trajectories/NPZ в summary отсутствуют, поэтому fit не воспроизводился заново; final metrics, coverage, routing, controls и decision пересчитаны независимо из648 trial records.
