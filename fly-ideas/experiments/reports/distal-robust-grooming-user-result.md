# Серия 84R: пользовательский результат distal-robust model

## Статус и источник

Пользователь прислал завершённый `summary-9.json`. SHA-256:

`f8fb2cd8a8caddaafc986a739ed724ed723f7a5f81dc370dc50114189fb0be22`

Schema `eight-hour-distal-robust-grooming-result-v1`, status `completed`, mode `long`. Summary содержит 160 уникальных final cases: motions 301–310 × 16 corners.

Frozen source83 model SHA совпадает с опубликованной серией83:

`79ad0b29f904067d3b8ece3e81a395d66606ab7202015d5c47b254bfa484a9fd`.

Candidate model SHA по summary:

`1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c`.

Полная папка результата, SQLite, model NPZ, protocol и complete manifest не передавались. Поэтому независимо проверены JSON records и агрегаты, но не candidate NPZ, runner SHA или файловый manifest на компьютере пользователя.

## Время и объём обучения

Summary сообщает:

- active training `34 320,625` с, то есть 9 ч 32 мин 0,625 с;
- preregistered budget `28 800` с;
- превышение `5 520,625` с, или 19,17%;
- candidates/accepted `1 146/1 146`;
- training frames `56 154`, ровно 1 146 × 49.

Runner останавливается после завершённой atomic batch, но обычная партия не объясняет превышение на 92 минуты. Возможная приостановка компьютера внутри партии по одному summary не доказана. Поэтому результат нельзя описывать как ровно восьмичасовой по записанному active elapsed. Это protocol deviation следует сохранять независимо от primary no-go.

## Preregistered decision

`primary.passed = false`. Серия85 остаётся заблокированной.

Почти все blocking components прошли:

- все шесть global axis gates;
- обе distal-vs-source83 gates;
- combined candidate ниже source83, zero и controls;
- обе camera-Z safeguards;
- body X=4,18 safeguard;
- corner gate 13/16 при требовании 12/16.

Единственный blocking failure:

- body X=3,82, right distal wins `55/80` при требовании минимум `56/80`.

Pooled right-distal candidate в этой группе всё же ниже zero и source83. Но count gate был зарегистрирован заранее, поэтому результат нельзя округлить до успеха или компенсировать 13/16 corners.

## Global axes

| Ось | Candidate | Source83 | Zero | Wins vs zero | Wins vs source83 | Gate |
|---|---:|---:|---:|---:|---:|---|
| left proximal | 0,387897 | 0,392606 | 0,485879 | 145/160 | 93/160 | pass |
| left middle | 0,172743 | 0,190662 | 0,500544 | 160/160 | 136/160 | pass |
| left distal | 0,403039 | 0,409620 | 0,430375 | 127/160 | 98/160 | pass |
| right proximal | 0,361423 | 0,368278 | 0,462297 | 146/160 | 97/160 | pass |
| right middle | 0,173742 | 0,194834 | 0,500110 | 160/160 | 135/160 | pass |
| right distal | 0,390766 | 0,399949 | 0,424121 | 125/160 | 111/160 | pass |

Candidate улучшает source83 pooled по всем шести осям:

- left/right distal: 1,61% и 2,30%;
- left/right middle: 9,40% и 10,83%;
- left/right proximal: 1,20% и 1,86%.

Против zero distal improvement составляет 6,35% left и 7,86% right. Это лучше серии83/84 примерно с 4–5% distal gain, но эффект всё ещё заметно слабее middle axes.

## Combined и controls

Combined candidate/source83/zero:

`0,330720 / 0,339565 / 0,468251`.

Candidate ниже source83 на 2,60% и ниже zero на 29,37%. Controls:

- shuffled `0,448338`;
- static `0,513798`;
- closed `0,504521`.

По отдельным cases candidate combined выигрывает:

