# Series105C: genuine temporal cross-feature result

## Статус

Windows run завершён технически: `status=completed`. Frozen development gate **не выполнен**: `passed=false`, `development_candidate=false`, `scientific_result=false`. Это genuine held-validation no-go, не runtime failure.

Exact JSON сохранён без изменения как `temporal-crossfeature-adapter-105c-user-result.json`.

- JSON SHA-256: `d9f8c8400b4cff10ecc5b20132e06cb2ccb07f3cee3075d461a1c1622abcda39`
- runner SHA-256: `60c74e44bca8c64ecc667e6eb8705f6163565cdd0509230ca8872d50ac4b206f`
- Series105A+B result SHA-256: `92715b54fde5fb259ce3947e35edf4f8ba178f659c5de01096546ca739af6a14`
- trained model SHA-256: `9224cd9e4fd4a2f4b62376cc386d66d983f3c38353365e7d9dc6e47a4b8a68a9`

## Train-only CV

Все30 train pairs обработаны. CV state NRMSE монотонно снижался при усилении regularization:

| Ridge | Mean state NRMSE |
|---:|---:|
| 0,01 | 0,299225 |
| 0,1 | 0,282696 |
| 1 | 0,227908 |
| 10 | 0,175016 |
| 100 | **0,146472** |

По frozen rule выбран ridge100. Он находится на верхней границе заранее заданного grid; расширять grid после просмотра validation нельзя считать подтверждающим продолжением.

## Held validation gate

| Проверка | Требование | Результат |
|---|---:|---:|
| Action classification | ≥6/9 | 4/9, fail |
| Wins vs diagonal | ≥6/9 | 9/9, pass |
| Wins vs raw frozen | ≥6/9 | 9/9, pass |
| Wins vs neutral visual | ≥6/9 | 5/9, fail |
| Wins vs reversed visual | ≥6/9 | 7/9, pass |
| Wins vs zero state | ≥6/9 | 3/9, fail |
| Wins vs shuffled state | ≥6/9 | 9/9, pass |
| Distinct targets | все cases | pass |
| Mean below diagonal/raw | да | pass |

Mean truth RMSE,rad:

- cross-feature:0,160217;
- diagonal:0,189996;
- raw frozen:0,495953;
- neutral visual:0,174206;
- reversed visual:0,179466;
- zero state:0,169557;
- shuffled state:0,447958.

Cross-feature mapping улучшил diagonal и raw во всех9 validation cases. Он также лучше zero state по общей средней, но выигрывает только3/9: aggregate mean скрывает недостаточную casewise specificity. Neutral gate не пройден с5/9, на один case ниже frozen threshold.

## Action identity

Восемь из девяти cases классифицированы как `reach_withdraw`; только case1105 классифицирован как `foreleg_rubbing`. Правильны три genuine reach cases1101/1104/1107 и foreleg case1105. Ни один head-directed case не распознан. Таким образом, full72×72 temporal/axis mixing сменил направление class collapse, но не восстановил устойчивую action identity.

## Вывод

Гипотеза о том, что одного full linear temporal cross-feature mapping достаточно для official-eye transfer, не прошла frozen gate. Улучшение trajectory reconstruction реально и сильнее diagonal105B, но candidate не отделён надёжно от neutral/zero controls и не распознаёт действия.

Нельзя ослаблять6/9 gate, выбирать cases или трактовать9/9 против raw/diagonal как общий pass. Physical Series106 не авторизован. Series104,105B и105C сохраняются как разные no-go результаты. Любая следующая development-линия должна быть новой гипотезой, а не post-result расширением ridge grid; никакой исход здесь не подтверждает biological observation-to-action, FlyVis/FlyWire, living fly или mirror neurons.
