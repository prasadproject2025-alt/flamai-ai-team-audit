# Executive Memo: Tokenizer Economics & Routing Strategy

**TO:** Leadership Team  
**FROM:** Prasad — AI Team Intern  
**DATE:** September 3, 2026  
**SUBJECT:** Corrected Multilingual Tokenizer Economics and Production Routing Recommendation  

---

### 1. Corrected Headline Numbers

`REPORT_v0.md` reports Hindi at **5.89×–7.0×** English and attributes it to *"a property of the script, not the tokenizer."* **That attribution is the error**, and it is why the recommendation is wrong.

Holding the corpus, the denominator, and the text byte-identical and changing **only the tokenizer** — 100 parallel FLORES-200 sentences, tokens per parallel sentence:

| Language | `gpt2` (50k) | `Qwen2.5-1.5B` (151k) | `xlm-roberta-base` (250k) |
|---|---|---|---|
| Hindi | 7.31× | **4.30×** | 1.28× |
| Kannada | 13.22× | **6.70×** | 1.38× |
| Tamil | 15.07× | **5.91×** | 1.37× |
| Telugu | 12.69× | **6.79×** | 1.35× |

**The multiplier is a property of the vocabulary we deploy, not of the language.** There is no single "Hindi number" — only a number per tokenizer. `bench/model_spec.md` specifies FLM-4B with a **128k vocab**, so the middle column is the planning-relevant one: **≈4×–7×**. Both the report's 6× and the tempting 1.28× headline would mislead.

---

### 2. Strategic Routing Recommendation

**Do not build a separate Indic serving stack. Change the vocabulary instead.**

1. **Bifurcation solves the wrong problem.** Separate Indic routing adds dual cold starts, fragmented GPU memory pools, duplicated CI/CD, and fails on code-switched queries — while leaving token cost per Indic request *completely unchanged*.
2. **Vocabulary selection is the actual lever.** Moving Indic traffic from a general-purpose 151k vocabulary to an Indic-aware one is worth up to a **~5× reduction** in tokens per request (Kannada 6.70× → 1.38×). No routing topology approaches that. This is a model-procurement decision, not an infrastructure one.
3. **Interim capacity planning.** Until our production tokenizer is measured directly, budget **≈5× blended** for Indic traffic on the current 128k-class vocabulary — then re-measure before committing spend:

```powershell
python your-submission/partA/scripts/benchmark_v1.py --tokenizer <production-tokenizer>
```

---

### 3. The Biggest Caveat: Domain & Script Distribution

Our corpus is formal written text in native scripts; production traffic is neither.

- **Code-switching and transliteration**: a large share of Indian consumer chat arrives as Latin-script transliteration (Hinglish, Tanglish, Kanglish) or mixes English and Indic words in one sentence. Transliterated Indic text tokenizes on a completely different path from native script and can fragment into individual Latin letters. **None of the numbers above predict that behaviour.**
- **Sampling**: these are the **first 100** of FLORES-200 dev's 997 sentences. FLORES dev is grouped by source article, so the sample is topically clustered rather than random. Effects this large are unlikely to be sampling artifacts, but the corpus cannot support tight confidence intervals.

---

### 4. Production Monitoring Metric

$$\mathbf{P50\ Total\ Tokens\ per\ Completed\ Turn\ (Prompt + Completion),\ Segmented\ by\ Detected\ Language}$$

- **Input fertility vs. output verbosity**: this analysis measured *input encoding fertility*. Serving cost is driven by *total* turn tokens, so the monitor deliberately spans both — a prompt-token spike signals a shift toward high-fragmentation transliteration; a generated-token spike signals model verbosity drift.
- **Trigger threshold**: alert when the ratio $\frac{\text{Total Tokens}_{P50}(\text{Indic})}{\text{Total Tokens}_{P50}(\text{English})}$ drifts **more than ±25% from the baseline measured on our own production tokenizer** over a rolling 7-day window. The threshold is deliberately *relative*: an absolute trigger is meaningless when the baseline itself ranges from 1.3× to 6.8× depending on the deployed vocabulary.
