# Серия 82D: пользовательский результат distal observability diagnostic

## Статус и источник

Пользователь прислал завершённый `summary-5.json`. SHA-256 исходного файла:

`94f1142c79af42fb96d2c8c2446b1ccde4bcae55b9d28bb776acf1e235580e42`

Schema `distal-observability-diagnostic-result-v1`, status `completed`, mode `diagnostic`. SHA runner 82D `43b0f28abe5663cae300c878d3cc726398777ec6248aa12d798662ea6415805c` и закреплённого runner 82 `175b8ee1ef63a2e045fb62bff84bdfc345c05d8285f170397e033424ba3d96b1` совпадают с файлами репозитория.

Summary содержит 320 training diagnostics, 32 visibility records и 96 evaluation records для motions 221–226 × 16 corners. Полная локальная папка, модели, RGB и CSV не передавались.

## Frozen routing

Результат программы:

- visibility passed: **нет**;
- visible cells left distal: `8/16`;
- visible cells right distal: `8/16`;
- preregistered threshold: `12/16` для каждой оси;
- candidate representations: нет;
- route: `geometry_or_occlusion`;
- `authorizes_series83 = false`.

Запись `Visible cells L/R: 8/8` означает восемь cells для left и восемь для right, а не 8 из 8. Всего для каждой оси проверялось 16 cells.

## Локализация visibility failure

Все прошедшие cells относятся к FOV30, все FOV70 провалили RGB guard:

| FOV | Visible axis-cell pairs | Всего | Cells с обеими видимыми distal |
|---|---:|---:|---:|
| 30 | 16 | 16 | 8 |
| 70 | 0 | 16 | 0 |

При FOV30 медианное число изменённых RGB values на +10° составляло:

- left distal: 69–103 при 48×32 и 257–387 при 96×64;
- right distal: 60–108 при 48×32 и 252–433 при 96×64.

При FOV70:

- left distal: 10–18 при 48×32 и 38–78 при 96×64;
- right distal: 9–18 при 48×32 и 39–60 при 96×64.

Guard требовал median changed RGB48 ≥20. Feature-delta часть guard во всех FOV70 cells была выше 1e-4: standard48 level RMS находился примерно в диапазоне `0,00196–0,00355` для left и `0,00217–0,00322` для right. Следовательно, формальный failure вызван именно малым числом изменённых RGB values при FOV70, а не нулевыми features.

Сигнал при широком FOV не исчезает полностью, но пространственно слишком мал и не проходит заранее заданный guard. High-resolution RGB увеличивает число изменённых values примерно в 3–5 раз, однако fixed coarse pooling не превращает это в достаточное стабильное distal decoding.

## Representation comparison

| Representation | Left distal | Right distal | Wins L/R vs standard | Обе ниже zero |
|---|---:|---:|---:|---|
| standard48 level | 0,428980 | 0,459119 | 0/0 | нет |
| high96 level | 0,429682 | 0,459945 | 52/49 | нет |
| high96 edge | 0,424339 | 0,454878 | 58/54 | нет |
| high96 level+edge | 0,430652 | 0,460988 | 46/50 | нет |
| zero | 0,419746 | 0,452857 | — | — |

Edge-only является лучшим из обученных representations по pooled distal RMSE и даёт left wins `58/96`, то есть ровно проходит 60%-й case threshold для left. Но right имеет только `54/96`, и обе оси всё равно хуже zero. Поэтому edge-only является диагностически интересным, но не candidate по frozen rule.

Level+edge снова не помогает pooled distal и хуже standard на обеих осях этой новой батареи. Это подтверждает, что combined улучшение серии 82 нельзя переносить на distal axes.

## Взаимодействие FOV и zero

Pooled distal RMSE по FOV:

| Representation | FOV30 L/R | FOV70 L/R |
|---|---:|---:|
| standard48 level | 0,438939 / 0,469104 | 0,418785 / 0,448912 |
| high96 level | 0,440701 / 0,470964 | 0,418373 / 0,448656 |
| high96 edge | 0,430588 / 0,460482 | 0,417997 / 0,449205 |
| high96 level+edge | 0,444344 / 0,474310 | 0,416510 / 0,447269 |
| zero | 0,419746 / 0,452857 | 0,419746 / 0,452857 |

Важное уточнение: при FOV70 level+edge ниже zero по обеим distal axes, несмотря на слабый perturbation signal. Общий проигрыш zero создаётся FOV30, где visual perturbation сильнее, но predictions имеют большую ошибку и bias. Это не отменяет frozen route: visibility gate всё равно провален. Но следующий geometry/occlusion prototype должен решать **несогласованность масштаба и представления между FOV**, а не исходить из предположения, что distal полностью невидимы.

## Диагностика прогнозов

У всех representations distal gain through origin очень мал: примерно `0,007–0,034` при target RMS около `0,417–0,448` рад. Prediction RMS находится примерно в диапазоне `0,035–0,140` рад. Sign agreement при |target| ≥5° остаётся около `0,51–0,58`.

Это указывает на сильное attenuation и почти случайную передачу знака, а не только на небольшой постоянный offset. Edge повышает correlation и sign agreement, особенно при FOV70, но недостаточно для общего превосходства над zero.

## Решение

1. Серия 83 остаётся запрещённой.
2. Gate 82D не ослаблять: FOV70 не переименовывать в visible post hoc только потому, что feature delta ненулевая.
3. Следующий short prototype должен следовать `geometry_or_occlusion` route и нормализовать apparent distal scale между FOV30 и FOV70 без teacher/camera metadata в decoder.
4. Edge-only можно сохранить как diagnostic channel, но нельзя объявлять победителем.
5. Новый prototype должен снова иметь отдельные distal, zero, per-FOV и corner gates до запуска.

## Ограничения

Это short supervised synthetic engineering diagnostic. Perturbation +10° не является биологическим тестом зрения. Использовался один linear ridge decoder class. Нет replay, contacts, actuator dynamics, biological brain или mirror-neuron evidence.
