# Серия85: preregistered shared latent population prototype

## Основание

Series85 разрешена только после independently verified strict replication go84AA. Frozen source: selected model84Z SHA `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`, variant `ridge_0175`, right-distal ridge0,175, weight1,0. Runner84AA SHA `846bf4b56e7d6d221a8a5a35eb02675f16bde570ea7e7b7a8e2d822f4c33e879` проверяется до запуска.

Это короткий blocking prototype этапа II, а не новое долгое обучение. Model84Z не обучается и не изменяется. Motions421–450 раскрыты и запрещены.

## Operational population

Явная artificial shared population содержит шесть semantic units, по одной для каждой foreleg axis. Она используется в двух режимах:

- observation: units получают только RGB-history output frozen model84Z;
- execution: те же шесть units получают только proprioceptive body angles;
- один общий decoder переводит оба режима в72 replay coefficients с задержкой0,5с.

Equal-budget private observation control имеет те же шесть units и frozen84V encoder. Private execution path имеет те же шесть proprioceptive units. Это operational mirror-like criterion, а не утверждение о биологических нейронах.

## Данные

Две полностью blocking batteries:

- battery1: seed8502, motions451–460;
- battery2: seed8503, motions461–470;
- motions с окончанием1–5: piecewise5;
- остальные: piecewise9;
-16 geometry corners;
-20×16 =320 cases;
-49 оцениваемых frames на case.

Никакой development selection между batteries нет. Обе входят в primary и должны пройти независимо. Все20 motion hashes проверяются против всех accepted training hashes84Z; дополнительно сохраняется прежний broad overlap audit максимум128 training candidates.

## Метрики

Для каждой оси и каждой battery объединяются sufficient statistics всех10×16×49 samples. Pearson correlation вычисляется между activity unit в observation и activity той же unit в execution. Temporal-shuffled, static и closed RGB проходят тот же frozen encoder.

Cross-mode RSA строится на десяти motion-level representations: observation trace усредняется по16 views, execution trace берётся из proprioception; затем коррелируются45 попарных Euclidean distances. Null:1000 заранее seeded shuffled-label permutations.

Reconstruction использует общий six-unit-to-72-coefficient decoder. Private observation84V имеет равный six-unit budget.

## Blocking primary

Обе batteries отдельно должны выполнить всё:

1. минимум4/6 shared units имеют cross-mode correlation не ниже0,20;
2. для каждого засчитанного unit correlation выше shuffled, static и closed controls;
3. cross-mode RSA не ниже0,30 и строго выше p95 из1000 shuffled-label permutations;
4. pooled shared-observation RMSE не хуже equal-budget private observation84V более чем на2%;
5. pooled shared-observation RMSE ниже zero, shuffled, static и closed;
6. state содержит72 coefficients, не обновляется во время задержки0,5с и имеет одинаковый SHA до/после.

Primary pass только при2/2 прошедших batteries. Near-miss является no-go; нельзя объединить batteries, удалить motion/corner/unit или изменить thresholds после результата.

## Ресурсы и запуск

`experiments\RUN-SHARED-LATENT-POPULATION.bat`

GUI предлагает2/4/6/Максимум workers. «Максимум» использует все доступные логические процессоры и не вводит искусственного ограничения памяти ради других приложений. Расчёт должен занять существенно меньше долгого model-development run, потому что это frozen prototype без training.

При ошибке открывается UTF-8 файл `workspace\runs\ideas\i-observational\shared-latent-population\ПОСЛЕДНЯЯ-ОШИБКА-85.txt`.

## Ограничения

- artificial semantic units заданы инженером;
- только один grooming action family;
- natural vision отсутствует;
- нет action identity/compositional transfer, это задача series86;
- kinematic replay не является actuator dynamics;
- нет сил, мышц или closed-loop correction;
- результат не доказывает биологические mirror neurons.
