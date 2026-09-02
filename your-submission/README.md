# AI Team Intern Assignment — The Audit

**Author:** AI Engineering Intern  
**Repository:** [flamai-ai-team-audit](https://github.com/prasadproject2025-alt/flamai-ai-team-audit)  
**Submission Status:** All parts (A, B, C) complete, empirically verified under the Evidence Rule, and defense-ready.

---

## Repository Index & Deliverables

```
your-submission/
├── NOTEBOOK.md               # Graded chronological lab notebook (Log entries 01 to 07)
├── AI_USAGE.md               # Honest disclosure of AI assistance and error corrections
│
├── partA/                    # Part A: The Tokenizer Audit (50 pts)
│   ├── README.md             # Full rendered audit report (A1, A2, A3)
│   ├── AUDIT_REPORT.md       # Technical audit report with isolated evidence
│   ├── memo.md               # Executive recommendation memo (≤ 1 page) (A4)
│   ├── corpus/               # 100 parallel sentences (eng, hin, kan, tam, tel)
│   ├── scripts/
│   │   ├── download_corpus.py# Automated FLORES-200 parallel extraction script
│   │   ├── audit_evidence.py # Isolated before/after experiments for fertility.py
│   │   └── benchmark_v1.py   # Multi-tokenizer, multi-denominator benchmarking harness
│   └── results/
│       ├── audit_evidence.json    # Measured numerical evidence
│       ├── benchmark_results.json # Full benchmark statistics
│       └── corrected_metrics.csv  # Final comparison matrix
│
├── partB/                    # Part B: Capacity Reconciliation (20 pts)
│   ├── README.md             # Rendered calculations and written answers (B1, B2, B3, B4)
│   ├── CAPACITY_REPORT.md    # Technical report with goodput derivations and log checks
│   └── scripts/
│       └── verify_capacity.py# Automated script reproducing all B1–B4 arithmetic
│
└── partC/                    # Part C: Strategic Decision Memo (15 pts)
    ├── README.md             # Rendered decision memo
    └── memo.md               # Decision memo (≤ 1 page) with explicitly labelled sections
```

---

## Quick Replication & Defense Commands

All scripts run synchronously out-of-the-box:

```powershell
# Part A: Run script audit experiments (The Evidence Rule)
python your-submission/partA/scripts/audit_evidence.py

# Part A: Run full 5-language benchmark across all 4 denominators
python your-submission/partA/scripts/benchmark_v1.py

# Part A (Live Defense): Test any custom text input on screen
python your-submission/partA/scripts/benchmark_v1.py --text "बेंगलुरु में आज हल्की बारिश हो रही है।"

# Part B: Run capacity and goodput arithmetic verification
python your-submission/partB/scripts/verify_capacity.py
```
