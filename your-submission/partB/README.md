# Part B — Capacity Reconciliation: Calculations & Written Answers

This document provides the complete, mathematically derived, and empirically verified answers for **Part B (B1–B4)** of the Flam AI Intern Assignment.

```
Automated Verification Script: python your-submission/partB/scripts/verify_capacity.py
```

---

## B1 (7 pts). Model Spec & Hardware Sizing Arithmetic

### (a) Exact KV-Cache Bytes Per Token
In a Transformer with Grouped-Query Attention (GQA), the KV cache stores Key ($K$) and Value ($V$) activation states for every layer and attention head across each token:

$$\text{Bytes per Token} = 2 \times L \times H_{\text{kv}} \times D_{\text{head}} \times P$$

From `bench/model_spec.md`:
- $2$: Both Key and Value tensors
- $L = 28$: Transformer layers
- $H_{\text{kv}} = 8$: KV heads (Grouped-Query Attention)
- $D_{\text{head}} = 128$: Head dimension
- $P = 2\text{ bytes}$: FP16 precision

$$\text{Bytes per Token} = 2 \times 28 \times 8 \times 128 \times 2 = \mathbf{114,688\text{ bytes}} = \mathbf{112.0\text{ KiB/token}}$$

For a full sequence of length $4096$ tokens:
$$\text{Bytes per 4096-token Sequence} = 4096 \times 114,688 = \mathbf{469,762,048\text{ bytes}} = \mathbf{448.0\text{ MiB}} \approx \mathbf{0.4698\text{ GB}}$$

---

### (b) Approximate Maximum Concurrent 4096-Token Sequences on NVIDIA L4 (24 GB)
From `bench/model_spec.md`:
1. **Total GPU VRAM**: $24.0\text{ GB}$
2. **vLLM Managed Space** (`gpu_memory_utilization = 0.92`): 
   $$24.0\text{ GB} \times 0.92 = 22.08\text{ GB}$$
3. **Model Weights (FP16)**:
   $$\text{Parameters} = 4.2\text{ B} \implies 4.2 \times 2\text{ bytes} = 8.40\text{ GB}$$
4. **Non-KV Runtime Overhead** (activations, CUDA graphs):
   $$\text{Overhead} = 1.60\text{ GB}$$
5. **Net Memory Available for KV Cache**:
   $$\text{KV Cache Budget} = 22.08\text{ GB} - 8.40\text{ GB} - 1.60\text{ GB} = \mathbf{12.08\text{ GB}}$$

Calculating maximum concurrent 4096-token sequences:
$$\text{Max Concurrent Sequences} = \frac{12.08 \times 10^9\text{ bytes}}{469,762,048\text{ bytes}} = \mathbf{25.72\text{ sequences}}$$
*(Or using binary units: $\frac{12.08 \times 1024^3\text{ bytes}}{448 \times 1024^2\text{ bytes}} = \mathbf{27.61\text{ sequences}}$).*

---

### Verification Against `bench_log.csv`
For all runs where sequence length equals $4096$ (`prompt_len = 3584` + `gen_len = 512`):
- **Row 12 (`batch_size = 24`)**:
  `kv_cache_util = 0.93`, `preempted_seqs = 0`.  
  Implied total slot capacity: $\frac{24}{0.93} = \mathbf{25.81\text{ sequences}}$.
- **Row 13 (`batch_size = 32`)**:
  `preempted_seqs = 7`, `kv_cache_util = 0.97`.  
  Active concurrent sequences running: $32 - 7 = \mathbf{25\text{ sequences}}$.
- **Row 14 (`batch_size = 48`)**:
  `preempted_seqs = 23`, `kv_cache_util = 0.97`.  
  Active concurrent sequences running: $48 - 23 = \mathbf{25\text{ sequences}}$.

**Result**: Theory predicts **25.7 sequences**; the benchmark log demonstrates that hardware concurrency is strictly capped at **25 active sequences**.

---

## B2 (6 pts). Long-Context Throughput Anomaly & Preemption Mechanism

