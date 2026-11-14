# KV Store + skill=clm: Qwen3.5-4B vs 9B (paper settings; line = seed mean)

| family | model | skill | task | pressure | seed | reward | ops | edits | LM calls | peak ctx | min | end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kv_store | qwen35-4b | clm | kv-store-R260-seed42 | 0.42 | 42 | 0.875 | 27/27 | 3 | 51 | 13186 | 5.3 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R260-seed43 | 0.42 | 43 | 1.000 | 27/27 | 3 | 51 | 13880 | 5.4 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R1000-seed42 | 1.52 | 42 | 1.000 | 34/34 | 10 | 58 | 13304 | 6.7 | submit |
| kv_store | qwen35-4b | clm | kv-store-R1000-seed43 | 1.52 | 43 | 1.000 | 34/34 | 10 | 56 | 13212 | 6.6 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R4000-seed42 | 5.99 | 42 | 1.000 | 64/64 | 40 | 90 | 14282 | 11.8 | submit |
| kv_store | qwen35-4b | clm | kv-store-R4000-seed43 | 6.00 | 43 | 1.000 | 64/64 | 40 | 89 | 13516 | 11.2 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R16000-seed42 | 23.88 | 42 | 1.000 | 184/184 | 160 | 209 | 14887 | 29.6 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R16000-seed43 | 23.89 | 43 | 1.000 | 184/184 | 160 | 185 | 10752 | 26.5 | stream_exhausted |
| kv_store | qwen35-9b | clm | kv-store-R260-seed42 | 0.42 | 42 | 1.000 | 27/27 | 3 | 53 | 14070 | 7.9 | submit |
| kv_store | qwen35-9b | clm | kv-store-R260-seed43 | 0.42 | 43 | 1.000 | 27/27 | 3 | 51 | 13095 | 7.0 | submit |
| kv_store | qwen35-9b | clm | kv-store-R1000-seed42 | 1.52 | 42 | 0.625 | 26/34 | 9 | 47 | 26881 | 24.6 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R1000-seed43 | 1.52 | 43 | 0.333 | 19/34 | 10 | 69 | 29002 | 17.6 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R4000-seed42 | 5.99 | 42 | 1.000 | 64/64 | 39 | 88 | 19292 | 22.5 | submit |
| kv_store | qwen35-9b | clm | kv-store-R4000-seed43 | 6.00 | 43 | 0.250 | 47/64 | 39 | 69 | 31199 | 21.5 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R16000-seed42 | 23.88 | 42 | 0.000 | 32/184 | 30 | 38 | 30793 | 34.7 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R16000-seed43 | 23.89 | 43 | 0.000 | 43/184 | 37 | 48 | 35869 | 21.7 | budget_wall |
