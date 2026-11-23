# Этап1 Connectome Advantage: результат полного запуска пользователя

Статус: **completed, primary no-go**.

Источник: пользователь вставил полный `summary.json`. SHA скрипта в результате `dde8ea3d…` совпадает с закреплённым `experiments/templates/91_connectome_advantage_stage1.py`. Выполнены12 seeds, workers6. Исходные `seed_metrics.csv`, папка запуска и `complete.json` независимо не получены, поэтому агрегаты анализируются как присланный результат, а не как построчно проверенная папка.

## Заранее заданный primary

Для успеха `structured96` должна была одновременно:

1. превышать accuracy `shuffled96` минимум на0,02;
2. иметь trajectory RMSE не более0,98 от RMSE `shuffled96`;
3. выигрывать paired accuracy минимум на8 из12 seeds.

Результат: **ни один из трёх обязательных критериев полностью не выполнен**.

| Метрика | structured96 | shuffled96 | dense96 |
|---|---:|---:|---:|
| Accuracy | 0,991898 | 0,987500 | 0,993056 |
| Trajectory RMSE | 0,084110 | 0,078817 | 0,083832 |
| Accuracy после lesion10/96 | 0,990046 | 0,985648 | 0,985185 |
| RMSE после lesion10/96 | 0,107745 | 0,096830 | 0,109396 |
| Trainable parameters | 2505 | 2505 | 5577 |

## Проверка gates

- Accuracy margin structured минус shuffled: `+0,004398`, или **+0,44 процентного пункта**, при требовании `+0,02`.
- Предельный RMSE для structured: `0,077241`; фактически `0,084110`.
- Structured RMSE на **6,71% хуже** parameter-matched shuffled.
- Paired accuracy wins: **6/12**, требовалось **8/12**.
- Dense96 имеет лучшую accuracy, но преимущество над structured всего около0,12 процентного пункта; по RMSE dense также немного лучше structured, но хуже shuffled.

## Повреждение10 из96 units

- Accuracy уменьшилась у structured и shuffled одинаково: примерно на0,185 процентного пункта.
- У dense accuracy уменьшилась примерно на0,787 процентного пункта.
- RMSE увеличилась у structured на28,10%, у shuffled на22,85%, у dense на30,49%.

Это не поддерживает преимущество structured96 над parameter-matched shuffled96 по устойчивости к данному повреждению. Dense96 описательно сильнее теряет accuracy, но у неё другой parameter budget, поэтому это не спасает primary.

## Интерпретация

Первый preregistered тест **не обнаружил преимущества** заранее заданной structured96 topology. Все три модели почти достигли потолка accuracy, поэтому классификация оказалась слабым разделителем. Более чувствительная trajectory RMSE дала преимущество перемешанной parameter-matched сети, а не structured96.

Это полезный отрицательный результат. Нельзя ослаблять thresholds, называть +0,44 процентного пункта успехом или переходить к FlyWire mapping на основании этого запуска.

## Допустимый следующий шаг

Если программа продолжается, следующий этап должен быть новым preregistered development benchmark, а не повтором тех же seeds. Допустимо заранее усилить задачу так, чтобы убрать ceiling: fewer demonstrations, новые комбинации действий, более длинная задержка, continual learning и несколько уровней lesions. После разработки потребуется отдельная frozen replication на нераскрытой батарее. Старые12 seeds остаются раскрытыми и не могут быть финальным holdout.

## Ограничения

Это artificial96 benchmark.96 units не являются нейронами мухи, structured mask не является коннектомом, а синтетические действия не устанавливают преимущества животного мозга или биологический mirror mechanism.
