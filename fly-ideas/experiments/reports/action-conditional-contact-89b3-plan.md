# Серия89B3: preregistration predicted-action conditional contact

## Причина

89B2 улучшила aggregate contact, но direct wins против angle-only525/648 не достигли584. Failure action-specific: foreleg209/216, head181/216, reach135/216. Frozen89C и90 остаются blocked. Threshold не меняется, motions421–674 раскрыты.

## Новые данные

Development:

- motions675–692 × views501–508;
-144 visual cases;
- true action labels разрешены для fit prototypes/experts только здесь.

Untouched final:

- motions693–710 × views521–532;
-216 visual cases,648 trials;
- final action label не передаётся policy и используется только evaluation.

## Intervention

1. Common angle calibrator как89B.
2.18-D target summary: six means, std и RMS first differences.
3. Nearest development prototype предсказывает action без true label на inference.
4. Три13→2 contact experts fit по development true action.
5. Lambda0/.25/.5/1/2/4 выбирается отдельно для каждого expert только на development.
6. Common-contact model служит прямым control, чтобы изолировать условность.

## Final controls

Candidate predicted-action expert сравнивается с angle-only, common-contact, uncalibrated, zero, shuffled, open и shared-lesion.

## Primary gate

Required195/216 visual identities и584/648 trials. Все условия обязательны:

1. Predicted action correct≥195/216.
2. Safety648/648; recovery/completion≥584.
3. Candidate angle лучше uncalibrated, zero, shuffled, open, lesion≥584 каждого; mean angle≤1,05 angle-only.
4. Candidate contact лучше angle-only≥584.
5. Candidate contact лучше common-contact≥584: direct test action conditioning.
6. Candidate contact лучше минимум5 из7 controls, каждый засчитанный≥584.

Near-miss no-go. Go разрешает только frozen89C replication на новых motions/views; series90 blocked до replication go.

## Ограничения

Development experts используют synthetic action labels, inference использует predicted identity. Contact geometric proxy, не collision force. Reduced surrogate не является complete body/FlyGym. Нет natural vision, muscles или biological neurons.