### Anomaly Identification
Under the short-context sweep (`prompt_len = 512`), throughput increases monotonically with batch size (from $70.2\text{ tok/s}$ at batch 1 to $2267.3\text{ tok/s}$ at batch 64).

In the long-context sweep (`prompt_len = 3584`, `gen_len = 512`), throughput increases up to batch 24, but collapses beyond it:
- **Batch 24 (Row 12)**: `reported_tok_s = 1607.4`, `wall_clock_s = 61.16s`, `preempted_seqs = 0`, `kv_cache_util = 0.93`, `e2e_ms_p95 = 69221.3ms`.
- **Batch 32 (Row 13)**: `reported_tok_s = 1384.0` (**-13.9% drop**), `wall_clock_s = 94.71s` (**+54.9% wall time**), `preempted_seqs = 7`, `kv_cache_util = 0.97`, `e2e_ms_p95 = 97465.7ms`.
- **Batch 48 (Row 14)**: `reported_tok_s = 1298.5` (**-19.2% drop**), `wall_clock_s = 151.41s` (**+147.6% wall time**), `preempted_seqs = 23`, `kv_cache_util = 0.97`, `e2e_ms_p95 = 105427.5ms`.

### The Mechanism
As proven in B1, the GPU can hold at most **25 concurrent 4096-token sequences**.
1. At batch 32, the required memory is $32 \times 448\text{ MiB} = 14.34\text{ GiB} > 12.08\text{ GB}$. The vLLM scheduler hits its memory watermark (`kv_cache_util = 0.97`) and preempts **7 sequences**.
2. Under vLLM's recompute policy, evicted sequences lose their generated tokens and their KV cache is reclaimed. Once memory frees up, the scheduler must **recompute the entire 3,584-token prompt prefix from scratch**!
3. At batch 48, **23 out of 48 sequences are preempted**. The GPU enters **KV-cache thrashing**, spending the majority of its compute re-prefilling 3,584-token prompts over and over again rather than generating new tokens.

### Proposed Config Change & Predicted Quantitative Effect
- **Config Change**: Set `--max-num-seqs 24` in the vLLM serving configuration to cap active batch concurrency to the physical KV-cache limit.
- **Predicted Quantitative Effect**:
  1. **Zero Preemptions**: `preempted_seqs` drops from **23 to 0** at batch 48.
  2. **19.2% Faster Wall Time**: Requests are executed as two clean consecutive batches of 24. Total wall-clock time will be $2 \times 61.16\text{s} = \mathbf{122.32\text{s}}$ (saving **29.1 seconds** compared to $151.41\text{s}$).
  3. **Throughput Restored**: Throughput stays at **~1607 tok/s** rather than degrading to 1298 tok/s.
  4. **Halved Tail Latency**: The first 24 requests complete at **61.2s** instead of all stalling until 105.4s.

*(Enabling FP8 KV cache with `--kv-cache-dtype fp8` cuts footprint to 56 KiB/token, doubling capacity to 51 concurrent sequences, allowing all 48 sequences to run concurrently with zero preemptions).*

---

## B3 (4 pts). Exposing the `reported_tok_s` Misreading and Honest Goodput

### The Misreading in `REPORT_v0.md`
In Section 2 of `REPORT_v0.md`, the intern wrote:
> *"at batch 16, long prompts hit 1311 tok/s vs only 883 tok/s for short prompts. Longer prompts clearly give better GPU utilization. Recommendation: encourage clients to pack more context per request; throughput improves with prompt length. For capacity planning, assume ~1600 tok/s per L4 (best observed) and scale linearly with batch size, so batch 48 should give us ~3200 tok/s."*

Both conclusions come from misreading the column **`reported_tok_s`**:
- `reported_tok_s` measures:
  $$\text{reported\_tok\_s} = \frac{\text{num\_requests} \times (\text{prompt\_len} + \text{gen\_len})}{\text{wall\_clock\_s}}$$
