# Literature search: uncertainty-aware model-driven context management

Date: 2026-11-14. All entries were seen in WebSearch results; those marked [F] were also opened with WebFetch. Details not in an abstract were not verified. Plan tags: B = baseline (reproduce CLM), E = elicitation, D = direction/steering, I = implication/policy.

## 0. Target paper and repo
| Paper | Link | Finding | Tag |
|---|---|---|---|
| Context Language Models. Shao, Shen, ..., Zettlemoyer, Koh, 2026 [F] | https://arxiv.org/abs/2609.37725 | Context is a file the model may edit without restriction. Zero-shot CLM beats SOTA context management: +11.4% BrowseComp-Plus at 21.5% fewer FLOPs. Instruction steering gives up to +35.9 pts on a context-management task. Also covers online RL (Qwen3.5-9B) and Suffix Cache Reuse. | B |
| CLM code / ContextBench [F] | https://github.com/facebookresearch/context-language-models | README: ContextBench "measures what an agent keeps, updates, and offloads when its input does not fit". Tasks on HF `context-language-model/ContextBench`. Run via Harbor: `harbor jobs start --repo RulinShao/ContextBench -d contextbench -a clm_contextbench:ClmStream -m openai/<model>`. Works with any OpenAI-compatible endpoint, so an open-weights model served locally can be used. | B, D |

Note: the abstract page does not describe the edit ops or ContextBench. Read the repo (`clm/clm_harness`, `clm/clm_contextbench`) for the edit API.

## 1. LLM-driven context management / compaction and what it drops
| Paper | Link | Finding | Tag / code |
|---|---|---|---|
| Self-Compacting LM Agents (SelfCompact). Li, ..., Khashabi, 2026 [F] | https://arxiv.org/abs/2606.23525 | Model decides when to compact via a tool plus a rubric (compact after a subtask, hold off mid-derivation). Up to +18.1 pts math, 30-70% lower cost. "Unprompted models often can't reliably tell when their context has degraded", and a rubric closes the gap. | E, I. Closest prior work on the model's awareness of its own context state. No code listed. |
| Lost in Context Compaction (CONPACT). Wang et al., 2026 [F] | https://arxiv.org/abs/2608.11242 | Compactors keep only about 17% of injected side constraints. An agent deleted emails without approval in 30/100 sessions after compaction vs 0 before. A separate constraint extractor gets >90% retention. | E, I. Code: https://github.com/ZhiqiEliWang/compaction-integrity |
| What to Keep, What to Forget: Rate-Distortion View of Memory Compaction. Colaco, Lahjouji, 2026 [F] | https://arxiv.org/abs/2607.08032 | Keep/drop signals (attention magnitude, recency) can discard info a later query needs, and the loss is irreversible. Repeated agent compaction is rarely measured. | B, I. No code. |
| Beyond Compaction: Structured Context Eviction for Long-Horizon Agents, 2026 (search snippet only) | https://huggingface.co/papers/2606.11213.md | Argues summarization compaction has unpredictable loss, damages causal structure, and can add hallucinations. Proposes priority-ordered eviction. | I. Results not verified. |
| ACON. Kang et al., ICML 2026 | https://arxiv.org/abs/2510.00615 | Learns natural-language compression guidelines from failure pairs (compressed run fails, full run succeeds). Peak tokens -26 to -54%. | B, I. Code: https://github.com/microsoft/acon |
| Scaling Long-Horizon LLM Agent via Context-Folding. Sun, Chen et al., 2025 | https://arxiv.org/abs/2510.11967 | Branch into a subtask, then fold it into a summary. FoldGRPO RL. Matches ReAct with a 10x smaller active context. | B. Project page: context-folding.github.io |
| ReSum. Wu, Li et al., 2025 | https://arxiv.org/abs/2509.13313 | Periodic structured summaries for search agents. +4.5% over ReAct training-free, +8.2% more with RL. | B |
| Agentic Context Engineering (ACE). Zhang ... Zou, Olukotun, ICLR 2026 | https://arxiv.org/abs/2510.04618 | Names two failure modes of LLM rewriting: "brevity bias" (drops domain insight) and "context collapse" (iterative rewriting erodes detail). Itemized bullets avoid full rewrites. | E, I |
| MemGPT. Packer et al., 2023 | https://arxiv.org/abs/2310.08560 | The LLM pages information between context and external storage through function calls. | B (precursor) |
| Anthropic context management (context editing + memory tool) | https://www.anthropic.com/news/context-management | Claude clears stale tool results and chooses what to store in a file-based memory. Reported +29% (editing) and +39% (editing + memory) on an internal agentic eval. | B. Lab blog, secondary coverage only. |

