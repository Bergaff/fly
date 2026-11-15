# Пользовательский результат серии 81: raw + gated canonical multiscale

## Происхождение

Пользователь приложил оригинальный `summary-3.json`, SHA-256 `ef7e8b70532c6a6a7d87d44ffd7e0c7efd590e848bb36be01349b320238e3f08`. Статус `completed`, 320 training episodes и 96 evaluation cases на той же инженерной батарее, что серия 80. Runner 78 SHA совпадает. Это prototype с `scientific_result=false`; NPZ, predictions и manifest независимо не получены.

## Blocking decision

`Go for long training: НЕТ.` Long run с этим representation не разрешён.

Combined:

- raw `0,429705`;
- multiscale `0,426049`;
- zero `0,480002`;
- multiscale лучше raw на `0,85%`.

FOV safeguards прошли:

- FOV30 raw/multiscale `0,401454/0,400977`;
- FOV70 `0,456210/0,449725`.

Gating устранил крупный вред replacement canonicalization при FOV30 и сохранил часть преимущества при FOV70. Но all-outer criterion выполнен только в `4/16` held corners при требовании `12/16`.

## Оси

| Ось | Raw | Multiscale | Zero | Wins | Итог |
|---|---:|---:|---:|---:|---|
| left proximal | 0,430527 | 0,427780 | 0,447221 | 60/96 | pass |
| left middle | 0,372480 | 0,361397 | 0,513068 | 66/96 | pass |
| left distal | 0,481310 | 0,482134 | 0,483956 | 45/96 | fail |
| right proximal | 0,448700 | 0,446720 | 0,463412 | 62/96 | pass |
| right middle | 0,371829 | 0,359784 | 0,506893 | 65/96 | pass |
| right distal | 0,461014 | 0,462651 | 0,461805 | 40/96 | fail |

В отличие от серии 80 proximal теперь проходят. Middle улучшаются примерно на 3%. Но distal ухудшаются против raw; right distal также немного хуже zero. Поскольку шесть выходов ridge решаются независимо, это не простой trade-off общего loss между суставами: добавленное представление само по себе не даёт устойчивой информации для distal.

## Работа gate

### Ноль допустимых canonical eyes

- 48 cases, все FOV30;
- raw/multiscale `0,401454/0,400977`;
- 25/48 combined wins.

Canonical channels полностью отключены, поэтому multiscale почти воспроизводит raw и больше не наносит ущерб узкому FOV. Небольшая разница остаётся из-за совместного обучения multiscale weights и validity flags.

### Два допустимых canonical eyes

- 42 cases;
- raw/multiscale `0,457295/0,449862`;
- 31/42 combined wins.

Canonical scale полезен, когда объект полностью видим.

### Один допустимый глаз

- 6 cases;
- raw/multiscale `0,448541/0,448770`;
- 4/6 wins, но pooled чуть хуже.

Gate технически работает по назначению, однако improvement остаётся в основном combined/proximal/middle, не distal.

## Corner structure

All-outer pass: cells 3, 10, 12 и 14. Серия 80 имела 5/16, но набор прошедших cells изменился. На большинстве FOV70 cells proximal улучшаются, тогда как distal часто остаются хуже. Cells 11, 13, 15 и 16 демонстрируют характерный паттерн: proximal pass, distal fail.

Таким образом, проблема больше не сводится к crop border. После исправления border режима осталась ограниченная видимость/разрешимость distal segments в текущих 48×32 features.

## Вывод

Поддерживается:

> Image-derived gate успешно предотвращает вред canonical crop при FOV30 и использует canonical channel при полностью видимом объекте.

Не поддерживается:

> Raw + gated canonical representation достаточно для стабильного улучшения всех outer joints.

Повторять этот подход в восьмичасовом run нельзя.

## Следующий шаг

Не следует добавлять ещё один вариант того же crop. Следующая короткая проверка должна адресовать spatial resolution distal segments:

1. сравнить текущий 48×32 baseline с 96×64 observation;
2. сохранить более плотную spatial tiling для high-resolution representation;
3. использовать тот же balanced stream, но заранее закрепить отдельный distal gate;
4. требовать улучшения обеих distal axes против standard-resolution baseline и zero;
5. сохранить proximal/middle safeguards;
6. не запускать long training до прохождения проверки.

Это проверит гипотезу о недостаточном разрешении, а не продолжит подбирать crop по просмотренной батарее.
