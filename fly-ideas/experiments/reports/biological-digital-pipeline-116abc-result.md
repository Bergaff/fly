# Series116A–C — три направления в цифровой среде

Series116 не переименовывает искусственные96 channels. Она строит новую систему с реальными FlyVis type labels, reviewed FlyWire root sets и official v783 structural connectivity.

## 116A — реальная type/root карта

Создана матрица61×61. Каждая строка и колонка имеет FlyVis type, reviewed FlyWire root set и source type relation. Матрица содержит2 489 ненулевых type edges и7 335 202 synapses, агрегированных из72 954 строк официальной таблицы. Включено64 667 уникальных roots. Gate pass.

Это type/root-set structural map, не61 отдельных нейрон и не переделанная artificial96×96. Старая96×96 остаётся инженерной; новая61×61 является биологически индексированной заменой.

## 116B — цифровой motor readout

Из прямых и двухшаговых structural paths получены8 достижимых DN types: `DNc01`, `DNc02`, `DNg33`, `DNp11`, `DNp27`, `DNp30`, `DNp31`, `DNpe053` (по2 roots каждого типа в pinned annotation table). Frozen digital readout обучен на12 случаях и проверен на6 held-out случаях:6/6 правильных действий против2/6 у shuffled structure и2/6 у zero input. Gate pass.

Это digital structural readout. Названия трёх действий — frozen project labels; результат не утверждает, что эти DN-типы биологически управляют именно этими действиями.

## 116C — observe/execute evaluation

Pipeline выполнен на6 held-out случаях. Same-action centered cosine=0.874377; other-action=0.871965; shuffled-structure same-action=0.507901. Structure specificity поддержана (margin0.366476), но action specificity не прошла finalized Series116 threshold0.01 (margin0.002413). Это development analysis: threshold зафиксирован перед checked run, но после разработки метода, а не в независимой confirmation. Method выполнен и выдаёт descriptive type candidates, но biological mirror-neuron claim=false.

## Итог

Все три цифровых направления **реализованы**: real type/root structural map, DN-path digital readout и observe/execute evaluation. Положительный результат есть для structural map и digital readout; mirror analysis показывает структурную, но не достаточную action specificity. Никакой biological function claim не делается.

Runner SHA-256 `73b4eedcaab384cf63fc48da749bb7ffdef0b2ebc83a1f7d7a0e66c9139e114a`; result SHA-256 `0ef6b1bdf05c3bd81b061e9232fe511c905af947c26e1f9c10e8eab341ba6d9a`.

Запуск: `experiments\RUN-BIOLOGICAL-DIGITAL-PIPELINE-116ABC.bat`.