## 2. Context degradation, and awareness of what is in context
| Paper | Link | Finding | Tag / code |
|---|---|---|---|
| Lost in the Middle. Liu et al., TACL 2023 | https://arxiv.org/abs/2307.03172 | U-shaped accuracy by position of relevant info. | B |
| Context Rot. Hong, Troynikov, Huber (Chroma), 2025 | https://trychroma.com/research/context-rot | 18 LLMs degrade non-uniformly with input length. Distractors and low query-target similarity make it worse. | B. Code: https://github.com/chroma-core/context-rot |
| Context Length Alone Hurts LLM Performance Despite Perfect Retrieval. Du et al., EMNLP Findings 2025 | https://arxiv.org/abs/2510.05381 | Accuracy drops 13.9-85% with length even when evidence is retrieved perfectly or irrelevant tokens are masked. Reciting evidence first helps. | B. Supports a length-alone effect, separate from lost information. |
| Self-knowledge of context: see SelfCompact (sec. 1) | | Models cannot reliably tell when their own context has degraded. | E |

## 3. Epistemic uncertainty and calibration
| Paper | Link | Finding | Tag / code |
|---|---|---|---|
| Language Models (Mostly) Know What They Know (P(True), P(IK)). Kadavath et al., 2022 | https://arxiv.org/abs/2207.05221 | Larger models are calibrated on P(True). P(IK) is trainable. P(IK) rises when relevant source material or hints are in context. | E |
| Teaching Models to Express Uncertainty in Words. Lin, Hilton, Evans, TMLR 2022 | https://arxiv.org/abs/2205.14334 | Fine-tuned GPT-3 verbalizes calibrated confidence. | E |
| Can LLMs Express Their Uncertainty? Xiong et al., ICLR 2024 | https://arxiv.org/abs/2306.13063 | Verbalized confidence is overconfident. Consistency and hybrid methods are better. All methods struggle on hard tasks. | E |
| Semantic Uncertainty (Kuhn, Gal, Farquhar, 2022) and Detecting hallucinations with semantic entropy (Farquhar et al., Nature 2024) | https://neurips.cc/virtual/2022/65659 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC11186750 | Entropy over meaning clusters of sampled answers detects confabulation. Sampling-based, so it could be applied to "keep/delete" decisions. | E |
| Agentic Uncertainty Quantification (AUQ). Zhang et al., 2026 [F] | https://arxiv.org/abs/2601.15703 | Verbalized confidence is carried in memory ("uncertainty-aware memory"), and low confidence triggers reflection. Closest to "uncertainty labels in the context file". | E, I. No code listed. |
| Agentic Uncertainty Reveals Agentic Overconfidence. Kaddour et al., ICLR 2026 | https://arxiv.org/abs/2602.06948 | Coding agents predict 73% success against a true 35%. Pre-execution estimates discriminate about as well as or better than post-execution ones. A "find bugs" framing cuts overconfidence by up to 15 pp. | E. Code: https://github.com/sevn-ai/agentic-uncertainty |
| UQ in LLM Agents: Foundations, Challenges, Opportunities (survey), 2026 (snippet) | https://arxiv.org/pdf/2602.05073 | Frames agent UQ as multi-turn, not single-answer. | E |

