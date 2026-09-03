#!/usr/bin/env python3
"""
benchmark_v1.py -- Corrected multilingual tokenizer benchmarking.

Evaluates:
  - Languages: English (eng), Hindi (hin), Kannada (kan), Tamil (tam), Telugu (tel)
  - Tokenizers:
      1. gpt2 (tiktoken) [English-centric baseline]
      2. xlm-roberta-base (transformers) [Multilingual / Indic-aware]
  - Denominators:
      - per parallel sentence (semantic information unit)
      - per whitespace word
      - per grapheme cluster (akshara / true visual syllable via regex \\X)
      - per UTF-8 byte
      - per Unicode code point (chars)

Computes true micro-averages and comparative ratios relative to English.
Outputs results to console, CSV, and JSON.
"""

import os
import sys
import json
import csv
import regex
import unicodedata
import tiktoken
from transformers import AutoTokenizer

sys.stdout.reconfigure(encoding="utf-8")

def count_graphemes(text: str) -> int:
    """Count extended grapheme clusters (true visual characters/aksharas)."""
    return len(regex.findall(r"\X", text))

def load_corpus(corpus_dir, languages):
    corpus = {}
    for lang in languages:
        path = os.path.join(corpus_dir, f"{lang}.txt")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing corpus file: {path}")
        with open(path, "r", encoding="utf-8") as f:
            lines = [unicodedata.normalize("NFC", l.strip()) for l in f if l.strip()]
        corpus[lang] = lines
    
    # Assert strictly parallel
    lens = {lang: len(lines) for lang, lines in corpus.items()}
    assert len(set(lens.values())) == 1, f"Sentence counts differ: {lens}"
    return corpus

