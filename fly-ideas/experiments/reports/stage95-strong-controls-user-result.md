# Stage95 strong controls: пользовательский development-результат

## Проверка

Присланный `summary-35.json` сообщает completed:13119/13119 replicates,4 workers,67439,203125 worker CPU seconds (18,7331 worker-hours). Script SHA `43157af6…` совпадает с запущенной версией Stage95. Во всех84 агрегатах `n=13119`; parameter counts и protocol совпадают с preregistration.

Получен только summary. SQLite, protocol.json и complete.json отдельно не получены, поэтому individual rows и SHA папки независимо не проверены.

## Gate

`retains_stage94_vs_shuffled=true`, но `beats_every_strong_control=false`, поэтому `development_candidate=false` и `interpretation=no_candidate`.

| Контроль | Few-shot harsh accuracy margin | RMSE ratio | Harsh Wilson95 lower | Overall Wilson95 lower | Итог |
|---|---:|---:|---:|---:|---|
| shuffled96 | +0,030355 | 0,945562 | 0,633854 | 0,601515 | Stage94 advantage сохранён |
| temporal96 | +0,039753 | 0,960192 | 0,710957 | 0,637065 | structured96 выигрывает |
| learned_sparse96 | +0,017981 | 1,035997 | 0,375344 | 0,320799 | structured96 проигрывает RMSE и dual stability |
| rnn54 | +0,074740 | 1,143201 | 0,311683 | 0,329610 | structured96 выигрывает accuracy, но сильно проигрывает RMSE/dual |

## Интерпретация

Stage94 не был случайностью относительно shuffled96: на значительно большем development-наборе преимущество сохранилось и стало менее пограничным. Structured96 также уверенно превосходит temporal96, поэтому эффект не объясняется любой простой локальной временной маской.

Но более сильные controls разрушают общий Pareto claim. В few-shot combined-harsh:

- structured96: accuracy0,254937, RMSE0,311349;
- learned_sparse96: accuracy0,236956, RMSE0,300530;
- rnn54: accuracy0,180197, RMSE0,272348.

Structured96 лучше распознаёт ordered class, но learned-sparse и особенно RNN значительно точнее восстанавливают траекторию. Строгий dual-win gate закономерно не проходит. Это не near-miss: Wilson lower около0,32–0,38 далеко ниже0,50.

При budget30 structured96 часто лучше RNN по RMSE, но preregistered gate специально требовал устойчивость across budgets и harsh paired comparisons; менять его после результата нельзя.

## Вывод

Stage95 — **development no-go против сильных controls**. Нельзя готовить frozen replication этой же structured96 как «лучшую общую архитектуру», нельзя исключать RMSE, learned-sparse или RNN после просмотра результата и нельзя переходить к biological mapping на основании Stage94.

Сохраняется более узкий результат: structured96 имеет устойчивое classification advantage над parameter-matched shuffled96 и temporal96 в этой синтетической задаче. Но общий joint accuracy+trajectory claim не выдержал сильных controls.

Следующий допустимый исследовательский шаг должен быть новым вопросом, а не ремонтом gate: либо заранее разделить classification и trajectory как разные hypotheses с отдельными архитектурами, либо проверить multi-head/hybrid модель в новом development этапе. Любая такая модель потребует новых frozen seeds при успехе.

## Исправление интерфейса после обратной связи

После этого запуска GUI восстановлен и расширен: отдельные кнопки «Продолжить незавершённый расчёт» и «Начать новый расчёт»; workers выбираются кнопками2/4/6/Максимум и клавишами2/4/6/M; во время расчёта показываются процент, примерное оставшееся время и дата/время окончания. Это UI-исправление не меняет сохранённый Stage95 результат.
