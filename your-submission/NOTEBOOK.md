# Chronological Lab Notebook: The Audit

**Author:** AI Engineering Intern  
**Project:** Flam AI Intern Assignment — The Audit  
**Status:** Chronological working log (Hypothesis → Experiment → Result → Revision)

---

## Log Entry 01: Initial Setup & Environment Verification
- **Date/Time:** 2026-09-02 22:03 IST
- **Hypothesis:** We can run the existing `starter_kit/fertility.py` script out of the box using Python 3.11.
- **Experiment:** Ran `python starter_kit/fertility.py` with the provided sample corpora.
- **Result (Failure/Dead End):** Failed immediately with `ModuleNotFoundError: No module named 'tiktoken'`.
- **Revision:** Inspected installed environment via `pip list`. `transformers` and `tiktoken` were missing. Installed `tiktoken` (v0.14.0) and `transformers` (v5.16.1) along with dependencies (`regex`, `tokenizers`, `typer`).
- **Retest:** Ran `fertility.py` on `eng_sample.txt` and `hin_sample.txt`. Successfully reproduced the exact baseline numbers from `REPORT_v0.md`:
  - `eng`: fertility 1.27 tok/word, 0.226 tok/char
  - `hin`: fertility 7.45 tok/word, 1.579 tok/char
  - Reported ratio: 5.89× worse for Hindi.

---

## Log Entry 02: Corpus Assembly & Sourcing
- **Date/Time:** 2026-09-02 22:11 IST
- **Hypothesis:** We can query the Hugging Face `openlanguagedata/flores_plus` dataset via `datasets-server` or raw GitHub URLs without authentication.
- **Experiment:** Attempted fetching `openlanguagedata/flores_plus/resolve/main/dev/eng_Latn.jsonl`.
- **Result (Failure/Dead End):** Encountered `401 Client Error: GatedRepoError`. The new `flores_plus` repository requires an authenticated Hugging Face token.
- **Revision:** Traced the official Meta NLLB download link directly from the original FLORES-200 release (`https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz`).
- **Experiment 2:** Streamed the 25.5 MB archive, extracted exactly 100 parallel sentences for:
  - `eng_Latn` (English)
  - `hin_Deva` (Hindi)
  - `kan_Knda` (Kannada - Dravidian)
  - `tam_Taml` (Tamil - Dravidian)
  - `tel_Telu` (Telugu - Dravidian)
- **Result:** Successfully extracted and aligned 100 parallel sentences per language. Saved to `partA/corpus/`.

---

## Log Entry 03: Auditing `fertility.py` (Applying the Evidence Rule)
- **Date/Time:** 2026-09-02 22:15 IST
- **Objective:** Systematically isolate code bugs, conceptual flaws, and harmless elements in `fertility.py`.

### Test 3A: Whitespace Splitting Bug
- **Hypothesis:** `line.split(" ")` creates empty string elements on multiple spaces, artificially inflating word counts and deflating fertility.
- **Experiment:** Inspected sample corpora. Found double spaces in `eng_sample.txt` line 7 (`"books  in"`) and `hin_sample.txt` line 10 (`"किताबें  अलमारी"`). Compared word counts using `split(" ")` vs `split()`.
- **Result:**
  - English words: 79 (naive) vs 78 (clean) -> fertility shifts from 1.265 to 1.283.
  - Hindi words: 62 (naive) vs 61 (clean) -> fertility shifts from 7.448 to 7.598.
- **Takeaway:** Naive splitting silently corrupts the word denominator whenever irregular whitespace exists.

### Test 3B: Lowercasing Bias
- **Hypothesis:** `line = line.lower()` artificially advantages English because English has upper/lowercase casing while Indic scripts have none.
- **Experiment:** Compared GPT-2 tokenization on English and Hindi with vs without `.lower()`.
- **Result:**
  - Hindi tokens: 459 (with `.lower()`) vs 459 (without `.lower()`) -> 0% change.
  - English tokens: 99 (with `.lower()`) vs 96 (without `.lower()`) -> tokens shifted across subword boundaries.
- **Takeaway:** Casing operations mutate the baseline language while being a no-op on the comparison language.

### Test 3C: Macro vs Micro Averaging
- **Hypothesis:** Calculating fertility as `sum(tokens / words) / N` (macro-average) is biased by short sentences.
- **Experiment:** Computed macro vs micro fertility on the sample corpus.
- **Result:** English macro = 1.247 vs micro = 1.231; Hindi macro = 7.598 vs micro = 7.525.
- **Takeaway:** Macro-averaging gives equal weight to uneven sentences. Micro-averaging should be the reported primary metric.

