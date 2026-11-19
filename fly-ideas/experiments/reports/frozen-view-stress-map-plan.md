# Серия 79: frozen geometric stress map

## Вопрос

Серия 78 прошла transfer primary, но сохранила view penalty 13,96%; test 146 проиграл zero, а static control был лучше normal на test 141. Серия 79 не обучает модель заново. Она картирует границу устойчивости frozen model 78 на четырёх новых движениях.

## Источник

Пользователь выбирает завершённую папку серии 78. Runner проверяет database checkpoint, `complete.json`, manifest, protocol и SHA `model_new.npz`. До и после расчёта проверяются SHA всех файлов source.

## Новые движения

Holdout `161–164`, seed `7902`: два piecewise5 и два piecewise9. Они не использовались серией 78.

## View grid

Фиксируется до просмотра новых прогнозов:

1. matched reference;
2. one-factor sweeps FOV, camera side, camera height, body X и body Y;
3. все 32 угла training envelope серии 78;
4. все 32 угла evaluation envelope серии 78;
5. две точные конфигурации tests 141 и 146.

Последние две точки явно помечены `posthoc_series78_failure_probe` и исключены из primary. One-factor и outer envelope служат stress diagnostics.

Для каждой view cell и каждого движения сохраняются normal/zero/shuffled/static/closed RMSE, осевые RMSE, доля clipped framewise outputs, RGB SHA, число уникальных кадров, changed RGB, feature variance, 72-coefficient state SHA и покадровые autonomous predictions.

## Primary

Primary использует только 32 `core_corner` training-envelope cells, по четырём новым движениям, всего 128 cases.

Для каждой оси:

- pooled normal ниже zero;
- normal выигрывает минимум 70% cases.

Combined normal должен быть ниже zero, shuffled, static и closed. Кроме того, минимум 24/32 core cells должны отдельно пройти строгую проверку: каждая ось pooled по четырём движениям ниже zero с минимум 3/4 wins, combined normal ниже zero и всех controls.

Matched, one-factor, evaluation-corner, outside-envelope и post-hoc probes не могут улучшить primary.

## Replay

Framewise frozen predictions сжимаются в 72 cosine coefficients. State считается неизменным в течение 0,5 с; replay получает только state и phase. RGB, teacher и framewise prediction buffer после observation недоступны.

## Допустимый вывод

При успехе primary: устойчивость серии 78 распространяется на углы её полного synthetic training hyperrectangle на новых движениях.

Stress-map failure boundary остаётся описательной. Даже успех не доказывает natural view invariance, biological memory, mirror neurons, actuator dynamics или физическое grooming.
