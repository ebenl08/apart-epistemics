# M6 semantic entropy of CLM context decisions: results (9B)

Plan: [`../instruction-semantic-entropy.md`](../instruction-semantic-entropy.md). Decisions: [`../decisions.md`](../decisions.md).
Code: `infra/semantic_entropy/` (`entropy.py`, `collect.py`, `m6_run.sh`, `m6_status.sh`, `analyze.py`).
Pod `obvrywyztadwv4` (1×A40, $0.59/h, EU-SE-1). Outputs on the volume: `runs/m6-se/`, logs `runs/logs/m6-*.log`.

## Config

**Control (M5, unchanged):** M5 `skill=clm` 9B trials (42 logged: KV R260 s44–49, KV R1000/R4000/R16000 s46–49,
LogTriage 4 levels s44–49), `CB_SETTINGS=paper`, vLLM 0.33.0 BF16 prefix caching, rootfs
`sha256:05a994d2…` (same as M5), sampling T 0.7 / top_p 0.95 / thinking on / max_tokens 8192 (the logged request body, resent as is).

**New:** K = 10 samples per point (`n=10`, per-point seed), ≤ 40 points per trial (all `context_edit_turn`s +
5 `context_stay_turn`s per fill bin, capped at 40), outcome = per-block stay/edit/offload/delete + clobber flag,
or `invalid` / `no_tool_call` / `context_status` / `error`; discrete SE in bits.

## Milestones

| # | Done when | State |
|---|---|---|
| 0 | Log fields confirmed | done (earlier session) |
| 1 | `entropy.py` self-check | **done** |
| 2 | Gate A on dev trials | **done: 4/4 trials, 432/432 turns byte-identical** |
| 3 | Gate B + 10 labels hand-checked | **done: Gate B 160/160; 10/10 labels correct** |
| 4 | SE for dev trials; 5 high-SE points read | **done** (below) |
| 5 | Full 9B run + QA | running |
| 6 | Part 2 analysis, go/no-go | pending |

## Dev trials (milestones 2–4)

| trial | reward | mean SE | max SE | share SE = 0 | edit-turn SE (n) | stay-turn SE (n) | invalid samples |
|---|---|---|---|---|---|---|---|
| KV R4000 s46 (wall) | 0.125 | 0.30 | 1.36 | 0.57 | 0.27 (27) | 0.36 (13) | 21 |
| KV R4000 s49 | 1.0 | 0.36 | 1.52 | 0.57 | 0.39 (31) | 0.26 (9) | 20 |
| LT L1600 s49 (wall) | 0.0 | 0.21 | 1.57 | 0.70 | 0.25 (23) | 0.14 (17) | 1 |
| LT L1600 s47 | 1.0 | 0.04 | 0.47 | 0.93 | 0.04 (33) | 0.00 (7) | 0 |

- Samples are diverse (10 distinct reasoning traces at every point checked), but most converge on the skill's
  offload recipe, so 57–93% of points have SE = 0 (plan risk 2, "recipe floor"). SE is not flat, though.
- **The 5 highest-SE points** (1.29–1.57 bits) all mix three kinds of decision:
  1. offload the incoming batch now (the recipe);
  2. answer or look up a pending GET first, leaving the context untouched (`grep 'SET K… =' /tmp/ctx_offload/*`);
  3. the same recipe but cutting a different set of earlier turns (e.g. deleting 6 old blocks vs editing 3 of them).
  These are real context-management choices, not labelling noise.
- LogTriage: the failed trial (s49) has 5× the mean SE of the successful one (s47). KV: no difference on this pair.
- Hand check (10 random KV R4000 s46 samples): the offload script labels the SET-BATCH block `offload` and the
  turns it cut (not saved) `delete`; a `grep` on a missing offload file is `invalid` (exit 2, no edit); an ANSWER `printf`
  leaves every block `stay`. All 10 correct.

## Full 9B run (milestone 5)

- Pass 1 on 42 trials: 40 identical, 2 diverge, both on `ls -la /tmp` (directory size / mtime differ; disk content
  the same). Per the plan, points after the divergence are dropped: LT L320 s49 keeps turns < 43 of 84, LT L1600 s45
  keeps < 101 of 130.
- 1409 points chosen. Sampling at 16 concurrent points (dev used 8; KV cache was at 4%).
