# Пользовательский результат серии 80: canonical view representation prototype

## Происхождение

Пользователь приложил оригинальный `summary-2.json`, SHA-256 `953131963d0b8a232e41bec5a1f8b5bf93fc916db39b6ca8bc6009b99e9462c9`. Статус `completed`, 320 training episodes, шесть новых motions и 16 held corners, 96 evaluation cases. Runner 78 SHA совпадает с опубликованным протоколом.

Это короткий representation ablation с `scientific_result=false`, а не long-run результат. NPZ моделей, predictions CSV и complete manifest независимо не получены.

## Blocking decision

`Go for long training: НЕТ.` Решение корректно и не должно изменяться post hoc.

Combined canonical немного лучше raw:

- raw: `0,429705`;
- canonical: `0,426518`;
- zero: `0,480002`;
- улучшение canonical против raw: только `0,74%`.

Feature view-distance снизилась с `0,134401` до `0,126688`, на `5,74%`. Но все четыре outer axes одновременно улучшились только в `5/16` held corners при требовании `12/16`.

## Оси

| Ось | Raw | Canonical | Zero | Wins canonical vs raw | Итог |
|---|---:|---:|---:|---:|---|
| left proximal | 0,430527 | 0,423660 | 0,447221 | 53/96 | fail |
| left middle | 0,372480 | 0,381532 | 0,513068 | 52/96 | pass safeguard |
| left distal | 0,481310 | 0,472380 | 0,483956 | 56/96 | fail |
| right proximal | 0,448700 | 0,440741 | 0,463412 | 55/96 | fail |
| right middle | 0,371829 | 0,379112 | 0,506893 | 53/96 | pass safeguard |
| right distal | 0,461014 | 0,453134 | 0,461805 | 56/96 | fail |

Outer axes улучшаются в pooled RMSE только на 1,6–1,9%, а wins составляют 55–58%, ниже preregistered 60%. Distal canonical лишь на 1,9–2,4% лучше zero. Middle ухудшились против raw на 2,0–2,4%, хотя остались значительно лучше zero и прошли safeguard.

Canonicalization даёт небольшой симметричный эффект, но не достаточно сильный или стабильный для long-run gate.

## Почему aggregate feature distance вводит в заблуждение

Эффект резко зависит от FOV.

### FOV 30°

- все `96/96` eye observations касаются границы crop;
- raw/canonical RMSE: `0,401454/0,410024`, canonical хуже;
- feature distance: `0,135957/0,147805`, canonical хуже.

При узком FOV объект уже крупный и частично упирается в границы сенсора. Crop-resize не может восстановить отсутствующие pixels и дополнительно искажает представление.

### FOV 70°

- только `6/96` eye observations касаются границы;
- raw/canonical RMSE: `0,456210/0,442398`, canonical лучше;
- feature distance: `0,132845/0,105571`, canonical заметно лучше.

Здесь demonstrator меньше и полностью помещается в кадр, поэтому crop-resize действительно нормализует масштаб.

Итоговое снижение feature distance на 5,74% усредняет противоположные режимы: canonicalizer помогает wide-FOV изображениям, но вредит narrow-FOV.

## Border diagnostics

- training: border touch `449/640` eyes, или 70,16%;
- evaluation: `102/192`, или 53,13%;
- uniform-interior training episodes: border touch 87,19%;
- balanced exact corners: 53,13%.

Высокая частота border touch означает, что простой foreground bounding box часто не является полноценным объектным crop. Это не constant-RGB defect: bounded и production данные имеют меняющиеся кадры, но canonicalization геометрически неполна.

## Corner structure

Все outer axes улучшились в cells 1, 2, 12, 14 и 15. При этом cell 2 имеет ухудшение combined RMSE, потому что outer-only criterion не гарантирует улучшение middle/combined.

На FOV 30° canonical combined лучше raw только в 2/8 cells и feature distance хуже во всех восьми. На FOV 70° canonical combined лучше raw во всех 8/8 и feature distance также лучше во всех восьми, но all-outer criterion выполнен только в 3/8.

## Вывод

Поддерживается:

> Sequence-level image crop частично нормализует малый объект при широком FOV и немного снижает aggregate view-distance.

Не поддерживается:

> Один foreground crop-resize является достаточным representation upgrade для устойчивого декодирования proximal/distal joints во всём core view space.

Восьмичасовой запуск с этим canonicalizer запрещён.

## Следующий прототип

Следует сохранить raw information и добавлять canonical information, а не заменять одно другим. Наиболее обоснован следующий короткий ablation:

1. raw feature history остаётся неизменной;
2. canonical feature history добавляется вторым scale channel;
3. border-touch flags сообщают модели, когда canonical crop неполон;
4. сравниваются raw против raw+canonical multiscale на том же stream;
5. те же held corners и строгий outer-axis gate;
6. никакого long run до прохождения gate.

Такой multiscale/gated подход может использовать canonical advantage при FOV 70°, не теряя raw representation при FOV 30°.
