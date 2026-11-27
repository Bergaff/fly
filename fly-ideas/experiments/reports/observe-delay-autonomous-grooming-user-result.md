# Пользовательский результат серии 77: observation, state, delay, autonomous replay

## Происхождение и целостность

Пользователь прислал полный `summary.json`; локальная result-папка, predictions CSV и contact CSV не передавались. Отчёт имеет статус `completed`, режим `full`, holdout seed `7702`, tests `121–130` и ожидаемый SHA frozen model серии 75 `bb8de6a8…`. SHA runner 76 также совпадает с опубликованным preregistered pipeline.

Для всех десяти тестов SHA 72-коэффициентного состояния до и после задержки 0,5 с совпадает. Во время replay разрешены только coefficient state и phase; RGB, teacher commands и framewise prediction buffer запрещены.

## Primary

Primary выполнен без исключений.

| Ось | Normal replay RMSE | Zero RMSE | Wins | Итог |
|---|---:|---:|---:|---|
| left proximal | 0,201079 | 0,495714 | 10/10 | pass |
| left middle | 0,151511 | 0,478069 | 10/10 | pass |
| left distal | 0,340069 | 0,484841 | 10/10 | pass |
| right proximal | 0,216964 | 0,502447 | 10/10 | pass |
| right middle | 0,154809 | 0,485100 | 10/10 | pass |
| right distal | 0,345758 | 0,487467 | 10/10 | pass |

Combined pooled RMSE:

| Replay | RMSE |
|---|---:|
| normal compressed state | 0,248201 |
| shuffled state | 0,433824 |
| zero | 0,489004 |
| static state | 0,612971 |
| closed state | 1,030952 |

Normal выигрывает у zero на всех `10/10` holdout и снижает pooled RMSE на `49,24%`. Он лучше всех трёх заранее заданных controls, хотя primary требовал минимум два.

Shuffled control всё ещё лучше zero в pooled aggregate. Это ожидаемо возможно потому, что перестановка сохраняет распределение поз, но normal лучше shuffled на `42,79%`. Следовательно, временной порядок состояния содержит существенную информацию.

## Contacts

Mean kinematic contact F1: `0,955895` normal против `0,886689` zero, разница `+0,069206`. Normal лучше в `8/10` тестов. В tests 126 и 130 zero немного лучше normal, поэтому contact reconstruction не универсальна для каждого движения.

Contact F1 высокий даже у zero. Это означает, что геометрическая разметка контактов частично определяется базовой позой и широкими контактными областями; её нельзя интерпретировать как доказательство силового выполнения grooming.

## Научный вывод

Поддерживается узкий заранее заданный вывод:

> После matched RGB-наблюдения frozen visual decoder создаёт 72-мерное coefficient state. Неизменное состояние переживает задержку 0,5 с и затем воспроизводит наблюдавшуюся последовательность точнее zero, shuffled, static и closed controls без доступа replay к RGB, teacher-командам или framewise prediction buffer.

Это действительно демонстрирует автономность replay относительно входного видео после observation window. Это не означает изобретение нового действия: state является cosine-сжатием framewise estimates наблюдавшейся траектории.

Результат серии 76 ограничивает обобщение: механизм доказан только для исходного matched close-up observation distribution. Модель не перенеслась на FOV/body transformations.

## Что результат не доказывает

- actuator dynamics, силы, мышцы или closed-loop correction;
- физически устойчивое выполнение grooming;
- нейронную память или модель биологического мозга;
- mirror neurons;
- генерацию нового поведения;
- устойчивость к новому ракурсу, масштабу или положению тела.

Replay назначает qpos кинематически, после чего MuJoCo только регистрирует геометрические contacts.

## Следующий этап

Этапы A и B завершены. Наиболее информативное продолжение должно быть новой preregistered серией, а не post-hoc изменением primary:

1. обучить модель с camera/FOV/body augmentation;
2. снова заморозить её до transfer-теста;
3. проверить autonomous state/replay одновременно в matched и ранее проваленных view conditions;
4. отдельно, если требуется физическое управление, заменить qpos replay на actuators и closed-loop contact objective.

## Ограничение проверки

Числа валидированы по присланному текстовому `summary.json`. Без локальной result-папки агент не может независимо пересчитать NPZ/CSV или проверить checksummed manifest.
