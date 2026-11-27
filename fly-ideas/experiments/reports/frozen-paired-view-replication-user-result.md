# Серия84W: пользовательский результат frozen replication model84V

## Статус и источник

Пользователь прислал `summary-14.json`, SHA-256:

`1fa95757de83b09218987bf7c8ef89e49029a3620c3c39de7f82211d170c910b`.

Schema `frozen-paired-view-replication-result-v1`, status `completed`, mode `full`. Присутствуют все160 cases: motions381–390 ×16 corners, по49 frames.

Protocol подтверждает read-only evaluation:

- `training_allowed=false`;
- runner84V SHA `05a0cdd4696af5b8901a1d34a205db8a286264f518cb54e93d1e0b9f9e9e4a52`;
- frozen model84V SHA `44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af`;
- frozen model84S SHA `a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f`;
- frozen model84R SHA `1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c`;
- seed8428, holdouts381–390,16 corners.

Полная папка результата и manifest не передавались, поэтому проверен summary, но не complete manifest пользователя.

## Preregistered decision

`primary.passed = false`.

Это строгий replication no-go. Series85 остаётся заблокированной.

Единственный grouped blocking failure: lower-X right-distal absolute count против zero равен59/80 при требовании60/80. Остальные lower-X comparator criteria проходят с большим запасом:

- candidate84V `0,329219`;
- model84S `0,341811`;
- model84R `0,349149`;
- zero `0,368746`;
- wins vs zero `59/80`, требуется60, **fail на один case**;
- wins vs84S `60/80`, требуется48;
- wins vs84R `64/80`, требуется48.

Candidate лучше zero pooled на10,72%,84S на3,68% и84R на5,71%. Но заранее установленный absolute count нельзя заменить pooled RMSE или округлить59 до60.

## Global axes

Все шесть global axes прошли:

| Ось | Candidate84V | Model84S | Model84R | Zero | Wins zero | vs84S | vs84R |
|---|---:|---:|---:|---:|---:|---:|---:|
| left proximal | 0,331407 | 0,352529 | 0,358586 | 0,487071 | 160 | 144 | 143 |
| left middle | 0,111050 | 0,123433 | 0,120955 | 0,401774 | 160 | 132 | 136 |
| left distal | 0,340568 | 0,363278 | 0,364599 | 0,384142 | 138 | 138 | 133 |
| right proximal | 0,337997 | 0,357374 | 0,364516 | 0,494661 | 160 | 144 | 137 |
| right middle | 0,125202 | 0,139059 | 0,136528 | 0,407433 | 160 | 133 | 142 |
| right distal | 0,327160 | 0,349434 | 0,351314 | 0,368746 | 124 | 129 | 131 |

Right distal улучшает84S на6,37% и84R на6,88%; comparator counts129/160 и131/160 выше требования96. Таким образом, dual-comparator эффект84V реплицирован global, но absolute lower-X uniformity не достигла полного preregistered порога.

## Combined и controls

Combined:

- candidate84V `0,281395`;
- model84S `0,300178`;
- model84R `0,303062`;
- zero `0,426789`;
- shuffled `0,401040`;
- static `0,559319`;
- closed `0,489058`.

Candidate лучше84S на6,26%,84R на7,15% и zero на34,07%. Combined case wins:

- zero160/160;
-84S146/160;
-84R149/160;
- shuffled160/160;
- static160/160;
- closed160/160.

## Geometry и corners

- body X=4,18: pass;
- body X=3,82: fail только из-за lower-X right-distal59/80 вместо60/80;
- camera Z=0,36: pass;
- camera Z=0,56: pass;
- corners14/16 pass, требовалось12/16, поэтому общий corner gate пройден.

Не прошли corners9 и13: right distal6/10 vs zero при минимуме7/10. Обе имеют lower body X=3,82. Минимальные wins по осям среди corners: left proximal10, left middle10, left distal7, right proximal10, right middle10, right distal6.

## Motion dependence

Lower-X right-distal absolute weakness сосредоточена в отдельных motions:

- motion382:1/8 wins vs zero, но2/8 vs84S и2/8 vs84R;
- motion388:1/8 vs zero,7/8 vs84S и6/8 vs84R;
- motion389:5/8 vs zero;
- остальные в основном6–8/8.

Global candidate при этом выигрывает у zero на motion382 только3/16 и на388 только4/16, но превосходит frozen comparators значительно чаще. Это означает, что84V стабильно улучшает прежние модели, однако на части новых trajectories обе старые модели и84V оказываются близки к абсолютному zero baseline по right distal.

Motions381–390 теперь раскрыты. Нельзя исключать382/388, дообучать на них frozen84V или искать новый seed ради одного дополнительного win.

## State, RGB и audit

- state неизменен160/160;
- SHA state до/после delay совпадает160/160;
- пустых RGB cases0;
- minimum unique RGB frames51;
- minimum changed RGB values25 486;
- minimum feature max std0,016407;
- maximum clipping fraction0,010204.

Audit128/16 384 non-exhaustive. Для490 frame queries:

- under0,001°:0;
- under1°:0;
- under5°:122.

## Интерпретация

Replication подтверждает сильное и широкое улучшение84V над84S/84R: все global axes, combined и оба comparator counts проходят. Но preregistration также требовала абсолютную lower-X uniformity против zero. Недостаёт одного из80 cases, и два lower-X corners имеют6/10 вместо7/10. Поэтому итог остаётся no-go, несмотря на сильные средние эффекты.

Следовательно:

1. Model84V остаётся frozen и не переобучается.
2. Series84V считается сильным model-development result, но полная replication не пройдена.
3. Series85 остаётся заблокированной.
4. Нельзя повторять84W с другим seed для поиска go.
5. Следующий допустимый model-development шаг должен заранее адресовать absolute lower-X right-distal failures, сохраняя уже полученное dual-comparator преимущество, и использовать полностью новые blocking motions.

## Ограничения claims

Это synthetic supervised reconstruction в прежнем generator family и geometry grid. Результат не показывает natural vision, новое действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
