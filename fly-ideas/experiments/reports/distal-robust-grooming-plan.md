# Серия 84R: восьмичасовая distal-robust grooming model

## Причина новой модели

Frozen series84 дала строгий no-go: left distal 67/96, lower-X left distal 32/48 и только 2/16 core cells. По всей карте прошли 9/72 cells, при camera Z=0,56 ни одна. Простая замена body X не создаёт устойчивую область. Поэтому model83 и её representation не донастраиваются post hoc: серия84R заранее фиксирует новую representation, обучение и независимый final gate.

Серия85 shared observation/execution остаётся заблокированной. Даже успех 84R сначала требует отдельной frozen replication новой модели.

## Frozen source и отсутствие model selection

Пользователь выбирает завершённую папку серии83. До запуска проверяются:

- SQLite checkpoint и completed stage;
- protocol, pinned scripts и complete manifest;
- SHA `model_new.npz`;
- соответствие полного или fixture режима.

Model83 копируется в новую immutable checkpoint как comparator. Она не обновляется и не задаёт teacher labels. Candidate architecture, ridge, seeds, views, holdouts и gates фиксируются до обучения. После результата нельзя выбирать другую ridge или crop в рамках этой серии.

## Representation

Обе синтетические камеры остаются 96×64, FOV 35°. Из gradient-energy каждого кадра строятся ровно 192 признака:

- whole-frame context: 4×6 bins на каждый глаз, 48 признаков;
- central crop rows 8:56, columns 12:84: 6×12 bins на каждый глаз, 144 признака.

Три последовательных кадра дают 576 признаков, как в checkpoint, но выделяют больше spatial capacity центральной области лап. Decoder остаётся линейным ridge и не получает geometry metadata.

Ridge заранее фиксирована:

- proximal/middle: 1,0;
- left/right distal: 0,35.

Это новая модель, а не сопоставимый single-factor ablation: одновременно меняются spatial representation, distal regularization и training geometry. Claims относятся ко всему package.

## Обучение

Ровно 8 часов active training, два worker process, transactional SQLite checkpoint, pause/resume и resource guards.

- motion seed `8411`;
- families piecewise5, piecewise9, harmonic, chirp;
- teacher clip ±55°;
- 25 FPS, 51 RGB frame и 49 target frame на episode;
- exact full-motion holdout collisions отклоняются.

Training views:

- 50% balanced 16 core corners body X=3,82/4,18;
- 25% balanced 72-cell map по девяти X от 3,70 до 4,30;
- 25% continuous interior полного диапазона;
- оба camera Z, side и body Y присутствуют в exact balanced частях.

## Независимая final evaluation

До обучения создаются motions 301–310 с seed `8412`:

- пять piecewise5;
- пять piecewise9;
- 16 core geometry corners;
- 160 final cases.

Для каждого case сохраняются candidate, frozen source83, zero, shuffled, static и closed; RGB/feature diagnostics; 72-coefficient state до и после задержки 0,5 с; framewise teacher/candidate/source83 predictions.

## Blocking primary

### Six-axis absolute gate

Для каждой оси candidate должна:

- иметь pooled RMSE ниже zero;
- выигрывать у zero минимум 112/160 cases.

### Distal comparator gate

Каждая distal axis должна дополнительно:

- иметь pooled RMSE ниже frozen source83;
- выигрывать у source83 минимум 96/160 cases.

Proximal/middle обязаны оставаться ниже zero и быть не более чем на 5% хуже source83 pooled.

### Combined controls

Candidate combined должна быть ниже:

- source83;
- zero;
- shuffled;
- static;
- closed.

### Geometry safeguards

Каждая из шести осей отдельно повторяет absolute gate:

- body X=3,82: минимум 56/80 wins;
- body X=4,18: минимум 56/80;
- camera Z=0,36: минимум 56/80;
- camera Z=0,56: минимум 56/80.

### Uniform corner gate

В каждой из 16 cells каждая ось должна иметь pooled candidate ниже zero и минимум 7/10 wins. Требуется минимум 12/16 полностью прошедших cells.

Pooled улучшение не может компенсировать axis, camera-Z или corner failure. Никакая diagnostic subset не спасает primary.

## Решение после серии

- `primary=false`: series85 остаётся заблокированной; thresholds, crop, ridge и motions не меняются post hoc.
- `primary=true`: новая модель всё ещё не переходит прямо к series85; сначала выполняется preregistered frozen replication на ещё одном наборе motions.

## Ограничения

Это supervised synthetic fixed-FOV reconstruction package. Оно не проверяет natural vision, новое действие, actuator dynamics, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
