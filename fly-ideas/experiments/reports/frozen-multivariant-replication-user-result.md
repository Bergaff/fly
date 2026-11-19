# Серия84AA: пользовательский результат frozen replication model84Z

## Статус и независимая проверка

Пользователь прислал `summary-18.json`, SHA-256:

`93daa4e4dc360b2b741ee7ff8cac6934d58d293c3aedc82bdc914184e71c468b`.

Schema `frozen-multivariant-replication-result-v1`, status `completed`. В summary находятся ровно160 уникальных cases: motions441–450 × corners1–16, по49 оцениваемых frames. Независимый verifier `tests/frozen-multivariant-replication-user-result-fixture.py` заново вычислил pooled metrics, case wins, body-X/camera-Z safeguards, lower-X comparator, corner gates и итоговый strict primary непосредственно из160 test records. Recomputed structure и все числа совпали с `primary` с tolerance1e-12.

`primary.passed = true`. Это independently verified strict frozen-replication go84AA. Научный блок series85, установленный после84Z, снят.

## Frozen identities и отсутствие повторного выбора

Подтверждены:

- runner84AA SHA `846bf4b56e7d6d221a8a5a35eb02675f16bde570ea7e7b7a8e2d822f4c33e879`;
- runner84Z SHA `fa4040d7271f2c98021042054ebe60767ad092de81d610a60815738be9f57a6b`;
- selected model SHA `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`;
- selected variant `ridge_0175`;
- right-distal ridge0,175;
- new-model weight1,0;
- frozen84V SHA `44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af`;
- frozen84S SHA `a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f`;
- frozen84R SHA `1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c`;
- seed8436, motions441–450,16 corners;
- `training_allowed=false`;
- `development_selection_allowed=false`.

Все10 motion SHA совпадают с preregistered generator output. В replication не было fit, обучения, выбора другого variant или изменения thresholds.

Полная local production-папка и `complete.json` не передавались через чат. Их exact manifest и source84Z immutability проверил local runner до выдачи summary; независимо по переданному файлу проверены summary SHA, identities,160 records и все decision gates, но не байты локального `complete.json`.

## Global right distal

- candidate84Z `0,391354`;
- frozen84V `0,406939`;
- frozen84S `0,430951`;
- frozen84R `0,436105`;
- zero `0,461261`;
- wins vs zero `141/160`;
- wins vs84V `142/160`, требуется96;
- wins vs84S `137/160`, требуется96;
- wins vs84R `142/160`, требуется96.

Candidate улучшает pooled right distal относительно84V на3,830%.

## Lower-X right distal

- candidate `0,406078`;
-84V `0,418982`;
-84S `0,434909`;
-84R `0,444282`;
- zero `0,461261`;
- wins vs zero `68/80`, требуется60;
- wins vs84V `73/80`, требуется48;
- wins vs84S `64/80`, требуется48;
- wins vs84R `67/80`, требуется48.

Candidate улучшает pooled lower-X right distal относительно84V на3,080%. Motion441 имеет только1/8 lower-X wins против zero, но preregistered решение является aggregate:68/80 и все corner gates проходят. Motion нельзя исключать post-hoc.

## Upper-X right distal

- candidate `0,376055`;
-84V `0,394528`;
-84S `0,426956`;
-84R `0,427772`;
- zero `0,461261`;
- wins vs zero `73/80`;
- wins vs84V `69/80`;
- wins vs84S `73/80`;
- wins vs84R `75/80`.

Candidate улучшает pooled upper-X right distal относительно84V на4,682%.

## Все global axes

| Ось | Candidate |84V |84S |84R | Zero | Wins zero | vs84V | vs84S | vs84R | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| left proximal |0,328347|0,327967|0,348996|0,353315|0,468189|160|66|136|135|pass|
| left middle |0,131113|0,131063|0,142711|0,139946|0,438548|160|81|132|138|pass|
| left distal |0,404669|0,405014|0,430486|0,436795|0,459104|142|74|134|140|pass|
| right proximal |0,351605|0,351454|0,370434|0,375260|0,487139|159|73|135|130|pass|
| right middle |0,150360|0,150830|0,164539|0,163173|0,475572|160|110|138|150|pass|
| right distal |0,391354|0,406939|0,430951|0,436105|0,461261|141|142|137|142|pass|

Для non-primary axes правило допускает не более5% ухудшения относительно каждого frozen comparator. Все пять axes проходят; небольшое ухудшение left proximal, left middle и right proximal относительно84V остаётся намного меньше5%.

## Combined и controls

- candidate `0,313090`;
-84V `0,316398`;
-84S `0,336030`;
-84R `0,339814`;
- zero `0,465213`;
- shuffled `0,453387`;
- static `0,587349`;
- closed `0,522098`.

Candidate улучшает combined pooled RMSE относительно84V на1,045%. Case wins:84V136/160,84S151/160,84R157/160, zero160/160, shuffled160/160, static160/160, closed159/160. Blocking gate основан на pooled combined, и candidate ниже всех семи comparators/controls.

## Geometry, state и audit

- body X=3,82: pass;
- body X=4,18: pass;
- camera Z=0,36: pass;
- camera Z=0,56: pass;
- corners16/16 pass, требовалось12/16;
- minimum corner wins:10,10,7,9,10,7 по шести axes;
- state unchanged160/160;
- state SHA до/после delay совпадает160/160;
- minimum unique RGB frames51;
- minimum changed RGB values29 953;
- minimum feature max std0,017088;
- maximum clipping fraction0,034014;
- overlap totals: under0,001° =0, under1° =0, under5° =94.

Audit охватывает128/16 384 accepted training candidates и не является exhaustive.

## Решение и границы вывода

84AA независимо воспроизводит strict advantage frozen `ridge_0175` на новом seed и новых motions441–450 без обучения или model selection. Это сильнее одиночного untouched-final go84Z и удовлетворяет заранее установленному условию разблокировки series85.

Результат всё ещё относится к synthetic supervised reconstruction, той же generator family/grid и linear ridge model. Он не доказывает natural vision, самостоятельно созданное действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.

Следующий этап должен быть заранее зарегистрирован как series85 и не может использовать раскрытые motions421–450 для blocking selection/evaluation. Нельзя post-hoc менять model84Z, ridge, thresholds или исключать motion441.
