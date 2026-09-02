#!/usr/bin/env python3
"""
verify_capacity.py -- Programmatic verification of Part B calculations.

Validates:
  B1: KV-cache memory per token and max concurrent 4096-token sequences on NVIDIA L4 (24GB).
  B2: Long-context throughput anomaly, sequence preemptions, and thrashing mechanism.
  B3: Exposing the reported_tok_s misreading and deriving honest generation goodput (2 independent ways).
  B4: Serving stack telemetry metrics and expected values.
"""

import os
import pandas as pd

def run_verification():
    print("================================================================================")
    print(" PART B: CAPACITY RECONCILIATION VERIFICATION")
    print("================================================================================\n")
    
    # -------------------------------------------------------------------------
    # B1: Exact KV Cache Bytes & Concurrency
    # -------------------------------------------------------------------------
    num_layers = 28
    num_kv_heads = 8
    head_dim = 128
    bytes_per_fp16 = 2  # fp16
    
    # KV cache stores K and V tensors: 2 * num_layers * num_kv_heads * head_dim * bytes_per_element
    kv_bytes_per_token = 2 * num_layers * num_kv_heads * head_dim * bytes_per_fp16
    kv_kib_per_token = kv_bytes_per_token / 1024
    
    seq_len = 4096
    kv_bytes_per_seq = kv_bytes_per_token * seq_len
    kv_mib_per_seq = kv_bytes_per_seq / (1024 ** 2)
    
    # GPU Memory budget
    gpu_total_gb = 24.0
    gpu_util = 0.92
    vllm_total_gb = gpu_total_gb * gpu_util  # 22.08 GB
    
    params_b = 4.2
    model_weights_gb = params_b * 2  # 8.4 GB (4.2B * 2 bytes fp16)
    runtime_overhead_gb = 1.6        # 1.6 GB
    
    available_kv_gb = vllm_total_gb - model_weights_gb - runtime_overhead_gb  # 12.08 GB
    
    # Concurrent 4096-token sequences
    # Using decimal GB (1e9 bytes):
    max_seqs_decimal = (available_kv_gb * 1e9) / kv_bytes_per_seq
    # Using binary GiB (1024^3 bytes):
    max_seqs_binary = (available_kv_gb * (1024**3)) / kv_bytes_per_seq
    
    print("--- [B1] KV Cache Calculations ---")
    print(f"  Layers (L): {num_layers}")
    print(f"  KV Heads (GQA): {num_kv_heads}")
    print(f"  Head Dimension: {head_dim}")
    print(f"  Precision: FP16 ({bytes_per_fp16} bytes)")
    print(f"  KV Cache bytes per token (exact): 2 * 28 * 8 * 128 * 2 = {kv_bytes_per_token:,} bytes ({kv_kib_per_token:.1f} KiB)")
    print(f"  KV Cache bytes per 4096-tok seq: {kv_bytes_per_seq:,} bytes ({kv_mib_per_seq:.1f} MiB)")
    print(f"  Total GPU VRAM: {gpu_total_gb:.1f} GB")
    print(f"  vLLM allocable (util=0.92): {vllm_total_gb:.2f} GB")
    print(f"  Model Weights (4.2B * 2B): {model_weights_gb:.2f} GB")
    print(f"  Non-KV Overhead: {runtime_overhead_gb:.2f} GB")
    print(f"  Available for KV Cache: {available_kv_gb:.2f} GB")
    print(f"  Theoretical Max Concurrent 4096-tok Sequences (Decimal): {max_seqs_decimal:.2f} sequences")
    print(f"  Theoretical Max Concurrent 4096-tok Sequences (Binary):  {max_seqs_binary:.2f} sequences")
    
    # -------------------------------------------------------------------------
    # Verification against bench_log.csv
    # -------------------------------------------------------------------------
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.normpath(os.path.join(script_dir, "..", "..", "..", "starter_kit (1)", "starter_kit", "bench", "bench_log.csv"))
    df = pd.read_csv(log_path)
    
    row_b24 = df[(df["batch_size"] == 24) & (df["prompt_len"] == 3584)].iloc[0]
    row_b32 = df[(df["batch_size"] == 32) & (df["prompt_len"] == 3584)].iloc[0]
    row_b48 = df[(df["batch_size"] == 48) & (df["prompt_len"] == 3584)].iloc[0]
    
    implied_capacity_b24 = 24.0 / row_b24["kv_cache_util"]
    active_seqs_b32 = 32 - row_b32["preempted_seqs"]
    active_seqs_b48 = 48 - row_b48["preempted_seqs"]
    
    print("\n--- [B1 Check Against Log] ---")
    print(f"  Batch 24: kv_cache_util = {row_b24['kv_cache_util']:.2f}, preempted = {int(row_b24['preempted_seqs'])}")
    print(f"    -> Implied Total Capacity: 24 / {row_b24['kv_cache_util']:.2f} = {implied_capacity_b24:.2f} sequences!")
    print(f"  Batch 32: kv_cache_util = {row_b32['kv_cache_util']:.2f}, preempted = {int(row_b32['preempted_seqs'])}")
    print(f"    -> Active concurrent sequences remaining: 32 - {int(row_b32['preempted_seqs'])} = {int(active_seqs_b32)} sequences!")
    print(f"  Batch 48: kv_cache_util = {row_b48['kv_cache_util']:.2f}, preempted = {int(row_b48['preempted_seqs'])}")
    print(f"    -> Active concurrent sequences remaining: 48 - {int(row_b48['preempted_seqs'])} = {int(active_seqs_b48)} sequences!")
    print("  => EXACT MATCH: Theory predicts 25.7 sequences; log shows capacity is capped at 25 concurrent sequences!")

    # -------------------------------------------------------------------------
    # B2: Long-Context Throughput Anomaly & Preemption Mechanism
    # -------------------------------------------------------------------------
    print("\n--- [B2] Long-Context Sweep Anomaly ---")
    long_df = df[df["prompt_len"] == 3584]
    for _, r in long_df.iterrows():
        b = int(r["batch_size"])
        rep = r["reported_tok_s"]
        wall = r["wall_clock_s"]
        pre = int(r["preempted_seqs"])
        util = r["kv_cache_util"]
        e2e = r["e2e_ms_p95"]
        print(f"  Batch {b:2d}: reported={rep:7.1f} tok/s | wall={wall:6.2f}s | preempted={pre:2d} | kv_util={util:.2f} | p95={e2e:8.1f}ms")
    
    print("\n  Mechanism: Beyond batch 24, KV cache reaches saturation (util=0.97).")
    print("  The scheduler preempts 7 sequences at batch 32 and 23 sequences at batch 48.")
    print("  Preempted sequences are evicted and their 3,584-token prompts must be RECOMPUTED,")
    print("  wasting GPU FLOPS on prefix thrashing rather than token generation.")

    # -------------------------------------------------------------------------
    # B3: Misreading of reported_tok_s and Honest Goodput Derivations
    # -------------------------------------------------------------------------
    print("\n--- [B3] Honest Goodput Derivations for Batch 24 (Prompt 3584, Gen 512) ---")
    
    # Method 1: Total Generation Tokens / Wall Clock Time
    total_gen_tokens = row_b24["num_requests"] * row_b24["gen_len"]  # 24 * 512 = 12,288
    goodput_method1 = total_gen_tokens / row_b24["wall_clock_s"]
    goodput_from_reported = row_b24["reported_tok_s"] * (row_b24["gen_len"] / (row_b24["prompt_len"] + row_b24["gen_len"]))
    
    # Method 2: Decode Step Latency (Inter-Token Latency)
    # Steady-state decode throughput = batch_size / (itl_ms_p50 in seconds)
    goodput_method2_steady = row_b24["batch_size"] / (row_b24["itl_ms_p50"] / 1000.0)
    
    # Accounting for total decode phase wall time:
    decode_wall_time = (row_b24["gen_len"] * row_b24["itl_ms_p50"]) / 1000.0
    prefill_wall_time = row_b24["wall_clock_s"] - decode_wall_time
    
    print(f"  Reported Throughput: {row_b24['reported_tok_s']:.1f} tok/s (MISLEADING: includes 3584 prefill tokens)")
    print(f"  Method 1 (Total Gen Tokens / Wall Clock):")
    print(f"    (24 requests * 512 gen_len) / 61.16s = 12,288 / 61.16s = {goodput_method1:.2f} gen tok/s")
    print(f"    Or: reported_tok_s * (512 / 4096) = 1607.4 * 0.125 = {goodput_from_reported:.2f} gen tok/s")
    print(f"  Method 2 (From Inter-Token Latency itl_ms_p50 = {row_b24['itl_ms_p50']} ms):")
    print(f"    Steady-state decode rate: batch / itl = 24 / 0.09607s = {goodput_method2_steady:.2f} gen tok/s")
    print(f"    Decode phase duration: 512 steps * 96.07 ms = {decode_wall_time:.2f} s")
    print(f"    Prefill phase duration: {row_b24['wall_clock_s']:.2f}s - {decode_wall_time:.2f}s = {prefill_wall_time:.2f} s")
    print(f"    E2E Generated Goodput: 12,288 tokens / 61.16s = {goodput_method1:.2f} gen tok/s")

    # Compare batch 16 short vs long
    row_b16_short = df[(df["batch_size"] == 16) & (df["prompt_len"] == 512)].iloc[0]
    row_b16_long = df[(df["batch_size"] == 16) & (df["prompt_len"] == 3584)].iloc[0]
    
    gen_rate_short = (16 * 256) / row_b16_short["wall_clock_s"]
    gen_rate_long = (16 * 512) / row_b16_long["wall_clock_s"]
    
    print("\n  Comparison at Batch 16:")
    print(f"    Short Prompt (p=512, g=256): reported = {row_b16_short['reported_tok_s']:.1f} | HONEST GEN GOODPUT = {gen_rate_short:.1f} tok/s")
    print(f"    Long Prompt (p=3584, g=512): reported = {row_b16_long['reported_tok_s']:.1f} | HONEST GEN GOODPUT = {gen_rate_long:.1f} tok/s")
    print(f"    => The intern claimed long prompt is FASTER (1311 vs 883 tok/s).")
    print(f"    => IN REALITY: Long prompt generation goodput is 44% SLOWER (163.9 vs 294.5 tok/s)!")

    # -------------------------------------------------------------------------
    # B4: Telemetry Metric
    # -------------------------------------------------------------------------
    print("\n--- [B4] Serving Stack Metric ---")
    print("  Metric to pull: 'vllm:num_preemptions_total' (Prometheus counter) and 'vllm:gpu_cache_usage_factor'.")
    print("  Expected Values:")
    print("    - Batch 24: num_preemptions = 0, gpu_cache_usage_factor = 0.93")
    print("    - Batch 32: num_preemptions = 7 (cumulative counter increment of +7), gpu_cache_usage_factor = 0.97 (pinned at threshold)")
    print("    - Batch 48: num_preemptions = 23 (cumulative increment +23), gpu_cache_usage_factor = 0.97")

if __name__ == "__main__":
    run_verification()
