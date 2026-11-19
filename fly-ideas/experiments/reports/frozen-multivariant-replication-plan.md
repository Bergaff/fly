# План series84AA: frozen replication selected model84Z

## Цель

Series84Z получила model-development go после выбора `ridge_0175` на development motions421–430 и успеха на untouched final431–440. Series84AA является отдельной read-only replication. Она не обучает модель, не повторяет development selection и не оценивает остальные пять variants как новые попытки.

## Frozen source

Пользователь выбирает завершённую production папку `multivariant_ridge_ensemble_...`. Runner проверяет:

- завершённый fixed-count stage и primary go84Z;
- complete manifest result folder;
- runner84Z SHA `fa4040d7271f2c98021042054ebe60767ad092de81d610a60815738be9f57a6b`;
- selected model SHA `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`;
- selected variant `ridge_0175`;
- right-distal ridge0,175;
- new-model weight1,0, то есть selected variant не является ensemble;
- frozen84V/84S/84R SHA;
- embedded84V arrays в model bundle точно совпадают с отдельным frozen84V comparator file.

До и после evaluation повторно хэшируются SQLite, selected model, comparators, summary, complete marker и recovery audit, если он присутствует. Source folder не изменяется.

## Новая replication evaluation

- seed8436;
- motions441–450;
- первые пять trajectories piecewise5, следующие пять piecewise9;
-16 exact geometry corners;
-160 cases по49 evaluated frames;
- no training;
- no model fitting;
- no variant selection;
- no threshold adaptation.

Motions321–440 раскрыты и запрещены для этой replication. New motion hashes проверяются против всех source labels.

## Строгий primary

Используется тот же `primary_decision`, что для untouched final84Z:

- global right distal candidate pooled ниже84V,84S и84R и минимум96/160 wins отдельно против каждого;
- global right distal ниже zero и минимум112/160 wins vs zero;
- lower-X right distal ниже zero и всех comparators;
- lower-X минимум60/80 wins vs zero;
- lower-X минимум48/80 отдельно vs84V/84S/84R;
- остальные axes ниже zero, минимум70% wins vs zero и не хуже каждого comparator более5%;
- combined ниже84V/84S/84R, zero, shuffled, static и closed;
- обе body-X и camera-Z groups проходят absolute gates;
- минимум12/16 corners, каждая axis минимум7/10 vs zero;
-72-coefficient state неизменен во время0,5s delay.

Thresholds не меняются после результата. Даже near-miss остаётся no-go.

## Audit и claims

128 training candidates audit-сэмплируются для overlap с replication motions. Audit non-exhaustive, если accepted total16 384. Replication остаётся synthetic supervised reconstruction в прежнем generator family и geometry grid. Она не доказывает natural vision, actuators, мышцы, силы, closed-loop correction, биологический мозг или mirror neurons.

## Запуск

После обновления проекта двойным щелчком:

`experiments\RUN-FROZEN-MULTIVARIANT-REPLICATION.bat`

Выбрать завершённую папку84Z `multivariant_ridge_ensemble_...`, не папку84V,84X или84Y. Расчёт только evaluation и должен быть существенно короче training run.

Series85 разблокируется только если full84AA получает strict primary go и результат независимо проверен.
