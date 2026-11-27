# Series121 — genuine local Qwen2.5:7b 60-case result

This is the user-supplied completed local Ollama run archived without changing the uploaded JSON. Uploaded-file SHA-256: `0f16b0ac2775df05059b64e7c608784af486592ec78e1e00286d72e026d0a41f`.

## Frozen facts

- Embedded case count: 60
- Model: `qwen2.5:7b`, family `qwen2`
- Ollama digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
- Reported parameters: 7,615,616,512
- Local artifact size: 4,683,087,332 bytes (4.361 GiB)
- Exact project solver: 60/60 (100%)
- Qwen2.5:7b: 21/60 (35%)
- Four candidates per case imply a 25% random-choice reference rate. A one-sided exact binomial tail for at least21 successes under p=0.25 is approximately 0.054. The Wilson95% interval is approximately24.2%–47.6%. Therefore this run does not cross a conventional one-sided0.05 threshold against random choice and should remain descriptive.
- Project timing: 9.546 microseconds/case averaged over 2,000 × 60 exact-solver evaluations.
- Qwen total wall time: 17.797 seconds; mean0.2966 seconds/case; median0.3291 seconds/case.
- Aggregate wall-time ratio: approximately31,073× Qwen / exact solver.
- Approximate throughput: exact solver104,756 cases/s; Qwen3.37 cases/s.

## Repeatability diagnostic

The60-case run uses the same seed and its first18 cases correspond to the earlier18-case run. Qwen changed answers on cases6 and15 despite temperature0 and the fixed prompt seed. The earlier run scored5/18; this run scored4/18 on the same first18 cases. The exact solver remained deterministic. This is an observed repeatability limitation of this local prompted-model path, not a general claim about Qwen.

## Timing diagnostic

Cases1–18 averaged0.1794 seconds/case, while cases19–60 averaged0.3468 seconds/case. This run had no39-second cold load like the earlier run, but wall time still varied during execution. The benchmark records end-to-end wall time; it does not isolate model evaluation, prompt processing, scheduling, thermal effects, or Ollama overhead.

## Valid interpretation

The exact solver is designed for this deterministic dot-product routing operation and therefore should be both accurate and fast. Qwen is a prompted general language model doing arithmetic through text generation. This result supports using the exact solver for this operation; it does **not** show general AI superiority, intelligence equivalence, or biological validity. It also is not a controller comparison: linear, MLP, RNN, finite-state, memory, and energy baselines remain unmeasured.
