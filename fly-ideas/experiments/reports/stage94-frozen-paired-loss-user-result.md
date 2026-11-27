# Stage94: frozen paired-loss replication — пользовательский результат

## Проверка происхождения

Присланный `summary-34.json` сообщает `status=completed`,2048/2048 replicates,6 workers и4761,28125 worker CPU seconds (1,32258 worker-hours). Script SHA `7d9c7135…` совпадает с замороженным Stage94 runner; source Stage92 SHA `0dbbdcb9…` также совпадает. Во всех42 агрегатах `n=2048`.

Получен только summary. `study.sqlite3`, `protocol.json` и `complete.json` независимо не получены, поэтому individual rows и SHA всей папки не проверены.

## Frozen gate

| Критерий | Порог | Результат | Итог |
|---|---:|---:|---|
| Few-shot combined-harsh accuracy margin | ≥0,030000 | 0,030003255 | пройден |
| Few-shot combined-harsh RMSE ratio | ≤0,970000 | 0,945660819 | пройден |
| Harsh dual rate, нижняя Wilson95 | ≥0,600000 | 0,624821032 | пройден |
| Overall dual rate, нижняя Wilson95 | ≥0,550000 | 0,595183316 | пройден |

Raw harsh dual rate:2620/4096=63,9648%. Raw overall dual rate:17228/28672=60,0865%. `frozen_pass=true`; `interpretation=computational_candidate_replicated`.

## Важная чувствительность

Accuracy margin прошёл порог только на0,000003255. В объединённых few-shot combined-harsh предсказаниях это соответствует всего трём дополнительным правильным решениям сверх минимального порога:2048 replicates ×450 test examples дают921600 решений; требование0,03 равно27648, наблюдаемая разность —27651.

Это не позволяет объявить no-go: frozen правило было задано как `≥0,03`, и результат его формально выполнил. Но научная интерпретация обязана назвать этот компонент пограничным. Остальные три компонента имеют заметный запас.

## Основной срез

Few-shot5 combined-harsh:

- structured96 accuracy0,254787; RMSE0,311496;
- shuffled96 accuracy0,224784; RMSE0,329395;
- dense96 accuracy0,233819; RMSE0,331755.

Budget30 combined-harsh:

- structured96 accuracy0,484992; RMSE0,128810;
- shuffled96 accuracy0,411584; RMSE0,133103;
- dense96 accuracy0,409470; RMSE0,134979.

После common-random-number correction и trajectory weight4 structured96 сохранила advantage не только по classification, но и по trajectory RMSE в этом независимом seed namespace.

## Вывод

Stage94 — **frozen computational pass** по заранее зафиксированному усиленному gate. Подтверждена воспроизводимость преимущества конкретной инженерной structured96 маски над parameter-matched shuffled96 в этой синтетической задаче при common random numbers и trajectory-loss weight4.

Это не «преимущество коннектома мухи»: маска не получена из FlyWire,96 units не являются нейронами, входы/действия синтетические, а software state не является биологической памятью. Результат не отменяет Series90: reviewed FlyVis→FlyWire mapping и валидированный motor readout всё ещё отсутствуют. Нельзя переименовывать structured96 в connectome или переносить численный эффект на живую муху.

Допустимый следующий шаг — обновлённый biological mapping preflight с теми же жёсткими требованиями к reviewed mapping и motor readout либо, если нужен более сильный computational claim, заранее зафиксированная sensitivity replication с отдельным accuracy-margin uncertainty rule. Нельзя менять Stage94 или скрывать пограничность его accuracy margin.
