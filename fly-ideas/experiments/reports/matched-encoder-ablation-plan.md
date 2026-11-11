# Серия 69: preregistered matched encoder ablation

## Вопрос

Серии 67–68 подтвердили rich модель на 10/10 matched движениях, но серия 67 одновременно изменила training distribution и encoder. Серия 69 проверяет вклад encoder при одном и том же training stream.

## Модели

**Compact:** 24 fixed nonlinear units, projection seed 6601, десять level cosine-компонент, 240 признаков, Adam `240 → 72`.

**Rich:** замороженная успешная модель серии 67, 96 units, level + delta, 1 920 признаков, Adam `1920 → 72`.

Обе используют одинаковые target coefficients, learning rate `0,002`, weight decay `1e-6`, 72-коэффициентное состояние, задержку 0,5 с и cosine replay. Rich модель не переобучается. Compact заново проходит ровно те candidate IDs, RGB scenes и targets, на которых была обучена rich модель. Каждый RGB SHA сравнивается с SQLite серии 67.

## Новая батарея

До compact training закрепляются пять новых random JSON длительностью 2 с и с точками через 0,5 с. Полные движения проверяются против 60 000 training episodes, train/test серии 59 и всех батарей до движений 45 включительно. Движения 31–35 и 41–45 запрещены.

## Primary

Ablation primary пройден, только если одновременно:

1. средняя normal RMSE rich ниже compact;
2. rich лучше compact минимум на 4/5 новых движений;
3. rich повторно проходит temporal primary против zero, static, shuffled и reversed.

Все результаты публикуются независимо от исхода. Для обеих моделей сохраняются normal и temporal controls, осевые метрики и состояния.

## Выполнение

- source: успешная полная серия 67;
- два render worker;
- SQLite checkpoint compact weights и моментов Adam;
- pause/resume через один BAT;
- проверки 4 ГиБ RAM и 2 ГиБ диска;
- модель и папка серии 67 остаются read-only;
- ожидаемая длительность сопоставима с серией 67, поскольку 60 000 сцен рендерятся повторно.

## Ограничения

Rich модель уже дала положительные результаты до формулирования ablation, поэтому сравнение не является полностью наивным открытием. Новая батарея закрепляется до compact training и не используется для настройки. Ablation остаётся synthetic matched опытом и не доказывает биологический механизм или зеркальные нейроны.
