# Серия86: preregistered multi-action and compositional shared-population test

## Основание

Series85 дала operational shared-population prototype go на одном foreleg-grooming family. Series86 проверяет, кодирует ли та же frozen six-unit population identity нескольких действий и их новый порядок, а не только общую фазу/амплитуду одной траектории.

Pins:

- runner85 SHA `cdef42fd5f4f45d7b5b37ab01f2b3ba4af22663265b1e1980254a7b44596b210`;
- selected model84Z SHA `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`;
- training model84Z запрещён;
- motions421–470 раскрыты и запрещены.

## Три synthetic kinematic motifs

1. `foreleg_rubbing`: opposed bilateral rubbing;
2. `head_directed_grooming`: synchronized bilateral head-directed pattern;
3. `reach_withdraw`: unilateral reach/withdraw, сторона заранее зависит от seed.

Названия обозначают инженерно заданные six-joint kinematic motifs. Они не доказывают контакт с головой или естественное поведение.

## Calibration, blocking identity и composition

Calibration seed8601:

- motions471–479;
-3 trajectories на action;
- amplitude0,70;
- speeds0,90/1,15/1,40;
-4 заранее заданных corners;
- fixed shared prototypes строятся как midpoint shared-observation/execution features;
- equal-budget private84V получает отдельные matched midpoint private-observation/execution prototypes и scale из тех же calibration motions;
- calibration не входит в primary и не выбирает thresholds/models.

Blocking identity seed8602:

- motions480–491;
-4 trajectories на action;
- held-out amplitudes0,85/1,00;
- held-out speeds0,75/1,25;
-16 corners;
- observation traces усредняются по views до классификации.

Compositional seed8603:

- motions492–497;
- все шесть ordered pairs разных actions;
- первая и вторая половина классифицируются отдельно;
-16 corners;
- новый порядок не встречается в calibration.

Всего324 render cases:36 calibration,192 identity,96 composition. Все motion hashes проверяются против всех accepted training hashes84Z и disclosed labels; дополнительно сохраняется broad audit128.

## Fixed 18-dimensional representation audit

Для каждого trace заранее фиксированы:

- mean шести units;
- standard deviation шести units;
- time-normalized RMS velocity шести units.

Для RSA все18 features делятся на shared calibration scale; расстояния не зависят от общего центрирования. Summary экспортирует prototypes, normalization scale, raw observation/execution/private feature vectors,66 identity pair labels и оба массива normalized RSA distances. Поэтому RSA можно независимо пересчитать без изображений.

## Blocking primary

Все пункты обязательны:

### Action identity

- shared observation минимум8/12 correct;
- не хуже equal-budget private84V более чем на1 case;
- strictly выше p95 из1000 shuffled-label permutations;
- минимум2/4 correct отдельно для каждого action.

### Cross-mode RSA

- correlation observation/execution pairwise distances не ниже0,30;
- строго выше p95 из1000 shuffled-motion permutations;
- distance vectors экспортируются.

### Compositional order

- минимум4/6 ordered pairs классифицированы полностью правильно;
- нельзя засчитать отдельные половины вместо exact ordered pair.

### Population safeguards

- минимум4/6 units имеют observation/execution correlation не ниже0,15;
- каждый засчитанный unit выше shuffled/static/closed controls;
- shared pooled RMSE не хуже equal-budget private84V более чем на5%;
- shared RMSE ниже zero/shuffled/static/closed;
-72 coefficients, delay0,5s и immutable state.

Near-miss является no-go. Нельзя удалить action, order, amplitude, speed, motion, corner или unit post hoc.

## Запуск

`experiments\RUN-MULTIACTION-COMPOSITIONAL-POPULATION.bat`

GUI:2/4/6/Максимум workers. Максимум использует все логические процессоры без искусственного резерва памяти для других приложений. Выбирается завершённая production-папка84Z. При ошибке открывается `workspace\runs\ideas\i-observational\multiaction-compositional-population\ПОСЛЕДНЯЯ-ОШИБКА-86.txt`.

## Ограничения

- engineered synthetic motifs;
- artificial semantic units;
- frozen supervised visual decoder;
- нет natural vision;
- нет самостоятельно созданного action;
- kinematic replay, не actuators;
- нет сил, мышц и closed-loop correction;
- не является доказательством биологических mirror neurons.
