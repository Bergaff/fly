# Серия 78: view-robust autonomous grooming

## Основание

Серия 76 показала matched success, но полный отказ geometric transfer. Серия 77 показала успешный autonomous replay из 72 коэффициентов после задержки в matched view. Серия 78 проверяет следующий заранее определённый вопрос: можно ли обучить зрительное отображение на разнообразии геометрии и затем сохранить autonomous replay на новых сочетаниях движения и вида.

## Один длительный расчёт

Активное обучение длится ровно 8 часов и использует два worker-процесса. Демонстратор и наблюдатель остаются двумя отдельными мухами. Пользователь запускает, продолжает или запрашивает паузу одним BAT:

`RUN-EIGHT-HOUR-VIEW-ROBUST-AUTONOMOUS-GROOMING.bat`

Среда не устанавливается через BAT. Используется среда приложения `workspace/.venv-two-flies`.

## Training distribution

Motion seed `7801`, view seed `7803`. Для каждого training episode независимо и детерминированно варьируются:

- FOV: 30–70°;
- lateral camera separation: 0,14–0,42;
- camera height: 0,36–0,56;
- body x: 3,82–4,18;
- body y: −0,32–0,32.

Движения используют piecewise5, piecewise9, harmonic и chirp. Teacher содержит шесть углов трёх суставов каждой передней лапы. Это supervised ridge, а не биологическое обучение.

Visual preflight проверяет движение каждого сустава, временную изменчивость RGB и различие нескольких augmentation views до создания долгой серии.

## Frozen evaluation

До обучения создаются движения 141–150 seed `7802`. Их SHA блокируются от training stream. View seed `7804` задаёт независимые комбинации, включая немного более широкий диапазон:

- FOV: 28–72°;
- camera separation: 0,12–0,46;
- camera height: 0,34–0,59;
- body x: 3,76–4,24;
- body y: −0,38–0,38.

После обучения модель замораживается. Каждый holdout дополнительно считается в matched view только как диагностический reference.

## Autonomous replay

В transfer view frozen model формирует framewise estimates, которые сжимаются в `6 × 12 = 72` cosine coefficients. State не обновляется `0,5 с`. Replay получает только coefficient state и phase. Ему запрещены RGB, teacher commands и сохранённый framewise prediction buffer.

Controls:

- shuffled observation;
- static first frame;
- closed black input;
- stationary zero baseline.

MuJoCo contacts измеряются после кинематического назначения qpos.

## Primary

Primary относится только к десяти unseen view-motion combinations, не к matched diagnostic.

Для каждой из шести осей одновременно:

1. pooled autonomous normal RMSE ниже zero;
2. normal выигрывает у zero минимум на 7/10 движений.

Combined normal должен:

1. быть ниже zero;
2. выиграть у zero минимум 7/10;
3. быть ниже каждого из shuffled, static и closed pooled controls.

Нельзя после результата исключать оси, holdout или view conditions. Matched score не может компенсировать провал transfer primary.

## Допустимый вывод

При успехе: synthetic supervised observer после view-augmented training может сжать наблюдавшееся действие в неизменное состояние и автономно реконструировать его после задержки на новых сочетаниях вида и движения.

Даже при успехе не поддерживаются утверждения о новом поведении, actuator dynamics, силах, мышцах, closed-loop управлении, биологической памяти или зеркальных нейронах.
