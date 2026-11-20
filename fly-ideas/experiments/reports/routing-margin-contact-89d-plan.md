# Серия89D: preregistration routing-margin contact

## Причина

Frozen89C strict no-go на motions819–836:

- identity212/216 формально прошла, но4 cases ушли в reach;
- foreleg/common194/216, не хватило1;
- oracle foreleg/common200/216 показывает, что две foreleg routing errors объясняют direct miss;
- soft582/648 не хватило2, broad6/8;
- candidate mean хуже standard всего на1,095×10⁻⁸, но strict gate failed.

Нельзя менять89C. Новая89D является development-серией на полностью новых данных.89B6 go остаётся историческим;90 blocked.

## Новые данные

- development837–854 × views741–748 =144 cases;
- untouched final855–872 × views761–772 =216 cases/648 trials;
- motions421–836 и все прежние final исключены;
- final не участвует в fit/selection.

## Intervention1: routing-margin ridge

Identity features остаются30-D. Ridge candidates расширены до `0,001/0,01/0,1/1/10/100`. Для каждого grouped leave-one-motion-out fold сохраняются:

- correct total;
- correct отдельно по каждому action;
- minimum action correct;
- mean true-class margin;
- minimum true-class margin.

Выбор до final лексикографический: minimum action correct, total correct, mean margin, minimum margin, затем меньший ridge. Candidate по-прежнему использует только predicted argmax, без true action.

## Intervention2: mean-stable foreleg boost

Boost candidates1,5/2/4/8 сохраняются. В каждом grouped fold boost должен сначала быть eligible: foreleg wins vs common≥90%. Среди eligible выбирается минимальный held-out contact MAE, затем angle RMSE, common wins, standard wins и меньший boost. Это заменяет89B6 приоритет максимума common wins и прямо адресует infinitesimal mean-vs-standard failure, не ослабляя common consistency.

Head/reach experts не получают robust reweighting. Standard-hard, soft mixture, oracle, angle-only, common, uncalibrated, zero, shuffled, open-loop и lesion controls сохраняются. Oracle true action только diagnostic.

## Primary gate

Без ослабления повторяются gates89B6/89C:

- identity total≥195/216 и по action≥65/72;
- safety648/648, recovery/completion≥584;
- пять angle wins≥584 и mean angle≤1,05 angle-only;
- contact vs angle-only/common total≥584;
- contact vs angle-only/common по каждому action≥195/216;
- минимум7/8 broad controls≥584;
- candidate mean contact≤standard-hard и≤soft-mixture;
- candidate mean contact≤oracle+0,02.

Near miss no-go. Только полный89D go разрешает отдельную frozen89E на новых motions/views. Series90 остаётся blocked до frozen go.

## Ограничения

Development использует synthetic labels; oracle имеет label leakage. Reduced support/geometric contact proxy не являются collision force, muscles, natural vision или biological-neuron validation.
