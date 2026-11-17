# Серия 84T: console stall и compute accounting

## Причина

Во время series84R окно показывало `0,4/8`, затем расчёт продолжился только после нажатия клавиши. Summary записала 34 320,625 с вместо budget 28 800 с, но всего 1 146 candidates. На Windows 10 это согласуется с QuickEdit/console selection: щелчок по консоли может остановить процесс или заблокировать вывод до выхода из selection mode. По одному summary механизм не доказан.

84T является только технической диагностикой перед следующим научным long run.

## Защита

Перед созданием worker processes Python через WinAPI:

- читает input console mode;
- устанавливает `ENABLE_EXTENDED_FLAGS`;
- снимает `ENABLE_QUICK_EDIT_MODE`;
- повторно читает mode и сохраняет фактический результат.

Изменение относится к текущей общей консоли процесса, а не к глобальной установке Windows.

## Fixed count

Расчёт выполняет ровно 128 новых deterministic candidates с тем же renderer и 576-D spatial-pyramid representation, что series84R. Время не может само завершить diagnostic: даже длительная скрытая пауза не заменяет отсутствующие candidates.

Для каждого candidate сохраняются:

- worker CPU seconds;
- worker wall seconds;
- coordinator batch wall seconds;
- motion, RGB, feature и target SHA;
- feature variance и finite guard.

Worker CPU не растёт во время suspension/waiting, тогда как coordinator wall растёт. Большой разрыв помогает обнаружить stall. Это accounting diagnostic, не точный hardware benchmark.

## Выход

`summary.json`, `candidate_timing.csv`, `ИТОГ.txt` и SHA manifest сообщают:

- 128/128 candidates и 6 272 frames;
- coordinator wall;
- сумму worker CPU и двухпроцессный equivalent;
- candidates/hour;
- максимальный batch wall/worker-wall ratio;
- число suspected blocked batches;
- QuickEdit mode before/after.

## Ограничения

- серия не обучает и не выбирает научную модель;
- не исправляет post hoc no-go 84R;
- worker CPU не включает ожидание и не равен wall duration;
- только следующий runner может использовать исправленное accounting правило;
- series85 остаётся заблокированной.
