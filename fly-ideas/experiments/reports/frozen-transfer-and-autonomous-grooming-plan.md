# Серии 76–77: frozen transfer и автономный grooming

## Этап A, серия 76

Замороженная успешная модель серии 75 проверяется без дообучения на новых holdout 101–110 seed 7602.

Условия: matched, FOV 50°, FOV 65°, lateral camera, body shift, one eye, central/distal mask и temporal shuffle. Primary требует matched преимущество каждой оси над zero с минимум 7/10 wins. Для каждой оси минимум два из четырёх geometric transfer условий должны иметь pooled RMSE ниже zero.

## Этап B, серия 77

На новых holdout 121–130 seed 7702 frozen модель 75 наблюдает двухсекундный grooming. Её framewise оценки сжимаются в 72 коэффициента: 12 cosine coefficients для каждого из шести суставов. Затем состояние не меняется 0,5 с. Replay получает только coefficients и replay phase; RGB, teacher commands и сохранённый framewise prediction buffer запрещены.

Контроли состояния строятся после shuffled, static и closed observations. Primary требует autonomous normal replay ниже zero по каждой оси и минимум 7/10 wins, а combined normal также должен превосходить минимум два из трёх observation controls.

MuJoCo contact trace измеряет контакт шести сегментов с головой. Это контакты после кинематической установки qpos, не actuator dynamics, силы или closed-loop control. Contact F1 является вторичным показателем.

## Запуск

Сначала двойным щелчком:

```text
experiments\RUN-FROZEN-VISIBLE-GROOMING-TRANSFER.bat
```

Затем независимо:

```text
experiments\RUN-OBSERVE-DELAY-AUTONOMOUS-GROOMING.bat
```

В обоих случаях выбирается папка завершённой серии 75. Нового восьмичасового обучения нет; исходная модель read-only.

## Ограничения

Это synthetic frozen evaluation. Серия 77 автономно реконструирует уже наблюдавшееся действие из сжатого состояния, но не создаёт новое поведение и не использует физические actuators. Нет биологического мозга, мышц, сил, естественного зрения или доказательства зеркальных нейронов.
