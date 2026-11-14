# KV Store + skill=clm: Qwen3.5-4B vs 9B, seeds 42-45 at R1000+ (line = seed mean)

| family | model | skill | task | pressure | seed | reward | ops | edits | LM calls | peak ctx | min | end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kv_store | qwen35-4b | clm | kv-store-R260-seed42 | 0.42 | 42 | 0.875 | 27/27 | 3 | 51 | 13186 | 5.3 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R260-seed43 | 0.42 | 43 | 1.000 | 27/27 | 3 | 51 | 13880 | 5.4 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R1000-seed44 | 1.51 | 44 | 1.000 | 34/34 | 10 | 58 | 13354 | 5.0 | submit |
| kv_store | qwen35-4b | clm | kv-store-R1000-seed42 | 1.52 | 42 | 1.000 | 34/34 | 10 | 58 | 13304 | 6.7 | submit |
| kv_store | qwen35-4b | clm | kv-store-R1000-seed43 | 1.52 | 43 | 1.000 | 34/34 | 10 | 56 | 13212 | 6.6 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R1000-seed45 | 1.52 | 45 | 1.000 | 34/34 | 10 | 58 | 17584 | 5.7 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R4000-seed44 | 5.98 | 44 | 0.000 | 34/64 | 31 | 37 | 30129 | 6.6 | budget_wall |
| kv_store | qwen35-4b | clm | kv-store-R4000-seed45 | 5.99 | 45 | 0.000 | 38/64 | 37 | 37 | 27614 | 9.4 | budget_wall |
| kv_store | qwen35-4b | clm | kv-store-R4000-seed42 | 5.99 | 42 | 1.000 | 64/64 | 40 | 90 | 14282 | 11.8 | submit |
| kv_store | qwen35-4b | clm | kv-store-R4000-seed43 | 6.00 | 43 | 1.000 | 64/64 | 40 | 89 | 13516 | 11.2 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R16000-seed44 | 23.87 | 44 | 1.000 | 184/184 | 160 | 209 | 14375 | 23.9 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R16000-seed45 | 23.87 | 45 | 1.000 | 184/184 | 160 | 208 | 14589 | 23.5 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R16000-seed42 | 23.88 | 42 | 1.000 | 184/184 | 160 | 209 | 14887 | 29.6 | stream_exhausted |
| kv_store | qwen35-4b | clm | kv-store-R16000-seed43 | 23.89 | 43 | 1.000 | 184/184 | 160 | 185 | 10752 | 26.5 | stream_exhausted |
| kv_store | qwen35-9b | clm | kv-store-R260-seed42 | 0.42 | 42 | 1.000 | 27/27 | 3 | 53 | 14070 | 7.9 | submit |
| kv_store | qwen35-9b | clm | kv-store-R260-seed43 | 0.42 | 43 | 1.000 | 27/27 | 3 | 51 | 13095 | 7.0 | submit |
| kv_store | qwen35-9b | clm | kv-store-R1000-seed44 | 1.51 | 44 | 1.000 | 34/34 | 10 | 58 | 13133 | 9.6 | stream_exhausted |
| kv_store | qwen35-9b | clm | kv-store-R1000-seed42 | 1.52 | 42 | 0.625 | 26/34 | 9 | 47 | 26881 | 24.6 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R1000-seed43 | 1.52 | 43 | 0.333 | 19/34 | 10 | 69 | 29002 | 17.6 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R1000-seed45 | 1.52 | 45 | 1.000 | 34/34 | 10 | 58 | 13549 | 9.6 | submit |
| kv_store | qwen35-9b | clm | kv-store-R4000-seed44 | 5.98 | 44 | 1.000 | 64/64 | 39 | 94 | 20003 | 18.3 | stream_exhausted |
| kv_store | qwen35-9b | clm | kv-store-R4000-seed45 | 5.99 | 45 | 0.000 | 16/64 | 11 | 22 | 34892 | 25.8 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R4000-seed42 | 5.99 | 42 | 1.000 | 64/64 | 39 | 88 | 19292 | 22.5 | submit |
| kv_store | qwen35-9b | clm | kv-store-R4000-seed43 | 6.00 | 43 | 0.250 | 47/64 | 39 | 69 | 31199 | 21.5 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R16000-seed44 | 23.87 | 44 | 0.000 | 49/184 | 45 | 54 | 26491 | 15.2 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R16000-seed45 | 23.87 | 45 | 0.000 | 16/184 | 12 | 25 | 27224 | 6.3 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R16000-seed42 | 23.88 | 42 | 0.000 | 32/184 | 30 | 38 | 30793 | 34.7 | budget_wall |
| kv_store | qwen35-9b | clm | kv-store-R16000-seed43 | 23.89 | 43 | 0.000 | 43/184 | 37 | 48 | 35869 | 21.7 | budget_wall |
