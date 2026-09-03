#!/usr/bin/env python3
"""
audit_evidence.py -- Isolated experiments proving bugs, conceptual flaws,
and harmless elements in fertility.py under the Flam AI Evidence Rule.

For each claim:
  - Isolate the single variable.
  - Run the exact before/after comparison.
  - Measure direction and magnitude of the distortion.
  - Output structured JSON and console breakdown.

Supports `--flaw <name>` to isolate and run individual experiments for live defense.
"""

import os
import sys
import json
import unicodedata
import argparse
import tiktoken

def load_lines(path):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line:
                lines.append(line)
    return lines

def run_flaw_whitespace(sample_dir, enc):
    eng_sample = load_lines(os.path.join(sample_dir, "eng_sample.txt"))
    hin_sample = load_lines(os.path.join(sample_dir, "hin_sample.txt"))

    def count_words(lines, naive=True):
        words_per_line = []
        for line in lines:
            w = [x for x in line.lower().split(" ")] if naive else line.lower().split()
            words_per_line.append(len(w))
        return words_per_line

    eng_w_naive = count_words(eng_sample, naive=True)
    eng_w_clean = count_words(eng_sample, naive=False)
    hin_w_naive = count_words(hin_sample, naive=True)
    hin_w_clean = count_words(hin_sample, naive=False)

    def calc_fertility_split(lines, naive=True):
        ferts = []
        for line in lines:
            toks = enc.encode(line.lower())
            w = line.lower().split(" ") if naive else line.lower().split()
            ferts.append(len(toks) / len(w))
        return sum(ferts) / len(ferts)

    return {
        "description": "line.split(' ') counts double spaces as empty words, inflating word count and artificially deflating fertility.",
        "eng_words_naive": sum(eng_w_naive),
        "eng_words_clean": sum(eng_w_clean),
        "hin_words_naive": sum(hin_w_naive),
        "hin_words_clean": sum(hin_w_clean),
        "eng_fertility_before_split_naive": calc_fertility_split(eng_sample, naive=True),
        "eng_fertility_after_split_clean": calc_fertility_split(eng_sample, naive=False),
        "hin_fertility_before_split_naive": calc_fertility_split(hin_sample, naive=True),
        "hin_fertility_after_split_clean": calc_fertility_split(hin_sample, naive=False),
        "eng_fertility_deflation_pct": ((calc_fertility_split(eng_sample, naive=False) - calc_fertility_split(eng_sample, naive=True)) / calc_fertility_split(eng_sample, naive=False)) * 100,
        "hin_fertility_deflation_pct": ((calc_fertility_split(hin_sample, naive=False) - calc_fertility_split(hin_sample, naive=True)) / calc_fertility_split(hin_sample, naive=False)) * 100,
    }

def run_flaw_lowercase(sample_dir, enc):
    eng_sample = load_lines(os.path.join(sample_dir, "eng_sample.txt"))
    hin_sample = load_lines(os.path.join(sample_dir, "hin_sample.txt"))

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

    return {
        "description": "line.lower() only affects English (Indic has no case), mutating English token count by 3.1% and altering the disparity ratio.",
        "eng_tokens_with_lower": eng_toks_lower,
        "eng_tokens_raw_casing": eng_toks_raw,
        "eng_fertility_with_lower": eng_fert_lower,
        "eng_fertility_raw_casing": eng_fert_raw,
        "hin_tokens_with_lower": hin_toks_lower,
        "hin_tokens_raw_casing": hin_toks_raw,
        "hin_fertility_with_lower": hin_fert_lower,
        "hin_fertility_raw_casing": hin_fert_raw,
        "ratio_with_lower": hin_fert_lower / eng_fert_lower,
        "ratio_raw_casing": hin_fert_raw / eng_fert_raw,
    }

def run_flaw_macro_micro(sample_dir, enc):
    eng_sample = load_lines(os.path.join(sample_dir, "eng_sample.txt"))
    hin_sample = load_lines(os.path.join(sample_dir, "hin_sample.txt"))

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

    return {
        "description": "fertility.py computes macro-average (average of ratios sum(T_i/W_i)/N) instead of micro-average (sum(T_i)/sum(W_i)).",
        "eng_macro": eng_macro,
        "eng_micro": eng_micro,
        "hin_macro": hin_macro,
        "hin_micro": hin_micro,
    }

