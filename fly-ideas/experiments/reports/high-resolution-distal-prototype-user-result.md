# Серия 82: пользовательский результат high-resolution distal prototype

## Статус и источник

Пользователь прислал завершённый `summary-4.json`. SHA-256 исходного файла:

`cda09972ff536cd1789c6c858b4e08849ea31946ffb12181e3103581c24d8066`

Schema `high-resolution-distal-prototype-result-v1`, status `completed`, mode `prototype`. Встроенный SHA runner серии 82 `175b8ee1ef63a2e045fb62bff84bdfc345c05d8285f170397e033424ba3d96b1` совпадает с файлом репозитория. Протокол содержит 320 training episodes с seeds 8201/8203 и frozen evaluation: motions 201–206, seed 8202, 16 held corners, 96 cases.

Полная пользовательская папка, NPZ и изображения не передавались. Проверка относится к присланному JSON, его внутренним агрегатам и локальной копии runner.

## Зафиксированный результат

`go_for_long_training = false`.

| Ось | Standard | Highres | Zero | Wins highres vs standard | Gate |
|---|---:|---:|---:|---:|---|
| left proximal | 0,423157 | 0,397784 | 0,462458 | 73/96 | pass |
| left middle | 0,382532 | 0,293917 | 0,494648 | 88/96 | pass |
| left distal | 0,473231 | 0,473464 | 0,464687 | 59/96 | fail |
| right proximal | 0,420722 | 0,395099 | 0,461679 | 73/96 | pass |
| right middle | 0,370217 | 0,279314 | 0,484252 | 88/96 | pass |
| right distal | 0,479971 | 0,479215 | 0,472521 | 60/96 | fail |

Combined standard/highres/zero: `0,426962 / 0,394241 / 0,473533`. Highres улучшает combined относительно standard на 7,66%, но combined не является blocking distal criterion.

Оба общих FOV safeguard прошли:

- FOV30 standard/highres: `0,391367 / 0,370218`;
- FOV70 standard/highres: `0,459810 / 0,416881`.

Held corners, в которых улучшены обе distal axes: `10/16`, при preregistered пороге `12/16`.

## Почему это no-go

Preregistered gate требовал одновременно для обеих distal axes:

1. highres ниже standard;
2. highres ниже zero;
3. не менее 60% case wins;
4. минимум 12/16 corners улучшают обе distal axes.

Фактически:

- left distal чуть хуже standard на 0,05% и хуже zero на 1,89%;
- right distal чуть лучше standard на 0,16%, но хуже zero на 1,42%;
- case-win части достаточно: 59/96 и 60/96;
- corner gate провален: 10/16.

То есть отказ не вызван числом wins. Основной отказ состоит в том, что обе distal predictions остаются хуже неподвижного zero control. Сильные улучшения middle axes, 23,17% и 24,55%, снижают combined RMSE и скрывают distal failure, поэтому combined score нельзя использовать для разрешения long run.

## Диагностика FOV

Улучшение обеих distal axes по corners сосредоточено при широком поле зрения:

- FOV30: 3/8 corners;
- FOV70: 7/8 corners.

На 48 cases каждого FOV pooled distal значения:

| FOV | Ось | Standard | Highres | Zero | Wins |
|---|---|---:|---:|---:|---:|
| 30 | left distal | 0,473467 | 0,477409 | 0,464687 | 24/48 |
| 30 | right distal | 0,479443 | 0,480720 | 0,472521 | 26/48 |
| 70 | left distal | 0,472994 | 0,469486 | 0,464687 | 35/48 |
| 70 | right distal | 0,480498 | 0,477704 | 0,472521 | 34/48 |

Highres помогает обеим distal axes при FOV70 относительно standard, но даже там не превосходит zero. При FOV30 highres ухудшает обе distal axes. Это уточняет область отказа, но не меняет preregistered решение.

## Техническая целостность

В summary присутствуют 320 training diagnostics и 96 evaluation records. Минимальное число уникальных кадров:

- training standard/highres: 48/51;
- evaluation standard/highres: 51/51.

Минимальный зафиксированный maximum feature standard deviation положителен: standard `0,019160`, highres `0,015307`. Признаков constant-RGB дефекта серии 74 в summary нет.

## Решение и следующий допустимый шаг

Серию 83, восьмичасовое high-resolution обучение, **не запускать**. Gate серии 82 не ослаблять post hoc.

Результат отвергает весь проверенный пакет `96×64 + pooled luminance + gradient-energy history` как достаточное решение distal failure. Он не разделяет эффект sensor resolution и gradient features. Следующий шаг должен быть новой заранее зарегистрированной короткой distal-focused диагностикой, а не long run: отдельно проверить видимость/сигнал distal сегментов и причину преимущества zero, особенно при FOV30. До такой диагностики этап roadmap 82–84 остаётся заблокированным.

## Ограничения claims

Это short supervised synthetic representation ablation. Нет replay, contacts, actuators, biological brain или доказательства mirror neurons. Результат не показывает, что высокое разрешение в принципе бесполезно; он показывает no-go только для зафиксированного полного representation package и protocol серии 82.
