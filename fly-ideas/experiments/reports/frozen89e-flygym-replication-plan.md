# Series102: frozen89E → official FlyGym frozen replication

## Решение до результата

Series101 прошёл bounded physical-adapter gate. Следующий этап выбран пользователем как независимая frozen-репликация. Series102 не меняет frozen89E, шестиканальный adapter, official MOTOR bridge, controls, thresholds или primary rule после просмотра Series101.

Это не Stage97, не возврат к synthetic optimization и не biological mapping. Training, model selection и post-result tuning запрещены.

## Точные prerequisites

- runner Series102 SHA-256: `612700b5a898d0c3bfa025a4f906de651476a5e08ffecad67d132d1a883c7848`;
- runner Series101 SHA-256: `00063575a7b8f0c23d5bb319ec3776f1ac04c963a069755e2daf4d25e2613a17`;
- genuine Series101 JSON SHA-256: `9577d951090e4104326652a76ce31b387f82e13910cead1c4e2d477d9c3374ea`;
- Series101 result обязан иметь `completed`, `primary.passed=true`, `scientific_result=false`;
- frozen89E, result89D, production84Z и body100 identities проверяются через закреплённый Series101 runner.

## Новые untouched cases

Шесть новых motions создаются до результата:

- IDs897–902;
- seeds102010–102012 и102020–102022;
- actions: foreleg rubbing, head-directed grooming, reach/withdraw;
- amplitudes0,66 и0,98;
- speeds0,68 и1,20.

Четыре новых views805–808 используют заранее записанные FOV33/37°, camera side/z и body x/y. Каждый motion hash проверяется против training/disclosed cases, Series89E и всех Series101 motions. Итого24 новых visual cases.

## Неизменяемый physical adapter

Без изменения Series101:

- шесть synthetic axes → left/right coxa pitch, trochanter-femur pitch, tibia pitch;
- unit gain от official neutral pose, clip±0,35rad;
- остальные36 actuators удерживают neutral pose;
- FlyGym2.1.1, MuJoCo MOTOR, dt0,0005s, frame interval0,04s;
- Kp18, Kd0,18, torque limit25;
- candidate использует q/dq closed-loop feedback;
- true open loop использует тот же candidate target, но torque не использует текущие q/dq.

## Controls и primary rule

Для каждого из24 cases выполняются candidate, zero state, shuffled state, shared lesion и true open loop:120 official FlyGym rollouts.

Frozen primary повторяет Series101 дословно:

1. все24 candidate cases finite, имеют ground contact и thorax z в0,15–2,5mm;
2. mean candidate tracking RMSE≤0,20rad;
3. candidate truth RMSE ниже zero и shuffled минимум в15/24 cases;
4. candidate truth RMSE ниже true open loop минимум в20/24 cases;
5. candidate target hash отличается от zero, shuffled и shared lesion во всех cases.

Shared-lesion wins и action classification сохраняются как secondary diagnostics и не добавляются в primary после результата.

## Windows запуск

После обновления дважды щёлкнуть `experiments/RUN-FROZEN89E-FLYGYM-REPLICATION.bat`. В GUI выбрать те же завершённые result89D и production84Z. Visual phase последовательна для сохранения памяти; Brian2 импортируется в main thread. GUI показывает общий процент и приблизительное оставшееся время. Результат или ошибка автоматически открываются и сохраняются в копируемых файлах.

## Допустимый вывод

Pass означает независимую bounded replication технической viability fixed physical adapter. Fail сохраняется как no-replication без изменения порогов. Ни один исход не подтверждает FlyVis, FlyWire/connectome mapping, мышцы, живую муху, biological mirror neurons или статью.
