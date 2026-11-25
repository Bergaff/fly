# Series105D: long action-aware temporal tournament

## Decision before outcomes

Series104 direct transfer,105B diagonal mapping and105C full linear mapping remain separate genuine no-go results. Series105D changes the hypothesis fundamentally: training may use action labels and actual demonstrator trajectories, and four declared action-aware temporal models compete on a selection split before one model can touch final data.

- expected Windows wall budget: up to15hours;
- runner SHA-256: `8c39bfca87f3a11f59ac82cca721c58bb142094f7cd26bb1d4d6ae275ab23e45`;
- exact Series105C result SHA: `d9f8c8400b4cff10ecc5b20132e06cb2ccb07f3cee3075d461a1c1622abcda39`;
- exact Series105C runner SHA: `60c74e44bca8c64ecc667e6eb8705f6163565cdd0509230ca8872d50ac4b206f`;
- required prior state: completed, `development_candidate=false`, `scientific_result=false`.

This is supervised engineering development, not frozen89E transfer.

## Data and checkpointing

All motions are generated and hash-checked against earlier lines and between splits.

- train IDs1108–1197:90 motions,30/action;
- model-selection IDs1198–1215:18 motions,6/action;
- untouched final IDs1216–1233:18 motions,6/action;
- one neutral official-eye capture is shared only as a control;
- every capture is atomically saved as a separate compressed checkpoint;
- GUI has explicit **Start new** and **Continue checkpoint** buttons, overall percentage and ETA;
- dependency/runtime interruption is resumable and is not a scientific no-go.

Final captures are not generated unless at least one declared model passes the frozen selection gate.

## Inputs and supervised targets

Each moving official-eye sequence yields:

- unchanged frozen72 coefficient state;
-384-dimensional deterministic temporal pool of edge history;
- reversed and deterministically shuffled versions for controls;
- actual demonstrator trajectory compressed into72 cosine coefficients;
- one of three generated action labels.

Unlike Series104–105C, action labels and actual truth are explicitly permitted for train cases. Selection/final labels and truth are used only for scoring.

## Four fixed ideas

1. **state_multitask_ridge** — frozen72 state → truth72 + action one-hot, ridge10.
2. **state_random_fourier** — deterministic384 cosine features of frozen state → truth72 + action, ridge10.
3. **temporal_pool_ridge** —384 temporal edge features → truth72 + action, ridge100.
4. **temporal_action_experts** — temporal action classifier ridge10 plus three class-conditional trajectory experts ridge100; inferred action selects the expert.

No architecture, feature dimension, seed, ridge or threshold changes are allowed after results.

## Selection gate

Each model is evaluated on18 selection cases. It must:

- classify≥12/18 actions correctly;
- candidate truth RMSE win≥12/18 separately against neutral visual, reversed visual, zero input and shuffled visual;
- produce distinct candidate/control target hashes.

Among eligible models, the smallest mean candidate truth RMSE wins; exact ties use model name. If none is eligible, final remains untouched and Series105D ends as a development no-go.

## Untouched final gate

Only the selected model is evaluated on18 final motions with the same thresholds: action≥12/18, wins≥12/18 against every control, and all targets distinct. Pass means only `development_candidate=true` and can authorize a separately preregistered physical Series106. It is not physical confirmation itself.

## Windows run

Double-click `experiments\RUN-ACTION-AWARE-TEMPORAL-TOURNAMENT-105D.bat`. Choose result89D and source84Z. For interruption, rerun the same BAT, choose **Continue checkpoint**, select the `action_aware_tournament_...` folder, then choose the same exact source folders.

## Limitations

This line is supervised by generated actions and actual demonstrator trajectories. It cannot rescue or rewrite Series104/105B/105C and cannot establish biological learning, FlyVis/FlyWire/connectome mapping, a living animal or mirror neurons. Physical Series106 stays blocked unless the untouched final gate passes exactly.