def run_flaw_typology(flores_dir, enc):
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

    return {
        "description": "Dravidian languages (Kannada) pack multiple morphemes per word (17.2 words/sent vs 22.2 in English, -22.5%). Measuring tokens-per-word imposes an artificial +29% penalty.",
        "eng": stats_eng,
        "hin": stats_hin,
        "kan": stats_kan,
        "kannada_word_compression_pct": ((stats_eng["words_per_sent"] - stats_kan["words_per_sent"]) / stats_eng["words_per_sent"]) * 100,
        "artificial_word_penalty_pct": ((stats_eng["words_per_sent"] / stats_kan["words_per_sent"]) - 1.0) * 100,
    }

def run_flaw_char_denominator(flores_dir, enc):
    flores_eng = load_lines(os.path.join(flores_dir, "eng.txt"))
    flores_hin = load_lines(os.path.join(flores_dir, "hin.txt"))
    flores_kan = load_lines(os.path.join(flores_dir, "kan.txt"))

    def get_rates(lines):
        toks = sum(len(enc.encode(l)) for l in lines)
        chars = sum(len(l) for l in lines)
        bytes_ = sum(len(l.encode("utf-8")) for l in lines)
        return toks / chars, toks / bytes_, bytes_ / chars

    eng_tpc, eng_tpb, eng_bpc = get_rates(flores_eng)
    hin_tpc, hin_tpb, hin_bpc = get_rates(flores_hin)
    kan_tpc, kan_tpb, kan_bpc = get_rates(flores_kan)

    ratio_char_hin = hin_tpc / eng_tpc
    ratio_byte_hin = hin_tpb / eng_tpb

    return {
        "description": "len(line) measures Unicode code points (UTF-16 code units), not visual syllables or UTF-8 information bytes. Dividing by codepoints inflates Hindi/English disparity from 2.82x to 7.21x (a 2.56x overstatement).",
        "eng_tok_per_char": eng_tpc,
        "hin_tok_per_char": hin_tpc,
        "kan_tok_per_char": kan_tpc,
        "eng_tok_per_byte": eng_tpb,
        "hin_tok_per_byte": hin_tpb,
        "kan_tok_per_byte": kan_tpb,
        "hin_bytes_per_char": hin_bpc,
        "kan_bytes_per_char": kan_bpc,
        "reported_disparity_char_ratio": ratio_char_hin,
        "true_byte_disparity_ratio": ratio_byte_hin,
        "distortion_overstatement_factor": ratio_char_hin / ratio_byte_hin,
    }

def run_flaw_shared_numerator(flores_dir):
    """
    Refuting REPORT_v0's logical fallacy:
    REPORT_v0 claimed tok/char (7.0x) confirms tok/word (5.9x).
    In reality, both share the exact same numerator (token count T).
    Under an Indic-aware tokenizer (XLM-R), BOTH metrics collapse together to 1.08x and 1.26x.
    """
    from transformers import AutoTokenizer
    enc_gpt2 = tiktoken.get_encoding("gpt2")
    tok_xlmr = AutoTokenizer.from_pretrained("xlm-roberta-base")

    flores_eng = load_lines(os.path.join(flores_dir, "eng.txt"))
    flores_hin = load_lines(os.path.join(flores_dir, "hin.txt"))

    def eval_tok(tokenizer_type, lines):
        if tokenizer_type == "gpt2":
            toks = sum(len(enc_gpt2.encode(l)) for l in lines)
        else:
            toks = sum(len(tok_xlmr.encode(l, add_special_tokens=False)) for l in lines)
        words = sum(len(l.split()) for l in lines)
        chars = sum(len(l) for l in lines)
        return toks / words, toks / chars

    gpt2_eng_tpw, gpt2_eng_tpc = eval_tok("gpt2", flores_eng)
    gpt2_hin_tpw, gpt2_hin_tpc = eval_tok("gpt2", flores_hin)

    xlmr_eng_tpw, xlmr_eng_tpc = eval_tok("xlmr", flores_eng)
    xlmr_hin_tpw, xlmr_hin_tpc = eval_tok("xlmr", flores_hin)

    return {
        "description": "REPORT_v0 claims tok/char corroborates tok/word. But both share the exact same numerator (token count T). When numerator is fixed via XLM-R, BOTH ratios collapse together (1.08x per word, 1.26x per char). Co-movement was an arithmetic artifact of a shared broken numerator, not independent validation.",
        "gpt2_hindi_vs_eng_word_ratio": gpt2_hin_tpw / gpt2_eng_tpw,
        "gpt2_hindi_vs_eng_char_ratio": gpt2_hin_tpc / gpt2_eng_tpc,
        "xlmr_hindi_vs_eng_word_ratio": xlmr_hin_tpw / xlmr_eng_tpw,
        "xlmr_hindi_vs_eng_char_ratio": xlmr_hin_tpc / xlmr_eng_tpc,
    }

