# Series112: frozen operational-router physical validation

Series111 passed both selection and untouched final, selecting `spatial_then_temporal_on_reject`. Series112 freezes that route before new outcomes and tests whether its nuisance-normalized targets remain safe and specific through the official simulated MOTOR body.

## Frozen authorization

- Series112 runner SHA `be3cc7431c889f6a19a961324c86ce21a2878a368958edc960fc5c963835f84f`;
- exact Series111 result SHA `9ecc0f2b4568ee2a0f5bcdeca552c28caa3e295b52c98993fdf8a04593146765`;
- Series111 runner SHA `f6f3e3efa6f11e7ada0a1fca66187ad3c971a39fa08c6d36b0daf474df858fef`;
- selected metadata artifact SHA `2810ecddc8cbc24e7cbcf4ac2c614a3971327236c0ba9c6bc008bccbd5bc9282`;
- exact Series105D base and Series107 adapter remain unchanged.

The selected artifact contains only the route name and runner hash, not learned arrays. Series112 therefore pins its SHA from the exact result and implements the declared deterministic route directly: use percentile-spatial for the whole case when its candidate is accepted, otherwise percentile-temporal. It never uses true action or nuisance-domain labels to route.

## Untouched design

- IDs1450–1467:18 fresh motions, one per action×nuisance domain;
- seeds112100–112152, amplitudes0,61–1,04 and speeds0,60–1,38;
- all hashes excluded against prior results and accepted source motions;
- deterministic dim, bright, low-contrast, sensor-noise, horizontal-shift and frame-dropout perturbations after official-eye capture;
- no training, selection, threshold change or post-result tuning;
- seven physical rollouts per case: candidate, neutral, reversed, shuffled, zero, base-shuffled diagnostic, and true open loop;126 total.

## Frozen gate

Candidate physical rollouts must all be finite, contacting, within thorax-z bounds, and have mean tracking RMSE≤0,20rad. Candidate acceptance, shuffled rejection and action identity each require≥15/18,≥4/6 per action and validity≥2/3 per nuisance domain. Candidate truth-RMSE wins against neutral/reversed/shuffled/zero require≥12/18,≥4/6 per action and≥2/3 per domain. Candidate must beat true open loop≥15/18 and all comparator targets must be distinct. Adapter gain remains diagnostic, matching the prospective Series111 operational rule.

Run `experiments\RUN-FROZEN-OPERATIONAL-ROUTER-PHYSICAL-112.bat` and choose Series105D, Series107, result89D and source84Z folders. A pass is simulated-body engineering evidence only: digital nuisances are not camera hardware, and this is not biological learning, living-fly, muscle, FlyVis/FlyWire or mirror-neuron evidence.
