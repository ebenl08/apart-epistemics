# LogTriage, Qwen3.5-4B + skill=clm (paper settings; line = seed mean)

| family | model | skill | task | pressure | seed | reward | ops | edits | LM calls | peak ctx | min | end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| log_triage | qwen35-4b | clm | log-triage-L320-seed42 | 0.46 | 42 | 1.000 | 47/47 | 23 | 74 | 19994 | 14.2 | stream_exhausted |
| log_triage | qwen35-4b | clm | log-triage-L320-seed43 | 0.46 | 43 | 1.000 | 47/47 | 23 | 73 | 11791 | 13.9 | stream_exhausted |
| log_triage | qwen35-4b | clm | log-triage-L1600-seed43 | 2.15 | 43 | 1.000 | 139/139 | 115 | 169 | 12710 | 45.6 | stream_exhausted |
| log_triage | qwen35-4b | clm | log-triage-L1600-seed42 | 2.15 | 42 | 1.000 | 139/139 | 115 | 169 | 12904 | 45.2 | submit |
| log_triage | qwen35-4b | clm | log-triage-L6400-seed42 | 7.89 | 42 | 1.000 | 143/143 | 119 | 168 | 12332 | 46.7 | stream_exhausted |
| log_triage | qwen35-4b | clm | log-triage-L6400-seed43 | 7.89 | 43 | 1.000 | 143/143 | 119 | 161 | 11513 | 46.2 | stream_exhausted |
| log_triage | qwen35-4b | clm | log-triage-L12800-seed42 | 15.73 | 42 | 0.000 | 175/262 | 170 | 200 | 26513 | 53.5 | budget_wall |
| log_triage | qwen35-4b | clm | log-triage-L12800-seed43 | 15.74 | 43 | 0.958 | 262/262 | 238 | 289 | 13500 | 59.7 | stream_exhausted |
