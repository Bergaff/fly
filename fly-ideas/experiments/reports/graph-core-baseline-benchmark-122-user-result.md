# Series122 — genuine user replication

The uploaded `summary-62.json` is archived unchanged. SHA-256: `f867d20f8127b58060d66f123dec5acb74f7844afe4af29fdf617e5c349799f7`.

## Reproduced deterministic results

The user run exactly reproduced every accuracy, generalization, noise, dropout, and ablation value from the local result:

- exact dot: 600/600 frozen test,100% new seed;
- nine-parameter diagonal bilinear ridge: 600/600 frozen test,100% new seed;
- parameter-matched4,213-parameter MLP: 547/600,90% new seed;
- max-weight-channel rule:343/600,57.33% new seed;
-17-parameter additive linear ridge:243/600,40.17% new seed;
- seeded random reference:134/600.

The exact and bilinear methods also matched under the shared perturbations:70.0% with noise std0.02,65.33% with10% input dropout, and77.27% mean accuracy after single-channel ablation.

## User-machine timing

| Method | Mean | p95 | Maximum |
|---|---:|---:|---:|
| Exact dot |0.171µs/case |0.214µs |0.278µs |
| Hand rule |0.169µs/case |0.208µs |0.254µs |
| Additive linear |0.102µs/case |0.123µs |0.136µs |
| Diagonal bilinear |0.161µs/case |0.210µs |0.251µs |
| Parameter-matched MLP |12.319µs/case |16.689µs |20.044µs |

Timings are batched NumPy/Python measurements and are platform-sensitive; they are not bare-metal controller latency or energy measurements.

## Conclusion

The independent user run reproduces the main Series122 finding: a nine-parameter diagonal-bilinear baseline is sufficient for this narrow weighted-dot-product task. Therefore this task cannot support Graph Core superiority or justify the full4,214-scalar capacity. The next benchmark must introduce temporal state, feedback, or a behavior target that is not algebraically identical to a nine-parameter dot product.
