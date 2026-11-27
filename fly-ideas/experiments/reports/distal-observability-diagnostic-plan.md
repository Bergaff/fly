# Серия 82D: distal observability diagnostic

## Основание

Серия 82 дала сильное улучшение combined и middle axes, но обе distal axes остались хуже stationary zero. Highres помог distal относительно standard преимущественно при FOV70 и ухудшил их при FOV30. Поэтому серия 83 запрещена. До следующего prototype нужно разделить видимость сегментов, sensor sampling и level/edge feature type.

Серия называется 82D, а не 83: это диагностическая ветвь failed gate, которая сама не разрешает long training.

## Frozen вопросы

1. Меняет ли поворот каждого distal joint RGB и coarse level features во всех held views?
2. Даёт ли 96×64 преимущество без edge channel?
3. Даёт ли edge channel преимущество отдельно от level?
4. Проигрыш zero связан с недостаточной видимостью или сохраняется при достаточном visual signal?

## Training и evaluation

Training сохраняет stream серии 82:

- 320 episodes;
- motion seed 8201;
- view seed 8203;
- balanced even-parity corners и uniform interior 50/50.

Evaluation новая и не использовалась для выбора серии 82D:

- motion seed 8222;
- IDs 221–226;
- 16 held odd-parity corners;
- 96 cases.

Все representations получают одинаковые движения, виды и labels.

## Factorial representations

Сравниваются четыре фиксированных варианта:

1. `standard48_level`: RGB 48×32, pooled level history, 576 features;
2. `high96_level`: RGB 96×64, те же 8×12 bins и только level history, 576 features;
3. `high96_edge`: RGB 96×64, только gradient-energy history, 576 features;
4. `high96_level_edge`: RGB 96×64, level + gradient-energy history, 1152 features.

Используется один и тот же linear ridge decoder class. Это разделяет level и edge channel, но не проверяет нелинейный decoder.

## Visibility perturbation

Независимый diagnostic motion использует seed 8224 и ID 299. В каждом из 16 held corners к каждой distal axis отдельно добавляется +10°. Для 48×32 и 96×64 записываются:

- медианное число изменённых RGB values по кадрам;
- RMS изменения признаков каждого representation.

Ось считается видимой в cell, если одновременно:

- median changed RGB48 ≥ 20;
- standard48 level feature delta RMS ≥ 1e-4.

Visibility gate требует минимум 12/16 cells отдельно для left distal и right distal. Этот порог является инженерным guard, а не биологическим порогом зрения.

## Заранее заданный routing

Диагностика не имеет `go_for_long_training` и всегда записывает `authorizes_series83=false`.

1. Если visibility gate провален, следующий short prototype меняет geometry/occlusion/camera observability.
2. Если visibility достаточна и один из high-resolution representations даёт обе distal ниже zero и минимум 60% wins против standard48 для каждой distal axis, следующий short prototype проверяет этот representation независимо.
3. Если visibility достаточна, но ни один representation не проходит условие выше, следующий short prototype меняет decoder/temporal model, а не разрешение или crop.

Выбранный route не является научным подтверждением причины. Он только предотвращает очередной дорогой запуск без локализации отказа.

## Диагностика проигрыша zero

Для каждой модели, case и distal axis сохраняются:

- RMSE;
- gain through origin;
- correlation prediction/target;
- mean bias;
- prediction и target RMS;
- sign agreement при |target| ≥ 5°.

Эти показатели различают attenuation, bias и sign failure, но не доказывают причинный механизм.

## Ограничения

Это short supervised synthetic engineering diagnostic. Нет replay, contacts, actuator dynamics, biological brain или mirror-neuron claim. Результат не позволяет запустить серию 83 без отдельного нового representation/decoder prototype и его preregistered six-axis gate.
