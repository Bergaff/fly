# Stage94: frozen paired-loss replication

## Почему меняется реализация

Stage92 no-go нельзя переобозначать. Paired-диагностика показала конкретную причину: при budget30 structured96 почти всегда сохраняет сильное преимущество accuracy, но преимущество RMSE близко к нулю. Например, combined-harsh accuracy wins 83,21%, RMSE wins 58,56%; lesion25 — 67,14% и47,19%. Дополнительно Stage92 использовал разные RNG seeds моделей не только для initialization и minibatch order, но и для lesion indices/state-noise. Последнее нарушает максимально парное сравнение: модели получали разные реализации повреждения.

## Зафиксированное исправление

1. Structured96, shuffled96 и dense96 получают одинаковый RNG seed для полной исходной матрицы весов, output head и minibatch order. Маски остаются различными.
2. Внутри одного replicate/budget/scenario все модели получают одинаковые lesion indices и один и тот же state-noise draw.
3. Ошибка12 trajectory outputs получает weight4 относительно каждого из9 classification outputs. Это не меняет метрику, только training loss.
4. Shuffled96 остаётся основным parameter-matched контролем. Dense96 остаётся диагностикой.

Common-random-number correction обязана была быть сделана независимо от направления результата. Weight4 выбран на раскрытом development pilot после Stage92:64 replicates дали ориентировочно harsh dual64,06% и overall59,15%; это selection evidence, не подтверждение. Weight2 дал overall54,69%, поэтому weight4 является раскрыто выбранной гипотезой и теперь замораживается.

## Независимость replication

- ровно2048 replicates;
- новый seed namespace `94000000-series`, не использованный в Stage92 и development pilots;
- Stage92 source закреплён SHA `0dbbdcb9…`;
- trajectory weight4, модели, budgets, scenarios, epochs и gate нельзя менять после запуска;
- fixed count не зависит от промежуточного результата.

## Усиленный frozen gate

Все четыре условия должны выполниться одновременно:

1. few-shot5 combined-harsh mean accuracy margin structured−shuffled ≥0,03;
2. few-shot5 combined-harsh RMSE ratio structured/shuffled ≤0,97;
3. нижняя граница95% Wilson для harsh dual-win rate ≥0,60;
4. нижняя граница95% Wilson для all-condition dual-win rate ≥0,55.

Это строже Stage92, где использовались point rates. Любой near-miss — frozen no-go. Порог нельзя округлять или ослаблять.

## Запуск и сохранение

Двойной щелчок: `experiments/RUN-STAGE94-FROZEN-PAIRED-LOSS.bat`.

GUI предлагает2/4/6/Максимум workers и показывает progress. Python запускается через `pythonw.exe`; вычисление не пишет в интерактивную консоль. После каждого replicate сначала commit SQLite, затем checkpoint JSON. Повторный запуск продолжает отсутствующие replicate IDs. Ошибки сохраняются в `ПОСЛЕДНЯЯ-ОШИБКА-STAGE94.txt`.

## Граница вывода

Даже frozen pass подтверждает только воспроизводимость преимущества искусственной structured96 маски в синтетическом benchmark.96 units не являются нейронами, маска не является коннектомом, state hold/noise не являются биологической памятью. Pass не открывает FlyWire автоматически: он разрешает только отдельное обсуждение следующего biological mapping preflight с ранее установленными ограничениями Series90.
