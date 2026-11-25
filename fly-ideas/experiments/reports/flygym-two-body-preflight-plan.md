# Series100: official FlyGym two-body preflight

## Решение и граница

После явного решения пользователя начата новая линия настоящего физического тела FlyGym. Это не Stage97 и не возврат к закрытой synthetic joint optimization Stage91–96. Старые gates, seeds и результаты не переименовываются.

Series100 является коротким техническим blocking gate. Она не обучает модель и не является научным опытом по наблюдению.

## Зачем этот этап

Series88–89E использовали reduced six-joint support surrogate и геометрический contact proxy. Series100 должна впервые проверить в локальном окружении пользователя:

- официальный `flygym==2.1.1`;
- два отдельных полных тела `NeuroMechFly` в одном `FlatGroundWorld`;
- настоящие MuJoCo position actuators;
- joint response, actuator forces и ground-contact sensors;
- конечное состояние и сохранение опоры обоих тел.

На preflight демонстратор получает диагностическую front-leg команду, а наблюдатель получает ту же команду с задержкой 0,08 с. Это проверка двух физических тел, а не визуальное наблюдение: RGB, frozen89E state и biological mapping отсутствуют.

## Закреплённый gate

Короткий run длится 0,36 с model time при timestep 0,0005 с. Gate проходит только если одновременно:

1. версия FlyGym точно 2.1.1;
2. созданы `demonstrator` и `observer` класса `NeuroMechFly`;
3. у каждого не менее 30 leg actuators;
4. все записанные physics values конечны;
5. front-leg response каждого тела не меньше 0,015 rad;
6. actuator force ненулевая;
7. ground contact хотя бы раз зарегистрирован у обеих мух;
8. thorax Z обеих мух остаётся в диапазоне 0,15–2,5 мм.

Gate не содержит accuracy, imitation или biological claim.

## Запуск на Windows

1. Открыть Fly Ideas двойным щелчком по `START.bat`.
2. Перейти «Мозг» → «Данные и окружение» → «Зрение и физическое тело».
3. Нажать «установить только FlyGym». Установка создаёт `workspace/.venv-flygym` через интерфейс; FlyVis для этого этапа не нужен.
4. Дважды щёлкнуть `experiments/RUN-FLYGYM-TWO-BODY-PREFLIGHT.bat`.
5. В окне нажать «Запустить короткую проверку».

Результат автоматически открывается и содержит `ИТОГ.txt`, `summary.json`, `physics_trace.csv` и `complete.json`. Ошибка сохраняется в копируемый `ОШИБКА.txt`.

## Следующий шаг только после go

После технического go разрешён отдельный короткий adapter prototype: неизменяемый output frozen89E преобразуется в заранее заданные target channels официального FlyGym-тела. Он обязан сравнить physical tracking, contact, stability и controls. Series100 сама такой adapter не реализует и не подтверждает его работоспособность.
