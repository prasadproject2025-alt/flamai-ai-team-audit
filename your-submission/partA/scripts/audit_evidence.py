#!/usr/bin/env python3
"""
audit_evidence.py -- Isolated experiments proving bugs, conceptual flaws,
and harmless elements in fertility.py under the Flam AI Evidence Rule.

For each claim:
  - Isolate the single variable.
  - Run the exact before/after comparison.
  - Measure direction and magnitude of the distortion.
  - Output structured JSON and Markdown table.
"""

import os
import sys
import json
import unicodedata
import tiktoken

def load_lines(path):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line:
                lines.append(line)
    return lines

def run_audit(sample_dir, flores_dir):
    enc = tiktoken.get_encoding("gpt2")
    
    eng_sample_path = os.path.join(sample_dir, "eng_sample.txt")
    hin_sample_path = os.path.join(sample_dir, "hin_sample.txt")
    eng_sample = load_lines(eng_sample_path)
    hin_sample = load_lines(hin_sample_path)
    
    results = {}
    
    # -------------------------------------------------------------
    # Experiment 1: line.split(" ") vs line.split() (Whitespace Bug)
    # -------------------------------------------------------------
    # eng_sample line 7: "Please keep the books  in the cupboard."
    # hin_sample line 10: "किताबें  अलमारी में रखी हैं।"
    def count_words(lines, naive=True):
        words_per_line = []
        for line in lines:
            if naive:
                w = [x for x in line.lower().split(" ")]
            else:
                w = line.lower().split()
            words_per_line.append(len(w))
        return words_per_line

    eng_w_naive = count_words(eng_sample, naive=True)
    eng_w_clean = count_words(eng_sample, naive=False)
    hin_w_naive = count_words(hin_sample, naive=True)
    hin_w_clean = count_words(hin_sample, naive=False)
    
    # Measure fertility impact
    def calc_fertility_split(lines, naive=True):
        ferts = []
        for line in lines:
            toks = enc.encode(line.lower())
            w = line.lower().split(" ") if naive else line.lower().split()
            ferts.append(len(toks) / len(w))
        return sum(ferts) / len(ferts)

    results["flaw1_whitespace_split"] = {
        "description": "line.split(' ') counts double spaces as empty words, inflating word count and artificially deflating fertility.",
        "eng_words_naive": sum(eng_w_naive),
        "eng_words_clean": sum(eng_w_clean),
        "hin_words_naive": sum(hin_w_naive),
        "hin_words_clean": sum(hin_w_clean),
        "eng_fertility_before_split_naive": calc_fertility_split(eng_sample, naive=True),
        "eng_fertility_after_split_clean": calc_fertility_split(eng_sample, naive=False),
        "hin_fertility_before_split_naive": calc_fertility_split(hin_sample, naive=True),
        "hin_fertility_after_split_clean": calc_fertility_split(hin_sample, naive=False),
    }

    # -------------------------------------------------------------
    # Experiment 2: line.lower() distortion on English vs Indic
    # -------------------------------------------------------------
    def calc_fertility_casing(lines, do_lower=True):
        ferts = []
        tok_counts = []
        for raw in lines:
            line = unicodedata.normalize("NFC", raw)
            if do_lower:
                line = line.lower()
            toks = enc.encode(line)
            words = line.split()
            ferts.append(len(toks) / len(words))
            tok_counts.append(len(toks))
        return sum(ferts) / len(ferts), sum(tok_counts)

    eng_fert_lower, eng_toks_lower = calc_fertility_casing(eng_sample, do_lower=True)
    eng_fert_raw, eng_toks_raw = calc_fertility_casing(eng_sample, do_lower=False)
    hin_fert_lower, hin_toks_lower = calc_fertility_casing(hin_sample, do_lower=True)
    hin_fert_raw, hin_toks_raw = calc_fertility_casing(hin_sample, do_lower=False)
    
    ratio_with_lower = hin_fert_lower / eng_fert_lower
    ratio_without_lower = hin_fert_raw / eng_fert_raw

    results["flaw2_lowercasing"] = {
        "description": "line.lower() only affects English (Indic has no case), reducing English token count by 5.6% and inflating the Hindi/English disparity ratio.",
        "eng_tokens_with_lower": eng_toks_lower,
        "eng_tokens_raw_casing": eng_toks_raw,
        "eng_fertility_with_lower": eng_fert_lower,
        "eng_fertility_raw_casing": eng_fert_raw,
        "hin_tokens_with_lower": hin_toks_lower,
        "hin_tokens_raw_casing": hin_toks_raw,
        "hin_fertility_with_lower": hin_fert_lower,
        "hin_fertility_raw_casing": hin_fert_raw,
        "ratio_with_lower": ratio_with_lower,
        "ratio_raw_casing": ratio_without_lower,
    }

    # -------------------------------------------------------------
    # Experiment 3: Macro-averaging vs Micro-averaging
    # -------------------------------------------------------------
    def calc_macro_vs_micro(lines):
        per_line = []
        total_toks = 0
        total_words = 0
        for raw in lines:
            line = unicodedata.normalize("NFC", raw)
            toks = enc.encode(line)
            words = line.split()
            per_line.append(len(toks) / len(words))
            total_toks += len(toks)
            total_words += len(words)
        macro = sum(per_line) / len(per_line)
        micro = total_toks / total_words
        return macro, micro

    eng_macro, eng_micro = calc_macro_vs_micro(eng_sample)
    hin_macro, hin_micro = calc_macro_vs_micro(hin_sample)

    results["flaw3_macro_vs_micro"] = {
        "description": "fertility.py computes macro-average (average of ratios sum(T_i/W_i)/N) instead of micro-average (sum(T_i)/sum(W_i)).",
        "eng_macro": eng_macro,
        "eng_micro": eng_micro,
        "hin_macro": hin_macro,
        "hin_micro": hin_micro,
    }

    # -------------------------------------------------------------
    # Experiment 4: Conceptual Flaw -- Whitespace word vs Agglutination
    # -------------------------------------------------------------
    # Evaluate across English, Hindi, and Kannada on FLORES-200 (100 parallel sentences)
    flores_eng = load_lines(os.path.join(flores_dir, "eng.txt"))
    flores_hin = load_lines(os.path.join(flores_dir, "hin.txt"))
    flores_kan = load_lines(os.path.join(flores_dir, "kan.txt"))

    def corpus_stats(lines):
        toks = sum(len(enc.encode(l)) for l in lines)
        words = sum(len(l.split()) for l in lines)
        chars = sum(len(l) for l in lines)
        bytes_ = sum(len(l.encode("utf-8")) for l in lines)
        sents = len(lines)
        return {
            "tokens": toks,
            "words": words,
            "chars": chars,
            "bytes": bytes_,
            "tok_per_word": toks / words,
            "tok_per_sent": toks / sents,
            "words_per_sent": words / sents,
        }

    stats_eng = corpus_stats(flores_eng)
    stats_hin = corpus_stats(flores_hin)
    stats_kan = corpus_stats(flores_kan)

    results["flaw4_typology_words"] = {
        "description": "Kannada words pack multiple morphemes per word (14.2 words/sentence vs 20.9 words/sentence in English). Measuring per-word penalizes agglutinative morphology.",
        "eng": stats_eng,
        "hin": stats_hin,
        "kan": stats_kan,
    }

    # -------------------------------------------------------------
    # Experiment 5: Conceptual Flaw -- len(line) Unicode Codepoint vs Bytes
    # -------------------------------------------------------------
    # Python len() counts codepoints. Indic characters have multiple codepoints per akshara.
    results["flaw5_codepoint_vs_bytes"] = {
        "description": "len(line) measures Unicode code points (UTF-16 code units), not visual graphemes or UTF-8 information bytes.",
        "eng_bytes_per_char": stats_eng["bytes"] / stats_eng["chars"],
        "hin_bytes_per_char": stats_hin["bytes"] / stats_hin["chars"],
        "kan_bytes_per_char": stats_kan["bytes"] / stats_kan["chars"],
        "eng_tok_per_byte": stats_eng["tokens"] / stats_eng["bytes"],
        "hin_tok_per_byte": stats_hin["tokens"] / stats_hin["bytes"],
        "kan_tok_per_byte": stats_kan["tokens"] / stats_kan["bytes"],
    }

    # -------------------------------------------------------------
    # Experiment 6: The Harmless Element -- unicodedata.normalize("NFC", line)
    # -------------------------------------------------------------
    # Test decomposed NFD vs composed NFC
    hin_nfd_toks = sum(len(enc.encode(unicodedata.normalize("NFD", l))) for l in hin_sample)
    hin_nfc_toks = sum(len(enc.encode(unicodedata.normalize("NFC", l))) for l in hin_sample)
    
    results["harmless_nfc_normalization"] = {
        "description": "NFC normalization looks suspicious to novices as mutating text, but is actually essential: NFD decomposed text fragments into stray combining code points, causing token bloat.",
        "hin_nfc_tokens": hin_nfc_toks,
        "hin_nfd_tokens": hin_nfd_toks,
        "bloat_under_nfd_pct": ((hin_nfd_toks - hin_nfc_toks) / hin_nfc_toks) * 100,
    }

    return results

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_dir = os.path.normpath(os.path.join(script_dir, "..", "..", "..", "starter_kit (1)", "starter_kit", "corpus_sample"))
    flores_dir = os.path.normpath(os.path.join(script_dir, "..", "corpus"))
    
    out_dir = os.path.normpath(os.path.join(script_dir, "..", "results"))
    os.makedirs(out_dir, exist_ok=True)
    
    audit_data = run_audit(sample_dir, flores_dir)
    
    out_json = os.path.join(out_dir, "audit_evidence.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
        
    print("Audit experiments completed successfully. Results saved to:", out_json)
    print("\n--- Summary of Measured Evidence ---")
    for key, data in audit_data.items():
        print(f"\n[{key}]")
        print(f"  Summary: {data['description']}")
        for k, v in data.items():
            if k != "description":
                print(f"    {k}: {v}")
