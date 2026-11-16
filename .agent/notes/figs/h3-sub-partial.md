# H3 decision level: directional ablation vs baseline (9B)

Trials: subset runs/m6-se/queue-h3sub.txt.

## Outcomes per condition

|               |   points |   SE plain |   SE valid-only |   SE rejection-sampled |   points with 10 valid calls |   share SE > 0 |   no_tool_call (of first 10) |   context_status (of first 10) |   error (of first 10) |   invalid (of first 10) |   agree with logged |   mean samples drawn |
|:--------------|---------:|-----------:|----------------:|-----------------------:|-----------------------------:|---------------:|-----------------------------:|-------------------------------:|----------------------:|------------------------:|--------------------:|---------------------:|
| baseline (9B) |      547 |      0.242 |           0.171 |                  0.226 |                        0.98  |          0.346 |                        0.002 |                              0 |                     0 |                   0.031 |               0.895 |                   10 |
| dom05         |      547 |      0.194 |           0.109 |                  0.192 |                        0.996 |          0.258 |                        0.001 |                              0 |                     0 |                   0.032 |               0.899 |                   10 |
| rand          |      547 |      0.232 |           0.168 |                  0.224 |                        0.989 |          0.333 |                        0.001 |                              0 |                     0 |                   0.027 |               0.898 |                   10 |
| dom           |      427 |      0.943 |           0.28  |                  0.185 |                        0.176 |          0.836 |                        0.481 |                              0 |                     0 |                   0.077 |               0.252 |                   10 |

## Paired change in SE vs baseline (same points, same seeds for the first 10 samples)

| condition | SE | points | trials | mean ΔSE per point | Wilcoxon p | mean ΔSE per trial [95% CI] | trials up |
|---|---|---|---|---|---|---|---|
| dom05 | plain K = 10 | 547 | 16 | -0.048 | 0.0039 | -0.041 [-0.087, +0.003] | 4/16 |
| dom05 | valid only | 542 | 16 | -0.062 | 0.0001 | -0.053 [-0.090, -0.021] | 2/16 |
| dom05 | rejection-sampled | 534 | 16 | -0.042 | 0.011 | -0.035 [-0.080, +0.006] | 5/16 |
| rand | plain K = 10 | 547 | 16 | -0.010 | 0.79 | -0.008 [-0.024, +0.005] | 5/16 |
| rand | valid only | 542 | 16 | -0.004 | 0.99 | -0.004 [-0.017, +0.007] | 6/16 |
| rand | rejection-sampled | 533 | 16 | -0.008 | 0.97 | -0.006 [-0.022, +0.008] | 5/16 |
| dom | plain K = 10 | 427 | 13 | +0.720 | 9.2e-53 | +0.695 [+0.598, +0.800] | 13/13 |
| dom | valid only | 349 | 13 | +0.172 | 1.1e-08 | +0.162 [+0.118, +0.203] | 12/13 |
| dom | rejection-sampled | 75 | 11 | +0.011 | 0.5 | +0.029 [-0.047, +0.101] | 5/11 |
