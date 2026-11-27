# Серия 81: raw + gated canonical multiscale prototype

## Основание

Серия 80 показала противоположный эффект replacement canonicalization: она помогает при FOV 70°, но вредит при FOV 30°, где foreground касается границы во всех eye observations. Поэтому raw representation нельзя удалять.

## Представление

Обе сравниваемые модели получают один и тот же training stream.

Baseline:

- 576 raw history features.

Multiscale:

- все 576 raw features без изменений;
- 576 canonical history features;
- два image-derived validity flags;
- всего 1154 features.

Если union foreground crop конкретного глаза касается любой границы изображения, 288 canonical features этого глаза, по 96 для каждого из трёх history frames, обнуляются. Raw eye features остаются доступными всегда. Gate не получает camera, FOV, body coordinates, teacher angles или MuJoCo state.

## Training и evaluation

Чтобы сравнение было связано с серией 80:

- 320 episodes;
- seeds 8001/8003;
- 50% balanced even-parity core corners;
- 50% continuous uniform interior;
- одинаковые labels и rendered RGB для raw и multiscale моделей.

Evaluation:

- motions 181–186 seed 8002;
- 16 held odd-parity corners;
- 96 cases.

## Blocking go/no-go

Для каждой outer axis multiscale должен:

- иметь pooled RMSE ниже raw и zero;
- выигрывать у raw минимум в 60% cases.

Для middle axes:

- multiscale ниже zero;
- ухудшение против raw не более 10%.

Дополнительно:

- combined multiscale ниже raw и zero;
- отдельно на FOV 30° и FOV 70° combined multiscale не хуже raw;
- минимум 12/16 held corners улучшают все четыре outer axes.

Feature-distance raw/canonical сохраняется только как диагностика и не участвует в go, потому что серия 80 показала, что aggregate distance может скрывать противоположные FOV regimes.

## Решение

Только `go=true` разрешит проектировать следующий long-run протокол. Fixture 8 episodes/32 cases проверяет pipeline, но его score не интерпретируется.

## Ограничения

Это supervised synthetic representation ablation, не научный long run. Он не проверяет autonomous replay, contacts, actuators, biological vision, brain или mirror neurons.
