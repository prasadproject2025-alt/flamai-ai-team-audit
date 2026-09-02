# Decision Memo: Casualizing Multilingual Assistant Outputs

**TO:** Leadership & Product Team  
**FROM:** AI Engineering Team  
**DATE:** September 2, 2026  
**SUBJECT:** Architectural Recommendation: Conversational Tone across 6 Indic Languages  

---

### Executive Recommendation

We recommend **Path (c): Prompt Engineering First**, coupled with vLLM prefix caching and a strict **Day 4 Kill Criterion** pivoting to **Path (a): Targeted LoRA SFT**. 

Path (b) (Inference-time Rewriter Model) is rejected immediately: placing a second 1B model on our single 24GB L4 GPU steals 2.5 GB from the KV cache, slashing concurrent capacity from 25 to 20 sequences and doubling latency. Path (a) carries catastrophic forgetting and validation risks across the 4 unstaffed languages. Prompt engineering preserves base model reasoning, requires zero serving stack alterations, and delivers immediate evaluation data on Day 1.

---

### 1. Explicit Assumptions
1. **Base Model Latent Capability**: FLM-4B-Instruct was pre-trained on diverse web text and contains latent colloquial Indic vocabulary; its formal tone is driven by conservative system prompt conditioning and textbook RLHF/SFT data.
2. **Reviewer Staffing Asymmetry**: With only **one reviewer (Hindi + Kannada)** at **10 h/week**, we have human oversight for only 2 of the 6 target languages. Tamil, Telugu, Bengali, and Marathi cannot be human-validated before launch without contractor expansion.
3. **Hardware Constraints**: The single A100-80GB is available for only 2 weeks; production serving remains locked to 1× NVIDIA L4 (24GB).

---

### 2. Back-of-Envelope Arithmetic

#### (a) Reviewer Throughput
- $1\text{ reviewer} \times 10\text{ hours/week} = 600\text{ minutes/week}$.
- At $2\text{ minutes}$ to read prompt, evaluate tone, and check correctness:
  $$\text{Capacity} = \frac{600\text{ mins}}{2\text{ mins/eval}} = \mathbf{300\text{ evaluations/week}} \quad (150\text{ Hindi}, 150\text{ Kannada})$$
- Over the 3-week timeline, total evaluation budget is **900 reviews**.

#### (b) Serving Cost & Latency (Path c vs. Path b)
- **Path (c) Prompt Engineering**: Adding a conversational persona + 2 few-shot exemplars adds $\sim 180\text{ tokens}$ to the system prompt.
  - With vLLM's `enable_prefix_caching=True`, the 180-token prefix is computed **once** and shared in KV cache across all requests.
  - Incremental GPU memory = **$0\text{ MB}$** per active request; incremental prefill latency = **$< 5\text{ ms}$**; generation throughput = **unaffected**.
- **Path (b) Rewriter Model (Why it fails)**:
  - A $\le 1\text{B}$ model in FP16 requires $2.0\text{ GB (weights)} + 0.5\text{ GB (overhead)} = 2.5\text{ GB}$.
  - On our 24GB L4 GPU, available KV-cache drops from $12.08\text{ GB}$ to $9.58\text{ GB}$, slashing maximum 4096-token concurrency from **25 to 20 sequences (-20% capacity)**.
  - Pipeline latency: Sequential two-model generation **doubles TTFT and end-to-end latency**.

#### (c) Data Volume & Training Cost (Path a Contingency)
- Target: 2,000 synthetic casual response pairs per language ($2,000 \times 6 = 12,000\text{ pairs}$; $\sim 4.8\text{M tokens}$).
- On 1× A100-80GB, LoRA fine-tuning (rank 16, FP16) for FLM-4B processes $\sim 3,000\text{ tok/s}$.
  $$\text{Training Time} = \frac{4.8\text{M tokens} \times 3\text{ epochs}}{3,000\text{ tok/s}} = 4,800\text{ seconds} = \mathbf{1.33\text{ hours per run}}$$
- Compute is plentiful ($\sim 1.3\text{ h}$ vs. $336\text{ h}$ available); the hard bottleneck is synthetic generation quality without external APIs and verification of 4 unstaffed languages.

---

### 3. Success Metric & Numeric Threshold

$$\mathbf{\ge 75\% \text{ Win Rate in Blind A/B Evaluation for Conversational Casualness, with } \le 2\% \text{ Fact/Grammar Regressions}}$$

- **Measurement**: Blind side-by-side comparison on a standardized test set of 100 conversational prompts evaluated by our native reviewer across Hindi and Kannada against current production outputs.

---

### 4. Kill Criterion (Date & Trigger)

**Deadline: Day 4 (Friday, Week 1) at 18:00 IST.**
- **Trigger**: If the native reviewer scores the best-performing prompt variant at **$< 60\%$ win rate** over baseline in Hindi or Kannada, OR if the model displays "slang hallucination" / severe grammatical corruption in **$> 5\%$ of outputs**.
- **Execution**: Abandon Path (c) immediately. Pivot 100% of remaining A100 time (10 days) to **Path (a) LoRA SFT**, fine-tuning solely a low-rank adapter (rank 16) on verified Hindi/Kannada seeds with cross-lingual regularization to prevent catastrophic forgetting.

---

### 5. First Experiment to Run on Day 1

1. **Test Set Assembly (Morning)**: Create 50 representative customer touchpoint queries (greetings, product questions, advice, complaints).
2. **Prompt Variant Generation (Afternoon)**: Run inference across FLM-4B on 3 prompt architectures:
   - *Variant 1 (Descriptive Persona)*: Explicit instructions on spoken tone, informal verb endings, and conversational pronouns.
   - *Variant 2 (Few-Shot Exemplars)*: 3 conversational few-shot pairs contrasting formal textbook responses with natural spoken responses.
   - *Variant 3 (Hybrid + Dialect Guidance)*: Persona instructions + few-shot pairs + allowed colloquial loanwords.
3. **Reviewer Batch Delivery (Evening)**: Hand off 100 blind paired responses (50 Hindi, 50 Kannada) to the reviewer for baseline scoring on Day 2 morning.
