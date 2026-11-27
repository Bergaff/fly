# Серия89B4: preregistration head identity and contact

## Причина

89B3 получила identity195/216 ровно на пороге; все21 ошибки относятся к head. Contact candidate лучше angle-only, но common579/648<584 и только3/7 controls pass.89C/90 blocked; motions421–710 раскрыты.

## Новые данные

- development711–728 × views601–608 =144 cases;
- untouched final729–746 × views621–632 =216 cases/648 trials;
- final не участвует fit/selection.

## Intervention

1.30-D identity features: mean/std/RMS velocity/min/max по6 axes.
2. Ridge classifier выбирается grouped leave-one-motion-out CV из0,01/0,1/1/10.
3. Три action contact experts; head contact имеет development selection weight1,5, другие0,75.
4. Expert lambda candidates0/.25/.5/1/2/4/8.
5. Candidate использует soft probability mixture, temperature выбирается development-only из0,25/0,5/1/2.
6. Hard-expert, common-contact и angle-only controls изолируют эффект mixture/conditioning.
7. Oracle expert использует final true action только как diagnostic control. Candidate API true action не получает.

## Primary gate

- identity≥195/216;
- safety648/648, recovery/completion≥584;
- стандартные angle wins≥584, mean angle≤1,05 angle-only;
- contact vs angle-only≥584;
- contact vs common-contact≥584;
- минимум6 из9 contact comparators≥584;
- candidate mean contact≤hard-expert mean;
- candidate mean contact≤oracle mean+0,02.

Near-miss no-go. Go разрешает только frozen89C на новых motions/views;90 blocked.

## Ограничения

Development использует synthetic action/contact truth. Oracle control имеет label leakage и не является deployable policy. Contact geometric proxy, reduced body, нет FlyGym/muscles/natural vision/biological neurons.
