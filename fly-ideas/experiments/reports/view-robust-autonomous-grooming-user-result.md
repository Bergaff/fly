# Пользовательский результат серии 78: view-robust autonomous grooming

## Происхождение

Пользователь прислал `ИТОГ.txt` и полный текст `summary.json`. Оригинальная result-папка, model NPZ, predictions CSV и checksummed manifest не передавались, поэтому арифметика проверяется по текстовой выписке, но локальные артефакты независимо не перечитываются.

Статус `completed`, режим `long`: 28 801,313 с активного обучения, 44 216 принятых кандидатов, 2 166 584 обучающих кадра. SHA новой модели: `145a07ac8e6f5294f230b57e6c5bee92509d6e95a6d4ab4a684d3adb42f3a90b`.

## Preregistered primary

Primary выполнен.

| Ось | Normal transfer RMSE | Zero RMSE | Wins | Снижение |
|---|---:|---:|---:|---:|
| left proximal | 0,441077 | 0,491699 | 8/10 | 10,30% |
| left middle | 0,364720 | 0,471993 | 8/10 | 22,73% |
| left distal | 0,431939 | 0,448278 | 9/10 | 3,64% |
| right proximal | 0,460296 | 0,506978 | 9/10 | 9,21% |
| right middle | 0,360164 | 0,464444 | 8/10 | 22,45% |
| right distal | 0,432179 | 0,449422 | 9/10 | 3,84% |

Каждая ось имеет pooled RMSE ниже zero и минимум 8/10 wins при требовании 7/10. Combined normal выиграл у zero на 9/10 view-motion combinations.

### Combined pooled

| Условие | RMSE |
|---|---:|
| matched diagnostic | 0,365767 |
| transfer normal | 0,416835 |
| shuffled | 0,456454 |
| zero | 0,472619 |
| static | 0,528253 |
| closed | 1,024248 |

Transfer normal ниже zero на 11,80%, shuffled на 8,68%, static на 21,09% и closed на 59,30%. Все три preregistered controls проиграли normal, поэтому controls-компонент primary также выполнен.

Новый view увеличивает ошибку относительно matched diagnostic на 13,96%. Следовательно, augmentation существенно улучшила перенос по сравнению с серией 76, но не устранила view penalty.

## Временная структура и state

На всех десяти holdout:

- состояние содержит 72 cosine coefficients;
- задержка равна 0,5 с;
- SHA state до и после задержки совпадает;
- replay не использует RGB, teacher или framewise prediction buffer.

Преимущество normal над shuffled умеренное, но согласуется с использованием временного порядка на aggregate уровне. Отдельно test 141 имеет static лучше normal, а test 146 normal хуже zero. Эти заранее включённые тесты остаются в primary.

## Contacts

Mean contact F1 normal/zero: `0,914995/0,906206`, разница только `+0,008789`. Normal лучше на 4/10, а на остальных шести F1 точно равен zero; случаев хуже zero нет.

Поэтому contact result является слабой положительной диагностикой, а не отдельным подтверждением физического grooming. Высокий F1 zero показывает сильную зависимость contact trace от базовой геометрии. Qpos назначается кинематически, без actuators, сил, мышц и closed-loop correction.

## Сравнение с сериями 76–77

Серия 76 показала полный отказ frozen model 75 на FOV/body transformations: transfer RMSE около 1,01 при zero 0,476. Серия 78 после view augmentation получила transfer RMSE 0,417 при zero 0,473 и прошла каждую ось. Это поддерживает причинно ограниченный инженерный вывод: разнообразие synthetic views во время supervised training устранило прежний catastrophic geometric failure в заранее заданном семействе transformations.

Сравнивать абсолютные RMSE серии 78 и серии 77 как парные нельзя: используются другие движения и views. Описательно matched score серии 78 `0,365767` хуже matched series 77 `0,248201`, что указывает на возможный trade-off между специализацией под один ракурс и устойчивостью к геометрии.

## Overlap audit

Аудит охватывает 128 из 44 216 training episodes и не является исчерпывающим. Среди 490 holdout frames:

- `<0,001°`: 0;
- `<1°`: 0;
- `<5°`: 107, или 21,84%, в выбранной выборке.

Это исключает почти точное угловое совпадение с выбранными 128 эпизодами, но не со всей training database и не проверяет идентичность RGB.

## Допустимый вывод

> В пределах заранее заданного synthetic семейства camera/FOV/body transformations view-augmented supervised observer формирует неизменное 72-коэффициентное состояние и после задержки автономно реконструирует наблюдавшееся grooming лучше zero, shuffled, static и closed controls на новых view-motion combinations.

Не поддерживаются утверждения о произвольной view invariance, новом поведении, actuator dynamics, физически устойчивом grooming, биологической памяти, мозге или зеркальных нейронах.

## Рекомендуемый следующий шаг

Не нужен ещё один восьмичасовой прогон того же типа. Следующая проверка должна заморозить модель 78 и без обучения провести дешёвую stress-test сетку по FOV, body shift и camera position. Она должна найти границу устойчивости и проверить новые крайние и комбинированные transformations. Только после этого имеет смысл выбирать между:

1. отдельным representation upgrade, если failure boundary остаётся близко к training range;
2. actuator/closed-loop этапом, если зрительный перенос сохраняется на stress grid.
