# Серия89: preregistration closed-loop surrogate embodied validation

## Решение до запуска

Series88 завершена actuator bridge prototype go. Series89 разрешена отдельно. Thresholds ниже нельзя менять после production result; near-miss является no-go.

## Frozen identities

- runner88 SHA-256 `888778dd5771f740e142747f0bad2eb1cadff8147bf01c6b2fe480c6952daa30`;
- published go88 extract SHA-256 `baa175ce7af1b20e7f37d9e24d3fb804620276b5f4073be6a15bd4a6ddd8e6e1`;
- source result SHA-256 `94fac84c12fb0049aada2dd5b04ac84da30d63808e6d0a45cd09d0c731780feb`;
- frozen selected model84Z read-only;
- training запрещён;
- motions421–566 раскрыты и исключены.

## Blocking battery

-36 новых motions567–602:12 replicates каждого из3 actions;
-12 preregistered interior view shifts IDs101–112;
-432 visual cases;
-3 initial profiles: neutral, pose offset, velocity offset;
-1296 embodied trials;
-в каждом trial одинаковый bounded mid-bout disturbance для paired controls.

Fixture не является научным результатом.

## Conditions

Каждый observer output сжимается в frozen72-coefficient state. Rollout не получает RGB или framewise observer buffer.

- `normal`: decoded state, proprioception/contact closed loop;
- `zero_state`: zero72-state;
- `shuffled_state`: fixed axis permutation и coefficient phase roll;
- `open_loop`: normal target без proprioception/contact feedback;
- `shared_lesion`: zero left-proximal/left-middle coefficient blocks, выбранных series87.

Truth trajectory не участвует в integration/controller и используется только после rollout для angle/contact evaluation.

## Metrics

- angle RMSE относительно truth;
- continuous geometric contact-proxy MAE относительно truth;
- finite values и joint limits;
- max torque и absolute-work effort;
- support tilt и minimum body-z;
- completion ratio;
- recovery после окончания disturbance.

## Primary gate

Всего1296 normal trials, required1167 (90%). Все условия обязательны:

1. Safety: все1296 normal trials имеют finite output,0 limit violations, torque≤0,35, energy≤4, tilt≤0,25rad и body-z≥0,30.
2. Recovery≤0,40с минимум в1167/1296.
3. Completion ratio≥0,65 минимум в1167/1296.
4. Normal angle RMSE ниже каждого из zero-state, shuffled-state, open-loop и shared-lesion минимум в1167 paired trials для каждого control.
5. Normal contact-proxy MAE ниже минимум трёх из четырёх controls; каждый засчитанный control должен иметь минимум1167 paired wins.

Series90 разрешается только при `primary.passed=true`, но как reviewed mapping gate, а не гарантированное завершение проекта.

## Выход и ошибки

`summary.json` сохраняет protocol, primary и все case/trial/control metrics. Source84Z проверяется до/после, result защищён manifest. Ошибка автоматически сохраняется в копируемый UTF-8 BOM `ПОСЛЕДНЯЯ-ОШИБКА-89.txt` и открывается без копирования консоли.

## Ограничения claim

Это closed-loop validation reduced six-joint actuator/support surrogate, не FlyGym, мышцы и не полноценное свободно стоящее тело. Contact является engineered geometric proxy, не collision force. State и controls искусственные; natural vision, novel action invention и biological neurons отсутствуют. Даже полный go89 означает только functional surrogate evidence и не доказывает biological mirror neurons.
