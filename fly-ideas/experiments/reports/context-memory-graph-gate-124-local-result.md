# Series124 — local context-memory gate result

Result SHA-256: `5618414dad79e73a6beb60622544d57f4a805c66ab547874805fd484047b7084`.

## Untouched final

| Model | Clean RMSE ↓ | Success ↑ | Late context accuracy ↑ |
|---|---:|---:|---:|
| Memoryless ridge |0.21696 |54.42% |50.59% |
| History-8 ridge |0.37594 |37.31% |42.78% |
| Random reservoir61 |**0.21622** |54.39% |100% |
| Graph reservoir61 |0.21624 |54.58% |100% |
| Privileged context ridge |0.21696 |54.69% |100% |
| Privileged context bilinear |0.21757 |55.08% |100% |

Development independently selected leak `.995` for both reservoirs. Removing the context cue reduced both reservoir context decoders to64.07%, while memoryless remained near chance. Under stronger noise graph context accuracy was91.20%; under extra partial observation and extra delay it remained100%.

## Decision

- Context necessity gate: **PASS**. Memoryless late decoding was50.59%, while privileged/context-memory models reached100%.
- Graph context-memory gate: **PASS** at100%.
- Cue-lesion specificity: **PASS** at64.07%.
- Graph control advantage: **FAIL**. Graph RMSE0.21624 did not beat random0.21622 or memoryless0.21696 by the preregistered0.005 margin.

Final decision: **NO_GO_KEEP_PHYSICAL_PORT_BLOCKED**.

The graph can preserve the short context cue, but the matched random reservoir preserves it equally well and has marginally lower RMSE. The motor readout does not convert context memory into a meaningful graph-specific control advantage. Therefore a new FlyGym port would add physical compute without first establishing that this new graph controller contributes anything specific.

Earlier Series100–112 official FlyGym/NeuroMechFly results remain part of the project. Series124 simply blocks claiming or running a new physical validation for this new controller until it beats matched controls.
