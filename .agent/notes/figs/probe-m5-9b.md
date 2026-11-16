# M6 Part 3: SE probes (m5-9b)

1409 points, 42 trials, 32 hidden-state layers. γ* = 0.000 bits (Kossen); high-SE share 0.30. 5-fold GroupKFold by trial; layer chosen on inner folds.

| target | features | score | layers chosen (per fold) |
|---|---|---|---|
| binary SE > γ* (AUROC) | TBG activations | **0.741** | [18, 18, 20, 20, 20] |
| continuous SE (Spearman) | TBG activations | **0.466** | [20, 22, 20, 22, 22] |
| binary SE > γ* (AUROC) | SLT activations | **0.648** | [12, 10, 12, 20, 12] |
| continuous SE (Spearman) | SLT activations | **0.331** | [12, 10, 30, 20, 12] |
| binary SE > γ* | control: fill + turn index | 0.578 | – |
| binary SE > γ* | control: TBG, shuffled labels | 0.483 | – |
| continuous SE | control: fill + turn index | 0.159 | – |
| continuous SE | control: TBG, shuffled labels | -0.033 | – |
| SE residualized on fill (Spearman) | TBG activations | **0.371** | [18, 22, 18, 18, 18] |
| trial reward < 0.5 (AUROC) | TBG activations | 0.671 | [0, 22, 22, 0, 22] |

Direction for H3 saved: `runs/m6-probe/direction-m5-9b.npz` (TBG layer 20; cos(probe w, diff-of-means) = 0.093).
