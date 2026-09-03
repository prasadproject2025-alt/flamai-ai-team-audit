# AI Usage Disclosure (`AI_USAGE.md`)

**Candidate:** Prasad  
**Assignment:** The Audit  

---

### Where AI Helped
1. **Corpus Extraction Automation (Part A)**:
   - AI helped write the Python tar streaming script (`download_corpus.py`) to parse Meta's 25.5MB `flores200_dataset.tar.gz` and extract only the target 5 languages without unzipping the full archive to disk.
2. **Experiment Isolation (Part A)**:
   - AI structured the `audit_evidence.py` runner to isolate variables one at a time (testing whitespace splitting, lowercasing, and macro vs micro averaging independently).
3. **Typological Reasoning (Part A)**:
   - AI helped frame the morphological differences between analytic languages (English) and agglutinative languages (Dravidian: Kannada, Tamil, Telugu), clarifying why tokens-per-word is structurally misleading.
4. **Memory Footprint Arithmetic (Part B)**:
   - AI helped cross-check the GQA KV-cache memory formula ($2 \times L \times H_{\text{kv}} \times D_{\text{head}} \times 2$) and structure `verify_capacity.py` to compare decimal GB vs binary GiB bounds.
5. **Constraint Modeling & Reviewer Arithmetic (Part C)**:
   - AI helped calculate the weekly human evaluation capacity (300 pairs/week) and prefix caching memory overhead ($0\text{ MB}$ incremental with vLLM shared blocks).

---

### Where AI Misled / Initial Mistakes Corrected
1. **Hugging Face Gated Datasets**:
   - AI initially attempted to download the FLORES corpus from `openlanguagedata/flores_plus` via Hugging Face API, assuming it was open. It threw a `401 Unauthorized / GatedRepoError`. We corrected this by tracing the original Meta AI direct tarball link from the FLORES-200 repository.
2. **Windows Terminal Character Encoding**:
   - When printing Hindi tokens in PowerShell, Python threw a `UnicodeEncodeError: 'charmap' codec can't encode characters` because Windows default console encoding was `cp1252`. We corrected this by explicitly reconfiguring `sys.stdout.reconfigure(encoding='utf-8')`.
3. **Potential Hallucination of NFC as a Bug**:
   - A naive AI reading of the assignment might have claimed that `unicodedata.normalize("NFC", line)` was a bug because it changes input bytes. Upon empirical verification, we proved that NFC is actually the *harmless and essential* element mentioned in the assignment prompt, because un-normalized NFD decomposes characters and causes severe subword token fragmentation.
4. **Initial Trust in Throughput Column Labels (Part B)**:
   - Standard LLM assistants often take columns like `reported_tok_s` at face value as generation throughput and attempt to fit scaling curves. We audited the harness arithmetic and verified that `reported_tok_s` includes prefill prompt tokens, which are 87.5% of long-context tokens. Recognizing this allowed us to expose the intern's false conclusion that long prompts increase GPU efficiency.
5. **Reflexive Bias Toward Fine-Tuning (Part C)**:
   - Unconstrained AI prompts frequently jump to "train an SFT model" whenever an A100 GPU is mentioned. We caught that doing an unvalidated SFT pass across Tamil, Telugu, Bengali, and Marathi without a single native speaker to verify outputs poses severe production risk. Grounding the decision in human reviewer throughput and serving VRAM constraints led to our staged recommendation.

---

### Where AI Misled Me And I Did Not Catch It Until A Late Self-Audit

These three are the entries I would most want a reviewer to read, because they are the ones
that survived into a "finished" draft. All are documented in full in `NOTEBOOK.md` Log Entry 09.

6. **A null result written up as a positive one (most serious).**
   AI-assisted drafting produced a confident mechanism narrative for the NFC finding —
   "NFD text fragments into stray byte-fallback tokens, inflating counts" — while the
   experiment backing it had measured **0.00%** and that zero was sitting in my own
   committed `results/audit_evidence.json`. Neither the model nor I noticed the
   contradiction, because the prose was plausible and I had already decided what the
   answer was. The root cause turned out to be interesting (no decomposable Devanagari
   code points occur in this corpus, so `NFD(text)==text`), but I only found it by
   re-running the experiment instead of re-reading the sentence. **Lesson: a generated
   explanation is not evidence, and a plausible mechanism paired with a null measurement
   is worse than no claim at all.**

7. **A distortion described in the wrong direction.**
   The lowercasing finding was written as "lowers English token counts, exaggerating the
   disparity." The measurements say the opposite: English tokens go 96 → 99 and the ratio
   falls from 6.09× to 5.92×. The write-up also contained a "5.6%" figure that appears
   nowhere in any output. Fixed by making every description in `audit_evidence.py` a
   computed f-string, so the prose is now generated from the data rather than written
   alongside it.

8. **A headline that depended on an unrepresentative choice.**
   Both the model and I settled on `xlm-roberta-base` as "the Indic-aware tokenizer" and
   built the 1.28×/1.35× headline on it, without asking whether it resembles anything we
   would actually serve. It does not — it is encoder-only, and `bench/model_spec.md`
   specifies a 128k-vocab generative model. Testing `Qwen2.5-1.5B` gave 4.30×–6.79×.
   The conclusion changed as a result. **Lesson: AI is good at optimising the answer to
   the question asked, and will not volunteer that the question was framed too narrowly.**

### What I Understand Versus What Was Generated

- **I can re-derive unaided:** all Part B arithmetic (KV bytes/token, the 25-sequence
  ceiling and its three log confirmations, both goodput derivations), the denominator
  argument in A3, and the shared-numerator refutation.
- **AI wrote most of the plumbing:** the tar-streaming download script, argparse wiring,
  CSV/JSON serialisation, and markdown table formatting.
- **AI got wrong and I had to correct:** the three items above, the "UTF-16 code units"
  terminology (Python 3 `len()` returns code points), and an over-strong claim that
  "Devanagari has no canonical decompositions" (it has 11; they simply do not occur in
  this corpus).
