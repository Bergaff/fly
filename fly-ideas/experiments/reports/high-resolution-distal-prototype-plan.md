# Серия 82: high-resolution distal representation prototype

## Основание

Серия 81 сохранила raw input и успешно исправила proximal/middle, но обе distal axes ухудшились. Следующая проверка меняет не crop, а пространственное разрешение.

## Сравнение на одном stream

Standard baseline:

- RGB 48×32;
- 576 level-history features текущего pipeline.

High-resolution package:

- RGB 96×64 с тем же FOV и pose;
- luminance pooled в 8×12 bins каждого глаза;
- high-resolution gradient-energy pooled в те же bins;
- три history frames;
- 1152 features.

Таким образом, high-resolution package сохраняет sub-bin edge information, которая может быть важна для маленьких distal ellipsoids. Сравнение оценивает весь пакет sensor sampling + edge representation, а не разделяет их эффекты.

## Stream

- 320 episodes;
- motion/view seeds 8201/8203;
- 50% balanced even-parity core corners;
- 50% continuous uniform interior;
- одинаковые movements, views и labels обеих моделей.

Evaluation:

- шесть новых motions IDs 201–206, seed 8202;
- 16 held odd-parity core corners;
- 96 cases.

Батарея отличается от серий 80–81, поэтому не настроена по их конкретным motion errors, хотя архитектурная гипотеза выбрана после их результатов.

## Blocking primary

Для left distal и right distal одновременно:

- pooled highres ниже standard и zero;
- highres выигрывает у standard минимум в 60% cases.

Safeguards для proximal/middle:

- highres ниже zero;
- highres не хуже standard более чем на 5%.

Дополнительно:

- combined highres ниже standard и zero;
- отдельно FOV30 и FOV70 highres не хуже standard более чем на 2%;
- минимум 12/16 held corners улучшают обе distal axes.

Только полный go разрешает серию 83, восьмичасовое high-resolution обучение. Fixture mode не интерпретируется.

## Ограничения

Это short supervised synthetic ablation. Нет autonomous replay, contacts, actuators, biological brain или mirror-neuron evidence.
