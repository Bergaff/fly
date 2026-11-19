# Серия89B5: preregistration predicted-hard contact

## Причина

89B4 strict no-go: identity216/216, direct contact624/607 и6/9 controls прошли, но soft candidate mean0,127288 хуже hard/oracle0,122068. Hard predicted=oracle во всех648 records. Routing исправлен; остаточное soft mixing разбавило правильный expert. Post-hoc hard counterfactual не меняет89B4.

## Новые данные

- development747–764 × views641–648 =144 cases;
- untouched final765–782 × views661–672 =216 cases/648 trials;
- motions421–746 и все прежние final исключены;
- final не участвует в fit/selection.

## Intervention

30-D grouped leave-one-motion-out ridge identity, per-action contact experts и head weight1,5 сохраняются. Primary candidate выбирает `argmax(predicted action probabilities)` и соответствующий hard expert. True action в candidate API не передаётся.

Soft mixture остаётся прямым control. Oracle expert получает true final action только как diagnostic label-leak control. Сохраняются angle-only, common-contact, uncalibrated, zero, shuffled, open-loop и shared-lesion controls.

## Primary gate

- identity total≥195/216 и по каждому action≥65/72;
- safety648/648, recovery/completion≥584;
- стандартные пять angle wins≥584 и mean angle≤1,05 angle-only;
- contact vs angle-only и common total≥584;
- contact vs angle-only и common отдельно для каждого action≥195/216;
- минимум7 из9 contact comparators≥584;
- candidate mean contact≤soft-mixture mean;
- candidate mean contact≤oracle mean+0,02.

Near miss no-go. Только полный89B5 go разрешает отдельный frozen89C на новых motions/views; series90 остаётся blocked.

## Ограничения

Development использует synthetic action/contact labels. Oracle содержит label leakage и не является deployable policy. Reduced support surrogate и geometric proxy не являются collision force, muscles, natural vision или biological-neuron validation.
