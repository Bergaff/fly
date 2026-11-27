# Серия 84S: fixed-count lower-X right-distal model

## Причина

Series84R улучшила source83 по всем global axes, прошла camera-Z и 13/16 corner gates, но primary провалена единственным count gate: body X=3,82 right distal 55/80 вместо 56/80. Series84T показала, что QuickEdit был включён, после отключения 128 fixed candidates рассчитались без stalls. Поэтому 84S одновременно:

- адресует lower-X right-distal consistency новой training distribution;
- устраняет wall-clock completion и console QuickEdit stall.

84R остаётся no-go и frozen comparator. Series85 заблокирована.

## Что нельзя делать

- не перезапускать `RUN-EIGHT-HOUR-DISTAL-ROBUST-GROOMING.bat`;
- не продолжать старую84R после просмотра motions301–310;
- не округлять55/80;
- не исключать weak motions/corners;
- не менять thresholds после результата84S.

## Frozen source84R

Пользователь выбирает завершённую папку84R. Проверяются SQLite stage, protocol, pinned scripts, complete manifest и SHA `model_distal_robust.npz`. Candidate84R и summary копируются в новую immutable checkpoint. Старые final motions заменяются новыми до начала обучения.

## Архитектура

Representation и ridge полностью сохраняются от84R:

- две камеры96×64, FOV35;
- whole-frame coarse edge context48 features/frame;
- central fine crop144 features/frame;
- три кадра, итог576;
- ridge1,0 proximal/middle и0,35 distal.

Таким образом, targeted intervention относится к training geometry и существенно большему fixed dataset, а не к новому crop/ridge. Эти два фактора вместе всё равно являются package и не изолируются друг от друга.

## Fixed-count обучение

- ровно `16 384` committed candidate IDs;
- seed `8421`;
- два worker;
- transactional SQLite и pause/resume;
- wall time только diagnostic и никогда не завершает обучение;
- QuickEdit отключается через WinAPI до start/resume; на Windows запуск запрещён, если отключение не подтверждено;
- для каждой committed партии сохраняются coordinator wall, worker CPU и worker wall.

Выбор 16 384 основан на series83 и 84T и ориентирован на 4–8 часов на компьютере пользователя. Это оценка, а не time gate: серия завершится только по count.

## Targeted training geometry

- 50% exact lower-X core corners, body X=3,82;
- 25% exact upper-X core corners, body X=4,18;
- 25% continuous full map body X=3,70–4,30;
- side, camera Z и body Y сбалансированы в exact groups.

Motion families остаются piecewise5, piecewise9, harmonic и chirp. Teacher clip ±55°.

## Независимая final evaluation

- seed `8422`;
- motions `321–330`;
- пять piecewise5 и пять piecewise9;
- 16 core corners;
- 160 cases;
- frozen source84R, zero, shuffled, static и closed;
- 72-coefficient state после задержки0,5с.

## Blocking primary

### Absolute axes

Каждая ось candidate ниже zero и минимум112/160 wins.

### Frozen comparator

Right distal candidate:

- pooled ниже source84R;
- минимум96/160 wins против source84R.

Остальные пять осей должны пройти absolute gate и быть не хуже source84R более чем на5% pooled.

### Lower-X target gate

На80 cases body X=3,82 right distal:

- candidate ниже zero и source84R pooled;
- минимум60/80 wins против zero;
- минимум48/80 wins против source84R.

Порог60/80 строже прежнего56/80 и заранее фиксирует, что новый package должен не просто пересечь старую границу.

### Geometry и corners

- body X=3,82 и4,18: каждая ось минимум56/80 wins vs zero, с дополнительным lower-X right-distal gate выше;
- camera Z=0,36 и0,56: каждая ось минимум56/80;
- минимум12/16 corners, в каждой все оси candidate ниже zero и минимум7/10 wins.

### Combined

Candidate combined ниже source84R, zero, shuffled, static и closed.

## После результата

- no-go: series85 остаётся заблокированной;
- go: требуется отдельная frozen replication модели84S на ещё одном новом motion set; прямой переход к85 запрещён.

## Ограничения

Synthetic supervised reconstruction, не natural vision. Нет нового действия, actuators, сил, мышц, closed-loop correction, биологического мозга или mirror neurons.