### Test 3D: The "Harmless Element" — NFC Normalization
- **Hypothesis:** `unicodedata.normalize("NFC", line)` was initially flagged by reviewers as suspicious because it mutates input text. We hypothesize that it is actually essential and harmless.
- **Experiment:** Tested tokenization under NFC vs decomposed NFD.
- **Result:** Modern subword tokenizers (like XLM-R) expect precomposed NFC characters. Under NFD, un-normalized decomposed combining characters fragment into stray byte fallback tokens. NFC normalization prevents arbitrary token bloat. It is not a bug; it is necessary hygiene.

---

## Log Entry 04: The Typological Denominator Discovery (A3)
- **Date/Time:** 2026-09-02 22:17 IST
- **Hypothesis:** Dravidian languages (Kannada, Tamil, Telugu) will look catastrophically bad under `tokens / word` not because of tokenization, but because they are agglutinative.
- **Experiment:** Ran `benchmark_v1.py` across all 5 languages on 100 parallel sentences using both `gpt2` and `xlm-roberta-base`.
- **Surprise / Result:**
  - In Kannada, 100 sentences take only **1,720 words** (17.2 words/sent), whereas English takes **2,221 words** (22.2 words/sent). Kannada expresses the same meaning in 22.5% fewer words because case markers and prepositions are bound to the root word!
  - Consequently, Kannada `tokens / word` under `gpt2` was **21.49 tok/word** (17.07× English).
  - But under `tokens / sentence` (holding meaning constant), the ratio was **13.22×**. The word denominator introduced an artificial **29% distortion**!
- **Key Breakthrough:** When switched to `xlm-roberta-base` (which has Indic vocabulary):
  - English: 31.2 tok/sentence
  - Hindi: 39.9 tok/sentence (**1.28×**)
  - Kannada: 43.1 tok/sentence (**1.38×**)
  - Tamil: 42.8 tok/sentence (**1.37×**)
  - Telugu: 42.3 tok/sentence (**1.35×**)
- **Conclusion:** The previous intern's claim that "the script is the root cause and Hindi is 6× more expensive" is completely false. With an appropriate multilingual tokenizer, the true serving overhead for Indic languages is only **28% to 38%**.

---

## Log Entry 05: Denominator Completeness & Testing the Intern's Own Script
- **Date/Time:** 2026-09-02 22:50 IST
- **Experiment 5A:** Re-tested the previous intern's original `fertility.py` on their original 10-line sample with the flag `--tokenizer hf:xlm-roberta-base` (a flag already supported in their code!).
- **Result:**
  - `eng`: 1.28 tok/word
  - `hin`: 1.42 tok/word
  - Output: `hin is 1.10x the fertility of eng (worse tokenization)`
  - Even on the intern's own tiny sample, the script itself disproves the 6× claim when pointed at an Indic-aware tokenizer!
- **Experiment 5B:** Implemented true Unicode extended grapheme cluster counting (`regex \X`) in `benchmark_v1.py` to evaluate the fourth denominator suggested in A3 (per grapheme cluster / akshara).
- **Result:** In Hindi, 100 sentences contain 88.7 grapheme clusters/sent (vs 134.9 codepoints/sent). Under XLM-R, Hindi is 0.45 tok/grapheme vs English 0.23 tok/grapheme (1.92×), showing that grapheme clusters (syllables vs letters) still reflect orthographic rather than semantic density. Tokens per parallel sentence remains the only robust economic cost driver.

---

## Log Entry 06: Part B Capacity Reconciliation & Goodput Derivations
- **Date/Time:** 2026-09-02 23:00 IST
- **Objective:** Reconcile `bench/model_spec.md` with `bench/bench_log.csv` and audit Section 2 of `REPORT_v0.md`.

