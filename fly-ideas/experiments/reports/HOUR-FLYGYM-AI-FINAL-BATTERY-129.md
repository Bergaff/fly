# Series129A–D — часовой финальный пакет FlyGym + AI

## Зачем это нужно

Короткие Series125/126 ответили на gates, но не дали длительного многовариантного сравнения. Этот единый launcher выполняет несколько разделённых подсерий примерно за60 минут на пользовательском Windows-компьютере с локальной `qwen2.5:7b`.

Пакет **не отменяет NO-GO Series126**, не запускает заблокированные Series127/128 и не создаёт Series130 с другим seed прежней synthetic-задачи.

## 129A — immutable official-FlyGym evidence audit

Проверяются SHA и совместно аудируются48 genuine historical official-FlyGym outcomes Series106,109,112. Для пяти физических метрик строятся10 000 bootstrap resamples и95% intervals. Это физический evidence audit, а не новый запуск Graph controller.

## 129B — четыре общих семейства exact-задач

Один и тот же case получает exact project-side answer и локальная Qwen:

1. `dn_routing` — weighted61→8 routing;
2. `multihop_readout` — ranking after frozen four-hop propagation;
3. `lesion_counterfactual` — наибольшее vector change после lesion;
4. `physical_control_audit` — выбор safe/lowest-error control из historical official-FlyGym outcomes.

Для каждого семейства циклически используются три формата prompt: direct JSON, compact table и verify-then-JSON. Case count не фиксируется: runner выполняет balanced round-robin до исчерпания временного бюджета.

## 129C — adaptive efficiency

Требуется ровно локальная `qwen2.5:7b`. GUI считает elapsed time и запускает столько cases, сколько компьютер успеет примерно за час. Сохраняются ответ, expected label, correctness, wall time, family, prompt variant и SHA payload каждого case. `case_rows.jsonl` пишется после каждого ответа; `progress.json` обновляется каждые четыре cases.

## 129D — immutable final decisions

Финал обязан оставить четыре вывода раздельными:

- fly digital/engineering: `NO_GO_EXTERNAL_BEHAVIOR_ADVANTAGE`;
- cross-animal transfer: алгоритм существует, independently validated species =0;
- AI comparison: только shared narrow exact tasks, не general-intelligence ranking;
- biological mirror neurons: не установлены.

## Запуск

1. Запустить Ollama и убедиться, что установлена `qwen2.5:7b`.
2. Открыть `experiments\RUN-HOUR-FLYGYM-AI-FINAL-129.bat`.
3. Нажать одну большую кнопку и не закрывать окно примерно60 минут.
4. Прислать `summary.json` из открывшейся result-папки. Для case-level аудита при необходимости также сохранить `case_rows.jsonl`.

Runtime может отклониться из-за одного последнего Ollama request. Ошибка сохраняется в `workspace\runs\ideas\i-observational\hour-flygym-ai-final-129\ПОСЛЕДНЯЯ-ОШИБКА-129.txt`.