def run_flaw_nfc(sample_dir, enc):
    hin_sample = load_lines(os.path.join(sample_dir, "hin_sample.txt"))
    hin_nfd_toks = sum(len(enc.encode(unicodedata.normalize("NFD", l))) for l in hin_sample)
    hin_nfc_toks = sum(len(enc.encode(unicodedata.normalize("NFC", l))) for l in hin_sample)

    return {
        "description": "NFC normalization is harmless and essential: subword tokenizers are trained on NFC. Decomposed NFD text fragments into combining characters and causes severe byte-fallback token bloat.",
        "hin_nfc_tokens": hin_nfc_toks,
        "hin_nfd_tokens": hin_nfd_toks,
        "bloat_under_nfd_pct": ((hin_nfd_toks - hin_nfc_toks) / hin_nfc_toks) * 100,
    }

def run_flaw_seed(sample_dir, flores_dir, enc):
    hin_sample = load_lines(os.path.join(sample_dir, "hin_sample.txt"))
    flores_hin = load_lines(os.path.join(flores_dir, "hin.txt"))
    sample_tpw = sum(len(enc.encode(l)) for l in hin_sample) / sum(len(l.split()) for l in hin_sample)
    corpus_tpw = sum(len(enc.encode(l)) for l in flores_hin) / sum(len(l.split()) for l in flores_hin)

    return {
        "description": "The 10-sentence sample corpus has high variance. 100 parallel sentences provide stable micro-averages.",
        "sample_10_sentences_hin_tpw": sample_tpw,
        "flores_100_sentences_hin_tpw": corpus_tpw,
    }

def main():
    parser = argparse.ArgumentParser(description="Audit evidence runner under the Evidence Rule.")
    parser.add_argument(
        "--flaw",
        choices=["whitespace", "lowercase", "macro-micro", "typology", "char-denominator", "shared-numerator", "nfc", "seed", "all"],
        default="all",
        help="Select a specific flaw experiment to isolate and execute.",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_dir = os.path.normpath(os.path.join(script_dir, "..", "..", "..", "starter_kit (1)", "starter_kit", "corpus_sample"))
    flores_dir = os.path.normpath(os.path.join(script_dir, "..", "corpus"))
    out_dir = os.path.normpath(os.path.join(script_dir, "..", "results"))
    os.makedirs(out_dir, exist_ok=True)

    enc = tiktoken.get_encoding("gpt2")

    flaw_map = {
        "whitespace": ("flaw1_whitespace_split", lambda: run_flaw_whitespace(sample_dir, enc)),
        "lowercase": ("flaw2_lowercasing", lambda: run_flaw_lowercase(sample_dir, enc)),
        "macro-micro": ("flaw3_macro_vs_micro", lambda: run_flaw_macro_micro(sample_dir, enc)),
        "typology": ("flaw4_typology_words", lambda: run_flaw_typology(flores_dir, enc)),
        "char-denominator": ("flaw5_codepoint_vs_bytes", lambda: run_flaw_char_denominator(flores_dir, enc)),
        "shared-numerator": ("flaw6_shared_numerator_fallacy", lambda: run_flaw_shared_numerator(flores_dir)),
        "nfc": ("harmless_nfc_normalization", lambda: run_flaw_nfc(sample_dir, enc)),
        "seed": ("sample_size_variance", lambda: run_flaw_seed(sample_dir, flores_dir, enc)),
    }

    if args.flaw != "all":
        key, fn = flaw_map[args.flaw]
        data = fn()
        print(f"\n[{key}]")
        print(f"  Summary: {data['description']}")
        for k, v in data.items():
            if k != "description":
                print(f"    {k}: {v}")
    else:
        results = {}
        for name, (key, fn) in flaw_map.items():
            results[key] = fn()

        out_json = os.path.join(out_dir, "audit_evidence.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print("All audit experiments completed. Results saved to:", out_json)
        print("\n--- Summary of Measured Evidence ---")
        for key, data in results.items():
            print(f"\n[{key}]")
            print(f"  Summary: {data['description']}")
            for k, v in data.items():
                if k != "description":
                    print(f"    {k}: {v}")

if __name__ == "__main__":
    main()
