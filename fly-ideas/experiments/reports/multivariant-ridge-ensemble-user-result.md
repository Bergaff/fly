# Серия84Z: пользовательский результат preregistered multi-variant ridge/ensemble

## Статус и источник

Пользователь прислал `summary-17.json`, SHA-256:

`19f9d1c37edc15570a58eefc0239bf54b817bd6bada9f72dfbf8975aac714671`.

Schema `multivariant-ridge-ensemble-result-v1`, status `completed`, fixed-count completion по committed candidate count. Завершены16 384/16 384 candidates и802 816 training frames. Wall diagnostic training `6028,844` с, то есть1ч40м28,844с; evaluation time в этом поле не учитывается.

Ожидаемые frozen SHA:

- model84V `44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af`;
- model84S `a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f`;
- model84R `1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c`.

Selected variant: `ridge_0175`. Reported selected model SHA:

`cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`.

Полная production-папка, `complete.json` и model bytes не передавались, поэтому независимо проверен summary, но не complete manifest и не фактический SHA model file пользователя.

## Preregistered decision

`primary.passed = true`.

Это строгий model-development go84Z на untouched final motions431–440. Все global axes, combined, lower-X comparator, обе body-X groups, обе camera-Z groups, controls и16/16 corners прошли.

Это ещё не replication go. Selected model84Z теперь нельзя переобучать, менять или повторно выбирать. Series85 остаётся заблокированной до отдельной frozen replication на следующих undisclosed motions.

## Development selection без final leakage

Шесть вариантов оценивались только на seed8434 motions421–430. Ни один не получил полного development strict pass. Это не препятствует заранее определённой selection procedure: она должна была выбрать один вариант deterministic key, после чего scientific primary вычислялась только на независимом final set.

| Variant | Strict | Core gates | Normalized RD wins | Normalized error | Global RD wins vs84V | Lower-X wins vs84V |
|---|---:|---:|---:|---:|---:|---:|
| ridge_0175 |0|5|1,48125|2,952790|121/160|58/80|
| ridge_0350 |0|1|0,94375|3,004241|69/160|41/80|
| ridge_0700 |0|0|0,58125|3,058364|47/160|23/80|
| ridge_1400 |0|0|0,57500|3,106884|44/160|24/80|
| ensemble_v75_new25 |0|1|0,96250|3,000759|70/160|42/80|
| ensemble_v50_new50 |0|1|0,96250|3,001720|70/160|42/80|

`ridge_0175` единственный выполнил все пять core conditions: global RD pooled ниже84V, global wins>=96, lower-X pooled ниже84V, lower-X wins>=48 и combined ниже84V. Его development strict failure был связан с absolute lower-X wins vs zero55/80 вместо60; body-X lower поэтому не прошёл. Selection key `[0,5,1.48125,-2.952790...,0]` строго превосходит остальные keys.

Final motions431–440 не участвовали в этой таблице и стали доступны selected variant только после выбора.

## Final global right distal

- candidate84Z `0,441619`;
- frozen84V `0,458562`;
- frozen84S `0,482291`;
- frozen84R `0,484141`;
- zero `0,514024`;
- wins vs zero `139/160`;
- wins vs84V `149/160`, требуется96;
- wins vs84S `143/160`, требуется96;
- wins vs84R `149/160`, требуется96.

Candidate улучшает pooled right distal относительно84V на3,695%. Все три comparator counts проходят с большим запасом.

## Final lower-X right distal

- candidate84Z `0,445987`;
- frozen84V `0,461998`;
- frozen84S `0,477402`;
- frozen84R `0,484126`;
- zero `0,514024`;
- wins vs zero `68/80`, требуется60;
- wins vs84V `77/80`, требуется48;
- wins vs84S `71/80`, требуется48;
- wins vs84R `76/80`, требуется48.

Candidate улучшает pooled lower-X right distal относительно84V на3,466%. Таким образом, именно failure84W `59/80` теперь исправлен на новом untouched final set без потери comparator advantage.

## Final upper-X right distal

