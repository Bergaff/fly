# Серия89B2: preregistration contact-aware policy development

## Почему не89C

Frozen89C была заранее разрешена только при полном go89B. Series89B получила `primary=false`: contact gate прошёл1/5 controls вместо≥4/5. Поэтому запуск89C с failed candidate был бы нарушением preregistration.89B2 является новым допустимым development stage. Threshold89B не меняется, motions421–638 раскрыты.

## Frozen identities

- runner89B SHA `99e0ccd01e9ae0ba27d61c4391e6cdff675793c8b10cbea41a4237a5b398a920`;
- no-go89B extract SHA `ad8405c5bab7511bafaa0c0fbfee44cfa3c357cdcabdb70cca8e196a01ab75e8`;
- source summary SHA `f4351c05599a059090310452857887da096fbff79699c407ec4bf1c8a8028664`;
- source84Z read-only.

## Новые данные

Development:

- motions639–656 × views401–408;
-144 visual cases;
- angle/contact truth разрешён для fit и выбора одного lambda.

Untouched final:

- motions657–674 × views421–432;
-216 visual cases;
-3 profiles,648 trials;
- final не участвует в fit/selection.

## Intervention

1. Прежний common angle calibrator13→6 fit заново только на new development.
2. Новый common contact predictor13→2 с ridge0,08 предсказывает два truth contact-proxy channels из тех же state features, без action label.
3. Differentiable contact adjustment минимизирует anchor к angle policy плюс выбранный contact objective.
4. Fixed lambda candidates:0;0,25;0,5;1;2;4.
5. Development selection минимизирует `angle RMSE +0,75 contact MAE`, при angle≤1,05 angle-only projected.
6. Soft projection, slew и barrier остаются как в89B.

Это supervised synthetic development, не autonomous learning.

## Final controls

- candidate contact-aware;
- angle-only89B-style policy;
- uncalibrated;
- zero-state;
- shuffled-state contact-aware;
- open-loop candidate;
- shared-lesion contact-aware.

## Primary gate

Required584/648. Все условия обязательны:

1. Safety648/648.
2. Recovery и completion≥584.
3. Candidate angle лучше uncalibrated, zero, shuffled, open и lesion≥584 для каждого.
4. Mean candidate angle≤1,05 angle-only mean.
5. Candidate contact MAE лучше angle-only≥584. Это обязательный direct test нового intervention.
6. Candidate contact лучше минимум4 из всех6 comparators, каждый засчитанный comparator≥584.

Near-miss является no-go. Полный go89B2 разрешает только отдельную frozen89C replication на новых motions/views. Series90 остаётся blocked до replication go.

## Ограничения

Contact остаётся geometric proxy, не collision force. Reduced support surrogate не является FlyGym, мышцами или полноценным телом. Development supervised на synthetic truth. Нет natural vision, action invention или biological neurons.
