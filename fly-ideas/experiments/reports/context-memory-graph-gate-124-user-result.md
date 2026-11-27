# Series124 — genuine user replication

The uploaded `summary-64.json` is archived unchanged. SHA-256: `01d22b977601893e25fb2eebda2dd9f954a2258bcfa7a5bc24ee6846c08e40b7`.

The user run exactly reproduced every deterministic development selection and untouched-final metric from the local Series124 result. Both random and graph reservoirs again selected leak `.995` on development only.

| Model | Final clean RMSE ↓ | Success ↑ | Late context ↑ | User latency |
|---|---:|---:|---:|---:|
| Memoryless ridge |0.21696 |54.42% |50.59% |25.82µs/step |
| History-8 ridge |0.37594 |37.31% |42.78% |33.37µs/step |
| Random reservoir61 |**0.21622** |54.39% |100% |43.78µs/step |
| Graph reservoir61 |0.21624 |54.58% |100% |43.47µs/step |
| Privileged context ridge |0.21696 |54.69% |100% |33.78µs/step |
| Privileged context bilinear |0.21757 |55.08% |100% |40.12µs/step |

Cue lesion reduced graph and random late-context decoding to64.07%, satisfying the frozen specificity gate. Context necessity and graph context-memory gates pass. The graph-control advantage gate fails because graph RMSE does not beat random or memoryless by the preregistered0.005 margin.

Final decision remains **NO_GO_KEEP_PHYSICAL_PORT_BLOCKED**. Earlier Series100–112 official FlyGym/NeuroMechFly evidence remains valid for those frozen adapters, but the new Series124 controller is not authorized for a new physical port.
