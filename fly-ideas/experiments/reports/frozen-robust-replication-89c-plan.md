# Серия89C: preregistration frozen robust replication

## Авторизация

89B6 дала independently verified full development go: identity216/216, safety/angle pass, action-specific contact gates pass, broad7/8, `primary.passed=true`. Исходный summary SHA `f1c36207…`, model SHA `b8beb562…`, runner SHA `1d308cb1…`, selected boost4.

89C разрешена только как отдельная frozen replication. Series90 остаётся blocked.

## Frozen policy

Программа требует локальную завершённую `result`-папку89B6 и проверяет:

- точный SHA `summary.json`;
- точный SHA `robust_foreleg_model.npz`;
- `complete.json` manifest;
- development primary go;
- boost4;
- точный runner89B6 и опубликованный extract.

Из NPZ неизменно загружаются angle/identity/common weights, robust и standard expert weights, обе группы lambda, temperature и boost. Fit, grouped-CV, selection и изменение threshold запрещены. Папки89B6 и84Z хешируются до/после.

## Новые данные

- frozen motions819–836;
- views721–732;
-18 motions×12 views=216 cases;
- profiles neutral/pose/velocity=648 trials;
- motions421–818 и все прежние final исключены.

Candidate использует predicted argmax robust hard expert без true action. Oracle получает true action только для diagnostic scoring.

## Primary gate

Без изменений повторяется точная функция decision89B6:

- identity total≥195/216 и по action≥65/72;
- safety648/648, recovery/completion≥584;
- пять angle wins≥584 и mean angle≤1,05 angle-only;
- contact vs angle-only/common total≥584;
- contact vs angle-only/common по каждому action≥195/216;
- минимум7/8 broad controls≥584;
- candidate mean contact≤standard-hard и≤soft-mixture;
- candidate mean contact≤oracle+0,02.

Near miss no-go. Только полный frozen89C go может разрешить отдельную series90.

## Ограничения

Synthetic truth используется для scoring и oracle. Reduced support/geometric contact proxy не являются collision force, muscles, natural vision или biological-neuron validation.
