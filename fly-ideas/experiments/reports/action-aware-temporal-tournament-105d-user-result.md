# Series105D: genuine action-aware temporal tournament result

## Статус

Run завершён полностью и быстрее верхней оценки15hours. Это не ранний выход: собраны все90 train,18 selection и18 conditional final cases. Все четыре модели прошли selection gate, winner дошёл до полного untouched final.

Final development gate **выполнен**: `passed=true`, `development_candidate=true`, `scientific_result=false`.

Exact JSON сохранён без изменения как `action-aware-temporal-tournament-105d-user-result.json`.

- JSON SHA-256: `59f8d54fbc7c062c068259d455484f643844f33092e655e195acb170cbfb9ad3`
- runner SHA-256: `8c39bfca87f3a11f59ac82cca721c58bb142094f7cd26bb1d4d6ae275ab23e45`
- Series105C result SHA-256: `d9f8c8400b4cff10ecc5b20132e06cb2ccb07f3cee3075d461a1c1622abcda39`
- selected model: `temporal_action_experts`
- selected model SHA-256: `1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1`

## Почему расчёт завершился быстро

15hours было верхней ожидаемой оценкой, а не требованием искусственно занимать процессор. Fixed protocol завершает run после126 official-eye captures и deterministic NumPy fits. На пользовательской машине этот workload оказался существенно быстрее. Summary подтверждает не shortcut, а полный путь:90 train motions,18 selection rows у каждой из4 моделей и18 final rows у выбранной модели.

## Selection

Все четыре заранее объявленные идеи прошли selection gate≥12/18:

| Модель | Action correct | Wins neutral/reversed/zero/shuffled | Mean candidate RMSE,rad |
|---|---:|---:|---:|
| state multitask ridge | 17/18 | 16/18,18/18,18/18,16/18 | 0,083326 |
| state random Fourier | 16/18 | 15/18,17/18,16/18,15/18 | 0,087320 |
| temporal pool ridge | 17/18 | 18/18,18/18,18/18,18/18 | 0,049207 |
| temporal action experts | 17/18 | 16/18,16/18,18/18,15/18 | **0,044689** |

По preregistered minimum-RMSE rule выбран `temporal_action_experts`. Final не участвовал в выборе.

## Untouched final

| Проверка | Требование | Результат |
|---|---:|---:|
| Action classification | ≥12/18 | **18/18** |
| Wins vs neutral visual | ≥12/18 | **15/18** |
| Wins vs reversed visual | ≥12/18 | **16/18** |
| Wins vs zero input | ≥12/18 | **18/18** |
| Wins vs shuffled visual | ≥12/18 | **17/18** |
| Distinct target hashes | все cases | pass |

Mean truth RMSE,rad:

- candidate:0,038314;
- neutral visual:0,137421;
- reversed visual:0,162602;
- zero input:0,188425;
- shuffled visual:0,122854.

Action classification по классам: foreleg6/6, head-directed6/6, reach/withdraw6/6. Candidate mean RMSE: foreleg0,048353, head0,046103, reach0,020486. Все foreleg controls и почти все head controls проиграны. У reach candidate выигрывает neutral3/6 и reversed4/6, поэтому общая specificity проходит, но per-action visual specificity для reach остаётся ограничением и не должна скрываться.

## Допустимый вывод

Series105D устанавливает successful **supervised non-physical development candidate**: official-eye temporal features позволяют обученной action-aware model обобщаться на untouched generated motions и превосходить сильные input controls по заранее объявленному общему gate.

Это не восстановление frozen89E: training использовало generated action labels и actual demonstrator truth. Это также не физическое подтверждение, не biological learning и не FlyVis/FlyWire/mirror-neuron evidence.

Pass разрешает подготовить отдельно frozen **Series106 physical validation** exact selected model. Для запуска понадобится оригинальная result-папка Series105D с `selected_action_aware_model.npz`; summary JSON не содержит саму матрицу модели. Series106 должен SHA-проверять model `1bbb15cd…`, не переобучать, использовать новые untouched motions и сохранить neutral/reversed/zero/shuffled/open-loop controls.
