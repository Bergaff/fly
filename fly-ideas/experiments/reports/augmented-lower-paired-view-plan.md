# План series84Y: augmented lower paired-view model

## Решение после84X

Series84X показала причинно понятный trade-off:3 lower-X+1 upper-X исправили lower-X, но удаление одного upper-X view ухудшило upper-X и дало no-go против frozen84V. Series84Y не повторяет84X. Она сохраняет все четыре exact paired views balanced84V и добавляет пятый distinct lower-X view.

Единственное содержательное изменение относительно84V:

-84V:2 lower-X+2 upper-X views на base motion;
-84Y: те же exact2 lower-X+2 upper-X views плюс1 lower-X view;
- representation576-D, ridge, clipping, trajectory families и49 training frames не меняются.

Это новая model-development серия, а не replication и не post-hoc rescue84W/84X.

## Fixed training

- training seed8431;
-4096 base motions, по1024 для piecewise5, piecewise9, harmonic и chirp;
-5 связанных views одного и того же движения;
-3 lower-X+2 upper-X;
-20 480 fixed candidates;
-1 003 520 ожидаемых training frames;
- завершение только по committed candidate count, wall time не является gate.

Число20 480 равно4096×5. Увеличение на25% относительно84V необходимо, чтобы добавить lower-X информацию, не удаляя ни один balanced84V view. Поэтому серия проверяет augmentation, а не перераспределение прежнего fixed render budget.

## Выбор ресурсов через интерфейс

При создании новой серии пользователь выбирает один режим:

1.2 workers;
2.4 workers;
3.6 workers;
4.МАКСИМУМ: `os.cpu_count()` workers, то есть все видимые логические процессоры.

Batch равен числу workers. Каждый worker ограничен одним BLAS/OpenMP thread через BAT. Выбранный режим записывается в immutable protocol и автоматически восстанавливается при продолжении. Продолжить папку с другим числом workers нельзя.

Это выбор процессов, а не строгий лимит RAM в гигабайтах. Фактическая память зависит от renderer и Windows. Режим «МАКСИМУМ» намеренно не резервирует CPU для Word или других приложений; система может стать малореактивной. SQLite transactional commit, pause/resume, RunLock, free-space guard и QuickEdit protection сохраняются.

Ориентиры по wall time, не критерии результата: около6–9ч для2 workers,4–6ч для4,3–4ч для6 и примерно2–3ч для максимума на12 logical CPU. Реальное масштабирование может быть нелинейным из-за RAM, MuJoCo и Windows scheduler.

## Frozen source и comparators

Источник только завершённая production84V:

- model84V SHA `44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af`;
- runner84V SHA `05a0cdd4696af5b8901a1d34a205db8a286264f518cb54e93d1e0b9f9e9e4a52`.

Frozen comparators:84V,84S и84R. Они не изменяются.

## Новая blocking evaluation

- seed8432;
- motions411–420;
-16 exact geometry corners;
-160 cases по49 frames;
- motions321–410 раскрыты и запрещены.

Primary сохраняет строгие gates84X:

- right distal globally: candidate pooled ниже каждого из84V/84S/84R и минимум96/160 paired wins отдельно против каждого;
- right distal lower-X: candidate ниже zero и каждого comparator, минимум60/80 wins vs zero и48/80 отдельно vs84V/84S/84R;
- каждая другая axis ниже zero, минимум70% wins vs zero и не хуже каждого comparator более чем на5%;
- combined candidate ниже84V,84S,84R, zero, shuffled, static и closed;
- обе body-X и обе camera-Z groups проходят absolute gates;
- минимум12/16 corners, для каждой axis минимум7/10 wins vs zero;
- state immutable during0,5s delay.

Пороги нельзя ослаблять после результата. Даже go84Y потребует отдельной frozen replication на следующих новых motions до series85.

## Запуск

Двойным щелчком:

`experiments\RUN-AUGMENTED-LOWER-PAIRED-VIEW.bat`

Для новой серии выбрать завершённую папку production84V, затем режим2/4/6/МАКСИМУМ. Для продолжения выбрать созданную папку `lower_augmented_paired_...`; режим ресурсов будет взят из её protocol.

## Ограничения claims

Это synthetic supervised reconstruction в прежнем generator family и geometry grid. Расчёт не демонстрирует natural vision, самостоятельно созданное действие, actuators, мышцы, силы, closed-loop correction, биологический мозг или mirror neurons.
