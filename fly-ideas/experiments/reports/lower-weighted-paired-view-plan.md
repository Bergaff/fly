# Серия84X: lower-weighted paired-view model

## Основание

Frozen replication84W подтвердила преимущество84V над84S/84R по всем global axes, но дала strict no-go: lower-X right-distal59/80 vs zero при пороге60. Corners9/13 дали6/10. Поэтому series85 заблокирована.

## Единственное научное изменение

Архитектура576-D, ridge, clipping, motion families, число base motions и общий fixed render count остаются84V. Меняется только распределение четырёх связанных views каждого движения:

- было84V:2 lower-X +2 upper-X;
- становится84X:3 lower-X +1 upper-X;
-4096 новых base motions seed8429;
-16 384 render-candidates, ожидаемо802 816 frames.

Число16 384 не является биологической константой. Это `4096 ×4`:4096=`2^12` base motions, поровну1024 на каждую из четырёх motion families; четыре views дают `2^14` renders. Такой count сохраняет точный compute budget84S/84V, поэтому эффект view allocation не смешивается с изменением размера dataset. Уменьшение до8192 ускорило бы запуск, но одновременно вдвое уменьшило бы число base motions и создало бы новую причину различий.

Три lower views имеют различные corner bits; один upper view циклически покрывает все восемь upper corners по base IDs. Это заранее выбранное targeted изменение для absolute lower-X consistency. Motions321–390 не используются.

## Ускорение, не научное изменение

По просьбе пользователя используются6 workers и batch6 вместо2/2. Каждый worker ограничен одним BLAS/OpenMP thread. На компьютере12 logical CPU/16GB RAM это увеличивает загрузку, оставляя ресурсы для Word. Completion остаётся только по fixed count, QuickEdit отключается, SQLite commit/pause/resume сохраняются. Ожидаемое wall time меньше84V, ориентировочно2,5–4 часа, но это не time gate.

## Frozen source

Выбирается завершённая папка84V. Проверяются SQLite, result manifest, runner84V SHA `05a0cdd4…`, production model84V SHA `44b98c31…` и embedded84S/84R. Все три модели read-only comparators.

## Новая blocking battery

- seed8430;
- motions401–410, пять piecewise5 и пять piecewise9;
-16 corners,160 cases;
- candidate сравнивается с84V,84S,84R,zero и controls;
- state72 coefficients, delay0,5с.

## Blocking primary

- каждая ось ниже zero и минимум112/160 wins;
- right distal ниже84V,84S,84R и минимум96/160 wins отдельно против каждой;
- остальные оси не хуже каждой frozen model более чем5%;
- lower-X RD ниже zero и всех трёх models, минимум60/80 vs zero и48/80 отдельно vs84V/84S/84R;
- обе body-X и camera-Z groups проходят все оси минимум56/80 vs zero;
- минимум12/16 corners проходят все оси минимум7/10;
- combined ниже84V,84S,84R,zero и controls.

Один fail означает no-go. Нельзя округлять, исключать motions/corners или искать другой seed.

## После результата

Даже go84X требует отдельной frozen replication на новых motions до series85. No-go сохраняет блокировку; motions401–410 становятся раскрытыми.

## Ограничения

Synthetic supervised reconstruction, не natural vision. Нет нового действия, actuators, сил, мышц, closed-loop correction, биологического мозга или mirror neurons.
