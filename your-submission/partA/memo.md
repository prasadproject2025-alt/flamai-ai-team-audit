# Executive Memo: Tokenizer Economics & Routing Strategy

**TO:** Leadership Team  
**FROM:** AI Team Intern  
**DATE:** September 2, 2026  
**SUBJECT:** Corrected Multilingual Tokenizer Economics and Production Routing Recommendation  

---

### 1. Corrected Headline Numbers

The preliminary findings in `REPORT_v0.md` claiming that Hindi is **5.89×–7.0× more expensive** than English were generated using an English-centric tokenizer (`gpt2`, 50k vocab) on an unrepresentative 10-sentence sample. In that configuration, Indic scripts decompose into 3-byte fallback sequences, causing severe artificial token inflation.

When evaluated on an aligned multilingual parallel corpus (FLORES-200) using an Indic-aware tokenizer (`xlm-roberta-base`, 250k vocab) holding semantic content constant across sentences:

- **Hindi (`hin`)**: **1.28×** tokens vs. English (39.9 vs. 31.2 tok/sentence) — **+28% cost overhead** (not +500%).
- **Kannada (`kan`)**: **1.38×** tokens vs. English (43.1 vs. 31.2 tok/sentence) — **+38% cost overhead** (not +1200%).
- **Tamil (`tam`)**: **1.37×** tokens vs. English (42.8 vs. 31.2 tok/sentence) — **+37% cost overhead** (not +1400%).
- **Telugu (`tel`)**: **1.35×** tokens vs. English (42.3 vs. 31.2 tok/sentence) — **+35% cost overhead** (not +1100%).

---

### 2. Strategic Routing Recommendation

**Do NOT build or route to a separate Indic-specialized serving stack.**

1. **Avoid Architectural Bifurcation**: Partitioning traffic into a separate Indic model introduces dual cold starts, fragmented GPU memory pools, double CI/CD pipelines, and catastrophic routing failure on mixed-language or code-switched queries.
2. **Standardize on Modern Wide-Vocab Models**: The serving overhead for Indic languages on a unified model with an Indic-aware vocabulary is only **28%–38%**, well within typical serving elasticity. We recommend serving all traffic through a unified multilingual model (such as modern Gemma, Llama 3, or Qwen models with 128k–256k vocabs) and budgeting a modest **1.35× blended capacity buffer** for Indic user traffic rather than a 6× multiplier.

---

### 3. The Biggest Caveat: Domain & Script Distribution

Our evaluation used the **FLORES-200** parallel corpus, which consists of formal, professionally translated encyclopedic text written in native Brahmic scripts. 

**Real-world Indian conversational traffic differs significantly:**
- **Code-Switching and Transliteration**: Over 60% of consumer chat in India uses Latin-script transliterations (Hinglish, Tanglish, Kanglish) or blends Hindi and English words in the same sentence. 
- Latin-transliterated Indic text tokenizes very differently from native scripts. While native scripts benefit from wide-vocab subwords, unusual transliterated spellings can fragment into individual Latin letters. 
- Budgeting and capacity planning must not assume all Indic traffic arrives in pure native Devanagari or Dravidian scripts.

---

### 4. Production Monitoring Metric

To validate these findings under real user traffic and catch regressions early, we will monitor:

$$\mathbf{P50 \text{ and } P95 \text{ Generated Tokens per Completed Interaction Turn, Segmented by Detected Request Language}}$$

- **Why this metric**: Tokens per completed turn directly determines per-request GPU compute time, KV-cache residency, and gross inference cost. 
- **Trigger Threshold**: If the ratio $\frac{\text{Tokens}_{P50}(\text{Indic})}{\text{Tokens}_{P50}(\text{English})}$ exceeds **1.50×** in production over a rolling 7-day window, it signals either:
  1. A shift toward high-fragmentation Latin-script transliteration, or
  2. Model verbosity imbalance (the model generating overly verbose conversational filler in Indic responses).
  This counter will immediately trigger vocabulary re-tuning or prompt-compression passes.
