# Серия88: пользовательский результат actuator bridge prototype

## Статус

Пользователь прислал `summary-22.json`, SHA-256:

`94fac84c12fb0049aada2dd5b04ac84da30d63808e6d0a45cd09d0c731780feb`.

Schema `actuator-bridge-prototype-result-v1`, status `completed`. Exact runner88 SHA `888778dd5771f740e142747f0bad2eb1cadff8147bf01c6b2fe480c6952daa30`, runner87, go87 extract и selected model84Z identities совпадают. Training false. Ровно480 unique `(motion, corner)` cases: motions537–566,10 replicates ×3 actions ×16 corners.

`primary.passed = true`. Все preregistered finite, joint-limit, support-stability, torque/energy, tracking, closed-vs-open и completion gates прошли. Это actuator bridge prototype go88. Отдельная preregistered series89 теперь разрешена.

## Независимая проверка

Из480 exported case metrics независимо пересчитаны:

- отсутствие NaN и limit violations;
- support tilt/body-z thresholds;
- torque и energy thresholds;
- mean closed/open tracking RMSE;
-480 paired closed-vs-open comparisons;
- completion count и aggregate primary logic;
- coverage30 motions ×16 corners;
- immutable72-coefficient state markers и forbidden-access flags.

Все пересчитанные значения точно совпали с reported primary. Сам actuator trajectory и torque time series не экспортированы, поэтому numerical integration нельзя независимо повторить из summary. Проверяется агрегирование runner-exported metrics, а не повторная симуляция dynamics.

## Primary

| Gate | Результат | Порог |
|---|---:|---:|
| Finite | pass480/480 | все |
| Joint limits | pass480/480 | все |
| Support stability | pass480/480 | все |
| Bounded torque/energy | pass480/480 | все |
| Closed-loop tracking RMSE |0,053664rad|≤0,12rad|
| Open-loop tracking RMSE |0,367405rad|closed <80% open|
| Closed лучше open |480/480|≥432/480|
| Completed bouts |479/480|≥432/480|

Closed-loop tracking RMSE равна примерно14,61% open-loop. Абсолютная разница около0,313740rad.

## По действиям

| Action | Cases | Closed RMSE | Open RMSE | Wins | Completed | Output-vs-truth RMSE |
|---|---:|---:|---:|---:|---:|---:|
| foreleg rubbing |160|0,066208|0,426336|160/160|160/160|0,295614|
| head-directed grooming |160|0,068288|0,380541|160/160|160/160|0,463626|
| reach/withdraw |160|0,026497|0,295337|160/160|159/160|0,287572|

Единственный case с completion ratio ниже0,65: motion545, corner1, reach/withdraw, ratio0,612245. Его target tracking RMSE0,018344rad, поэтому это не tracking failure; decoded target просто находился выше activity threshold меньше65% frames.

## Safety diagnostics

- total NaN count:0;
- total limit violations:0;
- max tilt:0,001002rad при пороге0,25;
- minimum body-z surrogate:0,393908 при пороге0,30;
- max torque:0,35, ровно hard limit;
- max energy:1,714266 при пороге4,0;
- unique target-policy hashes:480/480;
- state coefficients:72 во всех480 cases;
- state before/after delay совпадает480/480;
- teacher/RGB/framewise-buffer access flags false480/480.

## Важная интерпретация

Go88 показывает, что reduced bounded actuator plant устойчиво отслеживает frozen observer-derived target policy и closed-loop controller существенно превосходит заранее заданный open-loop comparator. Он не показывает столь же высокую точность относительно истинного движения.

Mean output-vs-truth RMSE по actions находится примерно от0,288 до0,464rad; особенно высока ошибка head-directed grooming0,463626rad. Primary намеренно проверял actuator tracking target policy, а не embodied task accuracy. Поэтому результат разрешает series89, но не заменяет её.

Также support stability имеет очень большой запас, но это engineered support surrogate. Max tilt около0,001rad не является доказательством устойчивости полноценной свободно стоящей мухи.

## Ограничения claim

- reduced six-joint actuator/support surrogate, не FlyGym и не complete body;
- geometric contact proxy, не collision force;
- мышцы и biological actuation отсутствуют;
- target policy реконструирует наблюдённое synthetic действие, а не изобретает новое;
- visual target error остаётся значительной;
- natural vision и biological neurons отсутствуют;
- exported summary не содержит trajectory/torque time series для независимого повторения integration.

## Следующий допустимый шаг

Series89: отдельно preregistered closed-loop embodied validation на новых motions/initial conditions/view shifts. Она должна включать normal, zero-state, shuffled-state, open-loop и lesion controls; angle, contact, stability, effort и recovery metrics. Motions421–566 теперь раскрыты и запрещены для нового blocking selection/evaluation.
