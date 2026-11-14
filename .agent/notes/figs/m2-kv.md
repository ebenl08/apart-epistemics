# M2 KV Store, Qwen3.5-4B + skill=clm (paper settings)

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
