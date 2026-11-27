# Серия89B6: preregistration robust foreleg contact

## Динамика перед89B6

Результаты действительно улучшаются, но ни один near miss не считается go:

-89B3: identity195/216, contact mean0,141665, common wins579;
-89B4: identity216/216, soft mean0,127288, common607, но soft хуже hard0,122068;
-89B5: identity216/216, hard mean0,121827, common617, angle-only635; отказ сузился до foreleg/common188/216<195 и6/9 controls.

От89B3 до89B5 mean contact снизилась примерно14,0%; от89B4 soft до89B5 hard примерно4,3%. Head common вырос162/216 в89B3 до216/216 в89B5. Routing исправлен: candidate=oracle648/648 в89B4/89B5. Это содержательный прогресс, но89C/90 остаются blocked.

## Новые данные

- development783–800 × views681–688 =144 cases;
- untouched final801–818 × views701–712 =216 cases/648 trials;
- motions421–782 и все прежние final исключены;
- final не участвует в fit/selection.

## Intervention

Standard hard experts89B5 сохраняются как direct control. Только foreleg expert получает robust reweighting.

Для каждого grouped leave-one-motion-out fold стандартный foreleg expert и common model обучаются без held motion. Development foreleg rows, где standard static contact error не лучше common, получают weight boost из preregistered `1,5/2/4/8`. Boost выбирается по grouped-CV: сначала максимум foreleg wins против common, затем против standard hard, затем минимум contact/angle error. После выбора robust foreleg model refit на всех development rows. Head/reach experts не меняются.

Primary использует argmax predicted action и robust hard expert без true action. Controls: standard-hard, robust soft mixture, angle-only, common-contact, oracle, uncalibrated, zero, shuffled, open-loop, shared-lesion. Oracle получает true action только для диагностики.

## Primary gate

- identity total≥195/216 и по каждому action≥65/72;
- safety648/648, recovery/completion≥584;
- пять angle wins≥584 и mean angle≤1,05 angle-only;
- contact vs angle-only/common total≥584;
- contact vs angle-only/common для каждого action≥195/216, включая foreleg/common;
- минимум7 из8 broad controls (`soft`, angle-only, common, uncalibrated, zero, shuffled, open, lesion)≥584; oracle и standard-hard не входят в этот count и оцениваются отдельно;
- candidate mean contact≤standard-hard и≤soft-mixture;
- candidate mean contact≤oracle+0,02.

Новый7/8 gate зарегистрирован до final и строже контрфактического пересчёта89B5:89B5 имела только6/8. Oracle не удалён, а вынесен из count как заведомо tied diagnostic при правильном routing. Near miss no-go. Только полный89B6 go разрешает отдельный frozen89C; series90 blocked.

## Ограничения

Development использует synthetic labels. Oracle имеет label leakage. Reduced support surrogate и geometric contact proxy не являются collision force, muscles, natural vision или biological-neuron validation.
