# Серия 82G: пользовательский результат scale-normalized camera prototype

## Статус и источник

Пользователь прислал завершённый `summary-6.json`. SHA-256 исходного файла:

`9bed977b784bc5ab05bf1313ca7fa410af3d9b4f08d6b0a66e044ad2ac9dd4e1`

Schema `scale-normalized-camera-prototype-result-v1`, status `completed`, mode `prototype`. SHA runner 82G `f4dbe408f750500623b201da46b8c5452a3d465541c16b54406afc9eab96de64` и закреплённого runner 82 `175b8ee1ef63a2e045fb62bff84bdfc345c05d8285f170397e033424ba3d96b1` совпадают с файлами репозитория.

Summary содержит 320 training diagnostics, 32 visibility records, 16 cell results и 96 evaluation records. Полная локальная папка, NPZ, RGB и CSV не передавались.

## Blocking result

`go_for_revised_long_training = true`.

Primary использовал только `fov35_edge`; tracked camera не участвовала в решении.

| Ось | Variable edge | FOV35 edge | Tracked35 diagnostic | Zero | Wins FOV35 vs variable | Gate |
|---|---:|---:|---:|---:|---:|---|
| left proximal | 0,401339 | 0,333496 | 0,180403 | 0,420796 | 87/96 | pass |
| left middle | 0,268441 | 0,178087 | 0,109915 | 0,403057 | 78/96 | pass |
| left distal | 0,471998 | 0,456971 | 0,334189 | 0,477705 | 69/96 | pass |
| right proximal | 0,414893 | 0,344652 | 0,197402 | 0,432531 | 85/96 | pass |
| right middle | 0,247752 | 0,156201 | 0,099619 | 0,378581 | 76/96 | pass |
| right distal | 0,442509 | 0,429496 | 0,314544 | 0,448349 | 66/96 | pass |

Combined variable/FOV35/tracked/zero:

`0,384111 / 0,336503 / 0,225144 / 0,428009`.

FOV35 улучшает combined относительно variable на 12,39% и относительно zero на 21,38%.

## Distal primary

Обе distal axes прошли все обязательные части:

- left distal: −3,18% против variable, −4,34% против zero, wins `69/96` или 71,88%;
- right distal: −2,94% против variable, −4,21% против zero, wins `66/96` или 68,75%.

Distal эффект меньше proximal/middle, но имеет правильный знак относительно обоих controls и проходит заранее заданный case threshold.

## FOV safeguards

Combined по группам исходного FOV:

- original FOV30 variable/FOV35: `0,373062 / 0,336626`;
- original FOV70 variable/FOV35: `0,394851 / 0,336381`.

Оба safeguards прошли. Fixed-FOV representation практически выравнивает combined score двух исходных групп.

Distal отдельно:

| Original FOV | Left variable/FOV35/zero | Right variable/FOV35/zero | Wins L/R |
|---|---:|---:|---:|
| 30 | 0,472430 / 0,456785 / 0,477705 | 0,440360 / 0,429645 / 0,448349 | 33/48, 29/48 |
| 70 | 0,471565 / 0,457157 / 0,477705 | 0,444647 / 0,429347 / 0,448349 | 36/48, 37/48 |

Правильный pooled знак сохраняется в обеих FOV-группах. Для right distal FOV30 wins `29/48`, лишь немного выше 60%, поэтому запас gate остаётся умеренным.

## Visibility и corners

Fixed-FOV visibility прошла во всех cells:

- left distal: `16/16`;
- right distal: `16/16`;
- требовалось: `12/16`.

Median changed RGB96 при +10°:

- left: range `197–338`, median `255`;
- right: range `200–354`, median `252`.

Минимальный edge feature delta RMS также значительно выше 1e-4: `0,001825` left и `0,002679` right.

Both-distal corner gate прошёл ровно на границе: `12/16`. По исходным FOV это `5/8` для FOV30 и `7/8` для FOV70. Четыре не прошедших cells: 4, 6, 8 и 12; во всех body X = 4,18. В трёх из четырёх отказ связан только с right distal, в cell 6 не улучшены обе distal axes. Это важная зона риска для long training, но исключать эти cells post hoc нельзя.

## Tracked-camera diagnostic

Tracked35 combined `0,225144`, существенно ниже primary FOV35 `0,336503`. Все шесть tracked axis scores также ниже FOV35. Это показывает большой оставшийся потенциал body-relative gaze stabilization.

Однако tracked camera использует simulator body pose для установки сенсора и заранее помечена diagnostic-only. Она не участвовала в gate и не является основанием для claims или замены primary результата.

## Решение

Полный preregistered gate пройден. Разрешено **проектирование переработанной серии 83** с fixed-FOV35 edge representation, balanced view sampling и новым независимым holdout.

Это разрешение не означает, что long training уже успешно. Для серии 83 до запуска необходимо отдельно зафиксировать:

- 8-hour active budget;
- новые training/evaluation seeds и motion IDs;
- fixed FOV35 как primary sensor;
- все шесть axis gates, zero и temporal controls;
- отдельный body-X=4,18 safeguard;
- 72-state delay/replay;
- tracked camera только как diagnostic, если она вообще включается.

Нельзя переносить motions 241–246 в tuning или evaluation серии 83.

## Ограничения

Серия 82G является short supervised synthetic geometry ablation. Fixed FOV меняет observation geometry. Tracked camera использует simulator body pose. Нет long-run replay result, contacts, actuator dynamics, biological brain или mirror-neuron evidence.
