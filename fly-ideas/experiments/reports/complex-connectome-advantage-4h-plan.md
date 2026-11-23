# Комплексный Connectome Advantage: четырёхчасовой development benchmark

## Причина

Stage91 завершился preregistered no-go. Accuracy всех трёх моделей была около99%, а structured96 имела trajectory RMSE на6,71% хуже parameter-matched shuffled96. Нельзя ослаблять старые gates или переходить к FlyWire. Stage92 является новым development benchmark, который ищет кандидатуру для будущей frozen replication на более трудной задаче. Он не является репликацией Stage91 и не доказывает преимущество биологии.

## Запуск

Двойной щелчок: `experiments/RUN-COMPLEX-CONNECTOME-ADVANTAGE-4H.bat`.

GUI предлагает workers2/4/6/Максимум. На Windows QuickEdit отключается и проверяется. При первом запуске один полный replicate используется только для калибровки. До основных результатов фиксируется число replicates, рассчитанное на приблизительно четыре часа wall time при выбранном числе workers. Поэтому завершение определяется fixed replicate count, а не прошедшими часами. Калибровочный replicate в результат не входит.

После каждого replicate транзакционно обновляются SQLite и `INCOMPLETE.json`. Повторный запуск BAT продолжает последнюю незавершённую папку. Ошибка автоматически пишется в `ПОСЛЕДНЯЯ-ОШИБКА-КОМПЛЕКСНЫЙ.txt`.

## Задача

Каждый пример содержит упорядоченную пару из трёх действий:

1. foreleg rubbing;
2. head-directed grooming;
3. reach-withdraw.

Всего девять ordered classes. Модель получает12 моментов шести синтетических каналов, после чего software latent state удерживается0,5с без нового сенсорного входа. Это не биологическая память.

Два режима данных на каждый ordered class:

- few-shot5;
- budget30.

## Модели

- `structured96`: заранее заданная модульная input mask;
- `shuffled96`: та же точная сумма связей после перемешивания, основной parameter-matched контроль;
- `dense96`: те же96 units, но больше параметров, диагностический unit-matched контроль.

Stage91 runner закреплён SHA `dde8ea3d…`. Его training implementation и mask constructor импортируются только при точном совпадении SHA.

## Семь условий

1. clean;
2. high view mixing;
3. occlusion;
4. lesion10/96;
5. lesion24/96, то есть25%;
6. corruption software state Gaussian noise0,08;
7. combined harsh: сильный view shift, lesion25% и state noise.

Каждый replicate использует новые детерминированные seeds. Старые12 seeds Stage91 не переиспользуются.

## Development gate

Structured96 становится только **кандидатом** для отдельной frozen replication, если одновременно:

- в few-shot5 combined harsh средняя accuracy выше shuffled96 минимум на0,03;
- там же RMSE structured не больше0,97 RMSE shuffled;
- strict dual wins, одновременно выше accuracy и ниже RMSE, составляют минимум60% harsh сравнений;
- strict dual wins составляют минимум55% всех сравнений.

Near-miss является no-candidate. Dense96 не может открыть gate, потому что имеет другой parameter budget.

Даже полный development go не открывает FlyWire mapping. Сначала потребуется новый runner, замороженная выбранная архитектура, полностью новые seeds и независимая blocking replication.

## Выходы

- `protocol.json`: fixed count, calibration, модели, условия и gate;
- `study.sqlite3`: строки каждого replicate и условия;
- `summary.json`: агрегаты и development gate;
- `ИТОГ.txt`: копируемый русский итог;
- `complete.json`: SHA protocol, summary и SQLite.

## Ограничения

96 units остаются инженерными. Модульная маска не является коннектомом. State corruption не моделирует молекулярную или клеточную память. Synthetic ordered actions не устанавливают преимущества мозга мухи или зеркальные нейроны. Выбранная по этому development benchmark архитектура обязательно подлежит отдельной frozen replication.
