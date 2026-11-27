# Серия 84U: пользовательский результат frozen replication model84S

## Статус и источник

Пользователь выполнил full read-only replication и прислал `summary-12.json`. SHA-256 файла:

`5733dcfd2523285f8218a8cf4331fe0a5719e719c2c2bc3d5d97fde74e29f8fc`.

Schema `frozen-lowerx-distal-replication-result-v1`, status `completed`, protocol mode `full`. Содержатся все160 preregistered cases: motions341–350 ×16 corners, каждый по49 оцениваемых frames.

Закреплены ожидаемые SHA:

- runner84S: `67915637388a508b88c112ce9f39a0396fcc5a2ef9492928f402826809a8dcd2`;
- frozen model84S: `a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f`;
- frozen model84R: `1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c`.

`training_allowed=false`. Model84S не переобучалась и не изменялась. Полная папка результата и `complete.json` не передавались, поэтому независимо проверен присланный summary, но не файловый manifest на компьютере пользователя.

## Preregistered decision

`primary.passed = false`.

Это replication no-go. Series85 остаётся заблокированной.

Провалены два связанных blocking требования right distal против frozen84R:

1. Global right distal:
   - model84S `0,402415`;
   - model84R `0,399432`;
   - zero `0,442769`;
   - wins против zero `138/160`, абсолютный критерий пройден;
   - wins против84R `77/160`, требовалось минимум96;
   - pooled84S хуже84R на0,747%.

2. Lower-X right distal, body X=3,82:
   - model84S `0,392338`;
   - model84R `0,393938`;
   - zero `0,442769`;
   - wins против zero `70/80`, требовалось60;
   - wins против84R `44/80`, требовалось48;
   - pooled84S лучше84R на0,406%, но count не прошёл с дефицитом4 cases.

Body-X group3,82 помечена failed только из-за встроенного lower-X comparator gate. Её обычный absolute right-distal gate против zero сам по себе прошёл:70/80 при базовом пороге56/80.

Нельзя округлять77/160 до96/160, заменять count pooled-средним, исключать motions или ослаблять lower-X threshold после просмотра.

## Global axes

| Ось | Model84S | Model84R | Zero | Wins vs zero | Wins vs84R | Gate |
|---|---:|---:|---:|---:|---:|---|
| left proximal | 0,358082 | 0,363789 | 0,477850 | 151/160 | 82/160 | pass |
| left middle | 0,159579 | 0,156408 | 0,405640 | 160/160 | 82/160 | pass |
| left distal | 0,397091 | 0,394157 | 0,437305 | 143/160 | 75/160 | pass по 5% non-degradation |
| right proximal | 0,366662 | 0,372375 | 0,493053 | 158/160 | 82/160 | pass |
| right middle | 0,166786 | 0,163685 | 0,408149 | 160/160 | 84/160 | pass |
| right distal | 0,402415 | 0,399432 | 0,442769 | 138/160 | 77/160 | **fail** |

Все шесть осей остаются лучше zero pooled и по preregistered absolute case count. Proximal axes лучше84R примерно на1,5%; middle и distal axes немного хуже84R, но для пяти нецелевых осей это находится внутри заранее разрешённого 5% bound. Для целевой right distal правило было строже и не выполнено.

## Combined и controls

Combined:

- model84S `0,325465`;
- model84R `0,325875`;
- zero `0,445318`;
- shuffled `0,426314`;
- static `0,567824`;
- closed `0,505907`.

Model84S лучше84R combined только на0,126%, зато лучше zero примерно на26,9%. Combined gate прошёл.

По отдельным cases model84S combined выигрывает:

- zero160/160;
- model84R78/160;
- shuffled160/160;
- static160/160;
- closed159/160.

Это показывает сильный абсолютный signal против controls, но не устойчивое превосходство новой модели над84R.

## Geometry gates

- body X=4,18: pass;
- body X=3,82: fail только из-за lower-X right-distal comparator44/80 вместо48/80;
- camera Z=0,36: pass;
- camera Z=0,56: pass;
- corners:16/16 pass при требовании12/16.

Минимальные wins против zero в отдельной corner cell:

- left proximal8/10;
- left middle10/10;
- left distal8/10;
- right proximal9/10;
- right middle10/10;
- right distal7/10.

То есть corner absolute gate прошёл полностью, одна right-distal cell находится ровно на минимуме7/10.

## Motion dependence

Right-distal wins против84R по16 corners сильно зависят от движения:

- motion341:13/16;
- 342:4/16;
- 343:4/16;
- 344:1/16;
- 345:10/16;
- 346:12/16;
- 347:1/16;
- 348:3/16;
- 349:16/16;
- 350:13/16.

На lower-X восьми corners соответствующие counts:6,3,4,1,3,8,1,3,8,7. Поэтому pooled lower-X RMSE немного лучше84R, но выигрыш не распределён достаточно широко по motions/corners. Особенно слабы motions344 и347. Эти motions теперь раскрыты; нельзя исключать их или обучать на них и выдавать результат за независимую replication.

## State, RGB и audit

- state неизменен160/160;
- state SHA до и после delay совпадает160/160;
- пустых RGB cases0;
- minimum changed RGB values26 872;
- maximum clipping fraction0,010204.

Audit охватывает128/16 384 accepted training candidates и не является exhaustive. Для490 проверочных frame queries:

- overlap under0,001°:0;
- under1°:0;
- under5°:78.

Это не указывает на exact replay в выборке audit, но не доказывает отсутствие близких fragments во всём training set.

## Интерпретация

Series84S была полным go на motions321–330, но её строгое преимущество над84R по целевой right-distal оси не воспроизвелось на motions341–350. Абсолютная реконструкция остаётся существенно лучше zero и controls, все corners прошли, а combined едва лучше84R. Однако preregistered replication требовала не просто полезный signal, а устойчивое превосходство целевой оси над frozen84R. Оно отсутствует.

Следовательно:

1. Series84S остаётся честным положительным результатом на своей заранее заданной батарее, но не считается независимо реплицированной.
2. Model84S остаётся frozen; не дообучать на motions341–350.
3. Series85 не разрешена.
4. Нельзя запускать ещё одну батарею только ради поиска удачного seed.
5. Следующий model-development этап должен быть заранее зарегистрированной новой серией с изменением, направленным на motion-invariant distal consistency. Все motions321–350 должны считаться раскрытыми и не могут быть blocking holdouts новой модели.

## Ограничения claims

Это synthetic supervised reconstruction в том же generator family и geometry grid. Даже успешные absolute gates не показывают natural vision, новое действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
