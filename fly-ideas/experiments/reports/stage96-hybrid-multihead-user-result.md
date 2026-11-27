# Stage96 hybrid multi-head: пользовательский development-результат

## Проверка

Присланный `summary-36.json` сообщает completed:32720/32720 replicates,6 workers,213195,6875 worker CPU seconds (59,2210 worker-hours). Script SHA `d8000261…` и закреплённый Stage95 SHA `58b74a79…` совпадают. Во всех84 агрегатах `n=32720`; каждая модель имеет4437 parameters.

Получен только summary. SQLite, protocol.json и complete.json отдельно не получены, поэтому individual rows и SHA папки независимо не проверены.

## Итог gate

- `classification_branch_pass=true`;
- `joint_vs_monolithic_pass=false`;
- `development_candidate=false`;
- `interpretation=no_candidate`.

## Structured classifier прошёл

| Hybrid control | Few-shot harsh accuracy margin | Harsh accuracy Wilson lower | Overall accuracy Wilson lower |
|---|---:|---:|---:|
| shuffled | +0,041407 | 0,803066 | 0,793322 |
| temporal | +0,056909 | 0,952450 | 0,975407 |
| learned | +0,020002 | 0,611700 | 0,552758 |

Structured classifier устойчиво превзошёл все три same-budget classifier controls, включая learned mask с dense warmup. Против learned запас margin и overall lower небольшой, но заранее заданные пороги выполнены.

## Полная hybrid против monolithic RNN54 прошла

- few-shot harsh accuracy margin+0,115278;
- RMSE ratio0,925029;
- harsh/overall RMSE Wilson lower0,577955/0,596278;
- harsh/overall strict dual Wilson lower0,564584/0,557211.

То есть специализация действительно устранила Stage95 tradeoff относительно RNN54: hybrid одновременно лучше классифицирует и устойчиво лучше восстанавливает траекторию.

## Learned-sparse остаётся блокирующим контролем

Средний few-shot harsh срез выглядит в пользу hybrid:

- accuracy margin+0,058790;
- RMSE ratio0,838246.

Но paired stability не прошла:

- harsh RMSE Wilson lower0,497529<0,50;
- overall RMSE lower0,442467<0,50;
- harsh dual lower0,456498<0,50;
- overall dual lower0,409179<0,50.

Причина видна по budget split. При few-shot5 hybrid trajectory значительно лучше learned-sparse: combined-harsh RMSE0,251787 против0,300374. При budget30 learned-sparse становится существенно лучше: combined-harsh0,134633 против0,158006; clean0,044428 против0,064056; occlusion0,072904 против0,101807. Поэтому сильный few-shot mean effect не превращается в устойчивое all-condition преимущество.

Это не общий near-miss. Только harsh RMSE lower близок к0,50; overall RMSE и dual lower отстают заметно. После просмотра результата нельзя исключить budget30 или заменить all-condition gate few-shot-only.

## Вывод

Stage96 — **частичный инженерный успех, но development no-go для общей joint hypothesis**.

Подтверждено:

1. structured classifier topology имеет устойчивое accuracy advantage над shuffled, temporal и learned same-budget branches;
2. разделённый RNN40 trajectory branch устраняет отставание перед monolithic RNN54;
3. exact-budget hybrid полезен в few-shot harsh режиме.

Не подтверждено:

1. устойчивое преимущество над learned-sparse96 across budgets/conditions;
2. общий development candidate для frozen replication;
3. какое-либо преимущество биологического коннектома.

Нельзя запускать frozen replication Stage96 как общего победителя. Научно честный следующий выбор — либо зафиксировать более узкую few-shot/classification hypothesis и отдельно подтвердить её, либо остановить эту synthetic optimization line. Любое новое изменение trajectory branch после просмотра Stage96 будет новым development этапом, а не ремонтом текущего no-go.