def evaluate_tokenizer(name, encode_fn, corpus):
    results = {}
    
    for lang, lines in corpus.items():
        total_tokens = 0
        total_words = 0
        total_chars = 0
        total_graphemes = 0
        total_bytes = 0
        num_sentences = len(lines)
        
        per_sent_tokens = []
        per_sent_fertility = []
        per_sent_tpc = []
        per_sent_tpg = []
        per_sent_tpb = []
        
        for line in lines:
            tokens = encode_fn(line)
            words = line.split()
            chars = len(line)
            graphemes = count_graphemes(line)
            bytes_ = len(line.encode("utf-8"))
            
            n_tok = len(tokens)
            n_w = len(words)
            
            total_tokens += n_tok
            total_words += n_w
            total_chars += chars
            total_graphemes += graphemes
            total_bytes += bytes_
            
            per_sent_tokens.append(n_tok)
            per_sent_fertility.append(n_tok / n_w)
            per_sent_tpc.append(n_tok / chars)
            per_sent_tpg.append(n_tok / graphemes)
            per_sent_tpb.append(n_tok / bytes_)
            
        results[lang] = {
            "num_sentences": num_sentences,
            "total_tokens": total_tokens,
            "total_words": total_words,
            "total_chars": total_chars,
            "total_graphemes": total_graphemes,
            "total_bytes": total_bytes,
            
            # Micro-averages (true corpus rate)
            "tok_per_sent": total_tokens / num_sentences,
            "tok_per_word": total_tokens / total_words,
            "tok_per_grapheme": total_tokens / total_graphemes,
            "tok_per_byte": total_tokens / total_bytes,
            "tok_per_char": total_tokens / total_chars,
            
            # Macro-averages (for auditing comparison)
            "macro_tok_per_word": sum(per_sent_fertility) / num_sentences,
            "macro_tok_per_grapheme": sum(per_sent_tpg) / num_sentences,
            "macro_tok_per_byte": sum(per_sent_tpb) / num_sentences,
            "macro_tok_per_char": sum(per_sent_tpc) / num_sentences,
            
            "words_per_sent": total_words / num_sentences,
            "graphemes_per_sent": total_graphemes / num_sentences,
            "bytes_per_sent": total_bytes / num_sentences,
        }
    
    # Calculate ratios relative to English
    base = results["eng"]
    for lang in results:
        results[lang]["ratio_per_sent"] = results[lang]["tok_per_sent"] / base["tok_per_sent"]
        results[lang]["ratio_per_word"] = results[lang]["tok_per_word"] / base["tok_per_word"]
        results[lang]["ratio_per_grapheme"] = results[lang]["tok_per_grapheme"] / base["tok_per_grapheme"]
        results[lang]["ratio_per_byte"] = results[lang]["tok_per_byte"] / base["tok_per_byte"]
        results[lang]["ratio_per_char"] = results[lang]["tok_per_char"] / base["tok_per_char"]
        
    return results

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Multilingual Tokenizer Benchmark (v1)")
    ap.add_argument(
        "--corpus",
        action="append",
        metavar="LANG=PATH",
        help="Optional custom language and corpus path, e.g. eng=path.txt (repeatable). Defaults to FLORES-200.",
    )
    ap.add_argument(
        "--tokenizer",
        action="append",
        choices=["gpt2", "xlm-roberta-base", "Qwen2.5-1.5B", "all"],
        default=None,
        help="Tokenizer(s) to benchmark (default: all).",
    )
    ap.add_argument(
        "--text",
        type=str,
        default=None,
        help="Single interactive text string to test across tokenizers.",
    )
    args = ap.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_dir = os.path.normpath(os.path.join(script_dir, "..", "corpus"))
    results_dir = os.path.normpath(os.path.join(script_dir, "..", "results"))
    os.makedirs(results_dir, exist_ok=True)
    
    # Setup Tokenizers.
    #
    # Three deliberately different vocabularies:
    #   gpt2              50k   English-centric BPE      -- what REPORT_v0 used
    #   xlm-roberta-base  250k  Indic-aware SentencePiece -- best case, but encoder-only
    #   Qwen2.5-1.5B      151k  generative, ungated       -- closest available proxy for
    #                                                        the 128k-vocab FLM-4B in
    #                                                        bench/model_spec.md
    # The spread between the last two is the point: the cost multiplier is a property of
    # the deployed vocabulary, not of the language.
    enc_gpt2 = tiktoken.get_encoding("gpt2")
    gpt2_fn = lambda s: enc_gpt2.encode(s)

    all_toks = {"gpt2": gpt2_fn}

    for label, repo in (("xlm-roberta-base", "xlm-roberta-base"),
                        ("Qwen2.5-1.5B", "Qwen/Qwen2.5-1.5B")):
        try:
            tok = AutoTokenizer.from_pretrained(repo)
            all_toks[label] = (lambda t: (lambda s: t.encode(s, add_special_tokens=False)))(tok)
        except Exception as exc:                                    # noqa: BLE001
            print(f"[warn] tokenizer '{repo}' unavailable ({type(exc).__name__}); skipping. "
                  f"Results will omit it.", file=sys.stderr)
    
    if args.tokenizer and "all" not in args.tokenizer:
        tokenizers = {k: all_toks[k] for k in args.tokenizer if k in all_toks}
    else:
        tokenizers = all_toks

    # Quick interactive mode for live defense testing
    if args.text:
        print(f"\nEvaluating raw text: {args.text}")
        print(f"Words: {len(args.text.split())} | Graphemes: {count_graphemes(args.text)} | Bytes: {len(args.text.encode('utf-8'))}")
        for tname, tfn in tokenizers.items():
            toks = tfn(args.text)
            print(f"[{tname}] Tokens ({len(toks)}): {toks}")
        return

    # Corpus mode
    if args.corpus:
        corpus = {}
        languages = []
        for cspec in args.corpus:
            lang, cpath = cspec.split("=", 1)
            languages.append(lang)
            with open(cpath, "r", encoding="utf-8") as f:
                corpus[lang] = [unicodedata.normalize("NFC", l.strip()) for l in f if l.strip()]
    else:
        languages = ["eng", "hin", "kan", "tam", "tel"]
        corpus = load_corpus(corpus_dir, languages)
        
    print(f"Loaded corpus for {languages} with {len(corpus[languages[0]])} sentences each.\n")
    
    all_benchmarks = {}
    csv_rows = []
    
    for tok_name, fn in tokenizers.items():
        print(f"==========================================================================================")
        print(f" Tokenizer: {tok_name}")
        print(f"==========================================================================================")
        bench = evaluate_tokenizer(tok_name, fn, corpus)
        all_benchmarks[tok_name] = bench
        
        print(f"{'lang':<5}{'words/s':>8}{'graph/s':>8}{'tok/sent':>10}{'ratio(sent)':>13}{'tok/word':>10}{'ratio(word)':>13}{'tok/graph':>10}{'ratio(graph)':>13}{'tok/byte':>10}{'ratio(byte)':>13}")
        print("-" * 115)
        for lang in languages:
            d = bench[lang]
            print(f"{lang:<5}{d['words_per_sent']:>8.1f}{d['graphemes_per_sent']:>8.1f}{d['tok_per_sent']:>10.1f}{d['ratio_per_sent']:>12.2f}x{d['tok_per_word']:>10.2f}{d['ratio_per_word']:>12.2f}x{d['tok_per_grapheme']:>10.2f}{d['ratio_per_grapheme']:>12.2f}x{d['tok_per_byte']:>10.3f}{d['ratio_per_byte']:>12.2f}x")
            
            csv_rows.append({
                "tokenizer": tok_name,
                "lang": lang,
                "words_per_sent": round(d["words_per_sent"], 2),
                "graphemes_per_sent": round(d["graphemes_per_sent"], 2),
                "bytes_per_sent": round(d["bytes_per_sent"], 2),
                "tok_per_sent": round(d["tok_per_sent"], 2),
                "ratio_vs_eng_sent": round(d["ratio_per_sent"], 2),
                "tok_per_word": round(d["tok_per_word"], 2),
                "ratio_vs_eng_word": round(d["ratio_per_word"], 2),
                "tok_per_grapheme": round(d["tok_per_grapheme"], 2),
                "ratio_vs_eng_grapheme": round(d["ratio_per_grapheme"], 2),
                "tok_per_byte": round(d["tok_per_byte"], 3),
                "ratio_vs_eng_byte": round(d["ratio_per_byte"], 2),
                "tok_per_char": round(d["tok_per_char"], 3),
                "ratio_vs_eng_char": round(d["ratio_per_char"], 2),
            })
        print()

    # Save to JSON only if default run
    if not args.corpus:
        json_path = os.path.join(results_dir, "benchmark_results.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_benchmarks, f, indent=2)
        print(f"Detailed JSON results saved to: {json_path}")
        
        csv_path = os.path.join(results_dir, "corrected_metrics.csv")
        fieldnames = list(csv_rows[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"Summary CSV metrics saved to: {csv_path}")

if __name__ == "__main__":
    main()