- zero: 160/160;
- source83: 119/160;
- shuffled: 160/160;
- static: 160/160;
- closed: 155/160.

Pooled combined gates полностью пройдены.

## Geometry safeguards

### Camera Z

Обе safeguards прошли по всем шести осям:

- Z=0,36: distal wins left/right `64/80` и `60/80`;
- Z=0,56: `63/80` и `65/80`.

Таким образом, сильный post hoc camera-Z pattern серии84 (`0/36` cells при Z=0,56) не повторился в новой модели на global grouped gate.

### Body X=4,18

Полностью пройден:

- left distal `69/80`, candidate/zero `0,395283/0,430375`;
- right distal `70/80`, `0,379861/0,424121`.

### Body X=3,82

Пять осей прошли. Right distal:

- candidate/source83/zero `0,401374/0,409604/0,424121`;
- 5,36% ниже zero;
- 2,01% ниже source83;
- wins vs zero `55/80`, требуется 56.

Это count-only miss на один case при положительном pooled эффекте. Он всё равно является blocking failure.

## Corner gate

Прошли 13/16, что выше preregistered требования 12/16. Не прошли только corners 1, 2 и 6, все при body X=3,82 и camera side=0,14:

| Corner | Z | Body Y | Failed axes |
|---:|---:|---:|---|
| 1 | 0,36 | −0,32 | right distal 6/10 |
| 2 | 0,36 | +0,32 | left distal 5/10; right distal 5/10 |
| 6 | 0,56 | +0,32 | left distal 5/10; right distal 5/10 |

Во всех failed corner-axis combinations pooled candidate ниже zero. Причина снова motion consistency, а не отрицательный pooled effect.

По сравнению с frozen model83 карта существенно улучшилась: series84 имела только 2/16 core cells на новых motions, тогда как новая model84R имеет 13/16. Это реальный package-level gain, но не отмена lower-X safeguard.

## Motion consistency

Наиболее слабые новые motions по distal wins среди 16 corners:

- motion304: left distal 6/16, right distal 10/16;
- motion307: 11/16 и 9/16;
- motion310: 12/16 и 9/16;
- motion302: 13/16 и 11/16.

Для lower-X right distal по восьми corners:

- motion304: 2/8;
- motion302: 3/8;
- motion307: 4/8;
- motions303 и310: 5/8;
- motions301,308,309: 8/8.

Нельзя исключать motion304 или другие слабые motions post hoc.

## State, vision и overlap audit

Во всех 160/160 cases:

- состояние содержит 72 coefficients;
- SHA до и после задержки 0,5 с совпадает;
- RGB не пустой;
- минимум changed RGB values равен 39 076;
- максимальная candidate clipped fraction равна 0,05442.

Overlap audit охватывает 128 из 1 146 accepted candidates и не является exhaustive. По десяти уникальным motions:

- under 0,001°: 0;
- under 1°: 0;
- under 5° frame queries: 90 из 490.

Это снижает риск exact trajectory replay, но не исключает близкие эпизоды во всём training set.

## Решение

1. Серия84R остаётся `primary=false`; gate 55/80 нельзя округлять до 56/80.
2. Серия85 shared observation/execution остаётся заблокированной.
3. Не повторять тот же eight-hour run, не менять ridge/crop post hoc и не исключать motions/corners.
4. Package дал существенное улучшение: все global axes, distal comparator, controls, обе camera-Z groups и 13/16 corners прошли.
5. Следующий этап не должен быть ещё одним body-X sweep. Нужен заранее зарегистрированный способ повысить lower-X right-distal consistency, сохранив frozen architecture result как comparator и используя новые holdouts.
6. Отдельно следует исправить/прояснить time accounting до следующего долгого обучения: reported active elapsed превысил budget на 92 минуты.

## Ограничения claims

Это synthetic supervised reconstruction package. Нет нового действия, actuators, сил, мышц, closed-loop correction, биологического мозга или доказательства mirror neurons.
