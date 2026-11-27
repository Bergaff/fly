# Stage92 paired diagnostic: пользовательский результат

Полная read-only диагностика получила 47 262 replicates и1 985 004 строки metrics. Воспроизведены Stage92 rates: harsh57,8276%, overall54,5946%.

## Главный диагноз

Проблема не в исчезновении classification advantage. В budget30 structured96 выигрывает accuracy очень часто: view-high99,05%, occlusion93,35%, state-noise93,18%, combined-harsh83,21%. Не проходит главным образом trajectory RMSE: соответствующие RMSE win rates71,31%,59,14%,56,31%,58,56%.

Наиболее показателен budget30 lesion25: mean accuracy delta+0,04616 и accuracy wins67,14%, но mean RMSE improvement−0,000823, RMSE wins47,19%, dual33,95%. Clean budget30 также почти насыщен: accuracy delta всего+0,00328, RMSE improvement+0,000113, dual32,71%. Эти две группы тянут overall вниз, но их нельзя исключить после просмотра результата.

В few-shot5 картина сильнее: combined-harsh dual65,31%, view-high77,30%, occlusion65,31%, state-noise64,56%. Stage92 harsh gate провалился потому, что он объединял few-shot5 с budget30 combined-harsh50,35%.

## Обнаруженный design defect

Stage92 использовал разные model-index seeds при training и evaluation. Поэтому structured и shuffled получали не только разные initialization/minibatch randomness, но и разные lesion unit sets и state-noise draws. Для paired architecture comparison повреждение обязано быть одинаковым. Это исправляется common random numbers для всех моделей; изменение обязательно независимо от направления эффекта.

## Выбранная development-коррекция

На раскрытом bounded pilot проверены общие RNG и trajectory-loss weights2/4. При64 disclosed replicates weight2 дал ориентировочно harsh61,72%, overall54,69%; weight4 — harsh64,06%, overall59,15%. Поэтому weight4 выбран как development candidate. Этот результат не является replication; все pilot seeds раскрыты.

Следующий Stage94 замораживает weight4, common initialization/batch order и одинаковые lesion/state noise, использует новый namespace seeds и усиленный Wilson95 gate. Старый Stage92 остаётся no-go.
