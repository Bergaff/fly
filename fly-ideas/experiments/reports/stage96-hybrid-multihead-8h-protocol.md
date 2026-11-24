# Stage96: exact-budget hybrid multi-head development, около8 часов

## Новый вопрос

Stage95 показал устойчивый tradeoff: structured96 лучше классифицирует ordered action, а learned-sparse96/RNN54 лучше восстанавливают траекторию. Старый joint gate не ремонтируется. Stage96 задаёт новую disclosed development hypothesis: можно ли в том же общем параметрическом бюджете разделить специализации — structured static branch для classification и recurrent branch для trajectory — и получить joint advantage над сильными monolithic controls?

## Точный бюджет4437

Каждая модель имеет ровно4437 trainable parameters.

Hybrid:

- classifier:61 static units,1464 input weights +61 bias +61×9 output +9 bias =2083;
- trajectory:40-unit RNN, где18 recurrent diagonal entries закреплены нулём:240 input +1582 recurrent +40 bias +480 output +12 bias =2354;
- всего2083+2354=4437.

## Модели

- `hybrid_structured`: structured classifier mask + RNN40 trajectory;
- `hybrid_shuffled`: parameter-matched shuffled classifier + та же архитектура RNN40;
- `hybrid_temporal`: temporal classifier + RNN40;
- `hybrid_learned`: dense-warmup/pruned classifier + RNN40;
- `learned_sparse96`: сильный monolithic control Stage95;
- `rnn54`: сильный exact-budget monolithic control Stage95.

У четырёх hybrid variants trajectory branch обучается одинаково и служит контролируемой общей частью; их различие проверяет именно classifier topology. Learned classifier снова получает dense warmup20%, то есть намеренное compute advantage.

## Данные и длительность

Сохраняются Stage95 ordered classes, budgets5/30, семь условий,220 epochs и одинаковые examples. Используется новый disclosed namespace `96000000-series`.

Один calibration replicate выполняется до main results и фиксирует count приблизительно на8 часов при выбранных workers. Завершение определяется fixed count, максимум50000 replicates.

## Gate

### Classification branch

Для `hybrid_structured` против `hybrid_shuffled` few-shot harsh accuracy margin≥0,02. Против каждого hybrid shuffled/temporal/learned:

- few-shot harsh mean accuracy строго выше;
- harsh paired accuracy Wilson95 lower≥0,55;
- overall paired accuracy Wilson95 lower≥0,55.

### Полная hybrid модель против monolithic controls

Против каждого learned_sparse96 и rnn54 одновременно:

- few-shot harsh mean accuracy выше;
- few-shot harsh mean RMSE ниже;
- harsh и overall paired RMSE Wilson95 lower≥0,50;
- harsh и overall strict dual accuracy+RMSE Wilson95 lower≥0,50.

Только прохождение всех условий выбирает development candidate. Любой pass потребует новой frozen replication и нового seed namespace.

## GUI и сохранение

GUI всегда предлагает `Начать новый расчёт`; при наличии checkpoint отдельно показывает `Продолжить незавершённый расчёт`. Workers выбираются кнопками2/4/6/Максимум либо клавишами2/4/6/M. Во время работы показываются процент, приблизительное оставшееся время и локальное время окончания. Pythonw не зависит от консоли. SQLite commit выполняется после каждого replicate; resume считает только отсутствующие IDs.

## Граница

Hybrid спроектирован после просмотра Stage95, поэтому это development selection. Даже успех показывает только engineering benefit task specialization в synthetic benchmark. Это не коннектом, не реальные нейроны, не биологическая память и не разрешение FlyWire mapping.