### B1 Arithmetic Verification
- **Hypothesis:** We can predict the physical concurrency limit of the NVIDIA L4 GPU purely from the model architecture.
- **Formula:** $\text{Bytes/tok} = 2 \times 28 \text{ layers} \times 8 \text{ KV heads} \times 128 \text{ dim} \times 2 \text{ bytes (fp16)} = 114,688 \text{ bytes} = 112.0 \text{ KiB}$.
- **Sequence Memory:** $4096 \text{ tokens} \times 114,688 = 469,762,048 \text{ bytes} = 448.0 \text{ MiB}$.
- **VRAM Budget:** $24 \text{ GB} \times 0.92 - 8.4 \text{ GB (weights)} - 1.6 \text{ GB (overhead)} = 12.08 \text{ GB}$ available for KV cache.
- **Prediction:** $12.08 \times 10^9 / 469,762,048 = 25.72 \text{ concurrent sequences}$.
- **Log Verification:** In `bench_log.csv`, batch 24 runs at `kv_cache_util = 0.93` with 0 preemptions ($24 / 0.93 = 25.81 \text{ capacity}$). At batch 32, exactly 7 sequences are preempted ($32 - 7 = 25$ running). At batch 48, exactly 23 are preempted ($48 - 23 = 25$ running). Hardware concurrency is mathematically capped at 25 sequences!

### B2 & B3 The Throughput Anomaly & The "reported_tok_s" Fallacy
- **Hypothesis:** `REPORT_v0.md` claim that "throughput improves with prompt length" and "batch 48 will deliver ~3200 tok/s" is mathematically impossible.
- **Discovery:** `reported_tok_s` was computed as $(num\_requests \times (prompt\_len + gen\_len)) / wall\_clock\_s$. It lumped prefill prompt tokens into the rate!
- **Evidence:**
  - For long prompts (p=3584, g=512), 87.5% of the tokens are prompt tokens.
  - At batch 16, honest generation goodput is **163.9 tok/s** for long prompts vs **294.5 tok/s** for short prompts. Long prompts actually generate tokens **44% slower**!
  - At batch 24, honest generation goodput is **200.9 tok/s** (derived via Method 1: $12,288 \text{ tokens} / 61.16\text{s}$, and Method 2: decode steady-state rate $24 / 0.09607\text{s} = 249.8 \text{ tok/s}$).
  - At batch 48, the scheduler thrashes, preempting 23 sequences and repeatedly recomputing their 3584 prompt tokens, causing throughput to collapse to 1298.5 tok/s.
- **Remedy:** Set `max_num_seqs = 24`. Capping batch size eliminates all preemptions, executes two clean 24-request batches in $122.3\text{s}$ (saving 29s / 19.2% wall time), and cuts p95 latency.

---

## Log Entry 07: Part C Decision Memo Reasoning & Trade-Off Analysis
- **Date/Time:** 2026-09-02 23:05 IST
- **Objective:** Evaluate three architectural paths (SFT, Rewriter Model, Prompt Engineering) to casualize responses across 6 Indic languages (Hindi, Kannada, Tamil, Telugu, Bengali, Marathi) under severe resource constraints (1x A100 for 2 weeks, 1 reviewer for Hindi/Kannada only @ 10 h/week, 3-week launch, zero external API budget).

### Trade-Off Breakdown & Rejection Rationale
- **Path (b) Rewriter Model — Rejected Immediately**:
  - Main serving hardware is 1x NVIDIA L4 (24GB).
  - A 1B rewriter model requires ~2.5 GB VRAM (FP16 weights + overhead).
  - From Part B, available KV cache is 12.08 GB. Adding the rewriter slashes KV cache to 9.58 GB, reducing 4096-token sequence concurrency from 25 to 20 (-20% capacity).
  - Sequential two-model generation doubles TTFT and generation latency. Unacceptable in production.
- **Path (a) Full SFT — High Risk of Catastrophic Forgetting & Blind Deployment**:
  - Training FLM-4B with LoRA on 12k pairs on the A100 is fast (~1.33 hours per run).
  - However, with no external API budget, synthetic data generation must rely on the un-casualized base model itself.
  - Crucially: **4 out of 6 languages (Tamil, Telugu, Bengali, Marathi) have ZERO human reviewers**. Fine-tuning model weights without human validation risks deploying hallucinated slang or broken syntax to production.
- **Path (c) Prompt Engineering — The Optimal Staged Choice**:
  - Adds ~180 tokens to system prompt.
  - Using vLLM prefix caching (`enable_prefix_caching=True`), the system prompt is computed once and shared. Incremental memory = 0 MB; prefill overhead < 5 ms.
  - Allows human evaluation on Day 1 for Hindi and Kannada.
  - If prompt engineering fails to hit the >= 60% win rate threshold by Day 4 (Kill Criterion), we still have 10 days of A100 time to execute a targeted LoRA SFT on validated Hindi/Kannada seeds.
