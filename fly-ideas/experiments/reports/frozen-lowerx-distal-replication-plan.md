# Серия 84U: frozen replication model84S

## Решение до расчёта

Series84S прошла все preregistered gates. Её model SHA `a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f` теперь заморожена. Series85 остаётся заблокированной до результата этой независимой replication.

## Запреты

- не перезапускать training84S;
- не менять веса, crop, ridge, clipping или thresholds;
- не выбирать motions/corners после просмотра результата;
- не исключать слабые cases;
- не запускать старые BAT84R и84S.

Runner открывает завершённую source84S, проверяет SQLite stage, protocol, complete manifest, runner84S SHA, model84S SHA и embedded model84R SHA. До и после расчёта он сверяет SHA source database, обеих моделей, summary и complete manifest. Запись выполняется только в новую папку replication.

## Новая батарея

- отдельный seed `8424`;
- motions `341–350`, пять piecewise5 и пять piecewise9;
- движения генерируются до прогнозов;
- раскрытые labels source84S блокируются по motion SHA;
- 16 тех же заранее заданных geometry corners;
- 160 cases по49 оцениваемых frames;
- frozen model84S сравнивается с frozen model84R, zero, shuffled, static и closed;
- internal state72 coefficients и delay0,5с без обновлений.

Motions321–330 не используются. Ограниченный audit сопоставляет новые trajectories с максимум128 accepted training candidates и явно остаётся non-exhaustive.

## Blocking primary без изменений

### Absolute axes

Каждая из шести осей model84S должна быть ниже zero pooled и выиграть минимум112/160 cases.

### Frozen comparator

Right distal должна быть ниже model84R pooled и выиграть минимум96/160 cases. Остальные пять осей проходят absolute gate и не хуже model84R более чем на5% pooled.

### Lower-X right distal

На80 cases body X=3,82:

- model84S ниже zero и model84R pooled;
- минимум60/80 wins против zero;
- минимум48/80 wins против model84R.

### Geometry и corners

- обе body-X groups проходят каждую ось минимум56/80 против zero;
- обе camera-Z groups проходят каждую ось минимум56/80;
- минимум12/16 corners проходят все оси, каждая минимум7/10 wins против zero.

### Combined и controls

Combined model84S ниже model84R, zero, shuffled, static и closed.

Все компоненты blocking: один fail означает replication no-go, без округления или post hoc изменения правила.

## Запуск

Двойной щелчок по `RUN-FROZEN-LOWERX-DISTAL-REPLICATION.bat`, затем выбор завершённой папки `lowerx_distal_fixed_count_...` series84S. Это evaluation-only расчёт, не 4–8-часовое обучение.

## После результата

- replication go: можно отдельно preregister series85;
- replication no-go: series85 остаётся заблокированной, model84S не переобучается на motions341–350.

## Ограничения

Это replication внутри того же synthetic generator family и geometry grid. Она проверяет перенос на новые motions/seeds, но не natural vision, новое действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
