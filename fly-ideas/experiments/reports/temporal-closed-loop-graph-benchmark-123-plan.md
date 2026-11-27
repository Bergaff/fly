# Series123 — synthetic temporal closed-loop Graph benchmark

## Purpose

Test all requested dimensions together: temporal state, action sequences, body feedback, sensory and motor delay, context, behavior switching, partial observability, and a nonlinear closed-loop target that is not one dot product.

## Frozen inputs and scope

Series123 exact-loads the genuine Series116 61×61 structure, Series116 61×8 paths, and three Series118 digital action prototypes by SHA-256. These inputs seed a **synthetic engineering environment**. They do not turn the simulation into biological validation.

Each episode has120 steps, two hidden contexts, three switching action modes, a two-step sensor delay, a two-step actuator delay, nonlinear body dynamics, disturbances, sparse observation, short context/action cues, and body feedback. Models train on seed123000001 and are frozen before seed123000002 tests.

## Models

- memoryless ridge: current61-channel observation plus8-channel body feedback;
- history-4 ridge: four explicit observation/body frames;
- random61-state recurrent reservoir with the same recurrent nonzero count as the graph;
- Series116 graph61-state recurrent reservoir;
- privileged oracle using hidden future target and context, included only as an upper-information reference.

All learned candidates use ridge motor readouts. Frozen test conditions are clean, stronger observation noise, additional partial observation, complete initial cue loss, and two extra sensor/motor delay steps.

## Gates and interpretation

A graph-advantage claim requires the graph reservoir to beat both the explicit-history model and matched random reservoir on clean and stress metrics. If it does not, the result remains NO-GO. This specific Series123 benchmark does not rerun a body. Earlier Series100–112 included official FlyGym/NeuroMechFly runs, but those frozen physical results do not automatically validate the newly defined Series123 Graph reservoir. Series123 is not a living-neuron result, whole-brain model, or general-intelligence benchmark.

Run `experiments\RUN-TEMPORAL-CLOSED-LOOP-123.bat` and return `summary.json` for user-machine replication.