- candidate84Z `0,437207`;
- frozen84V `0,455100`;
- frozen84S `0,487130`;
- frozen84R `0,484155`;
- zero `0,514024`;
- wins vs zero `71/80`;
- wins vs84V `72/80`;
- wins vs84S `72/80`;
- wins vs84R `73/80`.

Candidate улучшает pooled upper-X right distal относительно84V на3,932%. В отличие от84X/84Y, снижение right-distal ridge до0,175 улучшило обе X groups, а не перенесло качество между ними.

## Все global axes

| Ось | Candidate |84V |84S |84R | Zero | Wins zero | vs84V | vs84S | vs84R | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| left proximal |0,312279|0,312947|0,332047|0,338201|0,439964|159|88|143|138|pass|
| left middle |0,218719|0,219092|0,234907|0,231372|0,503025|160|77|133|137|pass|
| left distal |0,433666|0,434225|0,455635|0,458400|0,485101|132|87|134|140|pass|
| right proximal |0,317647|0,318577|0,337008|0,342826|0,447077|159|95|139|133|pass|
| right middle |0,217752|0,218603|0,233878|0,230885|0,500144|160|110|142|150|pass|
| right distal |0,441619|0,458562|0,482291|0,484141|0,514024|139|149|143|149|pass|

Candidate pooled ниже frozen84V по всем шести axes. Для пяти non-primary axes preregistered gate требовал не ухудшиться более чем на5%; все они фактически немного улучшились.

## Combined и controls

- candidate84Z `0,335848`;
- frozen84V `0,340109`;
- frozen84S `0,359146`;
- frozen84R `0,361311`;
- zero `0,482384`;
- shuffled `0,451936`;
- static `0,618819`;
- closed `0,500829`.

Candidate улучшает combined pooled RMSE относительно84V на1,253%. Case wins:

- zero160/160;
-84V142/160;
-84S155/160;
-84R157/160;
- shuffled160/160;
- static160/160;
- closed160/160.

## Geometry и corners

- body X=3,82: pass;
- body X=4,18: pass;
- camera Z=0,36: pass;
- camera Z=0,56: pass;
- corners16/16 pass, требовалось12/16;
- minimum corner wins: left proximal9/10, left middle10/10, left distal7/10, right proximal9/10, right middle10/10, right distal8/10.

Ни один corner не провалился. Минимум right distal8/10 выше обязательных7/10.

На lower-X motions438 и437 absolute wins vs zero равны2/8 и4/8, но aggregate68/80 и все corner gates проходят. Эти motion-level различия нельзя использовать для post-hoc исключения или tuning.

## State, RGB и audit

- state неизменен160/160;
- SHA state до/после delay совпадает160/160;
- minimum unique RGB frames51;
- minimum changed RGB values28 728;
- minimum feature max std0,017991;
- maximum clipping fraction0;
- overlap totals: under0,001° =0, under1° =0, under5° =1456.

Audit охватывает128 из16 384 accepted candidates и остаётся non-exhaustive.

## Научная интерпретация

84Z показывает, что предыдущие failures были связаны не только с view allocation. Более слабая right-distal regularization0,175 на новом balanced training seed дала одновременно:

- улучшение lower-X;
- улучшение upper-X;
- улучшение global right distal;
- небольшое улучшение остальных axes и combined;
- strong paired counts против frozen84V/84S/84R.

Cross-seed ensembles не были выбраны: на development они не достигли comparator gates. Следовательно, результат поддерживает изменение right-distal regularization, а не усреднение с84V.

Но один model-development final go не является replication. Motions421–440 теперь раскрыты. Нельзя повторять84Z, менять ridge после просмотра, выбирать другой вариант либо использовать эти motions как новую blocking replication.

## Следующий допустимый шаг

1. Сохранить полную папку84Z без изменений.
2. Считать selected model SHA `cb761051...` frozen candidate84Z, пока полный local manifest остаётся доступен.
3. Подготовить отдельную read-only frozen replication на новых motions, например441–450 с новым seed.
4. Replication не должна переобучать модель, повторять development selection или сравнивать шесть variants заново.
5. Series85 остаётся заблокированной до replication go.

## Ограничения claims

Это synthetic supervised reconstruction и linear ridge model в прежнем generator family. Результат не показывает natural vision, самостоятельно созданное действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
