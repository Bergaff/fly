# Series103: пользовательский результат official interbody vision preflight

## Статус

Полный Windows-запуск завершён. Все8 заранее зафиксированных technical checks выполнены: `primary.passed=true`. Результат остаётся `scientific_result=false`.

Исходный JSON сохранён без изменения как `flygym-interbody-vision-preflight-user-result.json`.

- SHA-256 JSON: `1a13fe460bfb7bfc0af70203465ba42b74ba0809d53672bdad0afb209c6184bf`
- runner SHA-256: `33bc95e41032d1f6bc823d626c6ea8c2f80a7135e5c3b8254c656b8400823d11`
- Series102 prerequisite SHA-256: `33795d582e9ac528304018300dc14c67db066d3452e1760df2bb74c9aef9a643`
- API: `NeuroMechFly.add_vision` + `Simulation.get_raw_vision('observer')`

## Primary checks

| Проверка | Порог/ожидание | Результат |
|---|---:|---:|
| FlyGym version | exact2.1.1 | pass |
| Official RGB shape | 49×2×64×96×3 | pass |
| Frozen-compatible features | 47×576 | pass |
| Finite/nonconstant | обязательно | pass |
| Moving-vs-neutral RGB delta | ≥0,05 uint8 | 19,467709 |
| Moving-vs-neutral edge delta | ≥1e-5 | 0,0142752 |
| Demonstrator mapped response | ≥0,03rad | 0,163094rad |
| Real force и observer contact | >0 | 9,326219;0,979592 |

Измеренные RGB и edge deltas значительно выше permissive sanity thresholds. Это подтверждает, что official observer-eye path не только импортируется, но и переносит заметный paired сигнал о moving demonstrator по сравнению с neutral episode.

## Вывод

Технический канал official body → official observer eyes → deterministic96×64 adapter → frozen-compatible edge-history shape работоспособен. Поэтому разрешён следующий отдельный preregistered этап: подать эти official-eye features в неизменённую frozen89E policy и сравнить с заранее фиксированными controls.

Этот результат сам по себе не показывает, что frozen89E понимает official images, не является imitation evidence и не подтверждает FlyVis, FlyWire/connectome mapping, biological vision или живую муху. Resize96×64 остаётся инженерным coordinate adapter.
