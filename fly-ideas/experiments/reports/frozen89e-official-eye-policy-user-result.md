# Series104: пользовательский результат frozen89E на official observer-eye images

## Статус

Полный Windows run завершён. Заранее зафиксированный primary gate **не выполнен**: `primary.passed=false`. Это genuine frozen domain-transfer no-go, а не runtime failure. По протоколу `scientific_result=false`.

Исходный JSON сохранён без изменения как `frozen89e-official-eye-policy-user-result.json`.

- SHA-256 JSON: `91109c557111c4278567d383a5f99ed281f05ea5bcbd5fa5e326752afdf6ba04`
- runner SHA-256: `ace8d99fa0ad71454fa7b4122868547c880817f9b45b9e654fb02245aad298a1`
- Series103 prerequisite SHA-256: `1a13fe460bfb7bfc0af70203465ba42b74ba0809d53672bdad0afb209c6184bf`
- training/selection/post-result tuning: false

## Primary gate

| Проверка | Порог | Результат |
|---|---:|---:|
| Candidate safe/contact | 6/6 | 6/6, pass |
| Mean tracking RMSE | ≤0,20rad | 0,118936rad, pass |
| Action classification | ≥4/6 | 2/6, fail |
| Wins vs neutral visual | ≥4/6 | 4/6, pass |
| Wins vs reversed visual | ≥4/6 | 3/6, fail |
| Wins vs zero state | ≥4/6 | 2/6, fail |
| Wins vs shuffled state | ≥4/6 | 3/6, fail |
| Wins vs true open loop | ≥5/6 | 6/6, pass |
| Visual/state targets distinct | все cases | да, pass |

Shared-lesion wins:3/6, secondary.

## Агрегированные physical metrics

| Условие | Mean truth RMSE, rad | Mean tracking RMSE, rad | Contact fraction | Finite |
|---|---:|---:|---:|---:|
| candidate | 0,197330 | 0,118936 | 0,979592 | 6/6 |
| neutral_visual | 0,196367 | 0,120849 | 0,979592 | 6/6 |
| reversed_visual | 0,191784 | 0,120549 | 0,979592 | 6/6 |
| zero_state | 0,165856 | 0,027487 | 0,979592 | 6/6 |
| shuffled_state | 0,212085 | 0,118491 | 0,979592 | 6/6 |
| shared_lesion | 0,213196 | 0,126238 | 0,959184 | 6/6 |
| open_loop | 0,496930 | 0,254671 | 0,979592 | 6/6 |

Candidate физически стабилен и closed-loop MOTOR существенно лучше true open loop, но это не доказывает visual-policy specificity. В среднем candidate хуже zero state, neutral visual и reversed visual.

## Классификационный collapse

Все6 official-eye cases предсказаны как `head_directed_grooming`. Правильны только два genuine head-directed cases904 и907. Foreleg rubbing и reach/withdraw не распознаны. Это согласуется с domain shift от synthetic external-camera images к official fisheye observer-eye images.

## Вывод

Fixed frozen89E policy **не переносится** на official observer-eye domain при заранее объявленном bilinear96×64 adapter. Image transport Series103 работоспособен, physical adapter Series101/102 работоспособен, но их прямое соединение не прошло specificity controls и action gate.

Порог нельзя ослаблять, а post-result tuning запрещён. Результат не разрешает заявлять official-eye imitation, biological observation-to-action, FlyVis/FlyWire mapping или mirror neurons. Synthetic optimization остаётся закрыта. Любая будущая попытка domain adaptation потребует нового явного решения, отдельного training protocol и новых untouched outcomes; она не может считаться frozen replication.
