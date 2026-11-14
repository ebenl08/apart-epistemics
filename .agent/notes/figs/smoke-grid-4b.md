# Smoke grid, Qwen3.5-4B, lowest level (dots = single trials)

| family | model | skill | task | pressure | seed | reward | ops | edits | LM calls | peak ctx | min | end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kv_store | qwen35-4b | clm | kv-store-R260-seed42 | 0.42 | 42 | 0.958 | 27/27 | 3 | 50 | 12923 | 4.0 | submit |
| kv_store | qwen35-4b | none | kv-store-R260-seed42 | 0.42 | 42 | 0.125 | 7/27 | 1 | 90 | 26746 | 36.9 | budget_wall |
| log_triage | qwen35-4b | clm | log-triage-L320-seed42 | 0.46 | 42 | 1.000 | 47/47 | 23 | 77 | 15738 | 9.7 | stream_exhausted |
| log_triage | qwen35-4b | none | log-triage-L320-seed42 | 0.46 | 42 | 0.000 | 17/47 | 0 | 34 | 25997 | 12.7 | budget_wall |
| needle_retention | qwen35-4b | clm | needle-retention-K4-C4-seed42 | 0.48 | 42 | 0.250 | 4/4 | 4 | 4 | 8305 | 1.6 | stream_exhausted |
| needle_retention | qwen35-4b | none | needle-retention-K4-C4-seed42 | 0.48 | 42 | 1.000 | 4/4 | 0 | 8 | 19056 | 1.0 | submit |
| sudoku_sketchpad | qwen35-4b | clm | sudoku-sketchpad-t8-seed42 | 0.59 | 42 | 0.000 | 8/8 | 8 | 12 | 13309 | 5.1 | stream_exhausted |
| sudoku_sketchpad | qwen35-4b | clm | sudoku-sketchpad-t8-seed43 | 0.59 | 43 | 1.000 | 8/8 | 7 | 9 | 10299 | 2.7 | stream_exhausted |
| sudoku_sketchpad | qwen35-4b | none | sudoku-sketchpad-t8-seed42 | 0.59 | 42 | 0.875 | 8/8 | 0 | 8 | 30730 | 14.0 | stream_exhausted |
