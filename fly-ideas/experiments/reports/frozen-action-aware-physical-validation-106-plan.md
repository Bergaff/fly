# Series106: frozen action-aware official-eye physical validation

## Frozen decision before outcome

Series105D passed its untouched supervised non-physical final. Series106 freezes the exact selected `temporal_action_experts` artifact and tests official observer-eye input through the selected model on official FlyGym MOTOR bodies.

- Series106 runner SHA-256: `282a7a87ae43b3c6a5b2432c01495c564ee3dc3e1247c0230015917ada5ea5fa`;
- Series105D runner SHA: `8c39bfca87f3a11f59ac82cca721c58bb142094f7cd26bb1d4d6ae275ab23e45`;
- genuine Series105D JSON SHA: `59f8d54fbc7c062c068259d455484f643844f33092e655e195acb170cbfb9ad3`;
- exact selected model SHA: `1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1`;
- model name/schema: `temporal_action_experts`, temporal classifier plus three trajectory experts;
- training, model selection and post-result tuning are forbidden.

The original Series105D result folder is required because the committed summary contains the model identity but not its arrays.

## Untouched physical cases

IDs1234–1245, four cases per action, seeds106100–106132, amplitudes0,64/0,76/0,89/0,97 and speeds0,74/0,91/1,08/1,19. Hashes must not overlap any earlier training, selection, validation or physical outcomes.

For each case:

1. official demonstrator executes the generated action;
2. observer receives official fisheye images;
3. unchanged edge history is compressed into the deterministic384-dimensional temporal pool;
4. frozen classifier chooses one of three frozen trajectory experts;
5. predicted72 coefficients decode to a49-frame six-axis target;
6. target drives the official observer MOTOR body through the established closed-loop bridge;
7. score uses actual demonstrator trajectory measured during capture.

## Physical controls

Six conditions per case,72 official physical rollouts:

- candidate;
- neutral visual input;
- reversed visual input;
- zero temporal input;
- deterministically shuffled visual input;
- true open loop using the candidate target without q/dq feedback.

Candidate/open-loop target hashes are equal. Candidate must differ from all visual/input controls.

## Frozen primary gate

1. all12 candidate rollouts finite, in thorax z0,15–2,5mm and with ground contact;
2. mean candidate tracking RMSE≤0,20rad;
3. action classification≥9/12 and≥3/4 in every action class;
4. candidate truth RMSE wins≥8/12 against neutral/reversed/zero/shuffled;
5. for every action separately candidate wins≥2/4 against each of those four controls;
6. candidate wins≥10/12 against true open loop;
7. candidate targets differ from neutral/reversed/zero/shuffled in all cases.

No threshold may be weakened after outcome.

## Windows run

Double-click `experiments\RUN-FROZEN-ACTION-AWARE-PHYSICAL-VALIDATION-106.bat`. Select, in order:

1. either the original Series105D run folder containing the `result` subfolder, or that `result` folder itself; the runner resolves both layouts and requires `selected_action_aware_model.npz`;
2. the completed result89D folder;
3. production source84Z.

GUI shows overall percentage and ETA and automatically opens result or a copyable error report. A missing/wrong model, dependency issue or launch failure is not a scientific no-go.

## Allowed conclusion

Pass establishes only frozen supervised engineering viability from official-eye temporal features to an official MOTOR body on new generated motions. It does not restore unchanged frozen89E and does not demonstrate biological learning, FlyVis/FlyWire/connectome mapping, muscles, a living fly or mirror neurons. `scientific_result` remains false for every outcome.

## Genuine outcome (recorded after the run)

The complete genuine Windows run is preserved in `frozen-action-aware-physical-validation-106-user-result.json` (SHA-256 `1eadcbcfea31c973f9993da16be7cd0b01998d2f4c6c7aa27c54b4c08da00be9`) and interpreted in the adjacent `.md` report.

The frozen primary gate did not pass. Safety/contact was 12/12, tracking RMSE was 0,060518rad, action identity was 12/12, aggregate wins were neutral11/12, reversed11/12, zero12/12, shuffled9/12 and open-loop12/12. The sole failed gate was class-balanced shuffled-input specificity for head-directed grooming: 1/4 wins versus the required2/4. `physical_development_candidate=false`; `scientific_result=false`. Series106 is closed as a genuine physical no-go; its threshold must not be weakened and its fixed final must not be rerun until it passes.
