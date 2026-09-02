# AI Usage Disclosure (`AI_USAGE.md`)

**Candidate / Intern:** AI Engineering Intern  
**Assignment:** The Audit (Part A Tokenizer Evaluation)  

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
