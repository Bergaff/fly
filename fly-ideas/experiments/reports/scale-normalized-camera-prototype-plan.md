# Серия 82G: scale-normalized camera geometry prototype

## Основание

Серия 82D выбрала frozen route `geometry_or_occlusion`. При FOV30 perturbation +10° давал сильный RGB signal, но pooled distal prediction проигрывал zero. При FOV70 signal был мал и не проходил visibility guard, хотя level+edge локально оказался ниже zero. Следующая проверка должна уменьшить apparent-scale mismatch, не подменяя результат изменением decoder после просмотра.

Серия 82G является новым short prototype. Это не серия 83 и не long run.

## Сравнение на одном stream

Все варианты используют RGB 96×64, gradient-energy history, 576 features и один linear ridge decoder class:

1. `variable_edge`: исходная variable geometry, FOV 30–70;
2. `fov35_edge`: FOV принудительно равен 35°, но camera side, camera Z и body X/Y остаются исходными;
3. `tracked35_edge`: diagnostic-only body-relative fixed camera rig, FOV35.

Primary candidate только `fov35_edge`. Tracked camera не может спасти primary и нужен для определения, достаточно ли одной нормализации масштаба или требуется полное gaze stabilization.

Decoder получает только pixels. `fov35_edge` не получает camera/body metadata. Diagnostic tracked sensor использует simulator body pose для положения камеры; это явно отмеченное engineering допущение.

## Новые данные

Training:

- 320 episodes;
- motion seed 8241;
- view seed 8243;
- 50% balanced even-parity corners;
- 50% uniform interior.

Evaluation:

- motion seed 8242;
- motion IDs 241–246;
- 16 held odd-parity corners;
- 96 cases.

Новая батарея не использовалась в сериях 82 или 82D.

## Visibility guard

Diagnostic motion seed 8244, ID 399. Каждая distal axis отдельно получает +10° во всех 16 held corners.

Для `fov35_edge` cell-axis считается visible, если:

- median changed RGB96 ≥40;
- edge feature delta RMS ≥1e-4.

Требуется минимум 12/16 visible cells отдельно для left distal и right distal.

## Blocking primary

Для обеих distal axes одновременно `fov35_edge` должен:

- иметь pooled RMSE ниже `variable_edge` и zero;
- выигрывать у variable минимум в 60% из 96 cases.

Для proximal/middle:

- RMSE ниже zero;
- не хуже variable более чем на 5%.

Общие safeguards:

- combined fov35 ниже variable и zero;
- в группах исходных FOV30 и FOV70 combined fov35 не хуже variable более чем на 2%;
- минимум 12/16 held corners улучшают обе distal axes;
- visibility guard пройден по обеим distal axes.

Только полный `go_for_revised_long_training=true` разрешает проектирование переработанной серии 83. Tracked-camera score не входит в go.

## Почему fixed FOV35

FOV35 находится рядом с narrow-FOV режимом, где distal perturbation был явно видим. Он фиксируется до результата и применяется одинаково в training/evaluation. Проверка не утверждает, что 35° биологически оптимальны; это engineering test масштаба.

## Ограничения

Это short supervised synthetic geometry ablation. Fixed-FOV sensor изменяет постановку наблюдения. Tracked camera использует simulator body pose и не является биологической системой gaze control. Нет replay, contacts, actuators, biological brain или mirror-neuron evidence.
