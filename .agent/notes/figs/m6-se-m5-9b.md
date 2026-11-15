# M6 Part 2: semantic entropy vs reward (m5-9b)

42 trials, 1409 decision points, 0 sample errors. Format-slip trials (reward 0 without a wall), excluded from the tests: none.

## Per cell (mean over trials)

| family     | level   |   n |   reward |   walls |   mean_se |   max_se |   frac_se0 |
|:-----------|:--------|----:|---------:|--------:|----------:|---------:|-----------:|
| kv-store   | R260    |   6 |    0.931 |       1 |     0.067 |    0.589 |      0.906 |
| kv-store   | R1000   |   4 |    0.542 |       2 |     0.186 |    0.9   |      0.703 |
| kv-store   | R4000   |   4 |    0.531 |       2 |     0.406 |    1.436 |      0.496 |
| kv-store   | R16000  |   4 |    0.25  |       3 |     0.325 |    1.368 |      0.546 |
| log-triage | L320    |   6 |    0.944 |       0 |     0.1   |    0.779 |      0.821 |
| log-triage | L1600   |   6 |    0.403 |       3 |     0.208 |    1.222 |      0.712 |
| log-triage | L6400   |   6 |    0.243 |       3 |     0.231 |    1.248 |      0.667 |
| log-triage | L12800  |   6 |    0.25  |       4 |     0.138 |    0.943 |      0.775 |

## H1: partial Spearman ρ(trial SE, reward | pressure level), 95% bootstrap CI over trials

| summary | n | ρ | 95% CI | raw ρ |
|---|---|---|---|---|
| mean_se | 42 | -0.587 | [-0.775, -0.282] | -0.590 |
| max_se | 42 | -0.417 | [-0.720, -0.053] | -0.533 |
| mean_se_hi | 19 | -0.307 | [-0.871, +0.299] | -0.168 |

## Regression: reward ~ mean_SE + C(family:level)

- SE coefficient -2.024 (SE 0.404, p = 0.000); ΔR² over level-only model = +0.259 (R² 0.400 → 0.659).

## Step level

- AUROC of point SE for harmful logged edit (deleted, not offloaded, or clobbered a file) among edit turns: **0.379** [0.318, 0.440] (n = 1051, positives 971)
- AUROC of point SE for point in a trial that hit the wall (all points): **0.613** [0.589, 0.636] (n = 1409, positives 653)

## Go / no-go for Part 3 (fixed in advance)

- Any partial |ρ| ≥ 0.3 with CI excluding 0: **True**
- Harmful-edit AUROC ≥ 0.65: **False** (0.379)
- **Decision: GO**

Plots: `m6-se-m5-9b.png`, `m6-se-fill-m5-9b.png`.
