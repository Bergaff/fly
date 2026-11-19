# Серия 69: matched encoder ablation, результат пользователя

## Статус источника

Пользователь выполнил полный расчёт и вставил `summary.json` текстом. Оригинальные байты JSON, NPZ, SQLite и complete manifest в репозиторий не передавались, поэтому их контрольные суммы независимо не проверены. Точная компактная транскрипция существенных полей сохранена в `matched-encoder-ablation-user-summary-extract.json`; отдельная fixture пересчитывает агрегаты.

## Неизменённый протокол

Обе модели получили один exact synthetic training stream из 60 000 эпизодов, одинаковые targets и Adam: learning rate 0,002, weight decay 1e-6. Compact encoder имел 24 fixed units, seed проекции 6601 и 240 level features. Замороженный rich encoder серии 67 имел 96 spatial units и 1920 level+delta features. Compact завершил 1875 optimizer steps. Модельные SHA-256: compact `f50531d876e066ad0bb011df05550f8c255bda771f7a7e79147f3a59a984c3c5`, rich `6c2eb4a1a6f111ad8d6184ca0778e2934ae3a538d33075961ba65bc9f3fd9f96`.

## Primary

| Holdout | Compact normal RMSE | Rich normal RMSE | Лучше |
|---:|---:|---:|---|
| 51 | 0,285308 | 0,264380 | rich |
| 52 | 0,239236 | 0,221886 | rich |
| 53 | 0,253199 | 0,241026 | rich |
| 54 | 0,394438 | 0,375674 | rich |
| 55 | 0,211660 | 0,245787 | compact |
| Среднее | 0,276768 | 0,269751 | rich |

Rich-minus-compact: −0,0070177 рад, то есть RMSE rich меньше примерно на 2,54% относительно compact. Rich выиграл 4 из 5 движений и повторно прошёл temporal primary, поэтому заранее заданный составной primary формально пройден.

Это небольшой и не универсальный эффект. На holdout 55 rich проиграл на 0,034127 рад. Размер выигрыша следует сообщать рядом с `primary_pass=true`, а не заменять бинарным результатом.

## Temporal controls

| Encoder | normal | zero | static | shuffled | reversed | closed | temporal primary |
|---|---:|---:|---:|---:|---:|---:|---|
| compact | 0,276768 | 0,387874 | 0,476095 | 0,351866 | 0,414170 | 0,718920 | пройден |
| rich | 0,269751 | 0,387874 | 0,509907 | 0,362247 | 0,434064 | 0,852605 | пройден |

Обе модели, а не только rich, имеют normal ниже static, shuffled, reversed и closed. Более того, в каждом из четырёх ненулевых агрегированных control conditions compact имеет меньшую RMSE. Это не отменяет primary: он сравнивал normal rich с normal compact и проверял temporal degradation внутри rich, а не требовал превосходства rich во всех вмешательствах. Closed остаётся сильным внераспределительным вмешательством и отдельно механизм не доказывает.

## Вывод

При одном exact synthetic training stream rich level+delta encoder даёт небольшой, preregistered-consistent выигрыш normal generalization на новой батарее. Это лучше разделяет вклад encoder, чем серии 67–68, но устойчивость ограничена 4 из 5 движений, а compact также проходит temporal controls. Результат не доказывает биологический механизм, зеркальные нейроны, перенос на другие распределения, мышцы или аэродинамику. Движения 51–55 нельзя использовать для настройки следующей модели.
