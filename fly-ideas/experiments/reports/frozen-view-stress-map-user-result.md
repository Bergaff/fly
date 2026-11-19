# Пользовательский результат серии 79: frozen view stress map

## Происхождение и целостность

Пользователь приложил оригинальный `summary.json`, SHA-256 файла `444637533940d410bbde05d37abf19b7292c68e66069c82ccd6e3bfc2e15411e`. Статус `completed`, mode `full`. Frozen source model SHA `145a07ac…` совпадает с серией 78; runner 78 SHA также совпадает. `no_retraining=true`.

Оригинальные model NPZ, observations, predictions CSV и complete manifest не переданы, поэтому они не пересчитывались независимо.

## Primary

Primary не выполнен. Combined aggregate выглядит положительно, но заранее закреплённая осевая проверка выявила отказ четырёх из шести суставов.

| Ось | Normal | Zero | Wins | Итог |
|---|---:|---:|---:|---|
| left proximal | 0,444381 | 0,430371 | 66/128 | fail |
| left middle | 0,363658 | 0,502599 | 117/128 | pass |
| left distal | 0,473998 | 0,450912 | 82/128 | fail |
| right proximal | 0,434724 | 0,419251 | 64/128 | fail |
| right middle | 0,356628 | 0,491643 | 123/128 | pass |
| right distal | 0,453930 | 0,424631 | 82/128 | fail |

Combined core pooled normal/zero: `0,423599/0,454412`, улучшение 6,78%. Normal также лучше shuffled/static/closed: `0,483547/0,517106/1,000603`. Однако combined score скрывает ухудшение proximal и distal осей, ради чего primary заранее был осевым.

Строго прошли только `9/32` core corners при требовании `24/32`.

Дополнительная структура core cells:

- combined normal ниже zero: 26/32;
- normal ниже всех controls: 31/32;
- все шесть осей ниже zero: 11/32;
- полный строгий критерий с axis wins: 9/32.

## Симметричная граница суставов

Отказ почти зеркально симметричен:

- middle устойчивы: left/right выигрывают 117/128 и 123/128;
- proximal примерно на уровне случайного разделения cases и pooled хуже zero;
- distal выигрывают 82/128 cases, но pooled хуже zero, то есть меньшинство крупных проигрышей перевешивает частые небольшие выигрыши.

Число core cells, где ось не прошла строгий cell-level критерий:

- left/right proximal: 19/32 и 17/32;
- left/right middle: 4/32 и 1/32;
- left/right distal: 12/32 и 12/32.

Это указывает не на общий отказ движения, а на недостаточную геометрическую устойчивость outer joints при сочетаниях view transformations.

## One-factor границы

При изменении одного параметра большинство условий устойчиво. Главные отдельные отказы:

| Условие | Normal | Zero | Clipped fraction |
|---|---:|---:|---:|
| FOV 20° | 0,7466 | 0,4544 | 0,683 |
| FOV 25° | 0,5083 | 0,4544 | 0,200 |
| camera Z 0,28 | 0,7317 | 0,4544 | 0,024 |
| camera Z 0,34 | 0,4836 | 0,4544 | 0,008 |
| body Y −0,60 | 0,5773 | 0,4544 | 0,182 |
| body Y +0,60 | 0,5436 | 0,4544 | 0,013 |

Camera-side sweep устойчив даже от 0,08 до 0,50. Body X сохраняет combined преимущество вплоть до 3,60–4,40, хотя при положительном сдвиге не все оси лучше zero. FOV 28–72 и body Y примерно −0,45…+0,45 в one-factor режиме в основном устойчивы.

Следовательно, основной отказ core primary создаётся не одиночными параметрами, а их взаимодействиями на углах многомерного пространства.

## Core corner interactions

Дескриптивно:

- FOV 30: strict pass 2/16;
- FOV 70: 7/16;
- body X 3,82: 7/16;
- body X 4,18: 2/16;
- camera Z 0,36: 3/16;
- camera Z 0,56: 6/16.

Особенно плохи комбинации малого FOV, низкой камеры и/или неблагоприятного body X. Худший core corner 03:

- FOV 30;
- camera side 0,14;
- camera Z 0,36;
- body X 4,18;
- body Y −0,32;
- normal/zero `0,506/0,454`.

Эти факторные сравнения описательные: cells зависимы и это не отдельный рандомизированный причинный эксперимент.

## Evaluation envelope и clipping

Среди 32 evaluation corners:

- combined normal ниже zero только в 10/32;
- все оси лучше zero только в 7/32;
- normal ниже всех temporal controls в 32/32.

Худшие точки объединяют FOV 28°, camera Z 0,34 и другие крайние параметры. Например eval corner 02 имеет normal `0,774` против zero `0,454`, clipping `0,406`.

Корреляция clipped fraction с `normal − zero`:

- все cells: `r≈0,726`;
- evaluation corners: `r≈0,838`;
- core corners: `r≈0,171`.

Clipping является сильным маркером тяжёлого внешнего отказа, но не объясняет большинство core failures, где clipping часто близок к нулю.

## Post-hoc probes

Точные view-конфигурации series 78 tests 141 и 146 исключены из primary. На четырёх новых движениях обе теперь имеют все оси ниже zero:

- probe 1 normal/zero `0,4316/0,4544`;
- probe 2 `0,3991/0,4544`.

Это показывает motion × view interaction: прежний отказ не воспроизводится автоматически на других движениях. Эти post-hoc probes не исправляют провал core primary.

## Научный вывод

Поддерживается:

> Frozen model 78 сохраняет combined signal и особенно устойчиво декодирует middle joints во многих view cells, но не обеспечивает preregistered six-axis robustness на полном training hyperrectangle.

Не поддерживается:

> View augmentation серии 78 создала равномерно устойчивое представление всех шести суставов во всех сочетаниях обучающего диапазона.

Серия 78 остаётся валидным успехом на своей независимой батарее 10 view-motion combinations. Серия 79 уточняет границу и не отменяет её, но запрещает широкое обобщение на весь hyperrectangle.

## Следующий шаг

Не следует просто расширять диапазон augmentation. Однофакторная устойчивость уже широка, а отказ возникает при сочетаниях. Следующая обучающая модель должна изменить представление:

1. spatial canonicalization по положению и масштабу тела до feature history;
2. balanced sampling углов и внутренних точек многомерного view space, а не только независимый continuous random stream;
3. отдельные multi-scale признаки для proximal/distal сегментов;
4. frozen проверка на новых core/evaluation corners без настройки по cells серии 79.

До нового восьмичасового запуска разумен короткий bounded prototype canonicalization, чтобы проверить RGB/feature invariance и отсутствие constant-input дефекта.
