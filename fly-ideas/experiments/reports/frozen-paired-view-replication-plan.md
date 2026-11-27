# Серия84W: frozen replication model84V

## Решение до расчёта

Model-development84V прошла все blocking gates на motions361–370. Candidate SHA `44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af` заморожена. Следующий допустимый расчёт только read-only replication; series85 остаётся заблокированной.

## Запреты

- не перезапускать training84V;
- не менять weights, representation, ridge, clipping или thresholds;
- не использовать motions321–370;
- не исключать слабые движения post hoc;
- не выбирать seed после результата.

Runner проверяет завершённую source84V, SQLite, complete manifest, runner84V SHA, frozen84V и embedded84S/84R SHA. Source files хешируются до и после evaluation.

## Новая батарея

- seed8428;
- motions381–390, пять piecewise5 и пять piecewise9;
-16 прежних geometry corners;
-160 cases по49 frames;
- frozen84V сравнивается с frozen84S, frozen84R, zero, shuffled, static и closed;
-72 coefficients, delay0,5с без обновлений;
- ограниченный non-exhaustive audit максимум128 training candidates.

## Blocking primary

Правила дословно повторяют84V:

- каждая ось ниже zero, минимум112/160 wins;
- right distal ниже84S и84R pooled и минимум96/160 wins отдельно против каждой;
- другие оси не хуже каждой frozen model более чем на5%;
- lower-X right distal ниже zero/84S/84R, минимум60/80 vs zero и48/80 отдельно vs84S/84R;
- обе body-X и camera-Z groups проходят все оси минимум56/80 vs zero;
- минимум12/16 corners проходят все оси минимум7/10;
- combined ниже84S,84R,zero и всех controls.

Один fail означает replication no-go без округления.

## Запуск

Двойной щелчок `RUN-FROZEN-PAIRED-VIEW-REPLICATION.bat`, затем выбор завершённой папки `paired_view_distal_...`. Это evaluation-only, не многочасовое обучение.

## После результата

- go: можно отдельно preregister следующий этап series85;
- no-go: series85 остаётся заблокированной, model84V не дообучается на381–390.

## Ограничения

Replication остаётся в synthetic generator family и geometry grid. Она не доказывает natural vision, новое действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
