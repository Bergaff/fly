# Series103: official FlyGym interbody vision preflight

## Цель

Series101 и frozen Series102 подтвердили fixed physical-adapter viability, но frozen89E получал изображения synthetic renderer, а не кадры официального тела. Перед policy bridge нужен короткий blocking preflight: проверить, что official eye cameras второй `NeuroMechFly` действительно получают изменяющиеся изображения при движении первой official мухи и что эти кадры детерминированно преобразуются в frozen89E-compatible shape.

Это technical bridge, не FlyVis, не Stage97 и не biological result. Frozen89E policy здесь не запускается. Training, model selection и post-result tuning запрещены.

## Закреплённый prerequisite

Series103 runner SHA-256: `33bc95e41032d1f6bc823d626c6ea8c2f80a7135e5c3b8254c656b8400823d11`.

Series102 genuine JSON SHA-256: `33795d582e9ac528304018300dc14c67db066d3452e1760df2bb74c9aef9a643`, status completed, primary pass, scientific_result false.

## Official API и сцена

- FlyGym2.1.1/MuJoCo;
- два `NeuroMechFly` в одном `FlatGroundWorld`;
- observer создаёт камеры через official `add_vision()`;
- изображения читаются только через official `Simulation.get_raw_vision('observer')`;
- official left/right fisheye-corrected RGB детерминированно уменьшаются bilinear resize до96×64;
- 49 кадров с интервалом0,04s;
- demonstrator двигает те же6 front-leg pitch DOF; observer удерживает neutral pose;
- paired neutral episode использует те же тела и observer, но demonstrator не двигается.

Frozen edge-history transform применяется без обучения только как shape/finite compatibility check:49×2×64×96×3 →47×576.

## Primary checks до результата

1. exact FlyGym2.1.1;
2. moving и neutral arrays имеют shape49×2×64×96×3;
3. edge-history arrays имеют shape47×576;
4. RGB/features finite и кадры nonconstant;
5. paired moving-vs-neutral mean absolute RGB delta≥0,05 в uint8 units;
6. paired edge-feature mean absolute delta≥1e-5;
7. demonstrator mapped joint response≥0,03rad;
8. реальные actuator force и observer ground contact ненулевые.

Все восемь checks обязательны. Thresholds являются permissive техническими sanity checks, а не behavioral evidence.

## Windows запуск

После обновления дважды щёлкнуть `experiments/RUN-FLYGYM-INTERBODY-VISION-PREFLIGHT.bat` и нажать одну кнопку. Папки89D/84Z не нужны. GUI показывает общий процент и ETA. Summary, three PNG previews, complete manifest и ошибки сохраняются в copyable файлы и открываются автоматически.

## Допустимый следующий шаг

Только при pass разрешается отдельный frozen official-eye policy bridge с заранее фиксированным preprocessing и controls. Pass не означает, что frozen89E понимает official images, и не подтверждает imitation или biological validity.
