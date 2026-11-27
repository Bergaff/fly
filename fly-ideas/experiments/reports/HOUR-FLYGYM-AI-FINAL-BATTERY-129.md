# Series129A–D — безопасный малый пакет FlyGym + AI

## Исправление ресурсоёмкости

Первая версия часового runner была снята после пользовательского сообщения о90% занятой памяти и сильных вентиляторах. Непрерывный часовой поток Qwen-запросов и автоматический запуск `ollama serve` больше не допускаются.

Текущая версия:

- **никогда не запускает Ollama server автоматически**;
- требует явного подтверждения непосредственно перед вычислением;
- выполняет ровно12 AI-запросов, а не неограниченный часовой цикл;
- делает паузу5 секунд между запросами;
- ограничивает каждый запрос timeout180 секунд;
- после завершения или ошибки отправляет Ollama `keep_alive:0` для немедленной выгрузки `qwen2.5:7b`;
- показывает предупреждение, что даже краткая загрузка Qwen временно занимает память.

Для ручной немедленной выгрузки всегда можно выполнить:

```bat
ollama stop qwen2.5:7b
```

## 129A — offline official-FlyGym evidence audit

Без тяжёлого моделирования проверяются SHA и совместно аудируются48 genuine historical official-FlyGym outcomes Series106,109,112. Для пяти физических метрик выполняются10 000 быстрых bootstrap resamples и строятся95% intervals. Это historical evidence audit, а не новый Graph-controller run.

## 129B —12 лёгких shared cases

Сохраняются четыре разные exact task families:

1. `dn_routing`;
2. `multihop_readout`;
3. `lesion_counterfactual`;
4. `physical_control_audit`.

Каждая запускается ровно три раза: direct JSON, compact table и verify-then-JSON. Итого4×3=12 локальных Qwen-запросов.

## 129C — bounded efficiency

Сохраняются answer, expected label, correctness, wall time, family, prompt variant и payload SHA. `case_rows.jsonl` записывается после каждого ответа, `progress.json` — также после каждого ответа. Никакого adaptive hour loop больше нет.

## 129D — неизменные границы вывода

- fly digital/engineering: `NO_GO_EXTERNAL_BEHAVIOR_ADVANTAGE`;
- cross-animal transfer: алгоритм существует, independently validated species =0;
- AI comparison: только narrow exact tasks, не ranking общего интеллекта;
- biological mirror neurons: не установлены;
- Series127/128 остаются неавторизованными.

## Запуск

1. Только если краткая загрузка Qwen приемлема, самостоятельно запустить Ollama.
2. Открыть `experiments\RUN-HOUR-FLYGYM-AI-FINAL-129.bat` — имя оставлено для совместимости, но часовой режим удалён.
3. Прочитать предупреждение и подтвердить12 запросов. Кнопка «Нет» ничего не запускает.
4. После результата прислать `summary.json`.

Если память или вентиляторы снова резко возрастают, остановить запуск и выполнить `ollama stop qwen2.5:7b`. Продолжать вычисление не требуется.
