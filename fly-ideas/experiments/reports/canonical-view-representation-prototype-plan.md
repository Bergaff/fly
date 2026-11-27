# Серия 80: canonical view representation prototype

## Основание

Серия 79 показала, что one-factor устойчивость модели 78 широка, но proximal/distal суставы отказывают на сочетаниях view transformations. Простой рост диапазона augmentation не решает проблему представления. До нового восьмичасового расчёта серия 80 проверяет image-only spatial canonicalization.

## Статус

Это короткий технический ablation, не научная long-run серия. Он не загружает и не изменяет модель 78. Две новые raw/canonical ridge-модели обучаются на одном небольшом synthetic stream только для принятия решения о следующем протоколе.

## Canonicalization

Для каждого глаза по всей observation sequence:

1. foreground определяется фиксированным порогом luminance `<105`;
2. берётся union mask по времени;
3. bounding box расширяется на 2 pixels;
4. один и тот же crop применяется ко всем кадрам последовательности;
5. crop bilinear-resize до 48×32.

Camera, FOV, body coordinates, teacher angles и MuJoCo state canonicalizer не получает. Sequence-level crop допустим только во время observation window.

Guards останавливают расчёт при слишком маленькой mask или вырожденном crop. Логируются bounding boxes, border touches, RGB SHA и unique frames.

## Одинаковый training stream

Production prototype: 320 episodes, seeds 8001/8003.

- 50%: равномерное повторение 16 even-parity corners training envelope серии 78;
- 50%: continuous uniform interior.

Raw и canonical models получают одни teacher angles и те же rendered episodes. Отличается только preprocessing, поэтому их сравнение изолирует canonicalization внутри этого prototype.

## Frozen evaluation

Шесть новых motions seed 8002, IDs 181–186. Evaluation использует 16 odd-parity core corners, которые не подавались как точные corner training views. Всего 96 cases.

## Go/no-go для будущего long run

Для каждой outer axis: canonical pooled RMSE ниже raw и zero, минимум 60% case wins против raw.

Для middle axes: canonical ниже zero и ухудшение против raw не более 10%.

Дополнительно:

- combined canonical ниже raw и zero;
- canonical feature distance между matched и altered view ниже raw distance;
- минимум 12/16 held corners улучшают canonical против raw на каждой из четырёх outer axes.

Если критерий не выполнен, новый восьмичасовой запуск с этим canonicalizer запрещён. Fixture mode с 8 episodes служит только проверкой pipeline и не интерпретируется.

## Ограничения

Prototype одновременно использует balanced training stream для обеих моделей; он не оценивает прежнюю model78. Это supervised synthetic preprocessing, не biological vision, memory, mirror neurons, contacts или actuator control.
