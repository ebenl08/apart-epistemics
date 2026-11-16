# M6 Part 3: SE probes (m5-9b-rl)

1435 points, 42 trials, 32 hidden-state layers. γ* = 0.000 bits (Kossen); high-SE share 0.12. 5-fold GroupKFold by trial; layer chosen on inner folds.

| target | features | score | layers chosen (per fold) |
|---|---|---|---|
| binary SE > γ* (AUROC) | TBG activations | **0.818** | [28, 28, 28, 20, 28] |
| continuous SE (Spearman) | TBG activations | **0.383** | [28, 28, 28, 22, 28] |
| binary SE > γ* (AUROC) | SLT activations | **0.729** | [10, 10, 30, 8, 8] |
| continuous SE (Spearman) | SLT activations | **0.260** | [10, 10, 20, 6, 10] |
| binary SE > γ* | control: fill + turn index | 0.493 | – |
| binary SE > γ* | control: TBG, shuffled labels | 0.522 | – |
| continuous SE | control: fill + turn index | 0.004 | – |
| continuous SE | control: TBG, shuffled labels | -0.006 | – |
| SE residualized on fill (Spearman) | TBG activations | **0.238** | [14, 12, 24, 20, 22] |
| trial reward < 0.5 (AUROC) | TBG activations | 0.576 | [28, 26, 24, 10, 22] |

Direction for H3 saved: `runs/m6-probe/direction-m5-9b-rl.npz` (TBG layer 28; cos(probe w, diff-of-means) = 0.094).
