# Series105A+B: official-eye diagnostic и paired domain adaptation

## Решение до результата

Series104 завершён как preregistered no-go: unchanged frozen89E не прошёл action/specificity gates на official observer-eye изображениях. Его thresholds, cases и вывод не меняются.

Один Windows BAT последовательно выполняет две явно разные фазы:

- **105A** — post-result диагностика на уже раскрытых motions903–908, без fit и без pass/fail;
- **105B** — новая development-линия с заранее заданным обучаемым domain adapter, отдельными train и validation motions.

Runner SHA-256: `b070fff687dfcfd263c6868b59954283486dd84b5a4e07156816f333a13dae67`.

Exact prerequisites:

- corrected Series104 runner SHA `ace8d99fa0ad71454fa7b4122868547c880817f9b45b9e654fb02245aad298a1`;
- genuine Series104 no-go JSON SHA `91109c557111c4278567d383a5f99ed281f05ea5bcbd5fa5e326752afdf6ba04`;
- Series104 `status=completed`, `primary.passed=false`, `scientific_result=false`;
- прежние result89D/source84Z/frozen files проверяются неизменённой prerequisite chain.

## Series105A: диагностика

Для каждого раскрытого motion903–908 повторно создаются:

1. official observer-eye sequence;
2. unchanged frozen edge history/state/readout;
3. synthetic external-camera reference того же движения на четырёх закреплённых views801–804.

Сохраняются RGB/temporal/edge statistics, cosine и normalized RMSE между official и mean synthetic states, action probabilities и target-to-actual-demonstrator RMSE. 105A не обучает, не выбирает модель, не имеет primary gate и не может изменить Series104.

## Series105B: adapter

### Split

- train IDs1051–1062: 12 motions, по4 на каждое действие;
- validation IDs1063–1068: 6 motions, по2 на каждое действие;
- seeds, amplitudes и speeds заданы в runner;
- exact motion hashes проверяются против прежних sets и между train/validation;
- validation никогда не используется для fit или выбора.

### Fixed adapter

Каждый train motion образует paired sample:

- input: 72-dimensional frozen coefficient state из official eyes;
- target: среднее 72-dimensional frozen state четырёх synthetic views того же motion.

По каждой координате независимо вычисляется affine mapping. Slope равен paired correlation × synthetic standard deviation / official standard deviation и заранее clipped в `[-3,3]`. Нет cross-feature mixing, action labels, trajectory truth, grid search, hyperparameter selection или post-result tuning. Модель сохраняется как `paired_diagonal_adapter.npz`.

Это новая обученная engineering model, а не unchanged frozen89E replication.

## Frozen non-physical validation gate

На шести validation motions adapted policy должна:

1. правильно классифицировать action минимум4/6;
2. иметь меньший target-to-actual-truth RMSE минимум4/6 против каждого контроля: raw unchanged frozen, neutral visual, reversed visual, zero state, shuffled state;
3. иметь distinct target hashes от neutral/reversed/zero/shuffled во всех cases;
4. иметь mean truth RMSE ниже raw unchanged frozen.

Успех означает только `development_candidate=true` и разрешает отдельно preregistered untouched **physical Series106**. Он не является physical confirmation. Fail закрывает этот exact adapter без ослабления gate.

## Windows workflow

Дважды щёлкнуть `experiments\RUN-OFFICIAL-EYE-DIAGNOSTIC-ADAPTATION-105AB.bat`, затем выбрать завершённые result89D и production84Z. Один GUI выполняет 105A, train105B и validation105B последовательно, показывает общий процент и ETA, автоматически открывает result или copyable error report.

## Ограничения

Ни один исход не восстанавливает Series104 и не подтверждает biological observation-to-action, FlyVis/FlyWire/connectome mapping, мышцы, живую муху или mirror neurons. Series105B использует synthetic domain как engineering teacher reference. Любая physical проверка требует новых untouched outcomes и отдельного frozen protocol.
