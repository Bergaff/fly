# Stage92: пользовательский четырёхчасовой development-результат

## Статус

Полный присланный `summary-33.json` сообщает `status: completed`: 47 262 из 47 262 replicates, 6 workers, 112 193,28125 worker CPU seconds (31,1648 worker-hours). Во всех 42 агрегатах (2 бюджета × 7 условий × 3 модели) `n=47262`. Stage91 SHA совпадает с закреплённым значением. Script SHA относится к первоначальному runner до исправления WinError5 и отличается от текущего файла ожидаемо.

Это результат искусственного development benchmark. Он не является biological result, проверкой FlyWire, реальными нейронами или frozen replication.

## Заранее заданный gate

| Критерий | Требование | Результат | Итог |
|---|---:|---:|---|
| Few-shot combined-harsh accuracy margin structured−shuffled | ≥ 0,030000 | +0,032501 | пройден |
| Few-shot combined-harsh RMSE ratio structured/shuffled | ≤ 0,970000 | 0,945658 | пройден |
| Harsh strict dual wins | ≥ 60% | 54 661/94 524 = 57,8276% | не пройден |
| Все условия, strict dual wins | ≥ 55% | 361 235/661 668 = 54,5946% | не пройден |

Итог заранее заданного conjunctive gate: `candidate_for_frozen_replication=false`, `interpretation=no_candidate`.

До harsh-порога не хватило 2 054 dual wins; до all-condition порога — 2 683. Близость второго порога не разрешает округлять или менять критерий после просмотра результата.

## Основной срез

При few-shot5 и combined-harsh:

- structured96: accuracy 0,267057; RMSE 0,314317;
- shuffled96: accuracy 0,234556; RMSE 0,332379;
- dense96: accuracy 0,243227; RMSE 0,336076.

Средние margin и ratio проходят две величинные части gate, но replicate-level строгая совместная победа accuracy и RMSE недостаточно устойчива.

При budget30 и combined-harsh structured96 имеет accuracy 0,538394 против 0,457250 у shuffled96, но RMSE ratio 0,98566, поэтому среднее преимущество RMSE здесь существенно слабее few-shot режима.

## Вывод

Stage92 — **development no-go**. Structured96 демонстрирует интересные средние преимущества в нескольких стрессовых срезах, особенно по accuracy, но не проходит два заранее зафиксированных критерия устойчивости. Нельзя открывать frozen replication как подтверждение выбранного кандидата, ослаблять пороги, переопределять dual win или переходить к FlyWire mapping на основании этого результата.

Допустимый следующий шаг — диагностически исследовать причины расхождения средних эффектов и paired stability на уже раскрытых данных. Для этого подготовлен read-only запуск `experiments/DIAGNOSE-STAGE92-PAIRED-STABILITY.bat`: он раскладывает dual wins на accuracy-only, RMSE-only и neither по каждому budget и условию, не изменяя SQLite. Любая новая архитектура или новый gate будут новым development benchmark и потребуют затем отдельной замороженной проверки.

## Наблюдение о консольной паузе

Несмотря на `console_guard.disabled=true` (`before=487`, `after=423`), пользователь снова видел остановку вывода, после которой случайная клавиша возобновила работу. Следовательно, одного отключения QuickEdit недостаточно. Для следующих долгих расчётов вычислительный процесс не должен писать прогресс в интерактивную консоль: stdout/stderr направляются в файл, состояние показывается через GUI или читается из checkpoint. Клавиатурный ввод не должен находиться на пути выполнения расчёта.

## Ограничения проверки

Получен только присланный `summary-33.json`. `study.sqlite3`, `protocol.json`, `complete.json` и исходная папка запуска независимо не получены. Арифметика gate, размеры агрегатов и `n` проверены по JSON; строки SQLite и контрольные SHA полного набора файлов не проверены.
