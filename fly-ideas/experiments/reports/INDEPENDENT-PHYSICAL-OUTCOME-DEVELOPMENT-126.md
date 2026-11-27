# Series126 — independent physical-outcome development

## До запуска: что именно было установлено

Из Series125–129 эмпирический результат до этого запуска существовал только у **Series125**: four-hop 61×61 проходит узкую structural self-consistency, но не показывает внешнее behavioral advantage и не разрешает новый physical port. Series126–129 были условным протоколом, а не заранее известными PASS.

- **126:** независимая behavioral development-цель; исход до запуска не известен.
- **127:** untouched digital replication только после GO в126.
- **128:** новый official FlyGym physical run только после GO в127.
- **129:** неизменяемый финальный аудит независимо от GO/NO-GO цепочки.

## Независимая цель

Target — пять ранее измеренных выходов official FlyGym/NeuroMechFly: tracking RMSE, truth RMSE, contact-frame fraction, maximum actuator-force norm и absolute-work energy. Они взяты из genuine user artifacts Series106,109 и112, созданных до Series126 и не вычисленных из61×61 Graph Core. Все три JSON, graph matrix и action prototypes проверяются по SHA-256.

Это **offline prediction исторических физических outcomes**, а не исполнение нового Graph controller. Старые adapters не переименовываются в Graph Core.

## Разделение и модели

- Series106:12 fit cases.
- Series109:12 заранее определённых fit cases (`foreleg_rubbing`, `head_directed_grooming`) и6 development-selection cases (`reach_withdraw`, по одному в каждом nuisance domain).
- Series112:18-case historical audit. Он не используется для настройки, но уже существовал и был ранее просмотрен, поэтому честно называется historical audit, а не новым untouched final.

На development выбирается ridge alpha из `[1e-4, 1e-3, 1e-2, 0.1, 1, 10]`. Сравниваются constant mean, metadata linear, raw type linear, frozen four-hop graph, rewired topology, matched-random graph weights и fixed-random-feature MLP. Primary metric — средний RMSE пяти outcomes после зафиксированной нормализации. Graph GO требует не менее5% улучшения против **каждого** learned control.

## Локальный исход

| Model | Historical-audit normalized RMSE |
|---|---:|
| constant mean | 0.793394 |
| metadata linear | 0.888066 |
| raw types | 0.888082 |
| graph four-hop | 0.888083 |
| rewired graph | 0.888083 |
| matched-random graph | 0.888083 |
| random-feature MLP | 2.322068 |

**Gate: NO-GO.** Frozen graph практически совпал с raw, rewired и random controls и проиграл простому constant mean. Требуемого5% преимущества нет. Series127 и128 не авторизованы. Это отрицательный инженерный результат; он не отменяет узкую structural self-consistency Series125 и не меняет исторические FlyGym evidence Series100–112 для их собственных frozen adapters.

## Ограничения

Набор мал (48 исторических cases суммарно), outcomes статичны, а historical audit не является новым скрытым набором. Поэтому Series126 достаточна для отклонения заявленного преимущества на доступной цели, но не для общего вывода, что topology никогда не может быть полезна. Биологические mirror neurons, living-neuron identity и whole-brain claims не проверялись.

Повторение Windows: `experiments\RUN-INDEPENDENT-PHYSICAL-OUTCOME-126.bat`. Результат появляется в `workspace\runs\ideas\i-observational\independent-physical-outcome-126\...\summary.json`.
