# Frozen89E: пользовательский результат

Статус: **full preregistered frozen replication go**. Впервые выполнена замороженная репликация после успешной development-серии. Это разрешает подготовить отдельную series90, но не является её результатом.

## Аутентификация

- исходный `summary-32.json`: SHA-256 `c2608558f4fcddd570367010b8293ecd04204099fae6b26cf2935b44618869a3`;
- runner89E: `06e41e7ec789514f4ee8bbd06365b9b51a4570e24f5b1451890795d066c5e1bf`;
- runner89D: `ac85ba29b05535d48bf238ffb955f526b0c4b18419a7526e352afba86ae2304d`;
-89D extract/summary: `32953b4a…` / `fcde095e…`;
- frozen89D model: `82fbfe153ccba204f141737bd052193289b2d9494776ff8c05bd315c320ed85c`;
- frozen84Z: `cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0`;
- identity ridge0,01, foreleg boost4, training/selection false.

Все pins совпали. Full mode, workers6. Motions873–890, views781–792:216 unique cases/648 trials. Actions72/72/72, profiles216/216/216, seeds648 unique.

## Независимый пересчёт

| Gate | Результат | Требование | Итог |
|---|---:|---:|---|
| Identity total |216/216 |≥195 | pass |
| Identity per action |72/72 каждый |≥65 каждый | pass |
| Safety |648/648 |648 | pass |
| Recovery |648/648 |≥584 | pass |
| Completion |648/648 |≥584 | pass |
| Angle wins |648/648/648/646/648 |≥584 каждый | pass |
| Contact vs angle-only |636/648 |≥584 | pass |
| Contact vs common |633/648 |≥584 | pass |
| Foreleg angle/common |215/201 |≥195/195 | pass |
| Head angle/common |213/216 |≥195/195 | pass |
| Reach angle/common |208/216 |≥195/195 | pass |
| Broad controls |7/8 |≥7/8 | pass |
| Mean candidate≤standard |0,124517≤0,124796 | обязательно | pass |
| Mean candidate≤soft |0,124517≤0,130136 | обязательно | pass |
| Mean candidate≤oracle+0,02 |0,124517≤0,144517 | обязательно | pass |

`identity_gate_passed=true`, `angle_gate_passed=true`, `contact_gate_passed=true`, `primary.passed=true` независимо воспроизведены.

Contact wins: standard134, oracle0, soft598, angle636, common633, uncalibrated562, zero648, shuffled648, open642, lesion648. Broad fail только uncalibrated;7/8 пройдено.

## Репликационный вывод

Frozen policy не обучалась и не выбиралась на motions873–890. Routing остался идеальным: candidate=oracle во всех648 trials. Foreleg/common201 прошёл с запасом6; soft598 прошёл с запасом14. Mean candidate лучше standard на0,0002791, примерно0,224%, и soft примерно4,32%.

Эффект robust foreleg относительно standard остаётся небольшим, поэтому frozen go подтверждает стабильность всей composite policy и preregistered gates, а не крупный изолированный causal effect reweighting.

89C no-go остаётся историческим и не переписывается.89E является новой, независимо авторизованной frozen replication после89D go.

## Решение

-89D development go подтверждён отдельной frozen89E;
- frozen89E: **go**;
- теперь разрешена подготовка отдельной series90 с собственным preregistration;
-89E данные нельзя использовать для скрытой настройки series90 final;
- этот результат не доказывает biological mirror neurons или полноценную физическую муху.

## Ограничения

Synthetic truth используется для scoring и oracle diagnostic. Reduced support/geometric contact proxy не являются collision force, muscle dynamics, natural vision или biological-neuron validation. Frozen model не refit; coverage, metrics, routing, controls и decision пересчитаны независимо из648 trial records.
