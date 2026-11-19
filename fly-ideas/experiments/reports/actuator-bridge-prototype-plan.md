# Серия88: preregistration actuator bridge prototype

## Решение до запуска

Series87 завершена causal operational go. Series88 разрешена как отдельный actuator prototype. Никакие thresholds ниже нельзя менять после production result. Near-miss является no-go.

## Frozen identities и данные

- runner87 SHA-256 `105f0c26e0b9fd5e0fa9a6060af48fe4fa900da09ff5e906116da1d12d7caa54`;
- published go87 extract SHA-256 `f30a118a72e450cbe76024c74ff32764b8f545f41b3ecc6b3957f9fd0a6faf6f`;
- source result SHA-256 `033a2fc502c99bfca0b17adee53386bfb9f7fdab989b14a04d6394f2e1c27fa6`;
- frozen selected model84Z загружается read-only;
- training запрещён;
- motions421–536 раскрыты и исключены.

Новая blocking battery: motions537–566, 10 replicates каждого из трёх actions, все16 geometry corners, всего480 independent visual-actuator cases. Fixture не является научным результатом.

## Intervention

Observer формирует six-axis trace. Он немедленно сжимается прежним frozen 72-coefficient replay codec и декодируется в target policy. Actuator rollout получает только target policy и seed. Его API не принимает teacher trajectory, RGB или framewise observer buffer.

Шесть ограниченных joint plants имеют:

- timestep0,004с и policy frame0,04с;
- joint limits ±55°;
- torque limit0,35 условных единиц;
- inertia и viscous damping;
- proprioceptive feedback `q,dq`;
- два geometric contact-proxy channels и distal contact correction;
- bounded support/tilt surrogate;
- hard limit handling.

Closed-loop сравнивается с preregistered open-loop controller на той же target policy, initial perturbation и limits. Truth используется только после rollout для diagnostic task RMSE, не controller.

## Primary gate

Все условия обязательны:

1. Во всех cases нет NaN/Inf.
2. Во всех cases нет sample joint-limit violations.
3. Во всех cases max tilt ≤0,25rad и minimum body-z surrogate ≥0,30.
4. Во всех cases torque ≤0,35 и absolute-work energy ≤4,0.
5. Mean closed-loop target tracking RMSE ≤0,12rad.
6. Mean closed-loop tracking RMSE <0,80 open-loop RMSE.
7. Closed-loop лучше open-loop минимум в90% cases, то есть432/480.
8. Bout completion ratio ≥0,65 минимум в432/480 cases.

`primary.passed=true` разрешает только отдельную preregistered series89 embodied validation. Любой failure блокирует series89 до нового заранее описанного engineering intervention.

## Выход

`summary.json` сохраняет protocol, primary, все480 case metrics, hashes и limitations. Каждый case сохраняется отдельно. Source84Z hashes проверяются до/после, result защищён manifest. Ошибка автоматически записывается в копируемый UTF-8 BOM `ПОСЛЕДНЯЯ-ОШИБКА-88.txt`.

## Ограничения claim

Это reduced six-joint actuator/support surrogate, а не FlyGym, мышцы или полноценное свободно стоящее тело мухи. Contact является engineered geometric proxy, не collision force. Target реконструирует наблюдённый synthetic action и не является изобретением нового действия. Natural vision, biological neurons и reviewed biological mapping отсутствуют. Даже полный go88 не является series89 closed-loop embodied validation.