- In long prompts ($p=3584, g=512$), **87.5% of the tokens are prompt prefill tokens** and only 12.5% are generated output tokens.
- At batch 16:
  - Short prompt ($p=512, g=256$): Honest generation goodput = $\frac{16 \times 256}{13.91\text{s}} = \mathbf{294.5\text{ gen tok/s}}$.
  - Long prompt ($p=3584, g=512$): Honest generation goodput = $\frac{16 \times 512}{49.97\text{s}} = \mathbf{163.9\text{ gen tok/s}}$.
- Generating with long prompts is **44.3% SLOWER** in generation speed than with short prompts because larger KV caches stress memory bandwidth during decode.

---

### Deriving Honest Goodput for Batch 24 Long-Prompt (Row 12)

Values from Row 12: `batch_size = 24`, `prompt_len = 3584`, `gen_len = 512`, `wall_clock_s = 61.16`, `reported_tok_s = 1607.4`, `itl_ms_p50 = 96.07`.

#### Method 1: Total Generation Tokens / Wall-Clock Time
$$\text{Total Generated Tokens} = 24 \times 512 = 12,288\text{ tokens}$$
$$\text{Honest Goodput} = \frac{12,288\text{ tokens}}{61.16\text{ seconds}} = \mathbf{200.92\text{ generated tok/s}}$$
*(Or equivalently: $1607.4 \times \frac{512}{3584 + 512} = 1607.4 \times \frac{1}{8} = \mathbf{200.93\text{ generated tok/s}}$).*

#### Method 2: Derived from Inter-Token Latency (`itl_ms_p50 = 96.07 ms`)
During decode, the GPU generates 1 token per sequence concurrently across all 24 requests:
$$\text{Decode Phase Throughput} = \frac{\text{batch\_size}}{\text{ITL (seconds)}} = \frac{24}{0.09607\text{ s}} = \mathbf{249.82\text{ gen tok/s}}$$

Reconciling prefill and decode:
- Decode phase duration: $512\text{ steps} \times 0.09607\text{ s} = 49.19\text{ seconds}$.
- Prefill phase duration: $61.16\text{s} - 49.19\text{s} = 11.97\text{ seconds}$.
- End-to-end goodput across the entire request lifecycle:
  $$\text{Goodput}_{\text{E2E}} = \frac{12,288\text{ tokens}}{11.97\text{s} + 49.19\text{s}} = \mathbf{200.92\text{ gen tok/s}}$$

---

### What Should `REPORT_v0.md` Have Said?
1. **`reported_tok_s` includes prefill tokens**: Real generation throughput for long prompts is only **~201 tok/s** at batch 24 and **164 tok/s** at batch 16 (44% lower than short prompts). Clients should **minimize prompt prefix length**, not inflate it.
2. **Linear scaling to batch 48 is impossible**: The L4 GPU is physically capped by KV cache at **25 concurrent sequences**. Scaling past batch 24 triggers severe thrashing, causing throughput to collapse to 1298 tok/s with 23 preemptions.

---

## B4 (3 pts). Serving Stack Telemetry to Confirm Preemption Thrashing

To confirm the B2 mechanism in production, pull the Prometheus metric:

$$\mathbf{vllm:num\_preemptions\_total} \quad (\text{and } \mathbf{vllm:gpu\_cache\_usage\_factor})$$

### Expected Behavior & Values:
- **Batch 1 to 24**: `vllm:num_preemptions_total = 0`, `vllm:gpu_cache_usage_factor` scales smoothly from **0.01 to 0.93**.
- **Batch 32**: `vllm:gpu_cache_usage_factor` pegs at **0.97** (preemption watermark); `vllm:num_preemptions_total` shows a sharp jump of **+7** (matching `preempted_seqs = 7`).
- **Batch 48**: `vllm:gpu_cache_usage_factor` remains pinned at **0.97**; `vllm:num_preemptions_total` increments by **+23** (matching `preempted_seqs = 23`). Additionally, `vllm:prompt_tokens_total` rate spikes relative to output tokens, proving that the GPU is burning compute re-prefilling evicted prompts.
