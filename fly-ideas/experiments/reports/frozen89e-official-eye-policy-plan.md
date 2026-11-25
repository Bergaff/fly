# Series104: frozen89E policy on official FlyGym observer-eye images

## Решение до результата

Series1038/8 подтвердил official body→observer eyes→96×64→edge-history transport. Series104 впервые подаёт эти official-eye features в неизменённую frozen89E policy и проверяет её выход на official MOTOR body второй мухи.

Training, model selection и post-result tuning запрещены. Это не FlyVis, не Stage97 и не biological mapping.

## Exact prerequisites

- Series104 runner SHA after pre-run length compatibility fix `ace8d99fa0ad71454fa7b4122868547c880817f9b45b9e654fb02245aad298a1`;
- Series102 runner SHA `16309bb094236e861fff6eeb1b4d24ce072d6f7ab55c8f88cd6f12e6d94d7a19`;
- Series103 runner SHA `33bc95e41032d1f6bc823d626c6ea8c2f80a7135e5c3b8254c656b8400823d11`;
- genuine Series103 result SHA `1a13fe460bfb7bfc0af70203465ba42b74ba0809d53672bdad0afb209c6184bf`, primary pass, scientific_result false;
- прежние frozen89E/result89D/source84Z identities проверяются по неизменённой цепочке.

## Новые untouched motions

IDs903–908, actions foreleg rubbing/head-directed grooming/reach-withdraw, seeds104010–104012 и104020–104022, amplitudes0,75/0,88, speeds0,84/1,08. Hashes обязаны отличаться от training/disclosed, Series89E, Series101 и Series102.

## Visual-policy path

Для каждого motion:

1. demonstrator official NeuroMechFly выполняет команду;
2. observer official eyes получают49 fisheye-corrected RGB frames через `get_raw_vision`;
3. bilinear adapter даёт tensor49×2×64×96×3;
4. неизменённый frozen edge-history даёт47×576;
5. неизменённые frozen89E state/readout дают6-axis target;
6. target управляет6 front-leg pitch DOF observer через тот же MOTOR bridge Series101/102;
7. truth — actual mapped trajectory demonstrator, измеренная во время visual capture, без первых двух history frames.

## Controls

Для каждого из6 cases выполняются7 physical conditions,42 rollouts:

- candidate: moving official-eye images;
- neutral_visual: official-eye images neutral demonstrator;
- reversed_visual: moving official-eye sequence в обратном времени;
- zero_state;
- shuffled_state;
- shared_lesion;
- true open_loop: candidate target без текущих q/dq.

Candidate/open-loop target hashes одинаковы. Visual/state control hashes обязаны отличаться.

## Frozen primary rule

1. все6 candidate cases finite/contact и thorax z0,15–2,5mm;
2. mean candidate tracking RMSE≤0,20rad;
3. action classification correct≥4/6;
4. candidate truth RMSE выигрывает≥4/6 против neutral visual, reversed visual, zero state и shuffled state;
5. candidate выигрывает≥5/6 против true open loop;
6. candidate target отличается от neutral/reversed/zero/shuffled/shared-lesion во всех cases.

Shared-lesion wins логируются, но не добавляются в primary после результата.

## Windows запуск

После обновления дважды щёлкнуть `experiments/RUN-FROZEN89E-OFFICIAL-EYE-POLICY.bat`, выбрать те же завершённые result89D и production84Z. GUI показывает общий процент/ETA, error/result открываются автоматически. Visual capture последовательна; Brian2 импортируется в main thread.

Первый genuine pre-run остановился во время первого case до сохранения metrics/result: новые motions содержат51 raw frames и дают49 policy frames после history offset, а neutral-visual control был ошибочно создан из49 raw frames и дал47 policy frames. Это вызвало shape mismatch47×6 vs49×6. Никаких summary/outcome не было просмотрено. Compatibility fix выводит neutral raw-frame count из exact frozen motion (`len(items[0].angles_deg)`), поэтому candidate, neutral, reversed и truth имеют одинаковые49 policy frames. Motions, images, model, targets, controls, thresholds и primary rule не меняются.

## Допустимый вывод

Pass означает только bounded engineering viability frozen policy на official-eye domain. Fail означает domain-transfer no-go при неизменённом adapter; thresholds не ослабляются. Ни один исход не подтверждает FlyVis/FlyWire/connectome mapping, biological vision, мышцы, живую муху или mirror neurons.
