# Закрытие synthetic joint optimization после Stage96

## Решение

Пользователь явно выбрал остановить дальнейшую синтетическую оптимизацию общей accuracy+trajectory hypothesis вместо запуска новой узкой frozen few-shot/classification replication. Поэтому Stage97 не создаётся и условно выбранный4-часовой бюджет не применяется.

## Сохранённая последовательность результатов

1. Stage91: preregistered no-go против parameter-matched shuffled96; classification почти у потолка, trajectory RMSE хуже.
2. Stage92: более трудный development no-go; средние few-shot harsh эффекты прошли, paired stability не прошла.
3. Stage94: frozen computational pass после common-random-number correction и trajectory weight4, но accuracy margin прошёл только на три net correct predictions сверх порога.
4. Stage95: Stage94 advantage сохранился против shuffled/temporal, но общий joint gate провален против learned-sparse96 и RNN54 по trajectory stability.
5. Stage96: exact-budget hybrid подтвердил structured classification branch и прошёл RNN54, но learned-sparse96 остался лучше по budget30 trajectory; общий candidate=false.

## Итог

Поддержан узкий development-вывод: structured classifier topology в этой синтетической задаче устойчиво превосходит shuffled, temporal и learned same-budget classifier branches. Поддержан инженерный вывод: task-specialized hybrid лучше monolithic RNN54 при том же числе параметров.

Не поддержан общий вывод о превосходстве structured/hybrid architecture одновременно по classification и trajectory across budgets и сильных controls. Нельзя исключать learned-sparse96, budget30 или RMSE после просмотра результатов.

Ни один результат этой линии не является evidence о коннектоме мухи: masks инженерные, units программные, stimuli/actions синтетические. Series90 gate reviewed FlyVis→FlyWire mapping и validated motor readout остаётся закрыт.

## Условия возможного возврата

Возврат допустим только по новому явному решению пользователя. Потребуются новая заранее записанная hypothesis, новый runner и untouched seeds. Старые Stage92/94/95/96 seeds и результаты раскрыты и не могут быть переименованы в frozen подтверждение новой узкой hypothesis.
