# H3 decision level: directional ablation vs baseline (9B)

Trials: subset runs/m6-se/queue-h3sub.txt.

## Outcomes per condition

|               |   points |   SE plain |   SE valid-only |   SE rejection-sampled |   points with 10 valid calls |   share SE > 0 |   no_tool_call (of first 10) |   context_status (of first 10) |   error (of first 10) |   invalid (of first 10) |   agree with logged |   mean samples drawn |
|:--------------|---------:|-----------:|----------------:|-----------------------:|-----------------------------:|---------------:|-----------------------------:|-------------------------------:|----------------------:|------------------------:|--------------------:|---------------------:|
| baseline (9B) |      547 |      0.242 |           0.171 |                  0.226 |                        0.98  |          0.346 |                        0.002 |                              0 |                     0 |                   0.031 |               0.895 |               10     |
| dom05         |      547 |      0.194 |           0.109 |                  0.192 |                        0.996 |          0.258 |                        0.001 |                              0 |                     0 |                   0.032 |               0.899 |               10     |
| dom           |      547 |      0.984 |           0.325 |                  0.25  |                        0.146 |          0.859 |                        0.499 |                              0 |                     0 |                   0.074 |               0.226 |               10     |
| dom-rs        |      289 |      0.949 |           0.288 |                  0.832 |                        0.837 |          0.827 |                        0.479 |                              0 |                     0 |                   0.075 |               0.266 |               23.042 |
| rand          |      547 |      0.232 |           0.168 |                  0.224 |                        0.989 |          0.333 |                        0.001 |                              0 |                     0 |                   0.027 |               0.898 |               10     |

## Paired change in SE vs baseline (same points, same seeds for the first 10 samples)

| condition | SE | points | trials | mean ΔSE per point | Wilcoxon p | mean ΔSE per trial [95% CI] | trials up |
|---|---|---|---|---|---|---|---|
| dom05 | plain K = 10 | 547 | 16 | -0.048 | 0.0039 | -0.041 [-0.087, +0.003] | 4/16 |
| dom05 | valid only | 542 | 16 | -0.062 | 0.0001 | -0.053 [-0.090, -0.021] | 2/16 |
| dom05 | rejection-sampled | 534 | 16 | -0.042 | 0.011 | -0.035 [-0.080, +0.006] | 5/16 |
| dom | plain K = 10 | 547 | 16 | +0.742 | 3e-67 | +0.718 [+0.620, +0.829] | 16/16 |
| dom | valid only | 451 | 16 | +0.184 | 1.4e-10 | +0.172 [+0.102, +0.259] | 14/16 |
| dom | rejection-sampled | 80 | 13 | +0.040 | 0.37 | +0.061 [-0.043, +0.175] | 6/13 |
| dom-rs | plain K = 10 | 289 | 9 | +0.713 | 1.5e-34 | +0.696 [+0.576, +0.827] | 9/9 |
| dom-rs | valid only | 243 | 9 | +0.145 | 5.7e-05 | +0.145 [+0.072, +0.210] | 8/9 |
| dom-rs | rejection-sampled | 240 | 9 | +0.624 | 7.6e-27 | +0.597 [+0.463, +0.723] | 9/9 |
| rand | plain K = 10 | 547 | 16 | -0.010 | 0.79 | -0.008 [-0.024, +0.005] | 5/16 |
| rand | valid only | 542 | 16 | -0.004 | 0.99 | -0.004 [-0.017, +0.007] | 6/16 |
| rand | rejection-sampled | 533 | 16 | -0.008 | 0.97 | -0.006 [-0.022, +0.008] | 5/16 |
