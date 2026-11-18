# Серия 84V: пользовательский результат paired-view distal consistency

## Статус и источник

Пользователь прислал завершённый `summary-13.json`. SHA-256:

`2097ca310cdaa9baa4f085883857ea58d826d8b0fb8460c8fc236f7d69db1ce3`.

Schema `paired-view-distal-consistency-result-v1`, status `completed`, mode `fixed_count`, completion basis `committed_candidate_count`. Завершены16 384/16 384 candidates, все приняты,802 816 training frames. Wall diagnostic24 323,328с, то есть6ч45м23,328с.

Frozen comparators совпадают:

- model84S `a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f`;
- model84R `1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c`.

Reported candidate84V SHA:

`44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af`.

Summary содержит все160 final cases: motions361–370 ×16 corners, по49 frames. Полная папка, NPZ, SQLite, protocol и complete manifest не передавались. Поэтому reported candidate SHA и paired training layout нельзя независимо пересчитать по файлам пользователя. Runner84V SHA отсутствует в summary; опубликованный runner имеет SHA `05a0cdd4696af5b8901a1d34a205db8a286264f518cb54e93d1e0b9f9e9e4a52`.

## Preregistered decision

`primary.passed = true`.

Все blocking components прошли одновременно против frozen84S и frozen84R. Это полный model-development go84V. Candidate84V теперь должна быть заморожена; прямой переход к series85 всё равно запрещён до отдельной frozen replication на новых motions.

## Global axes

| Ось | Candidate84V | Source84S | Source84R | Zero | Wins vs zero | vs84S | vs84R |
|---|---:|---:|---:|---:|---:|---:|---:|
| left proximal | 0,354828 | 0,376570 | 0,381421 | 0,486264 | 149 | 142 | 134 |
| left middle | 0,161757 | 0,176854 | 0,174906 | 0,435674 | 160 | 137 | 137 |
| left distal | 0,425264 | 0,450377 | 0,452096 | 0,484446 | 149 | 144 | 140 |
| right proximal | 0,373577 | 0,394881 | 0,400354 | 0,504961 | 149 | 143 | 130 |
| right middle | 0,154303 | 0,168248 | 0,167019 | 0,437054 | 160 | 133 | 135 |
| right distal | 0,431598 | 0,454942 | 0,456612 | 0,485714 | 144 | 135 | 140 |

Каждая ось candidate лучше обеих frozen models pooled, а не только находится внутри5% non-degradation. Улучшение right distal составляет5,13% против84S и5,48% против84R. Right-distal case counts135/160 и140/160 значительно выше blocking96/160.

## Combined и controls

Combined:

- candidate84V `0,337284`;
- model84S `0,357569`;
- model84R `0,359893`;
- zero `0,473088`;
- shuffled `0,459165`;
- static `0,547284`;
- closed `0,521045`.

Candidate улучшает84S на5,67%,84R на6,28% и zero на28,71%.

Combined case wins candidate:

- zero160/160;
- model84S149/160;
- model84R150/160;
- shuffled160/160;
- static160/160;
- closed150/160.

## Lower-X target

Body X=3,82, right distal:

- candidate84V `0,437139`;
- model84S `0,452872`;
- model84R `0,457997`;
- zero `0,485714`;
- wins vs zero69/80, требовалось60;
- wins vs84S61/80, требовалось48;
- wins vs84R65/80, требовалось48.

Candidate лучше84S на3,47%,84R на4,55% и zero на10,00%. В отличие от84U, pooled и оба case-count comparator gates проходят с заметным запасом.

## Geometry и corners

Обе body-X groups прошли все оси:

- lower-X right distal69/80 vs zero;
- upper-X right distal75/80.

Обе camera-Z groups прошли. Прошли16/16 corners при требовании12/16.

Минимальные wins против zero в любой corner cell:

- left proximal9/10;
- left middle10/10;
- left distal9/10;
- right proximal9/10;
- right middle10/10;
- right distal8/10.

Ни одна cell не находится на минимальном пороге7/10.

## Motion dependence

Right-distal comparator counts остаются неодинаковыми по motions, но pooled gates имеют большой запас. Наиболее слабое absolute движение361:5/16 wins vs zero, хотя11/16 vs84S и14/16 vs84R. На lower-X motion361 имеет1/8 vs zero,6/8 vs84S и6/8 vs84R. Motion370 имеет4/8 lower-X wins vs zero, но7/8 и8/8 против comparators.

Эти локальные слабости не скрываются: все motions остаются в заранее заданном primary, а corner/global/group gates проходят. Нельзя утверждать одинаковое качество на каждом движении.

## State, RGB и audit

- state неизменен160/160;
- state SHA до/после delay совпадает160/160;
- пустых RGB cases0;
- minimum unique RGB frames51;
- minimum changed RGB values28 141;
- minimum feature max std0,016796;
- maximum clipping fraction0,013605.

Audit охватывает128/16 384 accepted candidates и не является exhaustive. Для десяти уникальных motions:

- under0,001°:0;
- under1°:0;
- under5°:108 из490 frame queries.

Это исключает exact/near-1° replay в ограниченной audit sample, но не доказывает отсутствие близких fragments во всём training set.

## Интерпретация

Paired-view intervention дала сильное и согласованное улучшение на новой батарее361–370: candidate лучше обеих frozen models по всем шести осям, combined, right-distal global и lower-X. Это поддерживает гипотезу, что repeated counterfactual views одного движения уменьшают motion/view confounding.

Однако84V одновременно является новой обученной моделью и проверена только на одной final battery. Поэтому:

1. Series84V фиксируется как полный preregistered model-development go.
2. Candidate SHA `44b98c…` теперь frozen; retraining/tuning запрещены.
3. Motions361–370 раскрыты и не могут использоваться как blocking replication holdouts.
4. Следующий этап только read-only frozen replication84V на новых motions/seeds с теми же comparators и blocking gates.
5. Series85 остаётся заблокированной до replication go.

## Ограничения claims

Это supervised synthetic reconstruction в прежнем generator family и geometry grid. Результат не доказывает natural vision, новое действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
