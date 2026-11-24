# Stage95: сильные computational controls, development около4 часов

## Причина

Stage94 формально прошёл frozen gate, но few-shot accuracy margin имел запас только три правильных решения сверх порога. Кроме того, основным контролем оставался единственный shuffled96. До biological mapping нужно проверить, является ли преимущество специфичным к structured96 или его воспроизводят более сильные обычные архитектуры.

Stage95 является новым development benchmark. Его seeds будут раскрыты и не могут использоваться в будущей frozen replication.

## Модели

- `structured96`: Stage94 mask,4437 trainable parameters;
- `shuffled96`: parameter-matched shuffled mask,4437;
- `temporal96`:96 units с четырьмя соседними временными шагами всех шести каналов,4437;
- `learned_sparse96`: dense warmup20% epochs, затем magnitude pruning до2304 input weights, итог4437;
- `rnn54`: recurrent network54 units с12 закреплёнными нулевыми recurrent entries, ровно4437;
- `dense96`:9045 parameters, только диагностический контроль.

Learned-sparse получает вычислительное преимущество на dense warmup. Поэтому это намеренно сильный контроль: совпадает финальное число параметров, но не training FLOPs. RNN совпадает по числу параметров, но не по числу units. Dense96 не участвует в gate.

Для static96 моделей одинаковы полная initialization и minibatch order. Lesion units и state-noise draws одинаковы для всех96-unit моделей. У RNN54 совпадает доля lesion, но точные unit indices и форма noise не могут совпадать из-за другой размерности.

Все модели используют trajectory loss weight4,220 epochs, одинаковые training/test examples и условия Stage94.

## Длительность

До основных результатов выполняется один calibration replicate. Он не записывается в итог. По его CPU time и выбранным workers фиксируется replicate count, рассчитанный приблизительно на4 часа. После этого завершение определяется fixed count, а не часами. Защитный максимум50000 replicates.

GUI всегда даёт явный выбор `Начать новый расчёт`; при наличии checkpoint отдельно показывает `Продолжить незавершённый расчёт`. Workers нового запуска выбираются кнопками2/4/6/Максимум или клавишами2/4/6/M. Во время работы показываются done/total, процент, приблизительное оставшееся время и локальная дата/время окончания. ETA пересчитывается по wall-throughput текущей сессии и является приблизительной. Python запускается через `pythonw.exe` и не зависит от консольной клавиатуры. SQLite commit выполняется после каждого replicate; Continue вычисляет только отсутствующие IDs и сохраняет workers старого protocol.

## Development gate

Сначала structured96 обязана сохранить Stage94 gate против shuffled96:

- few-shot combined-harsh accuracy margin≥0,03;
- RMSE ratio≤0,97;
- harsh Wilson95 lower≥0,60;
- overall Wilson95 lower≥0,55.

Затем для **каждого** `temporal96`, `learned_sparse96`, `rnn54` одновременно:

- few-shot combined-harsh mean accuracy строго выше;
- few-shot combined-harsh mean RMSE строго ниже;
- harsh dual-win Wilson95 lower≥0,50;
- overall dual-win Wilson95 lower≥0,50.

Только выполнение всех условий выбирает development candidate. Любой near-miss — no-candidate. Новый кандидат потребует отдельного runner и нового frozen seed namespace.

## Граница вывода

Даже pass показывает только преимущество инженерной маски на синтетическом benchmark над выбранными computational controls. Это не коннектом, не реальные нейроны, не биологическая память и не evidence для FlyWire. Series90 mapping gate остаётся отдельным обязательным барьером.
