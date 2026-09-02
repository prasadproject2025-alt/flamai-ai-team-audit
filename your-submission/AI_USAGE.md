# AI Usage Disclosure (`AI_USAGE.md`)

**Candidate / Intern:** AI Engineering Intern  
**Assignment:** The Audit (Part A Tokenizer Evaluation)  

---

### Where AI Helped
1. **Corpus Extraction Automation**:
   - AI helped write the Python tar streaming script (`download_corpus.py`) to parse Meta's 25.5MB `flores200_dataset.tar.gz` and extract only the target 5 languages without unzipping the full archive to disk.
2. **Experiment Isolation**:
   - AI structured the `audit_evidence.py` runner to isolate variables one at a time (testing whitespace splitting, lowercasing, and macro vs micro averaging independently).
3. **Typological Reasoning**:
   - AI helped frame the morphological differences between analytic languages (English) and agglutinative languages (Dravidian: Kannada, Tamil, Telugu), clarifying why tokens-per-word is structurally misleading.

---

### Where AI Misled / Initial Mistakes Corrected
1. **Hugging Face Gated Datasets**:
   - AI initially attempted to download the FLORES corpus from `openlanguagedata/flores_plus` via Hugging Face API, assuming it was open. It threw a `401 Unauthorized / GatedRepoError`. We corrected this by tracing the original Meta AI direct tarball link from the FLORES-200 repository.
2. **Windows Terminal Character Encoding**:
   - When printing Hindi tokens in PowerShell, Python threw a `UnicodeEncodeError: 'charmap' codec can't encode characters` because Windows default console encoding was `cp1252`. We corrected this by explicitly reconfiguring `sys.stdout.reconfigure(encoding='utf-8')`.
3. **Potential Hallucination of NFC as a Bug**:
   - A naive AI reading of the assignment might have claimed that `unicodedata.normalize("NFC", line)` was a bug because it changes input bytes. Upon empirical verification, we proved that NFC is actually the *harmless and essential* element mentioned in the assignment prompt, because un-normalized NFD decomposes characters and causes severe subword token fragmentation.
