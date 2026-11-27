# Series105A+B: genuine Windows result

## Статус

Run технически завершён: `status=completed`. Exact preregistered development gate **не выполнен**: `primary.passed=false`, `development_candidate=false`, `scientific_result=false`. Это genuine adapter no-go, а не ошибка BAT или dependency failure.

Exact JSON сохранён без изменения как `official-eye-diagnostic-adaptation-105ab-user-result.json`.

- JSON SHA-256: `92715b54fde5fb259ce3947e35edf4f8ba178f659c5de01096546ca739af6a14`
- runner SHA-256: `b070fff687dfcfd263c6868b59954283486dd84b5a4e07156816f333a13dae67`
- Series104 result SHA-256: `91109c557111c4278567d383a5f99ed281f05ea5bcbd5fa5e326752afdf6ba04`
- trained adapter SHA-256: `ed021faa3fd3b84ad49183c68313177196c9462af399b83f5ad1f803a0e303ec`

## 105A: domain-shift diagnosis

На раскрытых motions903–908 unchanged official-eye path снова классифицировал только2/6 и во всех случаях выбрал `head_directed_grooming`. Synthetic reference того же движения и четырёх frozen views классифицировал5/6.

| Диагностика | Mean | Range |
|---|---:|---:|
| Official↔synthetic state cosine | -0,149018 | -0,265559…-0,015228 |
| State normalized RMSE | 1,623223 | 1,597447…1,667629 |
| Official target truth RMSE,rad | 0,501423 | 0,410618…0,591625 |
| Synthetic target truth RMSE,rad | 0,152898 | 0,078223…0,245936 |

Official images не были пустыми или статичными: mean temporal absolute RGB delta9,435322, edge standard deviation0,039272. Диагностика указывает не на отсутствие visual signal, а на сильное несоответствие frozen representation: все шесть official-to-synthetic state cosines отрицательны.

## 105B: paired diagonal adapter

Adapter обучен на всех12 заранее заданных train pairs1051–1062. Mean absolute per-feature correlation был только0,289699; nonzero scales72/72. Validation IDs1063–1068 не участвовали в fit или selection.

### Frozen validation gate

| Проверка | Требование | Результат |
|---|---:|---:|
| Action classification | ≥4/6 | 2/6, fail |
| Wins vs raw frozen | ≥4/6 | 6/6, pass |
| Wins vs neutral visual | ≥4/6 | 5/6, pass |
| Wins vs reversed visual | ≥4/6 | 3/6, fail |
| Wins vs zero state | ≥4/6 | 2/6, fail |
| Wins vs shuffled state | ≥4/6 | 6/6, pass |
| Distinct control targets | все cases | pass |
| Mean adapted RMSE < raw | да | 0,200818 < 0,504072, pass |

Mean truth RMSE,rad:

- adapted:0,200818;
- raw frozen:0,504072;
- neutral visual:0,211603;
- reversed visual:0,211444;
- zero state:0,171385;
- shuffled state:0,447356.

Adapter значительно исправил амплитудную/trajectory ошибку raw official state, но не восстановил action identity или visual specificity. Он в среднем хуже zero state и не выигрывает достаточно часто у reversed visual. Predicted actions на validation: один `head_directed_grooming` и пять `reach_withdraw`; правильны только два reach/withdraw cases1065 и1068.

## Вывод

Exact paired diagonal affine adapter закрывается как development no-go. Результат полезен диагностически: official-eye signal присутствует, а простой coordinate-wise domain alignment уменьшает raw trajectory error, но слабая paired correlation и отсутствие specificity показывают, что representation mismatch не сводится к независимому scale/offset72 координат.

Нельзя ослаблять gate, выбирать validation cases или выдавать улучшение6/6 против raw за общий pass. Series106 physical confirmation **не разрешён**, потому что prerequisite `development_candidate=true` не получен. Любой следующий подход должен быть новой явно обучаемой development-гипотезой с новым train/validation split; он не исправляет Series104 или105 и не является biological/FlyVis/FlyWire/mirror-neuron evidence.
