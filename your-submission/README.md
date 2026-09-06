# AI Team Intern Assignment — The Audit

**Author:** Durga Prasad S  
**Repository:** [flamai-ai-team-audit](https://github.com/prasadproject2025-alt/flamai-ai-team-audit)

Every number in this submission is produced by a script in `partA/scripts/` or
`partB/scripts/` and can be re-derived from a clean checkout. Claims that did not survive
re-measurement are recorded as revisions in `NOTEBOOK.md` Log Entry 09 rather than quietly
removed.

---

## Headline Finding

`REPORT_v0.md` concludes Hindi costs ~6× English and attributes it to *"a property of the
script, not the tokenizer."* Holding the corpus, the denominator, and the text
byte-identical and changing **only the tokenizer**:

| Language | `gpt2` (50k) | `Qwen2.5-1.5B` (151k) | `xlm-roberta-base` (250k) |
|---|---|---|---|
| Hindi | 7.31× | 4.30× | 1.28× |
| Kannada | 13.22× | 6.70× | 1.38× |

The cost multiplier is a property of **the deployed vocabulary**, not of the language.
The one variable the report declared irrelevant is the only one that moves the number.

---

## Deliverables

```
your-submission/
├── NOTEBOOK.md        # chronological log; Entry 09 records three claims that failed re-measurement
├── AI_USAGE.md        # where AI helped, where it misled me, and what I can re-derive unaided
│
├── partA/             # The Tokenizer Audit (50 pts)
│   ├── AUDIT_REPORT.md    # A1 corpus + caveats, A2 evidence-backed audit, A3 corrected analysis
│   ├── memo.md            # A4 recommendation memo (≤ 1 page)
│   ├── corpus/            # 100 parallel FLORES-200 sentences × 5 languages
│   ├── scripts/           # download_corpus.py, audit_evidence.py, benchmark_v1.py
│   └── results/           # audit_evidence.json, benchmark_results.json, corrected_metrics.csv
│
├── partB/             # Capacity Reconciliation (20 pts)
│   ├── CAPACITY_REPORT.md # B1–B4 calculations and written answers
│   └── scripts/verify_capacity.py
│
└── partC/memo.md      # Decision Memo (15 pts)
```

## Reproduce Everything

```powershell
# A2 — all eight claims, each independently isolatable
python your-submission/partA/scripts/audit_evidence.py
python your-submission/partA/scripts/audit_evidence.py --flaw lowercase
python your-submission/partA/scripts/audit_evidence.py --flaw nfc

# A3 — 3 tokenizers × 5 denominators
python your-submission/partA/scripts/benchmark_v1.py

# B1–B4 — all capacity and goodput arithmetic
python your-submission/partB/scripts/verify_capacity.py
```

**Live demo of the headline finding** — one Kannada phrase, three tokenizers:

```powershell
python your-submission/partA/scripts/benchmark_v1.py --text "ಬೆಂಗಳೂರಿನಲ್ಲಿ ಇಂದು ಮಳೆ"
# gpt2: 62 tokens | xlm-roberta-base: 3 tokens | Qwen2.5-1.5B: 34 tokens
```

## Claims Audited

| # | Claim | Verdict |
|---|---|---|
| 1 | `line.split(" ")` invents ghost words | Real bug — deflates fertility |
| 2 | `line.lower()` is applied to one side only | Real bug — **shrinks** the gap 6.09× → 5.92× |
| 3 | Macro-averaging instead of micro | Real statistical flaw |
| 4 | Tokens-per-word vs agglutinative morphology | Real conceptual flaw — +29.1% artificial penalty |
| 5 | Tokens-per-code-point as a denominator | Real conceptual flaw — 2.56× overstatement |
| 6 | "The two metrics agree, so it's robust" | Real logical flaw — shared numerator |
| 7 | `unicodedata.normalize("NFC", …)` | **Harmless and necessary** — +4.52% inflation without it |
| 8 | `random.seed(1337)` | **Harmless** — 0 RNG consumers, provably inert |
