# 24. Training strategy: orchestrator, agents and decision models

One page per question: what is trained, how, on what, and how we know it worked. Details live in `19` (DeckForge-LM), `20` (agents), `21` (tools), `09` (Laya), `25` (visual inspector). This document is the master plan that ties them together.

## 1. What is trained

| Component | Model | Method | Data | Primary metric | Gate owner |
|---|---|---|---|---|---|
| All agents (language work) | DeckForge-LM (`df-lm`, Qwen3 dense, sizes 32B, 14B, 8B) | SFT multitask, DPO, GRPO per agent, distillation | C1 to C7 (`19`, section 4) | golden-brief QA score, agent suite scores | `19` section 6 |
| Agent specialisation | per-agent LoRA adapters (rank 16) | SFT and GRPO on the agent's own data | agent traces, repair pairs | agent suite score | `20` section 11 |
| Orchestrator decisions (routing, scope, stop, escalate) | Laya heads (small option sets), CLM heads (large candidate sets) | supervised from logged outcomes plus counterfactual replay (section 3) | decision logs, replays, synthetic requests | end-to-end QA pass and cost per deck | section 3.4 |
| Supervisor (free-form revisions) | `df-lm` adapter `df-supervisor` | SFT on synthetic revision requests, GRPO with a routing reward (the routed owner's result is accepted on replay) | synthetic requests, user re-requests | route and scope accuracy, revision acceptance | `20` section 11 |
| Fast judges (text) | Laya heads `J_*` | supervised with calibration | exact-label synthetic defects, corpus positives, teacher labels | recall and precision on accepted items | `09` section 9.2 |
| Fast judges (visual) | Laya-Vision heads `V_*` | supervised with calibration | rendered snapshots with synthetic visual defects, corpus snapshots | recall and precision per defect type | `25` section 8 |
| Rubric reviewer (visual) | `df-vlm` | SFT on critique data, DPO on correct vs incorrect critiques | snapshots with exact-label defects, corpus critique descriptions | defect recall with correct region | `25` section 8 |
| Best-of-N verifier | CLM head `df-clm-verifier` | contrastive fine-tune (InfoNCE) | accepted vs rejected outputs from traces | top-1 pick quality on held-out tasks | section 5 |
| Tool router | Laya `D_TOOL_NEED`, `D_TOOL_GROUP` and CLM `tool-rank` head | supervised | tool outcome labels, accepted tool trajectories | selection accuracy | `21` section 6 |
| Learned tools | Laya and CLM heads, image ranker | supervised | `21` section 5.4 | per-tool metric | `21` section 5.4 |

## 2. The two decision models and when each is used

| Question shape | Model | Why |
|---|---|---|
| Typed question with 2 to 12 described options, needs calibrated probabilities and abstention (route, scope, defect class, gaps) | **Laya** | calibrated, abstains, tens of ms |
| Ranking many candidates (75 frameworks, 1,600 icons, all tools, N generated titles, N storylines), or the same action set reused across many states | **CLM-8B** (Stanford and NVIDIA, Apache-2.0) | contrastive scoring with cached action embeddings, cost barely grows with the number of candidates, strong as a verifier. Text-only in v0.1 |
| Typed question about a rendered slide image | **Laya-Vision** (independent fork of Laya, experimental, 201M parameters) | one forward pass over an image plus text, calibrated |
| Open critique, explanation, rewriting | DeckForge-LM or `df-vlm` | generation needed |

CLM serving facts that shape the design: it needs a frozen Qwen3-8B pooling encoder served by vLLM (`--runner pooling`, default `--max-model-len 2048`) plus `clm-serve` (heads of about 20M parameters, a fixed-size vector cache reserved at start-up). A head only works with the encoder it was trained against, so the CLM encoder is the **base** Qwen3-8B, never our fine-tuned `df-lm`. Its API is `POST /v1/systemone` (typed questions, TypeSafe-compatible) and `POST /v1/rank` (rank answers for a context).

## 3. Training the orchestrator

### 3.1 What is learned and what stays fixed

| Part | Fixed (code) or learned | Model |
|---|---|---|
| W1 topology, stage order, budgets, safety gates, interrupts | fixed | none |
| Ask the user or assume (`D_BRIEF_GAPS` threshold policy) | learned | Laya |
| Research needed for an analysis (`D_RESEARCH_NEEDED`, new) | learned | Laya |
| Framework shortlist ranking | learned | CLM (`framework-rank` head) |
| Exhibit tie-break | learned | Laya, CLM priors |
| Revision route and scope | learned | Laya, supervisor adapter fallback |
| Repair strategy per defect | learned | Laya |
| Stop repairing (`D_REPAIR_STOP`, new): accept residual minor defects or try another round | learned | Laya |
| Escalate a judge to Tier 2 or Tier 3 (beyond the fixed rules) | learned | Laya on confidence features |
| Pool routing (`D_POOL_ROUTE`, new): send a call to the 14B or 32B pool when both exist | learned | Laya |
| Best of N selection (variants for exec summary, key titles) | learned | CLM verifier head |

### 3.2 Data for orchestrator training

1. **Behaviour logs**: every decision row in `decision_log` with its later outcome (QA defects cleared, user accepted, cost and time). Only successful runs are used for behaviour cloning.
2. **Counterfactual replay** (the main source): LangGraph checkpoints make every decision point re-playable.
   - `deckforge replay sample --decision D_REPAIR_STRATEGY --n 500` picks checkpoints just before a decision.
   - For each, the replayer forks the run from that checkpoint (`graph.aupdate_state(config_at_checkpoint, {...forced choice...})` then `astream(None, forked_config)`) once per alternative option, in sandbox mode on eval briefs only.
   - Outcome per branch: final QA score, open blockers, LLM tokens, GPU seconds, wall time.
   - Label: the option with the best utility `U = QA score - 0.5 x blockers x 25 - 0.002 x seconds - 0.00001 x tokens` (weights in `config/utility.yaml`, reviewed by the founder).
   - These labels train the Laya and CLM heads. This is offline policy improvement without exposing customers to experiments.
3. **Synthetic requests**: 3,000 revision requests generated per agent and scope ("make the title punchier", "show this as a map", "add a slide on pricing", "the margin number is wrong") with known correct routes.
4. **Exploration on eval traffic only**: for low-risk decisions (exhibit tie-break, repair strategy), 5% epsilon-greedy exploration on internal eval runs to keep counterfactual coverage. Never on customer runs unless `allow_training` and `allow_exploration` are both set.

### 3.3 Method

| Decision family | Model | Training |
|---|---|---|
| Small typed choices | Laya head | `09` section 8 pipeline with replay labels as a new source (S6) |
| Rankings (frameworks, icons, tools, variants) | CLM head | `train/finetune.py --task clm` style contrastive training on (state text, chosen candidate) pairs with hard negatives mined from rejected candidates (`training/clm/`). Embeddings are cached once, so a head trains in minutes |
| Free-form routing | `df-supervisor` adapter | SFT on synthetic requests, GRPO with `environment_factory` exposing `call_<agent>` tools and a reward from the replayed outcome |

### 3.4 Orchestrator metrics

| Metric | Definition | Target (v1) |
|---|---|---|
| End-to-end success | runs reaching `succeeded` with no open blocker | at least 95% on golden briefs |
| Deck QA score | median `QAReport.score` | at least 85 |
| Repair rounds | mean rounds per deck | at most 1.0 |
| Cost per deck | LLM tokens and GPU seconds | 20% lower than the LLM-only orchestration baseline at equal QA score |
| Latency per deck | p50 and p95 wall time | `23` section 9.2 |
| User intervention rate | plan review edits plus regenerations per deck | down 30% from cycle 1 to cycle 4 |
| Clarification precision | questions whose answers changed the plan | at least 70% |
| Route accuracy (revisions) | correct agent and scope | at least 95% |
| Decision regret | utility of chosen option vs best replayed option, averaged | below 2 utility points |

## 4. Training the agents

Summary of `20` section 10 and `19` section 5, with the metrics that decide promotion:

| Agent | On what | How | Metrics (gate) |
|---|---|---|---|
| intake_analyst | C2 briefs with removed fields, user clarification answers | SFT, DPO (useful vs useless questions) | gap recall at least 0.85, question usefulness judge |
| data_analyst | C2 tables with code truth | SFT, GRPO with `DataEnv` | facts exact match at least 0.98, mapping accuracy |
| engagement_manager | C1 storylines and issue trees, accepted plans, plan review edits | SFT, DPO (approved vs edited plans), GRPO (validators, MECE, storyline judge) | validator first-try pass at least 0.80, MECE overlap below 0.05, storyline judge |
| researcher | tool trajectories with verified findings, web snapshot | SFT, GRPO with `ResearchEnv` | verified finding rate at least 0.95, tool calls per finding |
| viz_designer | C1 message-to-exhibit pairs, outcomes | SFT, DPO, CLM priors | chart fit at least 0.90, data validity 1.0 |
| copywriter | C1 titles and commentary, repair pairs | SFT, DPO, GRPO (`19` 5.3 rewards) | action title at least 0.95, supported at least 0.92, typed numbers 0 |
| art_director | C1 imagery and layout descriptions, Tier 3 outcomes | SFT, DPO | look-and-feel pass at least 0.95, visual judge mean |
| fact_checker, reviewer | exact-label synthetic defects (text and visual) | SFT for `df-lm` critiques, Laya and Laya-Vision heads | recall at least 0.90 blockers, precision at least 0.75 |
| repair_specialist | repair trajectories | SFT, GRPO with `RepairEnv` | cleared at least 0.85, new defects at most 0.05 |
| supervisor | synthetic revision requests, user re-requests | SFT, GRPO | route accuracy at least 0.95 |

## 5. Best-of-N and verification

For the slides that matter most (executive summary, decision slide, the top three insight slides), the copywriter and viz_designer generate N=3 variants. The CLM verifier head ranks them, and the top one is used. The UI can show the others as alternatives (`26`, US-6.4).

Training the verifier: pairs of (slide task text, accepted output) vs (same task, rejected output) from traces and C5 repairs, plus corpus titles as positives against model titles that failed judges. Metric: on held-out tasks, the verifier's pick matches the best variant by the full QA cascade at least 80% of the time. Gate: the verifier must beat "always take variant 1" by at least 10 points, otherwise best-of-N is switched off (it costs N times the generation).

## 6. Data strategy summary

| Source | Feeds | Volume target (v1) | Labels |
|---|---|---|---|
| C1 corpus inversion | agents, Laya judges, CLM priors, Laya-Vision positives, `df-vlm` critiques | 20k to 40k slides | corpus as gold |
| C2 synthetic briefs and code data | all agents, data analyst, intake | 5,000 briefs | exact facts |
| C3 open-teacher trajectories | all agents, tools | 3,000 to 5,000 accepted runs | verifiable checks |
| C4 self-improvement | all agents | grows | rewards |
| C5 repair pairs | copywriter, viz, repair, verifier | 10k pairs | QA outcome |
| C6 production feedback (install-local, opt-in) | per customer refinements | per customer | behavioural |
| C7 permissive public datasets | general skills, guard | as licensed | as published |
| S6 counterfactual replays | orchestrator heads | 500 to 2,000 replays per decision | utility |
| V1 synthetic visual defects | Laya-Vision, `df-vlm` | 20k snapshots | exact |

Splits are by group (deck, brief, corpus document) so near-duplicates never cross train and test. Every dataset is registered in `training/DATA_REGISTER.md` with source, licence, version and hash.

## 7. Schedule (cycles)

| Cycle | Starts after | Work | Exit |
|---|---|---|---|
| 0 Bootstrap | P4 | Base Qwen3 (no fine-tune) runs the pipeline. Open teacher generates C3. Corpus inversion produces C1. CLM and Laya run zero-shot in shadow | datasets C1, C2, C3 v1 frozen |
| 1 SFT | P6 | Multitask SFT on 14B, then 32B. Laya heads v1 from synthetic labels. CLM framework and icon heads | golden-brief QA up at least 10 points over base |
| 2 Preferences | Cycle 1 | DPO on 32B. Repair pairs. Best-of-N verifier. Laya-Vision heads from V1 | gates in `19` section 6 |
| 3 RL and orchestrator | Cycle 2 | GRPO for copywriter, engagement_manager, researcher, repair. Counterfactual replays and orchestrator heads | orchestrator metrics (section 3.4) |
| 4 Distil and ship | Cycle 3 | 14B and 8B distillation, quantised exports, laptop tiers | size bars, quantisation bars |
| Monthly | Cycle 4 | `19` section 10 loop | no regression gates |

## 8. Measurement framework

| Level | Metrics | Where measured |
|---|---|---|
| North star | Deck acceptance rate (downloaded with at most 2 slide regenerations), founder blind preference vs previous release and vs corpus-style references | product telemetry (install-local), release review |
| Quality | QA score, blocker rate, Tier 1 to 3 judge pass rates, inspector findings | eval harness, production QA reports |
| Component | agent suite scores, decision accuracy and calibration (ECE), tool benchmark, verifier pick quality | offline suites |
| Efficiency | tokens, GPU seconds, wall time per deck, cache hit rates | telemetry |
| Safety and trust | typed-number rate, unverifiable claim rate, injection quarantine rate, dummy-data disclosure | QA reports |

Statistical rule for "improved": paired bootstrap over the same briefs, 1,000 resamples, improvement counts only if the 95% interval excludes zero and the gain is at least 2 points (or the metric's stated bar).

Experiment tracking: MLflow (self-hosted, Apache-2.0) on the training host records config hash, data hashes, code commit, metrics and artifacts for every training run. Nothing is sent to a SaaS tracker.

## 9. Compute budget (estimate per cycle, to replace with measurements)

| Cycle | GPU-hours on 80 GB GPUs (estimate) | Main consumers |
|---|---|---|
| 0 | 150 to 300 | teacher generation, corpus inversion |
| 1 | 200 to 400 | SFT 14B and 32B |
| 2 | 150 to 300 | DPO, verifier, Laya-Vision |
| 3 | 300 to 600 | GRPO rollouts, counterfactual replays |
| 4 | 100 to 200 | distillation, quantisation, evals |
| Monthly | 100 to 250 | top-up training, evals |

These hours run on vendor GPUs for DeckForge releases. Customer installs run only small local jobs in their night window when enabled (`22`, section 4.2).
