# Серия84Y: пользовательский результат augmented lower paired-view model

## Статус и источник

Пользователь прислал `summary-16.json`, SHA-256:

`bb5ed966f0eae0870246287aeb7962e498d237306d2a34ff06527e7292b2d671`.

Schema `lower-augmented-paired-view-result-v1`, status `completed`, fixed-count completion по committed candidate count. Завершены20 480/20 480 candidates и1 003 520 training frames. Wall diagnostic `6961,813` с, то есть1ч56м01,813с. Summary не содержит выбранный worker mode, поэтому по одному wall time нельзя доказать, был ли выбран «Максимум».

Ожидаемые model SHA подтверждены:

- frozen84V `44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af`;
- frozen84S `a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f`;
- frozen84R `1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c`;
- candidate84Y `92a26360e994a70efced86ac1b5f9157ddafb63d78488ba387233304c59f6bf0`.

Присутствуют все160 blocking cases: motions411–420 ×16 corners, по49 frames. Полная production-папка и manifest не передавались, поэтому независимо проверен summary, но не complete manifest пользователя.

## Preregistered decision

`primary.passed = false`.

Это строгий model-development no-go. Series85 остаётся заблокированной. Нельзя повторять84Y с другим seed, выбирать удачные motions или ослаблять gates.

Добавление пятого lower-X view не превзошло balanced frozen84V ни global, ни в заранее выбранной lower-X target group.

## Blocking failures

### Global right distal

- candidate84Y `0,409708`;
- frozen84V `0,406586`;
- frozen84S `0,431630`;
- frozen84R `0,429717`;
- zero `0,464819`;
- wins vs zero `146/160`;
- wins vs84V `53/160`, требуется96;
- wins vs84S `149/160`, требуется96;
- wins vs84R `136/160`, требуется96.

Candidate хуже84V pooled на0,768% и недобирает43 paired wins до preregistered порога против84V. Сильное преимущество над84S/84R и zero не заменяет обязательное превосходство frozen84V.

### Lower-X right distal

- candidate84Y `0,404821`;
- frozen84V `0,404660`;
- frozen84S `0,423748`;
- frozen84R `0,428804`;
- zero `0,464819`;
- wins vs zero `73/80`, требуется60;
- wins vs84V `43/80`, требуется48;
- wins vs84S `74/80`, требуется48;
- wins vs84R `68/80`, требуется48.

Absolute lower-X weakness против zero исправлена, но candidate оказался на0,040% хуже84V pooled и недобрал5 paired wins. Поэтому специальный lower-X comparator gate не прошёл.

### Combined

- candidate84Y `0,302530`;
- frozen84V `0,300768`;
- frozen84S `0,322129`;
- frozen84R `0,322866`;
- zero `0,454816`;
- shuffled `0,433015`;
- static `0,583855`;
- closed `0,475953`.

Candidate хуже84V pooled на0,586%, поэтому strict combined-below-all-comparators gate также не проходит. Combined case wins:67/160 против84V,155/160 против84S,148/160 против84R и160/160 против zero/shuffled/static/closed.

## Upper-X и причина trade-off

Upper-X right distal:

- candidate84Y `0,414537`;
- frozen84V `0,408502`;
- frozen84S `0,439371`;
- frozen84R `0,430629`;
- zero `0,464819`;
- wins `73/80` vs zero;
- wins `10/80` vs84V;
- wins `75/80` vs84S;
- wins `68/80` vs84R.

Все четыре exact84V views действительно оставались в training set, однако сохранение примеров не означает сохранение fitted coefficients. Пятый lower-X view изменил вес geometry distribution в единой ridge objective. Общий optimum576-D regression сдвинулся, и upper-X стал хуже84V на1,477%. При этом lower-X не улучшился относительно84V. Значит, простое увеличение числа lower-X samples не решает конфликт одной общей модели.

## Все global axes

| Ось | Candidate |84V |84S |84R | Zero | Wins zero | vs84V | vs84S | vs84R | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| left proximal |0,309152|0,307925|0,334501|0,339610|0,478854|158|76|145|138|pass|
| left middle |0,140445|0,139424|0,153291|0,149569|0,428365|160|78|133|134|pass|
| left distal |0,384271|0,381872|0,403982|0,403273|0,434502|144|59|143|130|pass|
| right proximal |0,314364|0,313427|0,338343|0,343477|0,484359|158|76|144|133|pass|
| right middle |0,139628|0,138336|0,152413|0,149956|0,434620|160|71|131|131|pass|
| right distal |0,409708|0,406586|0,431630|0,429717|0,464819|146|53|149|136|**fail**|

Остальные оси проходят разрешённый preregistered предел не более5% хуже comparators, но каждая также немного хуже84V pooled. Это согласуется с общим сдвигом ridge optimum, а не с изолированным улучшением lower-X.

## Geometry, corners и controls

- body X=3,82: fail только из-за специального lower-X comparator gate против84V;
- body X=4,18: absolute zero safeguard pass;
- camera Z=0,36: pass;
- camera Z=0,56: pass;
- corners16/16 pass при требовании12/16;
- минимальные corner wins: left proximal9/10, middle10/10, distal8/10; right proximal9/10, middle10/10, distal9/10.

Absolute reconstruction относительно zero остаётся сильной и равномерной. Провал относится к обязательному улучшению над лучшей frozen model84V.

## Motion dependence

Lower-X right distal против84V особенно слаб на motions417 (`0/8`),414 (`1/8`) и419 (`2/8`). Motion415, наоборот, даёт только1/8 против zero, но7/8 против84V. Absolute baseline и comparator advantage снова измеряют разные свойства.

Motions411–420 теперь раскрыты. Их нельзя добавлять в обучение84Y, исключать post hoc или повторно использовать как blocking holdouts.

## State, RGB и audit

- state неизменен160/160;
- SHA state до/после delay совпадает160/160;
- minimum unique RGB frames51;
- minimum changed RGB values31 882;
- minimum feature max std0,017599;
- maximum clipping fraction0,034014;
- overlap totals: under0,001° =0, under1° =0, under5° =1680.

Audit охватывает128 из20 480 accepted candidates и остаётся non-exhaustive.

## Интерпретация и следующий допустимый класс модели

Series84X показала, что замена upper-X view на lower-X переносит качество между groups. Series84Y показала, что добавление lower-X view при сохранении всех balanced examples тоже сдвигает единую ridge objective и не превосходит84V. Поэтому дальнейшее увеличение, дублирование или перевзвешивание lower-X samples в той же общей576-D ridge модели научно плохо обосновано.

Следующий model-development шаг, если его готовить, должен менять способ моделирования конфликта geometry, а не только render count. Наиболее прямой заранее определяемый вариант: shared representation с раздельными geometry-conditioned heads либо balanced objective, где lower-X и upper-X вносят равный нормированный вклад независимо от числа renders. Это будет новая модель и потребует нового seed и новых undisclosed blocking motions.

До этого:

1. Candidate84Y не становится frozen production model.
2. Model84V остаётся лучшей frozen model, но replication84W остаётся no-go.
3.84X и84Y не повторять.
4. Series85 остаётся заблокированной.

## Ограничения claims

Это synthetic supervised reconstruction в прежнем generator family и geometry grid. Результат не показывает natural vision, самостоятельно созданное действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
