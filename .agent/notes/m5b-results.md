# M5B: does Qwen's context-pressure drop show up in other families?

2026-11-16. Setup, fixes and run history: [`handoff/handoff-m5b.md`](../handoff/handoff-m5b.md) and `decisions.md`.

## Question

In M5, Qwen 3.5 9B's ContextBench success fell as context pressure rose
([`m5-seed-sweep-results.md`](m5-seed-sweep-results.md)). M5B runs the same KV + LogTriage `clm` sweep on two
other families that use native tool calls:
- **Gemma 4 E4B**, thinking on;
- **Ministral 3 8B Instruct 2512**, which has no thinking mode.

There are 4 seeds per cell (42–45); M5 had 8.

## Answer: no, neither model reproduces it

Success means reward ≥ 0.95, as in M5. The trend test is Cochran–Armitage on success against log₂ pressure, one-sided for a decrease.

| Model | KV z (p) | LogTriage z (p) | Verdict |
|---|---|---|---|
| Qwen 3.5 9B (M5, 8 seeds) | −2.84 (0.002) | −3.27 (0.0005) | decreasing |
| Gemma 4 E4B | −0.00 (0.50) | −0.41 (0.34) | flat |
| Ministral 3 8B | −0.89 (0.19) | +1.19 (0.88) | flat |

**Success per cell**

| Family | Level | Qwen 9B (M5) | Gemma 4 E4B | Ministral 3 8B |
|---|---|---|---|---|
| KV | R260 (0.4x) | 7/8 | 1/4 | 3/4 |
| KV | R1000 (1.5x) | 4/8 | 1/4 | 1/4 |
| KV | R4000 (6.0x) | 4/8 | 1/4 | 3/4 |
| KV | R16000 (23.9x) | 1/8 | 1/4 | 1/4 |
| LogTriage | L320 (0.5x) | 6/8 | 1/4 | 0/4 |
| LogTriage | L1600 (2.2x) | 2/8 | 1/4 | 0/4 |
| LogTriage | L6400 (7.9x) | 0/8 | 0/4 | 0/4 |
| LogTriage | L12800 (15.7x) | 1/8 | 1/4 | 1/4 |

- **Gemma 4 E4B** is weak at every level, at about 25% success even with no pressure. There's no high starting point to fall from.
  Its `none` run scored 0 on all 16 trials and made no context edits, so the method text is what makes it act at all.
- **Ministral 3 8B, KV:** the closest to Qwen. It's strong at R260 and R4000 (3/4 each) and weak at R16000 (1/4).
  The test isn't significant with 4 seeds, and R1000 (1/4) breaks the shape.
- **Ministral 3 8B, LogTriage:** fails at every level, low pressure included. At L320 it gets only partial credit
  (mean reward 0.30). Its one success is at the highest level. Without a working baseline there's no trend to measure.

## Caveats

- **Power:** 4 seeds per cell, so 16 trials per family. A moderate decrease could be missed. Qwen's effect was large, which is
  why 8 seeds were enough there.
- **Two baselines are broken:** Gemma everywhere and Ministral on LogTriage are near the floor even at low pressure.
  For these model and task pairs, "no decrease" means the model can't do the task, not that it's robust to pressure.
- **Not a like-for-like comparison:**
  - Ministral has no thinking mode.
  - The proxy removes Ministral's empty assistant replies before sending its history back, because its tokenizer rejects them.
  - 5 Gemma trials were rerun with the same seeds after an infrastructure crash.
  - Ministral's `none` arm was skipped to save cost.
- The planned Llama 3.1 8B and Gemma 3 couldn't drive the harness's native `bash` tool, so they were replaced.
