# Серия 83: восьмичасовое fixed-FOV35 autonomous grooming

## Основание

Короткая серия 82G прошла полный blocking gate: fixed FOV35 edge representation улучшила все шесть осей, обе distal относительно variable и zero, visibility 16/16 и 12/16 corners. Поэтому разрешён один long run. Серия 83 не использует tracked camera как primary.

## Запуск и бюджет

Один BAT начинает, продолжает и запрашивает паузу:

`RUN-EIGHT-HOUR-FIXED-FOV-AUTONOMOUS-GROOMING.bat`

Активное обучение длится ровно 28 800 секунд. Используются два worker-процесса, batch 2, ограничение потоков численных библиотек до одного на процесс. При свободной RAM менее 4 ГиБ или диске менее 2 ГиБ новая партия не начинается. Последняя завершённая партия остаётся в SQLite.

Среда берётся из приложения `workspace/.venv-two-flies`; BAT ничего не устанавливает.

## Training

- motion seed `8301`;
- view seed `8303`;
- RGB двух камер `96×64`;
- FOV всегда `35°`;
- 576 pooled gradient-energy history features;
- families: piecewise5, piecewise9, harmonic, chirp;
- шесть выходов: proximal/middle/distal обеих передних лап.

View distribution:

- 50% episodes циклически покрывают все 16 exact corners четырёх факторов;
- 50% используют continuous uniform interior;
- camera side: `0,14–0,42`;
- camera Z: `0,36–0,56`;
- body X: `3,82–4,18`;
- body Y: `−0,32–0,32`.

Каждая training sequence получает supervised teacher angles. Это synthetic ridge learning, не биологическое обучение.

## Visual preflight

До создания новой серии и при resume проверяются:

- не менее 10 уникальных RGB-кадров;
- не менее 100 изменённых RGB values;
- edge feature std не менее `1e-4`;
- каждый из шести суставов меняет не менее 10 RGB values;
- разные geometry views дают разные RGB SHA.

Изменение runner или pinned dependencies после старта блокирует продолжение.

## Frozen evaluation

До обучения создаются и копируются новые movements:

- seed `8302`;
- IDs `261–270`;
- первые пять piecewise5, вторые пять piecewise9.

После обучения frozen model проверяется на полном произведении:

- 10 motions;
- 16 geometry corners;
- 160 independent motion-view cases.

Во всех corners FOV остаётся 35°. Половина cases имеет body X=4,18, что образует отдельный safeguard.

Motions 241–246 серий 82G не используются.

## Autonomous state и controls

В каждом case framewise visual estimates сжимаются в `6×12 = 72` cosine coefficients. Затем:

- state не обновляется 0,5 секунды;
- replay получает только coefficient state и phase;
- replay не получает RGB, teacher commands или сохранённый framewise prediction buffer.

Controls:

- stationary zero;
- shuffled observation frames;
- static first frame;
- closed black input;
- matched center view только как diagnostic reference.

Контакты MuJoCo являются кинематическими qpos contacts, а не actuator forces.

## Blocking primary

На всех 160 cases одновременно каждая из шести осей должна:

1. иметь pooled normal RMSE ниже zero;
2. выигрывать у zero минимум в 70% cases, то есть не менее 112/160.

Combined normal должен:

1. быть ниже zero;
2. выигрывать у zero минимум 112/160;
3. иметь pooled RMSE ниже shuffled, static и closed.

### Body X=4,18 safeguard

На 80 upper-body-X cases каждая ось отдельно должна:

- иметь pooled normal ниже zero;
- выигрывать минимум 56/80.

### Corner gate

Corner проходит только если на его десяти motions каждая из шести осей:

- pooled normal ниже zero;
- выигрывает минимум 7/10.

Требуется минимум 12/16 прошедших corners.

Ни combined, ни matched, ни tracked-camera diagnostics не могут компенсировать провал оси, body-X safeguard или corner gate.

## Допустимый вывод

При полном успехе: fixed-FOV35 synthetic observer после восьмичасового supervised обучения формирует 72-coefficient state и автономно реконструирует наблюдавшееся grooming после неизменной задержки на новых motions и full geometry grid.

Даже успех не доказывает новое поведение, actuator dynamics, силы, мышцы, closed-loop управление, биологическую память или зеркальные нейроны.
