# Серия 84: пользовательский результат frozen lower-body-X stress map

## Статус и проверенный источник

Пользователь прислал завершённый `summary-8.json`. SHA-256:

`7f187bed6f60d3136d21635bbfa84817fc3a00bb1d26118f16b5a83bb2fe2e11`

Schema `frozen-lower-bodyx-stress-map-result-v1`, status `completed`, mode `full`. В summary находятся 432 уникальных новых cases: motions 281–286 × 72 cells, а также 36 exact reproduction probes серии 83.

SHA runner84 в summary `0bbf0ef1d46a0896580b0fb887c26031fc6e6e4c96346dd87c03b14cc1093c40` точно совпадает с опубликованным runner. Закреплённый runner83 также совпадает: `dac7ea443081aad92faed5c0986066a617fcd2e61735b9292d1979dc6a8fb931`. SHA frozen model83 совпадает с серией 83: `79ad0b29f904067d3b8ece3e81a395d66606ab7202015d5c47b254bfa484a9fd`. Protocol отмечает `no_retraining=true`.

Полная локальная папка с `complete.json`, NPZ и source83 не передавалась. Поэтому проверены присланный JSON, его внутренние записи и совпадение закреплённых SHA, но не файловый manifest на компьютере пользователя.

## Preregistered decision

`primary.passed = false`. Серия 85 остаётся заблокированной.

Blocking failures:

1. pooled left distal: `67/96` wins при требовании минимум `68/96`;
2. safeguard body X=3,82, left distal: `32/48` при требовании `34/48`;
3. uniform core-cell gate: только `2/16` при требовании `12/16`.

Третий пункт является большим, а не пограничным отказом. Нельзя ослаблять порог, округлять 67/96 до 70%, выбирать только удачные X или camera Z post hoc.

## Primary: 96 новых core cases

| Ось | Normal | Zero | Wins | Gate |
|---|---:|---:|---:|---|
| left proximal | 0,298313 | 0,426671 | 80/96 | pass |
| left middle | 0,124521 | 0,371607 | 92/96 | pass |
| left distal | 0,437558 | 0,456415 | 67/96 | **fail** |
| right proximal | 0,267855 | 0,398760 | 80/96 | pass |
| right middle | 0,137033 | 0,381177 | 90/96 | pass |
| right distal | 0,424654 | 0,446071 | 69/96 | pass |

Combined normal/zero: `0,307356 / 0,414676`, то есть normal ниже zero на 25,88%. Combined normal также ниже pooled controls:

- shuffled `0,407980`;
- static `0,438428`;
- closed `0,454613`.

Это подтверждает полезный зрительный сигнал в среднем, но combined metric не может компенсировать distal consistency failures.

Distal улучшение остаётся малым:

- left: 4,13% ниже zero;
- right: 4,80% ниже zero.

## Safeguard body X=3,82

Пять осей прошли. Left distal имеет normal/zero `0,437902 / 0,456415`, но только `32/48` wins вместо 34. Right distal прошла точно по порогу: `34/48`, normal/zero `0,425324 / 0,446071`.

Следовательно, исходная lower-body-X проблема не устранена uniform образом. При этом она больше не сводится только к right distal из серии 83: на новых motions blocking осью стала left distal.

## Core-cell gate

Прошли только cells 22 и 54, одинаковая geometry combination при двух core X:

- camera side `0,42`;
- camera Z `0,36`;
- body Y `+0,32`;
- body X соответственно `3,82` и `4,18`.

Остальные 14/16 core cells провалены по motion consistency distal axes. Pooled normal в failed cells обычно остаётся ниже zero; причина состоит в 3–4 wins из 6 вместо требуемых 5/6.

По всем 72 cells:

- прошло 9/72;
- left distal cell gate прошла в 12/72;
- right distal в 22/72;
- proximal/middle прошли в 67–72/72;
- ни одна из 36 cells с camera Z=0,56 не прошла;
- при camera Z=0,36 прошло 9/36.

Связь с camera Z является post hoc диагностическим наблюдением, а не новым preregistered causal result. Она показывает, что простой выбор body X не создаёт устойчивую область.

## Body-X boundary map

| Body X | Combined gain vs zero | Left distal gain; wins | Right distal gain; wins | Cells passed |
|---:|---:|---:|---:|---:|
| 3,70 | 20,96% | −0,93%; 21/48 | −0,93%; 23/48 | 0/8 |
| 3,76 | 24,33% | 2,16%; 27/48 | 2,63%; 33/48 | 0/8 |
| 3,82 | 26,61% | 4,06%; 32/48 | 4,65%; 34/48 | 1/8 |
| 3,88 | 28,24% | 5,15%; 34/48 | 5,94%; 35/48 | 3/8 |
| 4,00 | 28,30% | 5,12%; 33/48 | 5,93%; 34/48 | 1/8 |
| 4,12 | 25,36% | 4,52%; 32/48 | 5,27%; 33/48 | 0/8 |
| 4,18 | 25,16% | 4,21%; 35/48 | 4,95%; 35/48 | 1/8 |
| 4,24 | 23,08% | 4,08%; 32/48 | 4,84%; 38/48 | 2/8 |
| 4,30 | 19,95% | 3,61%; 27/48 | 4,36%; 35/48 | 1/8 |

На X=3,70 обе distal axes хуже zero pooled. Лучший combined диапазон находится около 3,88–4,00, но даже там проходят только 3/8 и 1/8 cells. Поэтому нельзя заменить protocol одним «лучшим» X и объявить проблему решённой.

## Motion consistency

Новые движения различаются по тому, какие оси они поддерживают:

- motion 281 выигрывает distal во всех 16 core cells, но проигрывает обе proximal во всех 16;
- motion 284 выигрывает все шесть осей во всех 16;
- motion 286 выигрывает left distal только в 3/16 и right distal в 1/16;
- motion 282 выигрывает left/right distal только в 6/16 и 7/16.

Это не позволяет честно исключить motion 286 или сменить family post hoc. Картина указывает на motion-dependent representation/estimation, а не на единственную body-X boundary.

## Controls, state и reproduction

По всем 432 новым cases normal combined лучше:

- zero: 432/432;
- shuffled: 431/432;
- static: 410/432;
- closed: 393/432.

Во всех 432/432 cases состояние содержит 72 коэффициента и имеет одинаковый SHA до и после задержки 0,5 с. Пустых RGB cases нет; минимум changed RGB values равен 24 023; максимальная доля clipping normal равна 0,02381.

Все 36/36 exact failed probes серии 83 совпали по normal metrics и state SHA. Это подтверждает frozen reproduction и отсутствие скрытой смены модели, но старые probes диагностические и не входят в primary.

## Научное решение

1. Серия 84 является строгим no-go для перехода к серии 85.
2. Не повторять frozen sweep, не выбирать удачные cells и не ослаблять 5/6 или 12/16.
3. Простая коррекция body X недостаточна: failures сохраняются по всему диапазону и сильно зависят от distal axis, motion и camera Z.
4. Следующая допустимая работа должна быть заранее зарегистрированным изменением representation/training objective для устойчивости distal across motions и geometry, с новыми holdouts и отдельной frozen replication. Это будет новая модель, а не переименование model83.
5. Shared observation/execution population остаётся заблокированной до uniform six-axis go новой модели.

## Ограничения claims

Это synthetic supervised fixed-FOV reconstruction одной geometry family. Результат не демонстрирует новое действие, actuator dynamics, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
