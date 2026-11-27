# Серия85: пользовательский результат shared latent population prototype

## Статус

Пользователь прислал `summary-19.json`, SHA-256:

`f3fc151bedebaaac8600412172696157f9491144ac23fb7c23a11d76a479d4db`.

Schema `shared-latent-population-result-v1`, status `completed`. Exact runner85 SHA `cdef42fd5f4f45d7b5b37ab01f2b3ba4af22663265b1e1980254a7b44596b210`, runner84AA SHA и selected model84Z SHA совпадают. Training отсутствовал. В summary ровно320 уникальных cases: motions451–470 × corners1–16.

`primary.passed = true`: обе независимо blocking batteries прошли все preregistered gates. Это operational shared-population prototype go85. По roadmap разрешён переход к отдельно preregistered series86 с несколькими действиями и compositional holdout.

## Граница независимой проверки

Fixture заново вычислил из320 records:

- pooled reconstruction metrics;
- все30 reported unit correlations из sufficient statistics;
- correlation margins против shuffled/static/closed;
- dual-active classification6/6 в каждой battery;
- matched-private performance;
- state immutability;
- структуру records и audit.

Все эти значения совпали с summary. RSA threshold и сравнение с p95 проходят по reported значениям, однако motion-level observation/execution signatures или45 distance pairs в summary не сохранены. Поэтому RSA невозможно независимо пересчитать из переданного файла. Это ограничение экспорта, а не обнаруженный failure, но результат нельзя называть полностью independently recomputed.

## Frozen identities

- runner85 `cdef42fd…`;
- runner84AA `846bf4b5…`;
- selected model84Z `cb761051…`;
- selected variant `ridge_0175`;
- shared units6;
- private observation units6;
- common decoder coefficients72;
- training false;
- seeds8502/8503;
- motions451–470.

## Battery1: motions451–460

Status pass, dual-active units6/6.

| Unit | Shared correlation | Лучший control | Margin |
|---|---:|---:|---:|
| left proximal |0,772952|0,148733|0,624219|
| left middle |0,942882|0,400721|0,542160|
| left distal |0,356914|0,072879|0,284035|
| right proximal |0,759294|0,144899|0,614395|
| right middle |0,947476|0,425541|0,521935|
| right distal |0,378950|0,057409|0,321542|

Все units выше0,20 и выше temporal/static/closed controls. Требовалось4/6.

RSA:

- reported shared correlation `0,749845`;
- shuffled p95 `0,408724`;
-1000 permutations;
- gate pass.

Combined reconstruction:

- shared observation `0,351940`;
- equal-budget private84V `0,353931`;
- execution mode `0,028636`;
- zero `0,498117`;
- shuffled `0,477466`;
- static `0,552527`;
- closed `0,548954`.

Shared observation лучше private84V на0,562%, хотя gate допускал ухудшение до2%.

## Battery2: motions461–470

Status pass, dual-active units6/6.

| Unit | Shared correlation | Лучший control | Margin |
|---|---:|---:|---:|
| left proximal |0,807604|0,287050|0,520554|
| left middle |0,957481|0,202814|0,754667|
| left distal |0,440579|0,113800|0,326779|
| right proximal |0,798144|0,285509|0,512635|
| right middle |0,954174|0,189120|0,765053|
| right distal |0,515668|0,145354|0,370314|

RSA:

- reported shared correlation `0,793694`;
- shuffled p95 `0,340773`;
-1000 permutations;
- gate pass.

Combined reconstruction:

- shared observation `0,300359`;
- equal-budget private84V `0,304586`;
- execution mode `0,027419`;
- zero `0,448382`;
- shuffled `0,436895`;
- static `0,520316`;
- closed `0,536156`.

Shared observation лучше private84V на1,388%.

## State, RGB и overlap audit

- state immutable и SHA match320/320;
- minimum unique RGB frames51;
- minimum feature max std0,016249;
- accepted training candidates16 384;
- broad audit128/16 384, non-exhaustive;
- overlap totals: under0,001° =0, under1° =0, under5° =203.

Runner дополнительно проверил exact motion hashes against all accepted training hashes до evaluation.

## Научная интерпретация

На двух новых batteries RGB-only activity frozen model84Z и proprioception-only execution activity согласованы во всех шести заранее заданных semantic units. Согласование устойчиво к view corners, превосходит temporal/static/closed controls и не покупается ухудшением reconstruction относительно equal-budget frozen84V. Это выполняет operational criterion roadmap для artificial shared observation/execution population.

Но units являются инженерно заданными joint channels, а не обнаруженными нейронами. Один grooming action family не проверяет action identity. Shared activity может отражать общую кинематику и supervised reconstruction. Результат не доказывает биологические mirror neurons, natural vision, action invention, actuators, forces или closed-loop control.

## Следующий допустимый шаг

Series86 должна быть заранее зарегистрирована до просмотра новых результатов и включать минимум три действия:

1. foreleg rubbing;
2. head-directed grooming;
3. reach/withdraw или другой отдельный motif.

Нужны action identity, observation/execution selectivity, held-out order, amplitude/speed и compositional transfer. Motions421–470 теперь раскрыты и запрещены для новых blocking selection/evaluation. В series86 следует экспортировать motion-level signatures или pairwise RSA distances, чтобы RSA можно было независимо пересчитать из summary.
