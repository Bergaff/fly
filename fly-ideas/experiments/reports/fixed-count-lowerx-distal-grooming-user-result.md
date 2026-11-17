# Серия 84S: пользовательский результат fixed-count lower-X distal model

## Статус и источник

Пользователь прислал завершённый `summary-11.json`. SHA-256:

`7af53f0d91ab9d12da61d7d0c5f4d209e6e1cd47647ab9c0568dad1943dbc126`

Schema `fixed-count-lowerx-distal-grooming-result-v1`, status `completed`, mode `fixed_count`, completion basis `committed_candidate_count`. Summary содержит 160 final cases: motions321–330 ×16 corners.

Frozen source84R model SHA совпадает с опубликованным результатом:

`1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c`.

Candidate84S model SHA по summary:

`a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f`.

Полная папка результата, SQLite, model NPZ, protocol и complete manifest не передавались. Поэтому независимо проверены JSON records и агрегаты, но не candidate NPZ, runner SHA или файловый manifest пользователя.

## Fixed-count обучение и accounting

Завершены точно:

- candidates `16 384/16 384`;
- accepted `16 384/16 384`;
- training frames `802 816`, ровно16 384 ×49;
- batches `8 192`;
- timed candidates `16 384`;
- missing timing candidates `0`.

Wall diagnostic `27 100,516` с, то есть 7 ч31 мин40,516с. Coordinator batch wall sum `25 473,711` с, worker CPU sum `19 274,922` с. Throughput относительно полного wall diagnostic примерно2 176 candidates/hour.

Максимальная партия заняла14,497с, максимальный coordinator/worker ratio11,80. Полных batch records в присланном summary нет, поэтому локализовать этот эпизод нельзя. Он не повлиял на completion: серия закончилась только после16 384 committed candidates.

Таким образом, QuickEdit/wall-time дефект прежней серии не повторился как нарушение объёма обучения.

## Preregistered decision

`primary.passed = true`.

Все blocking components прошли:

- каждая из шести осей ниже zero и имеет не менее112/160 wins;
- right distal ниже frozen84R и имеет100/160 wins против comparator;
- остальные оси не хуже source84R более чем на5%;
- combined ниже source84R, zero и всех controls;
- lower-X right-distal target gate73/80 vs zero и62/80 vs source84R;
- обе body-X safeguards;
- обе camera-Z safeguards;
- corners16/16 при требовании12/16;
- state immutable160/160.

Это первый полный preregistered uniform six-axis model go после неудач серий83,84 и84R. По плану он ещё не разрешает series85: сначала нужна frozen replication model84S на новом motion set без retraining.

## Global axes

| Ось | Candidate | Source84R | Zero | Wins vs zero | Wins vs source | Gate |
|---|---:|---:|---:|---:|---:|---|
| left proximal | 0,283536 | 0,288836 | 0,400562 | 152/160 | 80/160 | pass |
| left middle | 0,180192 | 0,177411 | 0,445022 | 160/160 | 76/160 | pass |
| left distal | 0,448739 | 0,455130 | 0,489143 | 151/160 | 100/160 | pass |
| right proximal | 0,305568 | 0,309952 | 0,412527 | 148/160 | 82/160 | pass |
| right middle | 0,193819 | 0,192982 | 0,456579 | 160/160 | 90/160 | pass |
| right distal | 0,444486 | 0,450463 | 0,486396 | 147/160 | 100/160 | pass |

Candidate улучшает source84R pooled для proximal и distal на1,3–1,8%. Middle axes немного хуже source84R:

- left middle хуже на1,57%;
- right middle хуже на0,43%.

Это находится внутри preregistered 5% non-degradation bound и далеко ниже zero.

Против zero distal улучшение:

- left: 8,26%;
- right: 8,62%.

## Combined и controls

Combined candidate/source84R/zero:

`0,327295 / 0,331228 / 0,449626`.

Candidate ниже source84R на1,19% и ниже zero на27,21%. Controls:

- shuffled `0,439194`;
- static `0,512505`;
- closed `0,488003`.

По отдельным cases candidate combined выигрывает:

- zero160/160;
- source84R104/160;
- shuffled160/160;
- static160/160;
- closed146/160.

Pooled combined ниже всех controls, как требовал protocol.

## Target lower-X right distal

На body X=3,82:

- candidate `0,439821`;
- source84R `0,452042`;
- zero `0,486396`;
- wins vs zero `73/80`, требовалось60;
- wins vs source84R `62/80`, требовалось48.

Candidate ниже zero на9,58% и source84R на2,70%. Target gate пройден с запасом13 и14 wins соответственно, а не на границе.

Остальные lower-X axes также прошли. Left/right distal имеют соответственно74/80 и73/80 wins против zero. Поэтому прежний count failure84R55/80 не повторился.

## Geometry safeguards

Обе body-X группы прошли все оси:

- X=3,82: distal left/right74/80 и73/80;
- X=4,18:77/80 и74/80.

Обе camera-Z группы прошли:

- Z=0,36: distal74/80 и73/80;
- Z=0,56:77/80 и74/80.

Это uniform result по preregistered grouped gates, а не выбор удачной geometry post hoc.

## Corner gate

Прошли все `16/16` corners. Минимальные axis wins в любой cell:

- proximal:9/10;
- middle:10/10;
- left/right distal:8/10.

Таким образом, ни одна cell не находится ровно на минимальном пороге7/10. Это существенно сильнее84R, где прошли13/16.

## Motion consistency

Lower-X right distal по восьми corners:

- motions321,326,328,329,330: не менее6/8 wins против source84R;
- motion322:7/8;
- motion325:8/8;
- слабее comparator на motion327:3/8, но против zero8/8;
- motion323:4/8 vs source,8/8 vs zero.

Отдельные motion-dependent differences остаются, но preregistered pooled/count gates и все corner gates проходят. Нельзя post hoc исключать motions323/327 или объявлять каждое движение одинаково улучшенным.

## State, RGB и audit

Во всех160/160 cases:

- state содержит72 coefficients;
- SHA до и после задержки0,5с совпадает;
- пустых RGB cases нет;
- minimum changed RGB values33 662;
- maximum candidate clipping fraction0,01361.

Overlap audit охватывает128 из16 384 accepted candidates и не является exhaustive. По десяти уникальным motions:

- under0,001°:0;
- under1°:0;
- under5° frame queries:96 из490.

Это снижает риск exact trajectory replay, но не доказывает отсутствие близких training fragments во всём наборе.

## Решение

1. Серия84S фиксируется как полный preregistered model go.
2. Model84S и её SHA теперь замораживаются; дополнительное обучение или tuning до replication запрещены.
3. Следующий этап только read-only frozen replication на новых motions/seeds и тех же blocking X/Z/corner gates.
4. Series85 остаётся заблокированной до успешной replication.
5. Старые BAT 84R/84S не перезапускать для улучшения результата.

## Ограничения claims

Это synthetic supervised fixed-FOV reconstruction. Результат не демонстрирует natural vision, новое действие, actuators, силы, мышцы, closed-loop correction, биологический мозг или mirror neurons.
