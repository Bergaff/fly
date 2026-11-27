# Series120C — computational footprint versus reference AI

This compares storage/compute scale, **not intelligence or task quality**.

Project dense core: 4,214 scalars, about 16.46 KiB in FP32. Sparse nonzero core: 2,916 scalars. Observed Series119 throughput on the user's six-worker machine: 39.548 replicates/s.

| Explicit reference | Parameters | Reference/project parameter ratio |
|---|---:|---:|
| small_neural_network_1m | 1,000,000 | 237.3× |
| compact_transformer_100m | 100,000,000 | 23730.4× |
| reference_language_model_7b | 7,000,000,000 | 1661129.6× |

The project is vastly smaller, specialized and more directly interpretable. That can make it cheaper for this narrow graph-alignment task. It does not establish general-intelligence equivalence, superiority to AI, or biological brain-power equivalence. A performance ranking would require one shared dataset, task, split and metric; none exists here.