## 4. Uncertainty / knowledge-boundary directions in activations
| Paper | Link | Finding | Tag / code |
|---|---|---|---|
| Do I Know This Entity? Ferrando, Obeso, Rajamanoharan, Nanda, ICLR 2025 | https://arxiv.org/abs/2411.14257 | SAE features for known vs unknown entities. Steering them makes the model refuse known entities or hallucinate on unknown ones. They also affect the chat model. | D (key). Check the arXiv listing for code. |
| Refusal Is Mediated by a Single Direction. Arditi, Obeso et al., NeurIPS 2024 | https://arxiv.org/abs/2406.11717 | Difference-of-means direction. Ablating it removes refusal and adding it induces refusal, across 13 models. | D (recipe). Code: https://github.com/andyrdt/refusal_direction |
| Confidence Regulation Neurons. Stolfo et al., NeurIPS 2024 | https://arxiv.org/abs/2406.16254 | Entropy neurons (act on the LayerNorm scale through the unembedding null space) and token-frequency neurons. | D (output-side confidence). Code: https://github.com/bpwu1/confidence-regulation-neurons |
| LLMs Know More Than They Show. Orgad et al., ICLR 2025 | https://arxiv.org/abs/2410.02707 | Truthfulness signal is concentrated in particular tokens. The model may encode the right answer yet output a wrong one. Probes do not generalize across datasets. | D. Code: https://github.com/technion-cs-nlp/LLMsKnow |
| Geometry of Truth. Marks, Tegmark, COLM 2024 | https://arxiv.org/abs/2310.06824 | Linear truth direction. Mass-mean probes. Causal intervention flips true/false judgments. | D. Code: https://github.com/saprmarks/geometry-of-truth |
| Representation Engineering. Zou et al., 2023 | https://arxiv.org/abs/2310.01405 | Population-level reading and control vectors for honesty and other traits. | D. Code: https://github.com/andyzoujm/representation-engineering |
| Estimating Knowledge in LLMs Without Generating a Token (KEEN). Gottesman, Geva, EMNLP 2024 | https://arxiv.org/abs/2406.12673 | Probe on an entity-name representation predicts QA accuracy (r about 0.58-0.68). Suggested use: decide on retrieval or abstention. | D. Code: https://github.com/dhgottesman/keen_estimating_knowledge_in_llms |
| Two Axes of LLM Abstention. Wagner, 2026 [F] | https://arxiv.org/abs/2607.08456 | Answer confidence tracks correctness but not answerability. A hidden-state probe does the reverse (AUROC 0.69-0.77 on false premises). Two-threshold policy gives 0.75 coverage vs 0.31 for a single threshold. | D, I (two-score gate). No code listed. |
| Knowledge Knows, Verbalization Tells. Xiros et al., 2026 [F] | https://arxiv.org/abs/2607.05013 | Solvability knowledge and verbalization are separate linear directions. Steering along them improves abstention. | D (closest steering-for-abstention result). No code listed. |
| Purging the Gray Zone (GeoDe), 2026 (snippet) | https://arxiv.org/abs/2604.14324 | Truthfulness hyperplane used as a confidence classifier for abstention fine-tuning. | D. Code: https://github.com/Notbesidemoon/GeoDe (from the search result, not verified). |

## 5. Metacognition, introspection, abstention on actions
| Paper | Link | Finding | Tag / code |
|---|---|---|---|
| Looking Inward: Introspection. Binder et al., ICLR 2025 | https://arxiv.org/abs/2410.13787 | Models predict their own behavior better than another model trained on that behavior does. Works on simple tasks only. | E |
| Emergent Introspective Awareness. Lindsey (Anthropic), 2026 | https://arxiv.org/abs/2601.01828 | Concept injection. Claude Opus 4.1 detects an injected concept about 20% of the time. Functional, unreliable introspection. | E, D (injection/steering method) |
| Agentic Abstention: Do Agents Know When to Stop? Luo, Wen, Wang, NeurIPS 2026 [F] | https://arxiv.org/abs/2606.28733 | 13 agents, 28k tasks. Agents either never abstain or abstain late. More capable models are sometimes later to abstain. CONVOLVE distills stopping rules into context (26.7 to 57.4 recall). | I. Code: https://agentic-abstention.github.io |
| Check Yourself Before You Wreck Yourself: Selectively Quitting Improves LLM Agent Safety, 2025 (snippet) | https://arxiv.org/abs/2510.16492 | Quit option for low-confidence agents. Better safety at about 0.03 helpfulness cost on ToolEmu. | I |
| Structured Uncertainty-guided Clarification for LLM Agents, ACL Findings 2026 (snippet) | https://aclanthology.org/2026.findings-acl.2028.pdf | Uncertainty over tool parameters selects clarification questions. | I |
| Uncertainty-Aware Abstention with Provable Guarantees, 2026 (snippet) | https://www.alphaxiv.org/abs/2607.04430 | Calibrated confidence threshold with finite-sample risk guarantee. QA only. | I (thresholded gate) |

