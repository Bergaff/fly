# Серия 84T: пользовательский результат console/compute accounting

## Статус и источник

Пользователь прислал завершённый `summary-10.json`. SHA-256:

`0d4302c46b4eaf830fba0e528e4cf55193bd1414b24a5a3ab5a7edcacce1d56d`

Schema `console-compute-accounting-result-v1`, status `completed`. В summary находятся 128 records и 64 двухкандидатные партии.

SHA runner84T совпадает с опубликованным файлом:

`fb9b532fdf9286561da0756364ecfdbb5e7e3e19238df1d1c4ad6488d0321859`.

SHA закреплённого workload runner84R также совпадает:

`d60f23d33185fde7c18e56ccf26a510166955ded4c5384ec0578ec67185cfd6d`.

Полная папка с `complete.json` не передавалась, поэтому файловый manifest независимо не проверен. Проверены summary, records, batches и SHA двух runners.

## QuickEdit

WinAPI успешно прочитал и изменил console mode:

- platform `nt`;
- QuickEdit до запуска: `true`;
- mode before: `487`;
- QuickEdit после изменения: `false`;
- mode after: `423`;
- `disabled=true`.

Это прямо подтверждает, что QuickEdit был включён в новом командном окне до защиты. В 84T он был снят до запуска workers.

Результат не может доказать, что именно QuickEdit вызвал конкретную остановку 84R, поскольку mode84R тогда не записывался. Но наблюдение пользователя «возобновилось после клавиши», включённый QuickEdit до 84T и отсутствие stalls после его отключения делают этот механизм наиболее согласованным объяснением.

## Fixed-count completion

Полностью завершены:

- candidates `128/128`;
- sequence IDs `900000–900127`;
- frames `6 272`, ровно 128 × 49;
- unique motion SHA `128/128`;
- unique RGB SHA `128/128`;
- motion, RGB, feature и target SHA уникальны во всех 128 records;
- все features/targets finite;
- feature variance положительна во всех records.

Завершение определялось числом кандидатов, а не прошедшим временем. Поэтому скрытая пауза не могла сама завершить 84T.

## Timing

Главные результаты:

- coordinator wall: `77,407` с;
- worker CPU sum: `144,500` с;
- two-worker CPU equivalent: `72,250` с;
- worker-reported wall sum: `144,826` с;
- throughput: `5 952,96 candidates/hour`;
- parallel CPU utilization относительно `2 × wall`: `93,34%`.

Первая партия заняла `5,327` с из-за startup workers; поэтому её wall/worker ratio `4,465` не является stall и не прошла preregistered >30 s filter.

Для остальных 63 партий:

- median batch wall `1,138` с;
- p95 `1,196` с;
- maximum `1,243` с;
- median coordinator/worker-wall ratio `1,0012`;
- maximum ratio `1,0016`.

То есть после startup coordinator и workers двигались почти синхронно. `suspected_blocked_batches=0`.

Candidate worker CPU:

- median `1,125` с;
- p95 `1,188` с;
- maximum `1,250` с.

## Что это говорит о серии 84R

84T подтверждает, что на этом компьютере сам 84R workload способен устойчиво считать примерно 5 953 candidates/hour в коротком fixed-count режиме. Нельзя напрямую умножать этот throughput на восемь часов: 84R дополнительно обновляет training statistics, пишет transactional checkpoints и выполняет evaluation.

Тем не менее 1 146 candidates за reported 34 320,625 с серии84R несовместимы с непрерывной работой, наблюдаемой в 84T. Это усиливает вывод, что значительная часть elapsed84R не была полезным candidate compute. Точно рассчитанные 1 146 candidates и модель остаются реальными; утверждение о непрерывных восьми часах compute не поддерживается.

## Решение для следующего long runner

1. Отключать QuickEdit через WinAPI до workers.
2. Не использовать wall time как единственный completion gate.
3. Использовать фиксированное число committed candidates или worker-CPU accounting.
4. Сохранять per-batch worker CPU/wall и coordinator wall в checkpoint.
5. Startup и console/output waiting не считать training compute.
6. Сохранять возможность pause/resume, но completion должен зависеть от реально завершённых партий.

На основе 84T разумнее заранее закрепить fixed candidate count для следующей модели. Окончательный count следует выбирать с запасом на checkpoint overhead и целевым временем 4–8 часов; сам 84T научную модель не выбирает.

## Ограничения

Это короткая инфраструктурная диагностика, не hardware benchmark и не научный эксперимент. Она не обучает модель, не изменяет no-go 84R и не разблокирует series85.
