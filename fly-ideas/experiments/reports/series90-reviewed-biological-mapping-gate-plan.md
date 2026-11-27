# Серия90: reviewed biological mapping gate

## Роль серии

Это заключительный этап roadmap82–90 и bounded-аудит доказательств, а не ещё один подбор модели. Он разрешён только после independently verified frozen89E go. Закрытый gate является допустимым и заранее предусмотренным научным результатом.

## Вопрос

Существует ли на закреплённых версиях источников полная проверяемая цепь для действий89E:

`official FlyVis activity → reviewed type-to-FlyWire root IDs → fixed activity-to-rate rule → Shiu/FlyWire causal propagation → preregistered descending/motor readout → official FlyGym body`?

## Закреплённые источники

- frozen89E extract `fc4d84ff…`, исходный summary `c2608558…`;
- FlyVis commit `92b3845…` от 2026-08-06;
- Shiu model commit `91bdd1e…` от 2024-09-14;
- FlyGym commit `3c8ce5e…` от 2026-08-24;
- локальные протоколы70/71 `601d85a7…` / `485d6a17…`.

Source audit с cutoff 2026-09-18: `series90-reviewed-mapping-source-audit.json`, SHA `ceb7ab4a…`.

## Обязательные gates

Все9 должны быть true без post-hoc замены:

1. frozen89E functional prerequisite;
2. official FlyVis activity;
3. externally reviewed FlyVis-type→FlyWire-ID mapping;
4. fixed activity→rate rule;
5. Shiu/FlyWire simulation and lesions;
6. preregistered descending/motor readout для трёх действий;
7. mapping permutation and lesion controls;
8. official FlyGym body API;
9. validated end-to-end action chain.

Отсутствие mapping/readout нельзя заполнять exact-name matching, выбранными после результата DNs, ручными gains или обученным на целевом результате adapter. Если хотя бы один gate false, решение `mapping_gate_closed`, full-chain run запрещён.

## Заранее установленный текущий исход аудита

Аудит official sources, доступных не позднее cutoff 2026-09-18, обнаружил отдельные компоненты и возможность controls, но не обнаружил независимо reviewed mapping и validated motor readout для трёх действий89E. FlyVis не содержит FlyWire root-ID mapping; Shiu не содержит этого visual bridge и action readout; FlyGym предоставляет generic brain-to-VNC interface, но не Shiu-specific reviewed readout.

Поэтому текущая series90 должна завершиться `mapping_gate_closed`. Это не вычислительный no-go89C и не отмена frozen89E:89E остаётся функциональным synthetic go, а90 ограничивает биологическую интерпретацию.

## Разрешённый вывод

Серии82–89E поддерживают функциональный synthetic mirror-like surrogate: наблюдение связано с внутренним состоянием, задержанным автономным воспроизведением, causal digital lesions, actuator bridge и frozen replication. Это основание говорить о **функциональном цифровом аналоге зеркального механизма в пределах модели**.

## Запрещённый вывод

Нельзя заявлять обнаружение или доказательство биологических зеркальных нейронов, natural vision-to-action pathway, muscle-level control или причинность у живой мухи. Для такого шага нужны новые independently reviewed mappings/readouts, biological recordings/interventions и новый preregistration за пределами series90.
