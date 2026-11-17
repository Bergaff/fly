# Серия 84V: paired-view distal consistency model development

## Основание

Series84S прошла свою final battery321–330, но frozen replication84U на motions341–350 дала no-go. Абсолютный signal устойчив, однако right-distal превосходство над84R зависит от движения: global77/160 вместо96/160, lower-X44/80 вместо48/80. Особенно слабы уже раскрытые motions344 и347.

Series85 остаётся заблокированной. Model84S не переобучается.

## Единственное model-development изменение

Архитектура576-D, edge-history, ridge по осям, clipping, camera resolution, FOV, число render-candidates и fixed-count lifecycle остаются как84S.

Меняется только организация training distribution:

- 4 096 новых base motions, seed8425;
- каждое движение повторяется ровно в четырёх связанных ракурсах;
- два ракурса имеют body X=3,82, два body X=4,18;
- внутри пары противоположны side, camera-Z и body-Y bits;
- итого ровно16 384 committed render-candidates и802 816 frames;
- piecewise5, piecewise9, harmonic и chirp сбалансированы по base-motion ID.

В84S конкретное движение и ракурс семплировались независимо и почти всегда встречались одной парой. Контрфактическая четвёрка заставляет sufficient-statistics fit видеть одно и то же движение при существенно разных геометриях. Это заранее выбранная попытка уменьшить motion/view confounding, а не настройка на motions341–350.

## Запреты

- не менять model84S или model84R;
- не использовать motions321–350 в training, validation или blocking evaluation;
- не исключать motions344/347;
- не менять ridge, crop, thresholds или число candidates после результата;
- не запускать дополнительные seeds в поиске удачного результата;
- не переходить к series85 даже при go84V: сначала потребуется отдельная frozen replication нового кандидата.

## Источник

Пользователь выбирает завершённую папку series84S. Проверяются её SQLite stage, protocol, complete manifest, runner84S SHA и production model84S SHA `a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f`. Embedded model84R остаётся вторым frozen comparator.

## Fixed-count lifecycle

- ровно16 384 committed candidates;
- два workers;
- transactional SQLite и pause/resume;
- QuickEdit отключается и проверяется;
- wall time только diagnostic, completion только по count;
- ожидаемая длительность примерно как84S, около4–8 часов плюс evaluation;
- fixture mode ограничен2–8 candidates и не является научным результатом.

## Новая blocking evaluation

- seed8426;
- motions361–370, пять piecewise5 и пять piecewise9;
-16 заранее заданных corners;
-160 cases;
- candidate сравнивается одновременно с frozen84S, frozen84R, zero, shuffled, static и closed;
-72-coefficient state, delay0,5с без обновлений.

## Blocking primary

### Absolute axes

Каждая ось candidate ниже zero и минимум112/160 wins.

### Оба frozen comparators

Right distal должна:

- быть ниже model84S и model84R pooled;
- иметь минимум96/160 wins против каждой модели.

Остальные пять осей должны пройти absolute gate и быть не хуже каждой frozen model более чем на5% pooled.

### Lower-X right distal

На80 body-X=3,82 cases candidate должна:

- быть ниже zero, model84S и model84R pooled;
- иметь минимум60/80 wins против zero;
- иметь минимум48/80 wins отдельно против model84S и model84R.

### Geometry и corners

- обе body-X groups: каждая ось ниже zero, минимум56/80 wins;
- обе camera-Z groups: то же;
- минимум12/16 corners: все оси ниже zero и минимум7/10 wins.

### Combined и controls

Candidate combined ниже model84S, model84R, zero, shuffled, static и closed.

Все компоненты blocking. Один fail означает model no-go без округления и post hoc исключений.

## После результата

- no-go: series85 остаётся заблокированной; motions361–370 становятся раскрытыми;
- go: candidate замораживается, но series85 всё равно заблокирована до отдельной replication на совершенно новых motions/seeds.

## Ограничения

Это supervised synthetic reconstruction в прежнем generator family и geometry grid. Даже go не доказывает natural vision, новое действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
