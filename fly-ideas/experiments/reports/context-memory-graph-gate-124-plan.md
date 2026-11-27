# Series124 — context-necessary memory gate

Series123 showed that the short context cue was ignored. Series124 changes the action mapping by hidden context: the same observed action mode requires a different motor target in contexts0 and1. The context cue appears only at episode start, so late decoding requires memory.

## Separation

- Train seed124000001.
- Development seed124000002 selects only reservoir leak from `.90/.95/.98/.995`.
- Untouched final seed124000003.
-80 train,20 development,30 final episodes per condition by default.
- Series123 runner exact-pinned by SHA `73fd16bf5b730083d3e04308a58be739d5cfa26515f8a0658a462c1612be77ce`.

## Controls

Memoryless ridge, explicit history-8 ridge, matched random reservoir61, graph reservoir61, privileged context ridge, and privileged context×observation bilinear ridge. Final conditions: clean, context-cue lesion, stronger noise, additional partial observation, and extra delay.

## Gates

1. Context necessity: privileged late context decoding above95%, memoryless at or below65%.
2. Graph state decodes late context at or above80%.
3. Graph clean RMSE beats both random reservoir and memoryless ridge by more than0.005.
4. Cue lesion reduces graph late-context accuracy to at most65%.

Only all gates authorize a **new** FlyGym port. Earlier Series100–112 official FlyGym/NeuroMechFly evidence remains valid for those frozen adapters but cannot substitute for this gate.
