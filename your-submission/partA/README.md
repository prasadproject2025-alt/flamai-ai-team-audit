# Part A — The Tokenizer Audit

The full audit (A1 corpus, A2 script/metric audit, A3 corrected analysis) is in
**[AUDIT_REPORT.md](AUDIT_REPORT.md)**. The ≤1-page recommendation (A4) is in
**[memo.md](memo.md)**.

## Reproduce

```powershell
# Every claim in A2, with per-claim isolation
python scripts/audit_evidence.py                      # all claims -> results/audit_evidence.json
python scripts/audit_evidence.py --flaw lowercase     # isolate one claim
python scripts/audit_evidence.py --flaw nfc           # the harmless element
python scripts/audit_evidence.py --flaw seed          # the second harmless element

# A3: 3 tokenizers x 5 denominators -> results/corrected_metrics.csv
python scripts/benchmark_v1.py

# Rebuild the corpus from source
python scripts/download_corpus.py
```

## Layout

| Path | Contents |
|---|---|
| `AUDIT_REPORT.md` | A1–A3: corpus, evidence-backed audit, corrected cross-language analysis |
| `memo.md` | A4: ≤1-page recommendation memo |
| `corpus/` | 100 parallel FLORES-200 sentences × 5 languages |
| `scripts/` | `download_corpus.py`, `audit_evidence.py`, `benchmark_v1.py` |
| `results/` | `audit_evidence.json`, `benchmark_results.json`, `corrected_metrics.csv` |
