# Series101: frozen89E → official FlyGym adapter prototype

## Статус и цель

Series100 прошла9/9 technical body gates. Series101 является новым коротким development adapter prototype. Она не возобновляет Stage91–96, не обучает frozen89E и не открывает biological mapping Series90.

Цель: проверить, сохраняется ли преимущество frozen89E policy после фиксированного преобразования шести synthetic foreleg channels в настоящий MuJoCo motor control двух полных NeuroMechFly.

## Frozen sources

Runner требует локальные неизменяемые:

- production source84Z с model SHA `cb761051…`;
- successful result89D с model SHA `82fbfe15…`;
- repository runner89E SHA `06e41e7…`;
- published frozen89E go extract SHA `fc4d84ff…`;
- Series100 body-go JSON SHA `dea1acc5…`.

Training и model selection запрещены. Используются новые motions891–896 и views801–804, которых не было в Series84–101.

## Фиксированный mapping

Шесть synthetic channels становятся offsets от официальной neutral pose с unit gain и clip ±0,35rad:

1. left proximal → `c_thorax-lf_coxa-pitch`;
2. left middle → `lf_coxa-lf_trochanterfemur-pitch`;
3. left distal → `lf_trochanterfemur-lf_tibia-pitch`;
4. right proximal → `c_thorax-rf_coxa-pitch`;
5. right middle → `rf_coxa-rf_trochanterfemur-pitch`;
6. right distal → `rf_trochanterfemur-rf_tibia-pitch`.

Остальные36 leg actuators удерживают official neutral pose. Mapping, gain и clip нельзя менять после результата Series101.

## Реальный motor control

Обе мухи используют официальный `ActuatorType.MOTOR`, timestep0,0005s, frame interval0,04s, torque limit25, фиксированные gains Kp18/Kd0,18. Demonstrator получает frozen truth только как физическую демонстрационную команду. Observer candidate получает только frozen89E-derived target policy.

True open-loop получает тот же candidate target, но torque вычисляется только из target offset от neutral и target velocity, без текущих q/dq. Closed-loop candidate использует q/dq proprioception.

## Батарея

- 6 новых motions: по2 для foreleg rubbing, head-directed grooming и reach-withdraw;
- 4 новых views;
- 24 frozen visual cases;
- 5 физических условий: candidate, zero state, shuffled state, shared lesion и true open loop;
- всего120 official FlyGym rollouts после одной сборки мира с двумя телами.

## Blocking gate

Development go требует одновременно:

1. все24 candidate cases finite, имеют ground contact и thorax Z0,15–2,5мм;
2. mean candidate command-tracking RMSE ≤0,20rad;
3. candidate truth RMSE лучше zero state минимум15/24;
4. candidate лучше shuffled state минимум15/24;
5. candidate лучше true open loop минимум20/24;
6. target hashes candidate/zero/shuffled/lesion различаются в каждом case.

Shared lesion остаётся обязательным control и логируется, но не имеет blocking direction: Series87 causal effect не был равномерным по всем actions.

Даже полный go означает только работоспособность фиксированного synthetic-to-physical adapter. Он не подтверждает FlyVis, FlyWire, мышцы, живую муху или биологические зеркальные нейроны.

## Windows запуск

После обновления дважды щёлкнуть `experiments/RUN-FROZEN89E-FLYGYM-ADAPTER.bat`, затем выбрать завершённую result-папку89D и production-папку84Z. Окно показывает процент и примерное оставшееся время. Результаты и ошибки сохраняются в файлы; интерактивная консоль не используется.

Первый Windows pre-run с6 spawn workers завершился `BrokenProcessPool` до получения case result: один worker был аварийно завершён без Python traceback. Поскольку bounded visual phase содержит только24 cases, execution зафиксирован в безопасном последовательном режиме в GUI process. Это не меняет motions, views, frozen models, mapping, controls или gate, но не умножает память длинной import-chain и сохраняет настоящий traceback. При ошибке `ПОСЛЕДНЯЯ-ОШИБКА-101.txt` теперь автоматически открывается в Windows.
