# Серия89B5: пользовательский результат

Статус: **strict primary no-go**. Frozen89C и series90 не разрешены.

## Аутентификация

- исходный `summary-28.json`: SHA-256 `c14bbb13d7900ae017e5248b65d0eaac19e85c53c03e5124e4d6d0b3cf32b8e1`;
- runner89B5: `6ebd6af6910ec1e5b30984d9247e3fc7374031393466e7959ad37cfd1fc697fc`;
- runner89B4: `1f86189bc11e1822c81c488e1c85a377247ffd2d6d8286589d780e729cf07c2f`;
-89B4 extract/upload: `3c69f14b…` / `334c4a89…`;
- frozen model84Z: `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`.

Все pins совпали. Full mode, workers6. Development747–764, untouched final765–782;36 уникальных motion hashes. Final содержит18 motions×12 views=216 cases и648 trials. Actions72/72/72, profiles216/216/216, все seeds уникальны.

## Независимый пересчёт

| Gate | Результат | Требование | Итог |
|---|---:|---:|---|
| Identity total |216/216 |≥195 | pass |
| Identity per action |72/72 каждый |≥65 каждый | pass |
| Safety |648/648 |648 | pass |
| Recovery |645/648 |≥584 | pass |
| Completion |648/648 |≥584 | pass |
| Angle | все пять wins648; mean0,227256≤1,05×0,238170 | preregistered | pass |
| Contact vs angle-only total |635/648 |≥584 | pass |
| Contact vs common total |617/648 |≥584 | pass |
| Per-action vs angle-only |208/216,216/216,211/216 |≥195 каждый | pass |
| Per-action vs common |foreleg188/216, head216/216, reach213/216 |≥195 каждый | **fail** |
| Contact controls |6/9 |≥7/9 | **fail** |
| Mean candidate≤soft |0,121827≤0,126011 | обязательно | pass |
| Mean candidate≤oracle+0,02 |0,121827≤0,141827 | обязательно | pass |

`contact_gate_passed=false` и `primary.passed=false` воспроизводятся строго.

Contact wins hard candidate:

- soft mixture561;
- angle-only635;
- common617;
- oracle0, поскольку trajectories равны;
- uncalibrated568;
- zero648;
- shuffled648;
- open-loop647;
- shared-lesion648.

## Интерпретация

Predicted hard routing воспроизвёл идеальную identity: foreleg72/72, head72/72, reach72/72. Candidate и truth-label oracle совпали во всех648 trial records. Значит routing вновь не является причиной no-go.

Hard policy улучшила средний contact относительно soft mixture на0,004184, примерно3,32%, и head остаётся сильным:

- head candidate mean0,085062 против soft0,091639;
- head wins angle-only216/216 и common216/216;
- reach wins angle-only211/216 и common213/216.

Узкое место переместилось в foreleg/common direct control:188/216 вместо195. Foreleg mean candidate0,194589 лучше common0,215972, но paired wins87,0% не достигают preregistered90%. Aggregate mean и total617 не заменяют action-specific gate.

Второй отказ,6/9 controls, обусловлен тем, что oracle всегда tied0, а soft561 и uncalibrated568 ниже584. Mean hard лучше soft, но paired improvement против soft составляет86,6%, поэтому он не даёт седьмой control pass.

Нельзя удалять oracle из знаменателя, понижать195/584, заменять paired gates средними или постфактум считать6/8. Если продолжать, допустима только новая preregistered development-серия на полностью новых motions/views, нацеленная на foreleg/common paired consistency и устойчивое преимущество hard над soft.89C/90 остаются blocked.

## Ограничения

Development использует synthetic labels; oracle имеет label leakage и диагностический статус. Reduced support surrogate и geometric contact proxy не являются collision force, muscle dynamics, natural vision или biological-neuron validation. Raw development trajectories/NPZ отсутствуют в summary, поэтому fit не воспроизводился заново; coverage, final metrics, routing, controls и decision пересчитаны независимо из648 trial records.
