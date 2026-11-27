# Series129 — окончательное временное закрытие направления

## Решение

Направление Series120–129 **закрыто**. Дополнительные короткие или часовые расчёты не требуются. Series130 на другом seed той же synthetic-задачи запрещена stop rule.

Пользовательский `ИТОГ.txt` Series129 сохранён без изменений с SHA-256 `7c6a7362b569fb6bb990db8c9ad3181405957acc50ed315f4a2e3280cb8b49c6`. Он сообщает: completed,1,6 минуты,12 AI cases, Qwen accuracy50%, команда выгрузки модели отправлена. Detailed `summary.json` не был предоставлен, поэтому per-family результаты не восстанавливаются и не выдумываются.

## Главный ответ: в чём эта модель мозга лучше обычных нейросетей

### Что действительно установлено

1. **Интерпретируемость структуры.** Вычисление привязано к61 именованному типу клеток и8 descending channels. Можно показать путь, lesion и вклад конкретной структурной связи. У обычного dense MLP такой биологически именованной декомпозиции по умолчанию нет.
2. **Детерминированная трассируемость.** Frozen graph, SHA-входы и four-hop propagation точно воспроизводятся между Linux и Windows. Изменения topology, weights, labels и lesions дают измеримый контролируемый эффект.
3. **Structural self-consistency.** Series125 показала, что полный four-hop operator нельзя без потерь заменить one-hop, identity, rewired, shuffled, rank-8 или random graph внутри задачи, созданной этим же оператором.

Это преимущества как **интерпретируемого структурного исследовательского объекта**, а не доказанное превосходство по поведению или интеллекту.

### Где обычные модели оказались не хуже или лучше

| Проверка | Результат |
|---|---|
| Series122, узкая routing-задача |9-параметровая diagonal bilinear model дала те же100%, что exact graph computation; parameter-matched MLP дала91,17%. Компактность графа не победила простой специализированный baseline. |
| Series123, temporal closed loop | Graph RMSE `0.205012`; random reservoir `0.204230`; memoryless ridge `0.204197`. Преимущества graph topology нет. |
| Series124, context memory | Graph и random reservoir декодировали late context на100%, но random RMSE `0.216215` был немного лучше graph `0.216240`. Память есть, graph-specific advantage нет. |
| Series126, independent historical FlyGym outcomes | Graph normalized RMSE `0.888083`, практически как raw/rewired/random controls, и хуже constant mean `0.793394`. External behavioral advantage — NO-GO. |

**Итог:** преимущество этой цифровой brain-inspired структуры над обычными linear/MLP/reservoir моделями по accuracy, robustness, memory, latency или compactness **не установлено**.

## Отдельно: специализированный алгоритм против большой AI-модели

Series121 дала на общей узкой numeric routing-задаче:

- exact project solver: `60/60` —100%;
- Qwen2.5:7b: `21/60` —35%.

Series129 low-load run сообщил Qwen50% на12 смешанных cases. Это подтверждает только, что точный специализированный алгоритм эффективнее prompted LLM на собственной формализованной арифметической операции. Это не означает, что мозг мухи лучше Qwen, и не является сравнением общего интеллекта.

## Что можно сказать о настоящем биологическом мозге

Биологический мозг потенциально интересен из-за embodiment, непрерывного online learning, fault tolerance и низкого энергопотребления. Но в этом проекте эти свойства живой мухи не измерялись против искусственных нейросетей. Поэтому нельзя переносить известные свойства животного на цифровую61×61 модель.

Не установлены:

- living-fly energy advantage в общей задаче;
- превосходство обучения или адаптации;
- biological mirror neurons;
- whole-brain reconstruction;
- general intelligence advantage.

## Три окончательных раздельных вывода

1. **Fly digital/engineering:** структура интерпретируема и internally nonredundant, но external behavioral advantage над ordinary neural controls — **NO-GO**.
2. **Cross-animal transfer:** алгоритм переноса реализован; independently validated other species — **0**.
3. **AI comparison:** exact narrow solver лучше Qwen на narrow routing; general-intelligence comparison отсутствует.

## Условия возможного возвращения

Работа может быть открыта снова только при появлении хотя бы одного нового независимого источника:

- same-neuron observation/execution recordings живой мухи;
- causal interventions;
- данные другого животного для проверки transfer;
- заранее обоснованная новая physical target с prospective untouched split.

Новый seed, более длинный запуск Ollama или ещё одна synthetic variation не являются основанием для продолжения.