## 6. Uncertainty about context itself
| Paper | Link | Finding | Tag / code |
|---|---|---|---|
| Sufficient Context. Joren et al., ICLR 2025 | https://arxiv.org/abs/2411.06037 | Classifies whether context suffices. Frontier models answer wrongly rather than abstain when context is insufficient. Sufficiency-guided selective generation gives +2-10% correct among answered. | E, I. Autorater prompts released. |
| Adaptive Chameleon or Stubborn Sloth. Xie et al., ICLR 2024 | https://arxiv.org/abs/2305.13300 | Models accept external evidence that conflicts with memory when it is the only evidence, but show confirmation bias when some evidence agrees with memory. | E (parametric vs context trust). Code: OSU-NLP-Group (see paper). |
| Query-Level Uncertainty in LLMs. Chen et al., 2025 (snippet) | https://arxiv.org/abs/2506.09669 | Training-free, pre-generation estimate of knowledge boundary. | E |

## (a) Gap analysis (our novelty)
- No work I found studies uncertainty about the context-edit decision itself (keep/delete/summarize). Existing work either makes the model decide when to compact (SelfCompact), or detects loss after compaction (CONPACT), or makes compression rules learnable offline (ACON, ACE). None asks whether the model knows what the context is worth, or where its edit errors come from.
- CLM is new (Sept 2026). No paper tests CLM's unrestricted edits against an uncertainty measure.
- Uncertainty directions (Ferrando, Arditi, Marks, Wagner, Xiros) are tested on QA/refusal. None is steered on an edit-agent policy (edit aggressiveness, delete vs keep).
- Uncertainty gating exists for answers and agent stopping (Agentic Abstention, Quitting, Wagner two-score) but not for context mutations, which are irreversible and compound across turns.
- AUQ puts verbalized confidence into memory, but not into per-item labels in an editable context file that the model later reads when deciding what to delete.
- Open question: Du et al. show length alone hurts. So "compact more" may help even with perfect retention. This confound needs controlling when linking degradation to uncertainty.
- Wagner and Xiros show a model can represent a problem it does not report. This predicts a gap between internal uncertainty about context and edit behavior, which is directly testable here.

## (b) Top 5 must-read
1. Context Language Models (2609.37725) plus the repo and ContextBench.
2. Self-Compacting LM Agents (2606.23525), for model self-awareness of context state.
3. Lost in Context Compaction (2608.11242), for what compaction drops and irreversible deletes.
4. Do I Know This Entity? (2411.14257) together with Arditi et al. (2406.11717), for the steering recipe.
5. Two Axes of LLM Abstention (2607.08456) together with Agentic Abstention (2606.28733), for the two-score gate and abstention on actions.
Runner-up: Agentic Uncertainty Quantification (2601.15703).

## (c) Possible uncertainty-aware edit policies
1. Per-item confidence labels: when the model writes or summarizes a segment, it appends a verbalized confidence plus a "reason to keep" tag (AUQ-style). Later edit passes see these labels. Test whether the labels predict later regret (item needed after deletion).
2. Thresholded edit gate: allow delete or lossy summarize only when estimated uncertainty about the item's relevance is below tau. Otherwise keep verbatim, or move to an offload file (reversible, like MemGPT and the Anthropic memory tool). Calibrate tau for a risk budget, as in 2607.04430.
3. Two-score gate (Wagner-style): one score for "is this item relevant to the task?" (sufficiency or answerability) and one for "is my summary faithful?" (correctness). Edit only when both clear thresholds.
4. Probe-based gate: train a linear probe on the residual stream at the edit decision token (difference-of-means as in Arditi, or Ferrando-style known/unknown features) to predict edit regret. Gate or steer edits with it. Compare against verbalized confidence to look for a Xiros-style gap between internal knowledge and what the model says.
5. Reversible-by-default with a protected set: soft-delete (tombstone with a short summary) and a separate non-compressible store for constraints and goals (CONPACT extractor idea). Uncertainty only decides what goes into the compressible region.
