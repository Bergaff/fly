# Series126 — независимое пользовательское воспроизведение

Полученный от пользователя `summary-66.json` сохранён **без изменений** как `independent-physical-outcome-development-126-user-result.json`.

- SHA-256 пользовательского файла: `c57c6f636b5987628ea1983246344ee8bd77bbd4f37231f5d60880c56432aaf5`.
- Schema/status: `independent-physical-outcome-development-126-v1` / `completed`.
- Разбиение совпало:12 Series106 fit,12 Series109 fit,6 Series109 selection,18 Series112 historical-audit cases.
- Все выбранные alpha, категориальные решения и GO/NO-GO gates совпали с локальным запуском.
- Максимальное абсолютное отличие среди556 числовых научных значений после исключения машинозависимого времени выполнения: `8.82e-10`. Различия соответствуют floating-point реализации платформы и не меняют ни одного вывода.

## Воспроизведённые historical-audit результаты

| Model | User normalized RMSE |
|---|---:|
| constant mean | 0.7933941888 |
| metadata linear | 0.8880660481 |
| raw types | 0.8880824804 |
| graph four-hop | 0.8880826023 |
| rewired graph | 0.8880825727 |
| matched-random graph | 0.8880826479 |
| random-feature MLP | 2.3220677637 |

## Итог

**Series126 воспроизведена: `NO_GO_TEMPORARY_ENGINEERING_CLOSE`.** Graph Core не улучшил primary metric минимум на5% против каждого learned control; его результат практически совпал с raw, rewired и matched-random graph, а constant mean оказался лучше. Поэтому Series127 и Series128 остаются неавторизованными.

Это offline prediction ранее полученных official-FlyGym outcomes. Оно не является новым запуском Graph controller в FlyGym, не переименовывает старые adapters в Graph Core и не устанавливает биологические mirror neurons. Следующий разрешённый этап конечного плана — Series129 immutable final audit.
