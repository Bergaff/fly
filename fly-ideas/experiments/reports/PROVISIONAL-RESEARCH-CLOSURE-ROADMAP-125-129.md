# План временного завершения исследования — Series125–129

Цель — не бесконечно добавлять synthetic-тесты, а получить один из двух честных финалов: воспроизведённое инженерное преимущество на независимой behavioral/physical цели или документированный NO-GO с замороженными границами утверждений.

## Series125 — structural self-consistency

**Статус: завершена, PASS в узком смысле.** Проверить, что четыре прохода exact61×61 нельзя без потерь заменить one-hop, rewired/shuffled/permuted/random/rank-8 controls. Этот результат проверяет реализацию и nonredundancy структуры только относительно её собственного оператора. Он не считается внешним преимуществом.

## Series126 — independent behavioral target development

**Статус: завершена и независимо воспроизведена, NO-GO.** Использована цель, которая **не вычислена из61×61 графа**: пять historical official-FlyGym outcomes из Series106/109/112. На заранее разделённом fit/development и historical audit сравнены Graph Core, matched random graph, rewired graph, raw/metadata linear, random-feature MLP и constant mean.

Graph normalized RMSE `0.888083` практически совпал с raw/rewired/random controls и хуже constant mean `0.793394`. Заранее заданное улучшение минимум5% против каждого learned control не достигнуто. Пользовательский Windows-запуск воспроизвёл метрики с максимальным platform floating-point отличием `8.82e-10` и тот же gate. Поэтому engineering gate — **NO-GO**, Series127/128 не авторизованы. Series112 честно обозначена как ранее просмотренный historical audit, а не новый untouched final. Подробности: `INDEPENDENT-PHYSICAL-OUTCOME-DEVELOPMENT-126.md`.

## Series127 — untouched digital replication

**Статус: не авторизована локальным NO-GO Series126.** По исходному условному протоколу только если Series126 GO: заморозить architecture, mapping, gains, thresholds and seeds. Проверить новые motions, contexts, delays, viewpoints and perturbations без переобучения. Нужны paired confidence intervals и per-case exports, а не только средние.

Gate: graph advantage воспроизводится на untouched наборе и проходит shuffled/rewired/lesion controls. Иначе финальный NO-GO.

## Series128 — official FlyGym/NeuroMechFly physical replication

**Статус: не авторизована; нового physical run не было.** Только если Series127 GO: перенести **замороженный** новый controller в official FlyGym/MuJoCo. Сравнить на одном теле и одинаковых disturbances с matched random, MLP, zero/open-loop and lesion controls. Проверить contacts, support, joint limits, torque/energy, recovery and repeatability. Отдельный новый seed/run должен воспроизвести результат.

Даже PASS означает только bounded engineering controller evidence, не живые нейроны и не whole-brain model.

## Series129 — final audit and temporary closure

**Статус: завершена; направление временно закрыто.** Пользовательский low-load итог: completed за1,6 минуты,12 AI cases, Qwen accuracy50%, запрос выгрузки модели выполнен. Detailed summary не предоставлен, поэтому per-family значения не реконструируются. Immutable closure фиксирует: graph лучше ordinary neural controls только по интерпретируемой структурной трассируемости; behavioral, compactness и general-intelligence advantage не установлены. Series127/128 не авторизованы, Series130 с новым seed запрещена.

Собрать один immutable manifest: все runner/result SHA, platform differences, GO/NO-GO, failed series, exact claims and forbidden claims. Зафиксировать три отдельных финала:

1. **Fly digital/engineering:** GO только если Series126–128 прошли; иначе NO-GO с сохранённой structural self-consistency Series125.
2. **Cross-animal transfer:** algorithm exists, validated other species count remains0 unless independent target-animal data appear.
3. **AI comparison:** narrow solver benchmarks only; no general-intelligence ranking.

Биологический вывод остаётся отдельным: живые mirror neurons не установлены без independent same-neuron observation/execution recordings and causal interventions. Это не блокирует временное инженерное завершение, но запрещает biological claim.

## Stop rules

- Не создавать Series130 только ради улучшения уже просмотренного final.
- После любого final NO-GO возвращаться можно лишь с новым независимым dataset/animal recording или заранее обоснованной новой physical target, а не с новым seed той же синтетики.
- Не переносить PASS старого frozen FlyGym adapter на новый Graph controller автоматически.
- Не считать self-generated graph target независимым доказательством графа.

После Series129 исследование считается временно завершённым и воспроизводимо упакованным до появления новых независимых данных.
