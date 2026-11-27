# Series121 — genuine local Qwen2.5:7b result

This is the user-supplied completed local Ollama run archived without changing the uploaded JSON. Uploaded-file SHA-256: `c87573107441de86d7ba192fad4dd4a1c112723e6f01cea335ba8ccd75aade24`.

Despite the uploaded filename `summary-60.json`, the embedded benchmark contract records **18 cases**, so all conclusions use 18 as the denominator.

## Frozen facts

- Model: `qwen2.5:7b`, family `qwen2`
- Ollama digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
- Reported parameters: 7,615,616,512
- Local artifact size: 4,683,087,332 bytes (4.361 GiB)
- Exact project solver: 18/18 (100%)
- Qwen2.5:7b: 5/18 (27.78%)
- Four candidates per case imply a 25% random-choice reference rate. With only 18 cases, 5/18 is close to chance; a one-sided exact binomial tail under p=0.25 is approximately 0.481. This is a descriptive diagnostic, not a preregistered gate.
- Project timing: 9.230 microseconds/case averaged over 2,000 × 18 exact-solver evaluations.
- Qwen total wall time: 45.550 seconds; reported mean 2.531 seconds/case.
- Case1 took 39.468 seconds and includes cold model loading/startup. Excluding that first case as a clearly labeled post-hoc warm diagnostic, cases2–18 averaged 0.358 seconds/case (median 0.358 seconds/case).
- Reported aggregate speed ratio including cold start: 274,169× Qwen wall time / exact-solver time.
- Post-hoc warm wall-time ratio: approximately 38,761×.

## Valid interpretation

The exact solver is designed for this deterministic dot-product routing operation and therefore should be both accurate and fast. Qwen is a prompted general language model doing arithmetic through text generation. This result supports using the exact solver for this operation; it does **not** show general AI superiority, intelligence equivalence, or biological validity. The 18-case result is too small to characterize Qwen broadly, and the cold-start and warmed timings must not be conflated.
