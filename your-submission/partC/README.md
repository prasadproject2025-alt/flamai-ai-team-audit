# Decision Memo: Casualizing Multilingual Assistant Outputs

**TO:** Leadership & Product Team  
**FROM:** AI Engineering Team  
**DATE:** September 2, 2026  
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

- **Reviewer Throughput**:
  - $1\text{ reviewer} \times 10\text{ h/week} = 600\text{ mins/week}$.
  - At $2\text{ mins}$ per side-by-side evaluation: $\frac{600}{2} = \mathbf{300\text{ evaluations/week}}$ (150 Hindi, 150 Kannada; 900 total over 3 weeks).
  - 4 languages have zero internal human evaluation bandwidth.
- **Serving Cost (Path c vs. Path b)**:
  - *Path (c)*: Adding $\sim 180$ system prompt tokens with vLLM's `enable_prefix_caching=True` computes the prefix once. Incremental VRAM = **$0\text{ MB}$**, prefill overhead = **$< 5\text{ ms}$**, generation throughput = **unaffected**.
  - *Path (b)*: A 1B model in FP16 consumes $2.5\text{ GB}$ VRAM, shrinking available KV cache from $12.08\text{ GB}$ to $9.58\text{ GB}$. Concurrency drops from **25 to 20 sequences (-20%)**, and serial execution **doubles end-to-end latency**.
- **Data Volume & Training (Path a Contingency)**:
  - 2,000 response pairs per language $\times 6\text{ languages} = 12,000\text{ pairs}$ ($\sim 4.8\text{M tokens}$).
  - FLM-4B LoRA SFT (rank 16) on 1× A100 trains at $\sim 3,000\text{ tok/s}$:
    $$\text{Training Time} = \frac{4.8\text{M tokens} \times 3\text{ epochs}}{3,000\text{ tok/s}} = 4,800\text{ s} = \mathbf{1.33\text{ hours per run}}$$
  - Compute is plentiful; the true bottleneck is synthetic data quality without external APIs and lack of human reviewers for 4 languages.

---

### 3. Success Metric & Numeric Threshold
$$\mathbf{\ge 75\% \text{ Win Rate in Blind A/B Evaluation for Conversational Casualness with } \le 2\% \text{ Fact/Grammar Regressions}}$$
Evaluated by the native reviewer across a standardized test set of 100 conversational prompts in Hindi and Kannada against current production outputs.

---

### 4. Kill Criterion (Date & Trigger)
- **Deadline**: **Day 4 at 18:00 IST**.
- **Trigger**: If the best prompt variant fails to achieve **$\ge 60\%$ win rate** over baseline in either Hindi or Kannada, OR if the reviewer flags unnatural slang/grammar corruption in **$> 5\%$ of responses**.
- **Pivot**: Kill Path (c) immediately. Dedicate the remaining 10 days of A100 compute to **Path (a) LoRA SFT** using vetted Hindi/Kannada seeds and cross-lingual regularization.

---

### 5. First Experiment (Day 1)
1. **Morning**: Build a test suite of 50 conversational customer queries (greetings, product inquiries, humor, complaints).
2. **Afternoon**: Run FLM-4B inference across 3 prompt architectures:
   - *Variant 1*: Explicit persona instructions on spoken verb endings and informal pronouns.
   - *Variant 2*: 3 few-shot exemplars contrasting formal textbook vs. spoken colloquial responses.
   - *Variant 3*: Hybrid persona + few-shot exemplars + allowable colloquial loanwords.
3. **Evening**: Deliver 100 blind paired outputs (50 Hindi, 50 Kannada) to the reviewer for baseline scoring on Day 2 morning.
