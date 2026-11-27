# План series84Z: preregistered multi-variant ridge/ensemble

## Почему один multi-variant расчёт

Series84X и84Y показали, что изменение количества lower/upper views сдвигает единую ridge objective и не превосходит balanced frozen84V. Series84Z не продолжает view weighting. Она использует точный balanced84V training design на новых движениях и одновременно проверяет шесть заранее фиксированных вариантов регуляризации/ансамблирования.

Чтобы не выбирать победителя по final test, расчёт разделён на три уровня:

1. training seed8433;
2. development motions421–430 seed8434 для детерминированного выбора одного из шести вариантов;
3. untouched blocking motions431–440 seed8435 только для единственной выбранной модели.

Final motions не участвуют в выборе. Primary decision вычисляется только на selected variant и final blocking set.

## Fixed training

-4096 новых base motions seed8433;
- точные четыре paired views84V:2 lower-X+2 upper-X;
-16 384 candidates;
-802 816 ожидаемых training frames;
- те же576-D features, clipping, motion families и sufficient statistics;
- completion только по committed candidate count.

## Шесть вариантов

Все варианты создаются из одних и тех же fixed sufficient statistics:

1. `ridge_0175`: right-distal ridge0,175;
2. `ridge_0350`: исходный right-distal ridge0,35;
3. `ridge_0700`: right-distal ridge0,70;
4. `ridge_1400`: right-distal ridge1,40;
5. `ensemble_v75_new25`:75% frozen84V prediction +25% нового ridge0,35;
6. `ensemble_v50_new50`:50% frozen84V prediction +50% нового ridge0,35.

Остальные axes используют прежние ridge values. Веса и список вариантов закреплены до development evaluation. Frozen84V не изменяется.

## Development selection

Каждый вариант оценивается на motions421–430 ×16 corners. Сначала предпочтение получает вариант, полностью прошедший strict gates. Если таких нет или их несколько, применяется заранее фиксированный lexicographic key:

1. strict pass;
2. число выполненных core conditions: global RD pooled ниже84V, global RD wins>=60%, lower-X RD pooled ниже84V, lower-X wins>=60%, combined ниже84V;
3. сумма нормированных global и lower-X RD wins против84V;
4. минимальная сумма нормированных global RD, lower-X RD и combined errors относительно84V;
5. более ранний вариант в зафиксированном списке как последний tie-break.

Development результат не является scientific go и не разблокирует series85.

## Untouched final blocking

После выбора только selected variant оценивается на seed8435 motions431–440 ×16 corners. Frozen comparators84V/84S/84R. Строгие gates сохраняются:

- global right distal ниже каждого comparator и минимум96/160 wins отдельно;
- lower-X right distal ниже zero и каждого comparator, минимум60/80 vs zero и48/80 отдельно vs84V/84S/84R;
- другие axes ниже zero, минимум70% wins vs zero и не хуже каждого comparator более5%;
- combined ниже84V/84S/84R, zero, shuffled, static и closed;
- обе body-X и обе camera-Z groups;
- минимум12/16 corners, каждая axis минимум7/10 vs zero;
- immutable72-coefficient state during0,5s delay.

Motions321–420 раскрыты и запрещены. После расчёта motions421–440 также становятся раскрытыми. Даже final go84Z потребует отдельной frozen replication.

## Ресурсы и сохранение

Через интерфейс выбираются2/4/6 workers или МАКСИМУМ=`os.cpu_count()`. Batch равен workers, выбор записывается в immutable protocol и восстанавливается перед resume verification. Каждый worker ограничен одним BLAS/OpenMP thread. SQLite FULL transactions, pause/resume, QuickEdit protection, RunLock и fixed-count completion сохраняются.

Ориентиры, не gates: примерно5–8ч для2 workers,3–5ч для4,2,5–3,5ч для6 и около1,5–2,5ч для максимума на12 logical CPU. Двойная development/final evaluation добавит время после training.

## Запуск

Двойным щелчком:

`experiments\RUN-MULTIVARIANT-RIDGE-ENSEMBLE.bat`

Для новой серии выбрать завершённую production папку84V, затем2/4/6/МАКСИМУМ. Для resume выбрать созданную папку `multivariant_ridge_ensemble_...`; режим ресурсов будет восстановлен автоматически.

## Recovery первоначального evaluator

Первоначальный runner мог завершить весь training и затем остановиться с `KeyError: original_basename`; первая recovery-версия могла затем остановиться на избыточной проверке `Holdout label нарушен`. Исправленный runner требует ровно20 последовательных test inputs и определяет preregistered ID только из frozen index (`421–440`), без необязательных label fields. Для такой папки разрешена узкая автоматическая migration только если:

- script SHA равен одному из двух точных post-training failed84Z SHA;
- stage уже `evaluation`;
- committed count равен fixed target;
- candidate row count совпадает;
- все scientific protocol fields, sources, variants, seeds, development/final holdouts и visual preflight совпадают.

Меняется только `script_sha256`; рядом записывается `evaluation-recovery.json` с `scientific_protocol_changed=false`. Training не повторяется. Для любого другого отличия recovery блокируется.

## Ограничения claims

Это synthetic supervised reconstruction и linear ensemble в прежнем generator family. Результат не показывает natural vision, самостоятельно созданное действие, actuators, мышцы, силы, closed-loop correction, биологический мозг или mirror neurons.
