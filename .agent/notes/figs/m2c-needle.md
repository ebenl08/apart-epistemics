# Needle retention, Qwen3.5-4B + skill=clm (paper settings; line = seed mean)

| family | model | skill | task | pressure | seed | reward | ops | edits | LM calls | peak ctx | min | end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| needle_retention | qwen35-4b | clm | needle-retention-K4-C4-seed42 | 0.48 | 42 | 1.000 | 4/4 | 4 | 4 | 7616 | 2.2 | stream_exhausted |
| needle_retention | qwen35-4b | clm | needle-retention-K4-C4-seed43 | 0.49 | 43 | 1.000 | 4/4 | 4 | 4 | 9388 | 4.1 | stream_exhausted |
| needle_retention | qwen35-4b | clm | needle-retention-K4-C24-seed42 | 2.91 | 42 | 0.042 | 24/24 | 24 | 24 | 8017 | 20.2 | stream_exhausted |
| needle_retention | qwen35-4b | clm | needle-retention-K4-C24-seed43 | 2.92 | 43 | 0.167 | 24/24 | 24 | 24 | 8216 | 22.2 | stream_exhausted |
| needle_retention | qwen35-4b | clm | needle-retention-K8-C60-seed42 | 7.48 | 42 | 0.500 | 34/60 | 36 | 46 | 28356 | 51.9 | budget_wall |
| needle_retention | qwen35-4b | clm | needle-retention-K8-C60-seed43 | 7.49 | 43 | 0.850 | 52/60 | 51 | 51 | 24707 | 26.6 | budget_wall |
| needle_retention | qwen35-4b | clm | needle-retention-K2-C192-seed42 | 23.00 | 42 | 0.026 | 6/192 | 5 | 5 | 32811 | 4.4 | budget_wall |
| needle_retention | qwen35-4b | clm | needle-retention-K2-C192-seed43 | 23.01 | 43 | 0.495 | 101/192 | 100 | 111 | 25532 | 52.0 | budget_wall |
