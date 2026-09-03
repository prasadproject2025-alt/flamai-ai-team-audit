# Part B — Capacity Reconciliation

The full calculations and written answers for B1–B4 are in
**[CAPACITY_REPORT.md](CAPACITY_REPORT.md)**.

## Reproduce

```powershell
python scripts/verify_capacity.py
```

Reproduces every figure in B1–B4 from `bench/model_spec.md` and `bench/bench_log.csv`:
KV-cache bytes per token, the concurrency ceiling and its three independent
confirmations in the log, the preemption mechanism behind the long-context anomaly, and
both independent derivations of honest goodput.
