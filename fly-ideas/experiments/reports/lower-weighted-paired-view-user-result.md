# Серия84X: пользовательский результат lower-weighted paired-view model

## Статус и источник

Пользователь прислал `summary-15.json`, SHA-256:

`540aff2d1237f77824811ba784f9a59011b446d347816f736188350cde73a9b7`.

Schema `lower-weighted-paired-view-result-v1`, status `completed`, completion `fixed_count` по committed candidate count. Завершены16 384/16 384 candidates и802 816 training frames. Wall diagnostic `8820,016` с, то есть2ч27м00с. Это подтверждает, что6 workers ускорили production run; wall time не использовался как completion gate.

Модели имеют ожидаемые SHA:

- frozen84V `44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af`;
- frozen84S `a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f`;
- frozen84R `1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c`;
- candidate84X `fd12401a6cccdb17815c3f323553b38ffd22a17d541608a037dfa1813052acb5`.

Присутствуют все160 blocking cases: motions401–410 ×16 corners, по49 frames. Полная production-папка и manifest не передавались, поэтому независимо проверен summary, но не complete manifest пользователя.

## Preregistered decision

`primary.passed = false`.

Это строгий model-development no-go. Series85 остаётся заблокированной. Нельзя повторять84X с другим seed или ослаблять gates.

Lower-X intervention сама по себе сработала: lower-X right distal полностью проходит. Но перераспределение views ухудшило upper-X относительно frozen84V, поэтому global right distal и combined comparator gates не прошли.

## Blocking failures

### Global right distal

- candidate84X `0,431383`;
- frozen84V `0,430326`;
- frozen84S `0,456005`;
- frozen84R `0,456835`;
- zero `0,490911`;
- wins vs zero `143/160`;
- wins vs84V `81/160`, требуется96;
- wins vs84S `131/160`, требуется96;
- wins vs84R `124/160`, требуется96.

Candidate84X хуже84V pooled на0,246% и недобирает15 paired wins против preregistered порога. Он уверенно лучше84S/84R и zero, но gate требовал преимущество отдельно над каждым frozen comparator.

### Combined

- candidate84X `0,331909`;
- frozen84V `0,330785`;
- frozen84S `0,350421`;
- frozen84R `0,351407`;
- zero `0,480981`;
- shuffled `0,464995`;
- static `0,612999`;
- closed `0,520586`.

Candidate хуже84V pooled на0,340%, поэтому strict combined-below-all-comparators gate также не проходит. Case wins:71/160 против84V,142/160 против84S,128/160 против84R и160/160 против zero/shuffled/static/closed.

## Lower-X target и upper-X trade-off

Lower-X right distal, body X=3,82:

- candidate84X `0,425871`;
- frozen84V `0,432502`;
- frozen84S `0,451218`;
- frozen84R `0,456380`;
- zero `0,490911`;
- wins `73/80` vs zero при требовании60;
- wins `53/80` vs84V, `66/80` vs84S, `68/80` vs84R при требовании48 отдельно.

Это заметное исправление цели84W: absolute lower-X count вырос с59/80 до73/80, а candidate стал лучше всех comparators pooled.

Upper-X right distal, body X=4,18:

- candidate84X `0,436825`;
- frozen84V `0,428139`;
- frozen84S `0,460743`;
- frozen84R `0,457289`;
- zero `0,490911`;
- wins `70/80` vs zero;
- wins `28/80` vs84V;
- wins `65/80` vs84S;
- wins `56/80` vs84R.

Следовательно,3+1 weighting не дало бесплатного улучшения: оно перенесло качество с upper-X на lower-X. Именно28/80 против84V на upper-X тянет global result вниз.

## Все global axes

| Ось | Candidate |84V |84S |84R | Zero | Wins zero | vs84V | vs84S | vs84R | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| left proximal |0,351002|0,349650|0,367258|0,368929|0,452167|154|73|141|124|pass|
| left middle |0,145143|0,142296|0,155584|0,152512|0,490772|160|71|124|103|pass|
| left distal |0,432170|0,431555|0,459101|0,459560|0,496422|144|81|141|126|pass|
| right proximal |0,349959|0,349375|0,367477|0,371565|0,457312|151|80|140|133|pass|
| right middle |0,146209|0,143266|0,154690|0,153621|0,496164|160|77|128|117|pass|
| right distal |0,431383|0,430326|0,456005|0,456835|0,490911|143|81|131|124|**fail**|

Остальные оси проходят разрешённый preregistered предел не более5% хуже каждого comparator. Это не отменяет специально усиленный right-distal gate.

## Geometry, corners и controls

- body X=3,82: pass, включая усиленный lower-X comparator gate;
- body X=4,18: pass по absolute zero safeguard;
- camera Z=0,36: pass;
- camera Z=0,56: pass;
- corners16/16 pass при требовании12/16;
- минимальные corner wins: proximal8/10, middle10/10, distal8/10 слева; proximal8/10, middle10/10, distal7/10 справа.

Таким образом, absolute geometry robustness против zero стала сильнее84W. Провал относится не к zero/corner safeguards, а к сохранению качества frozen84V.

## Motion dependence

На lower-X right distal сильнейшие провалы против84V приходятся на motions401 и405: соответственно0/8 и1/8 wins, хотя оба дают8/8 против zero. Motion407 даёт только2/8 против zero, но7/8 против84V. Это показывает, что absolute baseline и comparator advantage измеряют разные свойства.

Motions401–410 теперь раскрыты. Их нельзя использовать как новые blocking holdouts, исключать post hoc или добавлять в84X.

## State, RGB и audit

- state неизменен160/160;
- SHA state до/после delay совпадает160/160;
- minimum unique RGB frames51;
- minimum changed RGB values34 779;
- minimum feature max std0,024757;
- maximum clipping fraction0,027211;
- overlap totals: under0,001° =0, under1° =0, under5° =1264.

Audit охватывает128 из16 384 accepted candidates и остаётся non-exhaustive.

## Интерпретация и следующий шаг

Series84X отвечает на научный вопрос однозначно: дополнительный lower-X view исправляет прежнюю lower-X absolute weakness, но один удалённый upper-X view приводит к сопоставимой потере на upper-X. Простое перераспределение fixed render budget `2+2 → 3+1` не превосходит balanced84V globally.

Поэтому:

1. Candidate84X не становится новой frozen production model.
2. Model84V остаётся лучшим frozen comparator, но её replication84W всё ещё no-go.
3. Series85 остаётся заблокированной.
4. Нельзя повторять84X, выбирать другой seed, менять пороги или объявлять успех по lower-X подгруппе.
5. Следующий model-development шаг должен сохранять четыре balanced84V views и добавлять lower-X информацию другим заранее определённым способом, либо увеличивать общий render budget. Это будет новая модель и потребует новых undisclosed holdouts.

## Ограничения claims

Это synthetic supervised reconstruction в прежнем generator family и geometry grid. Результат не показывает natural vision, самостоятельно созданное действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
