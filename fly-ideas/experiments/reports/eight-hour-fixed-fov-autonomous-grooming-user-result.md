# Серия 83: пользовательский результат восьмичасового fixed-FOV35 обучения

## Статус и источник

Пользователь прислал завершённый `summary-7.json`. SHA-256 исходного файла:

`0c0e321728a291eb70c942ea541203e8719812ed7b144bfd572522d3485c1540`

Schema `eight-hour-fixed-fov-autonomous-grooming-result-v1`, status `completed`, protocol mode `long`. Summary содержит 160 cases: motions 261–270 × 16 corners.

Активное обучение: `28 800,891` с. Сгенерировано и принято 18 686 candidates, 915 614 training frames. SHA сохранённой модели по summary: `79ad0b29f904067d3b8ece3e81a395d66606ab7202015d5c47b254bfa484a9fd`.

Полная папка результата, SQLite, NPZ, protocol/complete manifests и predictions не передавались. Поэтому SHA модели и точное соответствие локальному runner независимо не проверены; проверены присланный JSON, его 160 records и внутренние агрегаты.

## Preregistered decision

`primary.passed = false`.

Единственная проваленная составная часть: corner gate `10/16` при требовании `12/16`. Все остальные blocking части прошли:

- все шесть pooled axis gates;
- combined ниже zero и всех трёх controls;
- combined wins `160/160` против zero;
- body X=4,18 safeguard для всех шести осей;
- immutable 72-state во всех 160 cases.

Primary нельзя переименовывать в успех, несмотря на сильные pooled результаты.

## Pooled результаты

| Ось | Normal | Zero | Wins | Gate |
|---|---:|---:|---:|---|
| left proximal | 0,346086 | 0,477476 | 160/160 | pass |
| left middle | 0,166504 | 0,421724 | 160/160 | pass |
| left distal | 0,418300 | 0,440806 | 129/160 | pass |
| right proximal | 0,374185 | 0,512151 | 160/160 | pass |
| right middle | 0,173478 | 0,422748 | 160/160 | pass |
| right distal | 0,397797 | 0,419730 | 121/160 | pass |

Снижение RMSE против zero:

- proximal: 27,52% left, 26,94% right;
- middle: 60,52% left, 58,96% right;
- distal: 5,11% left, 5,23% right.

Distal остаются существенно слабее остальных осей, но общий осевой порог 112/160 пройден обеими.

Combined normal/matched/zero:

`0,329349 / 0,345583 / 0,450431`.

Controls shuffled/static/closed:

`0,434795 / 0,569881 / 0,495763`.

Normal ниже каждого control pooled и отдельно выигрывает у каждого control во всех `160/160` cases. Normal также лучше matched center diagnostic, что согласуется с обучением на balanced geometry, но не превращает failed corner gate в успех.

## Body X=4,18 safeguard

Safeguard полностью пройден на 80 cases. Distal:

- left normal/zero `0,413178 / 0,440806`, wins `73/80`;
- right normal/zero `0,392865 / 0,419730`, wins `72/80`.

Таким образом, риск body X=4,18, выявленный серией 82G, long training устранил. Все шесть failed corners серии 83 находятся, наоборот, при body X=3,82.

## Corner failure

Не прошли corners `1, 5, 6, 9, 13, 14`.

| Corner | Side | Z | Body X | Body Y | Причина |
|---:|---:|---:|---:|---:|---|
| 1 | 0,14 | 0,36 | 3,82 | −0,32 | right distal wins 5/10 |
| 5 | 0,14 | 0,56 | 3,82 | −0,32 | right distal wins 5/10 |
| 6 | 0,14 | 0,56 | 3,82 | +0,32 | left distal wins 6/10 |
| 9 | 0,42 | 0,36 | 3,82 | −0,32 | right distal wins 6/10 |
| 13 | 0,42 | 0,56 | 3,82 | −0,32 | right distal wins 6/10 |
| 14 | 0,42 | 0,56 | 3,82 | +0,32 | right distal wins 6/10 |

Во всех этих corner-axis combinations pooled normal всё равно ниже zero. Они провалены именно из-за недостаточной повторяемости по motions, 5/10 или 6/10 вместо 7/10, а не из-за отрицательного pooled эффекта.

Пять из шести corner failures вызваны right distal. Наиболее проблемные motions по case failures:

- left distal: 261 (7 corners), 262 (11), 263 (1), 266 (10), 269 (2);
- right distal: 261 (5), 262 (11), 265 (9), 266 (10), 269 (4).

Проблема сосредоточена в interaction `body X=3,82 × distal × отдельные motions`, особенно 261, 262 и 266. Нельзя post hoc исключать эти движения или corners.

## Autonomous state и controls

Во всех `160/160` cases:

- состояние содержит 72 коэффициента;
- SHA state до и после задержки 0,5 с совпадает;
- replay использует state+phase без RGB, teacher и framewise buffer согласно summary;
- normal лучше shuffled, static и closed по combined RMSE.

Это сильный functional reconstruction result, но preregistered overall primary остаётся failed из-за spatial corner consistency.

## Contacts

Mean contact F1 normal/zero:

`0,927699 / 0,918496`.

Normal лучше в 79 cases, равен в 72 и хуже в 9. Разница небольшая; contacts являются кинематическими qpos contacts и не доказывают actuator dynamics.

## Training-overlap audit

Audit охватывает 128 из 18 686 accepted candidates и не является exhaustive. Для десяти holdouts:

- совпадений ближе 0,001°: 0;
- совпадений ближе 1°: 0;
- frame queries ближе 5°: 115 из 490.

Это снижает риск точного replay training trajectory, но sample audit не доказывает отсутствие близких эпизодов во всём training set.

## Решение

1. Серия 83 остаётся `primary failed`.
2. Не повторять ещё одно восьмичасовое обучение с тем же protocol.
3. Серия 84 может быть только frozen read-only stress/diagnostic map существующей модели 83, без retraining и без исключения failed motions/corners.
4. Главная задача серии 84: подтвердить границу `body X lower × distal motion consistency`, отдельно left/right distal, и проверить соседние interior body-X values.
5. Переход к shared observation/execution population серии 85 запрещён до прохождения uniform six-axis frozen gate.

## Ограничения claims

Это synthetic supervised fixed-FOV observer и autonomous reconstruction наблюдавшегося действия. Нет нового поведения, actuator dynamics, сил, мышц, closed-loop correction, биологического мозга или доказательства mirror neurons.
