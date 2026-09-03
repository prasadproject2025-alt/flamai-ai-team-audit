# Decision Memo: Casualizing Multilingual Assistant Outputs

**TO:** Leadership & Product Team  
**FROM:** Prasad — AI Team Intern  
**DATE:** September 3, 2026  
**SUBJECT:** Architectural Recommendation: Conversational Tone across 6 Indic Languages  

---

### Executive Recommendation
We recommend **Path (c): Prompt Engineering First** with vLLM prefix caching and a strict **Day 4 Kill Criterion** pivoting to **Path (a): Targeted LoRA SFT**. 

Path (b) (Rewriter Model) is disqualified: placing a 1B model on our single 24GB L4 GPU steals 2.5 GB from the KV cache, slashing concurrent capacity from 25 to 20 sequences (-20%) and doubling latency. Full SFT (Path a) carries severe regression risks across the 4 unstaffed languages. Prompt engineering preserves core model reasoning, requires zero serving alterations, and produces immediate evaluation data on Day 1.

---

### 1. Assumptions
1. **Model Capability**: FLM-4B-Instruct contains latent colloquial Indic vocabulary from pre-training; its bookish tone is driven by system prompt and formal instruction conditioning.
2. **Reviewer Asymmetry**: With **one reviewer (Hindi + Kannada only)** at **10 h/week**, we have human quality verification for only 2 of the 6 target languages. Tamil, Telugu, Bengali, and Marathi cannot be human-evaluated before launch.
3. **Infrastructure**: Production remains locked to 1× NVIDIA L4 (24GB); the single A100-80GB is available for only 2 weeks.

---

### 2. Back-of-Envelope Arithmetic

- **Reviewer throughput**: $10\text{ h/wk} = 600\text{ min}$; at 2 min/eval → **300 evals/week** (900 over 3 weeks). **4 of 6 languages have zero human evaluation bandwidth.**
- **Serving cost, (c) vs (b)**: Path (c) adds ~180 system-prompt tokens; with `enable_prefix_caching=True` the prefix is computed once → **0 MB** incremental VRAM, <5 ms prefill, throughput unaffected. Path (b)'s 1B FP16 rewriter costs 2.5 GB, cutting KV cache $12.08 \to 9.58\text{ GB}$ and concurrency **25 → 20 sequences (−20%)**, while serial two-model generation **doubles latency**.
- **Path (a) contingency**: 2,000 pairs × 6 languages = 12,000 pairs ≈ 4.8M tokens. LoRA (r=16) on 1× A100 at ~3,000 tok/s → $\frac{4.8\text{M} \times 3}{3000} = \mathbf{1.33\text{ h/run}}$. **Compute is not the constraint** — synthetic data quality without external APIs, and the 4 unreviewed languages, are.

---

### 3. Success Metric & Numeric Threshold
$$\mathbf{\ge 75\% \text{ Win Rate in Blind A/B Evaluation for Casualness, with } \le 2\% \text{ Fact/Grammar Regressions}}$$
Judged by the native reviewer on **n = 100** prompts per language (Hindi, Kannada) vs. current production output — 200 evaluations, ≈3.3 reviewer-days at 60/day, so it completes before the Day 4 gate.

**Sample-size honesty:** at n = 100, a 75% observed rate carries a 95% CI of ≈**±8.5 points**. 75% observed is *not* statistically separable from 66% true, so this is a decision rule, not a measurement — hence the explicit middle band:

| Win rate (better of hin/kan) | Decision |
|---|---|
| **≥ 75%** | Ship. Freeze prompt; extend to the 4 unreviewed languages under automated checks only. |
| **60–74%** | **One** more iteration, re-tested by **Day 7**. Still < 75% → pivot to Path (a). No third iteration; the A100 window closes. |
| **< 60%** | Kill immediately (§4). |

---

### 4. Kill Criterion (Date & Trigger)
- **Deadline**: **Day 4 at 18:00 IST**.
- **Trigger**: If the best prompt variant fails to achieve **$\ge 60\%$ win rate** over baseline in either Hindi or Kannada, OR if the reviewer flags unnatural slang/grammar corruption in **$> 5\%$ of responses**.
- **Pivot**: Kill Path (c) immediately. Dedicate the remaining 10 days of A100 compute to **Path (a) LoRA SFT** using vetted Hindi/Kannada seeds and cross-lingual regularization.

---

### 5. First Experiment (Day 1)
1. **Morning**: Build a 50-query conversational test suite (greetings, product questions, humour, complaints).
2. **Afternoon**: Run FLM-4B across 3 prompt variants — (1) persona instructions on spoken verb endings and informal pronouns; (2) 3 few-shot exemplars contrasting textbook vs. colloquial; (3) hybrid persona + few-shot + permitted loanwords.
3. **Evening**: Ship the first 100 blind pairs (50 hin, 50 kan) to the reviewer for Day 2 scoring — this establishes the baseline and calibrates the 2 min/eval throughput assumption before we commit to the full n = 200 run.
