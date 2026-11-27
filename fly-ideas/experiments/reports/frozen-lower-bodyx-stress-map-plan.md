# Серия 84: frozen lower-body-X stress map

## Основание

Серия 83 прошла pooled axis, controls и body X=4,18 safeguards, но corner gate дала 10/16 вместо 12/16. Все шесть failed corners находились при body X=3,82; пять отказов относились к right distal, один к left distal. Серия 84 проверяет эту границу без нового обучения и без изменения model83.

## Источник и неизменность

Пользователь выбирает завершённую папку серии 83. Runner проверяет:

- SQLite checkpoint и completed stage;
- protocol и pinned scripts;
- `complete.json` и manifest;
- SHA `model_new.npz`;
- schema и production mode.

До и после серии84 сравниваются SHA всех файлов source83. Любое изменение блокирует результат.

## Новые primary motions

- seed `8402`;
- IDs `281–286`;
- три piecewise5 и три piecewise9;
- движения не использовались для настройки серий82–83.

## Frozen geometry map

FOV остаётся 35°, representation и weights не меняются.

Body X:

`3,70; 3,76; 3,82; 3,88; 4,00; 4,12; 4,18; 4,24; 4,30`.

Для каждого X проверяются все восемь комбинаций:

- camera side `0,14/0,42`;
- camera Z `0,36/0,56`;
- body Y `−0,32/+0,32`.

Итого 72 cells × 6 новых motions = 432 cases.

Primary использует только 16 preregistered core cells body X=3,82 и 4,18, то есть 96 cases. Остальные 56 cells являются boundary diagnostics и не могут улучшить primary.

## Exact failed probes

Отдельно воспроизводятся без включения в primary:

- motions `261, 262, 263, 265, 266, 269`;
- failed corners `1, 5, 6, 9, 13, 14`;
- 36 exact cases.

Normal metrics и SHA 72-state должны побайтово/канонически совпасть с source83 summary. Несовпадение останавливает серию84. Эти probes подтверждают frozen reproduction, но не являются новой независимой проверкой.

## Controls и состояние

Для каждого нового case:

- normal;
- stationary zero;
- shuffled frames;
- static first frame;
- closed black input.

Framewise estimates сжимаются в 72 cosine coefficients. State не обновляется 0,5 с; replay использует только state и phase.

Сохраняются RGB SHA, unique/changed RGB, feature variance, clipping, state SHA и framewise autonomous predictions.

## Blocking primary

На 96 core cases каждая из шести осей должна:

- иметь pooled normal ниже zero;
- выигрывать минимум 70%, то есть не менее 68/96 cases.

Combined normal должен быть ниже zero, shuffled, static и closed.

### Lower-body-X safeguard

На 48 cases с body X=3,82 каждая ось должна:

- иметь pooled normal ниже zero;
- выигрывать минимум 34/48 cases.

### Core-cell gate

Каждая core cell проверяется на шести новых motions. Cell проходит, только если каждая из шести осей:

- pooled normal ниже zero;
- выигрывает минимум 5/6 motions.

Требуется минимум 12/16 прошедших core cells.

Только полный frozen go разрешает переход к серии85. Neighbor cells и exact source probes не могут спасти primary.

## Ограничения

Это frozen synthetic stress map одной модели и одной geometry family. Нет retraining, natural vision, нового поведения, contacts, actuators, forces, closed-loop управления, biological brain или mirror-neuron evidence.
