# Серия87: preregistered causal shared-unit lesions

## Роль этапа

Series86 показала operational identity/composition, но корреляция не доказывает причинность. Series87 вмешивается в frozen artificial pathways и проверяет заранее заданный double-dissociation pattern.

Это causal test инженерной системы, не lesion biological neurons.

Pins:

- runner86 SHA `7dc5686028a2fe82d683f091a1f0a08deab25bcc2be41320b5d52e91de6d9714`;
- exact frozen model84Z;
- training запрещён;
- motions421–497 раскрыты и исключены.

## Данные

Calibration-only ranking:

- seed8701;
- motions498–506;
-3 actions ×3 speeds;
- amplitude0,75;
-4 fixed corners.

Blocking lesion evaluation:

-10 independent replicates;
- seeds от870200;
- motions507–536;
-3 actions в каждом replicate;
- held amplitudes0,8/0,9/1,0;
- held speeds0,7/1,0/1,3;
-16 corners;
-480 blocking render cases.

Всего516 renders. Motion hashes проверяются против all training hashes и published holdouts421–497; broad audit128 сохраняется.

## Четыре группы и одинаковый budget

Budget каждой lesion: ровно2 semantic units.

- `shared_selective`: top2 calibration units с correlation>=0,15, ranked по суммарному observation+execution causal impact;
- `observation_only`: top2 semantic feature blocks по calibration recognition-margin impact;
- `execution_only`: top2 proprioceptive channels по calibration execution-replay impact;
- `random_matched`:2 units из не выбранных shared units, fixed seed8704.

Ranking использует только motions498–506. Blocking507–536 не может изменить groups.

Observation-only intervention заменяет mean/std/velocity features выбранных axes на calibration center. Execution-only intervention обнуляет соответствующие proprioceptive channels. Shared/random lesions обнуляют semantic trace channels. Это разные artificial pathway roles с одинаковым semantic-unit budget, а не одинаковые biological cell types.

## Blocking primary

Все gates обязательны.

### Baseline recognition и observation-only effect

- baseline identity минимум20/30;
- baseline не хуже equal-budget private84V более чем на2 cases;
- observation-only lesion уменьшает true-vs-nearest-wrong margin в среднем;
- positive margin loss минимум18/30 motions.

### Shared causal effect

- mean observation-triggered replay degradation shared lesion >1,05× random matched degradation;
- shared degradation больше random минимум18/30 motions.

### Execution-only effect

- execution-lesion mean replay RMSE >1,20× intact execution RMSE;
- lesion ухудшает минимум27/30 motions.

### Double dissociation и collapse guard

- observation-specific recognition effect положителен;
- execution-specific production effect положителен;
- противоположные mode-specific routes неизменны конструкцией;
- shared-lesion observation output остаётся лучше full zero, чтобы общий collapse не считался mirror-specific эффектом.

Near-miss является no-go. Нельзя менять groups, budget, thresholds, actions, motions или corners после результата.

## Экспорт

Summary сохраняет:

- все calibration ranking scores и selected groups;
- per-motion baseline/private/lesion predictions;
- recognition margins;
- shared/random observation replay RMSE;
- intact/shared/execution/random production RMSE;
- aggregate gates;
- state and overlap records.

Это позволяет независимо пересчитать decision из summary, хотя raw RGB и full traces не передаются.

## Запуск

`experiments\RUN-CAUSAL-SHARED-UNIT-LESIONS.bat`

GUI:2/4/6/Максимум workers. Максимум использует все логические процессоры без искусственного резерва памяти. Выберите завершённую production-папку84Z. При ошибке откроется `workspace\runs\ideas\i-observational\causal-shared-unit-lesions\ПОСЛЕДНЯЯ-ОШИБКА-87.txt`.

## Ограничения

- engineered semantic/pathway lesions;
- synthetic action motifs;
- supervised frozen visual decoder;
- нет natural vision;
- нет biological cell mapping;
- kinematic replay, не actuators;
- нет сил, мышц или closed-loop correction;
- даже successful double dissociation не доказывает биологические mirror neurons.
