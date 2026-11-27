# Series121 — local project versus Ollama comparison

## Scope

This benchmark answers a narrow, reproducible question on the user's own machine: how do the exact project solver and one locally installed Ollama model compare when given the same numeric graph-routing cases?

Each deterministic case contains four real type names, their normalized eight-channel Series116 DN vectors, and a weight vector. The answer is the type with the largest dot product. The project uses its exact task-specific numeric solver. Ollama receives the same rounded values in a zero-temperature JSON prompt. Accuracy, wall time, case responses, local model digest/size and parameter count when reported are saved.

This setup intentionally favors the specialized solver and does not measure language, planning, vision, general intelligence or biological validity. A result cannot establish that the project is generally stronger than AI. It can show the cost and reliability difference for this one shared operation.

## Privacy and use

The runner connects only to `http://127.0.0.1:11434`; prompts are sent to the user's local Ollama service. The GUI lists installed models from `/api/tags`, lets the user choose6–60 cases, then saves `cases.json`, `summary.json` and a Russian text result under the workspace run folder.

Run: `experiments\RUN-LOCAL-OLLAMA-COMPARISON-121.bat`.
