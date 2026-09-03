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
import re
import sys
import json
import unicodedata
import argparse
import tiktoken

# Windows consoles default to cp1252, which cannot encode Devanagari/Dravidian output.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def load_lines(path):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line:
                lines.append(line)
    return lines

def find_corpus_sample(script_dir):
    """Locate starter_kit/corpus_sample whether or not the folder kept its download suffix."""
    repo_root = os.path.normpath(os.path.join(script_dir, "..", "..", ".."))
    candidates = [
        os.path.join(repo_root, "starter_kit (1)", "starter_kit"),
        os.path.join(repo_root, "starter_kit"),
        os.path.join(repo_root, "starter_kit (1)"),
    ]
    for base in candidates:
        if os.path.isdir(os.path.join(base, "corpus_sample")):
            return os.path.join(base, "corpus_sample")
    raise FileNotFoundError(
        "Could not locate starter_kit/corpus_sample. Looked in:\n  " + "\n  ".join(candidates)
    )


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

    _ef_n, _ef_c = calc_fertility_split(eng_sample, True), calc_fertility_split(eng_sample, False)
    _hf_n, _hf_c = calc_fertility_split(hin_sample, True), calc_fertility_split(hin_sample, False)

    return {
        "description": (
            f"REAL BUG. str.split(' ') keeps the empty string between consecutive spaces as a word; "
            f"str.split() collapses whitespace runs. Ghost words inflate the denominator: eng "
            f"{sum(eng_w_naive)} -> {sum(eng_w_clean)} ({sum(eng_w_naive) - sum(eng_w_clean)} ghost), "
            f"hin {sum(hin_w_naive)} -> {sum(hin_w_clean)} ({sum(hin_w_naive) - sum(hin_w_clean)} ghost). "
            f"DIRECTION: fertility is DEFLATED -- eng {_ef_n:.4f} vs {_ef_c:.4f} "
            f"({(_ef_n / _ef_c - 1) * 100:+.2f}%), hin {_hf_n:.4f} vs {_hf_c:.4f} "
            f"({(_hf_n / _hf_c - 1) * 100:+.2f}%)."
        ),
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

    ratio_lower = hin_fert_lower / eng_fert_lower
    ratio_raw = hin_fert_raw / eng_fert_raw
    eng_tok_delta = ((eng_toks_lower - eng_toks_raw) / eng_toks_raw) * 100
    ratio_delta = ((ratio_lower - ratio_raw) / ratio_raw) * 100

    return {
        "description": (
            f"REAL BUG, but it biases AGAINST the v0 conclusion. Asymmetric transform: Hindi "
            f"tokens are unchanged ({hin_toks_raw} -> {hin_toks_lower}, Devanagari has no case), "
            f"while English tokens move {eng_toks_raw} -> {eng_toks_lower} ({eng_tok_delta:+.1f}%) "
            f"as GPT-2 BPE merge boundaries shift. DIRECTION: lowercasing RAISES the English token "
            f"count, so it SHRINKS the reported disparity from {ratio_raw:.2f}x to {ratio_lower:.2f}x "
            f"({ratio_delta:+.1f}%). The methodology is unsound because the transform is applied to "
            f"only one side of the comparison -- but this particular bias understates the gap rather "
            f"than inflating it, so correcting it makes v0's headline slightly WORSE, not better."
        ),
        "eng_token_change_pct": eng_tok_delta,
        "ratio_change_pct": ratio_delta,
        "hin_tokens_unaffected": hin_toks_raw == hin_toks_lower,
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
        "description": (
            f"REAL STATISTICAL FLAW. fertility.py computes the macro-average sum(T_i/W_i)/N, which "
            f"weights a 2-word line the same as a 50-word line; the corpus rate is the micro-average "
            f"sum(T_i)/sum(W_i). DIRECTION: macro OVERSTATES both languages -- eng {eng_macro:.4f} vs "
            f"micro {eng_micro:.4f} ({(eng_macro / eng_micro - 1) * 100:+.2f}%), hin {hin_macro:.4f} vs "
            f"micro {hin_micro:.4f} ({(hin_macro / hin_micro - 1) * 100:+.2f}%). Small on this corpus, "
            f"but it is the wrong estimator and its size is corpus-dependent."
        ),
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

    ratio_word = stats_kan["tok_per_word"] / stats_eng["tok_per_word"]
    ratio_sent = stats_kan["tok_per_sent"] / stats_eng["tok_per_sent"]
    compression = ((stats_eng["words_per_sent"] - stats_kan["words_per_sent"]) / stats_eng["words_per_sent"]) * 100

    return {
        "description": (
            f"REAL CONCEPTUAL FLAW. On the same 100 parallel sentences English uses "
            f"{stats_eng['words_per_sent']:.1f} words/sent and Kannada {stats_kan['words_per_sent']:.1f} "
            f"({compression:.1f}% fewer words for identical meaning), because Kannada binds case "
            f"markers and postpositions onto the stem. Kannada therefore scores {ratio_word:.2f}x "
            f"English per WORD but only {ratio_sent:.2f}x per PARALLEL SENTENCE. DIRECTION: the word "
            f"denominator INFLATES the apparent penalty by {((ratio_word / ratio_sent) - 1) * 100:.1f}%, "
            f"an artifact of morphology rather than tokenizer cost. The denominator must hold meaning "
            f"constant across languages; whitespace words do not."
        ),
        "kan_ratio_per_word": ratio_word,
        "kan_ratio_per_sent": ratio_sent,
        "word_denominator_distortion_pct": ((ratio_word / ratio_sent) - 1) * 100,
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
        "description": (
            f"REAL CONCEPTUAL FLAW. Python 3 len(str) counts Unicode CODE POINTS (PEP 393 flexible "
            f"string representation) -- not UTF-8 bytes and not grapheme clusters. Indic aksharas span "
            f"several code points ({hin_bpc:.2f} UTF-8 bytes per code point for Hindi vs "
            f"{eng_bpc:.2f} for English), so the denominator swells for Indic text while the numerator "
            f"is untouched. MAGNITUDE: the identical tokens scored per code point give "
            f"{ratio_char_hin:.2f}x, but scored per UTF-8 byte give {ratio_byte_hin:.2f}x. DIRECTION: "
            f"the code-point denominator OVERSTATES the disparity by "
            f"{ratio_char_hin / ratio_byte_hin:.2f}x, and is the direct source of REPORT_v0's "
            f"'7.0x worse per character' headline."
        ),
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

    g_word = gpt2_hin_tpw / gpt2_eng_tpw
    g_char = gpt2_hin_tpc / gpt2_eng_tpc
    x_word = xlmr_hin_tpw / xlmr_eng_tpw
    x_char = xlmr_hin_tpc / xlmr_eng_tpc

    return {
        "description": (
            f"REAL CONCEPTUAL FLAW in REPORT_v0's REASONING (not in the script). v0 argues the "
            f"tok/char column 'confirms' the tok/word number and concludes 'no further measurement "
            f"needed'. But both metrics divide the SAME numerator (token count T), and under gpt2 that "
            f"numerator is dominated by a single artifact: Devanagari falling back to byte-level tokens. "
            f"Changing only the DENOMINATOR cannot test that artifact, so agreement is arithmetically "
            f"guaranteed rather than corroborative. Proof: swapping the denominator leaves both large "
            f"(gpt2 {g_word:.2f}x per word, {g_char:.2f}x per code point), but swapping the NUMERATOR "
            f"collapses both at once (xlm-roberta-base {x_word:.2f}x per word, {x_char:.2f}x per code "
            f"point). Independent confirmation requires a different tokenizer, not a different divisor."
        ),
        "gpt2_hindi_vs_eng_word_ratio": g_word,
        "gpt2_hindi_vs_eng_char_ratio": g_char,
        "xlmr_hindi_vs_eng_word_ratio": x_word,
        "xlmr_hindi_vs_eng_char_ratio": x_char,
    }

def run_flaw_nfc(flores_dir, enc):
    """
    The harmless element. Tested across four Indic corpora, NOT Hindi alone.

    Testing NFC on Hindi is structurally incapable of showing an effect: Unicode's
    decomposable Devanagari code points (the nukta forms) do not occur in this corpus,
    so NFD(text) == text and the delta is necessarily 0.00%. The Dravidian corpora DO
    contain decomposable characters, which is where the mechanism becomes measurable.
    """
    per_lang = {}
    for lang in ("hin", "kan", "tam", "tel"):
        lines = load_lines(os.path.join(flores_dir, f"{lang}.txt"))
        nfc_toks = sum(len(enc.encode(unicodedata.normalize("NFC", l))) for l in lines)
        nfd_toks = sum(len(enc.encode(unicodedata.normalize("NFD", l))) for l in lines)
        text = "".join(lines)
        decomposable = sorted({c for c in text if unicodedata.normalize("NFD", c) != c})
        per_lang[lang] = {
            "nfc_tokens": nfc_toks,
            "nfd_tokens": nfd_toks,
            "delta_pct": ((nfd_toks - nfc_toks) / nfc_toks) * 100,
            "nfd_is_noop_on_this_text": unicodedata.normalize("NFD", text) == text,
            "distinct_decomposable_chars_present": len(decomposable),
            "decomposable_chars_present": "".join(decomposable[:12]),
        }

    # Unicode DOES define decomposable Devanagari code points; they simply never
    # appear in this corpus. Measure that rather than asserting it.
    deva_decomposable = [chr(c) for c in range(0x0900, 0x0980)
                         if unicodedata.normalize("NFD", chr(c)) != chr(c)]
    hin_text = "".join(load_lines(os.path.join(flores_dir, "hin.txt")))
    worst = max(per_lang.values(), key=lambda d: d["delta_pct"])

    return {
        "description": (
            f"HARMLESS AND NECESSARY. Hindi shows {per_lang['hin']['delta_pct']:.2f}% because the "
            f"{len(deva_decomposable)} decomposable Devanagari code points Unicode defines "
            f"({''.join(deva_decomposable[:6])}...) do not occur in this corpus -- "
            f"NFD(text)==text is {per_lang['hin']['nfd_is_noop_on_this_text']}, so a Hindi-only test "
            f"cannot show anything. Measured on Dravidian corpora, which do contain decomposable "
            f"characters, dropping NFC inflates token counts: kan {per_lang['kan']['delta_pct']:+.2f}%, "
            f"tam {per_lang['tam']['delta_pct']:+.2f}%, tel {per_lang['tel']['delta_pct']:+.2f}%. "
            f"DIRECTION: removing NFC INFLATES tokens by up to {worst['delta_pct']:.2f}%. NFC costs "
            f"nothing and prevents that. Flagging it as a bug would be incorrect."
        ),
        "per_language": per_lang,
        "devanagari_decomposable_codepoints_defined_in_unicode": len(deva_decomposable),
        "devanagari_decomposable_examples": "".join(deva_decomposable),
        "any_decomposable_devanagari_char_in_our_corpus": any(c in hin_text for c in deva_decomposable),
        "max_inflation_pct_if_nfc_removed": worst["delta_pct"],
    }

def run_flaw_seed(sample_dir):
    """
    The second harmless element: random.seed(1337).

    A seeded RNG labelled "reproducibility" implies the script samples or shuffles the
    corpus, which would make every reported number depend on a hidden subset. Static
    analysis shows nothing ever draws from the stream, so the seed is provably inert.
    """
    fertility_path = os.path.join(os.path.dirname(sample_dir), "fertility.py")
    with open(fertility_path, "r", encoding="utf-8") as f:
        src = f.read()

    random_refs = re.findall(r"random\.\w+", src)
    rng_consumers = [r for r in random_refs if r != "random.seed"]
    sys_refs = re.findall(r"\bsys\.\w+", src)

    return {
        "description": (
            f"HARMLESS -- dead code, not data sampling. Static scan of fertility.py finds "
            f"{len(random_refs)} reference(s) to the random module ({', '.join(random_refs) or 'none'}), "
            f"of which {len(rng_consumers)} actually draw from the stream. Because nothing consumes "
            f"the RNG, the seed cannot influence any reported number -- deleting line 25 changes "
            f"every output by exactly 0. 'import sys' is likewise unused ({len(sys_refs)} call sites). "
            f"Looks like hidden corpus sampling; is provably inert. Flagging it as a bug would be "
            f"incorrect."
        ),
        "file_scanned": os.path.basename(fertility_path),
        "all_random_references": random_refs,
        "rng_consumers": rng_consumers,
        "seed_can_affect_output": len(rng_consumers) > 0,
        "unused_sys_import": len(sys_refs) == 0,
    }


def run_sample_variance(sample_dir, flores_dir, enc):
    hin_sample = load_lines(os.path.join(sample_dir, "hin_sample.txt"))
    flores_hin = load_lines(os.path.join(flores_dir, "hin.txt"))
    sample_tpw = sum(len(enc.encode(l)) for l in hin_sample) / sum(len(l.split()) for l in hin_sample)
    corpus_tpw = sum(len(enc.encode(l)) for l in flores_hin) / sum(len(l.split()) for l in flores_hin)

    return {
        "description": (
            f"Sample-size caveat for A1: the 10-sentence smoke corpus gives {sample_tpw:.3f} tok/word "
            f"for Hindi, the 100-sentence parallel corpus gives {corpus_tpw:.3f} "
            f"({((corpus_tpw - sample_tpw) / sample_tpw) * 100:+.1f}%). The v0 headline rests on the "
            f"noisier of the two."
        ),
        "sample_10_sentences_hin_tpw": sample_tpw,
        "flores_100_sentences_hin_tpw": corpus_tpw,
    }

def main():
    parser = argparse.ArgumentParser(description="Audit evidence runner under the Evidence Rule.")
    parser.add_argument(
        "--flaw",
        choices=["whitespace", "lowercase", "macro-micro", "typology", "char-denominator",
                 "shared-numerator", "nfc", "seed", "sample-variance", "all"],
        default="all",
        help="Select a specific flaw experiment to isolate and execute.",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_dir = find_corpus_sample(script_dir)
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
        "nfc": ("harmless_nfc_normalization", lambda: run_flaw_nfc(flores_dir, enc)),
        "seed": ("harmless_random_seed", lambda: run_flaw_seed(sample_dir)),
        "sample-variance": ("sample_size_variance", lambda: run_sample_variance(sample_dir, flores_dir, enc)),
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
