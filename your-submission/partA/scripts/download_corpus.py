#!/usr/bin/env python3
"""
download_corpus.py -- Fetch and prepare the FLORES-200 multilingual evaluation corpus.

Downloads official Meta NLLB FLORES-200 parallel dataset for:
  - English (eng_Latn)
  - Hindi (hin_Deva)
  - Kannada (kan_Knda) [Dravidian]
  - Tamil (tam_Taml)   [Dravidian]
  - Telugu (tel_Telu)  [Dravidian]

Extracts 100 parallel sentences per language, applies Unicode NFC normalization,
verifies line alignment, and writes them to partA/corpus/.
"""

import os
import io
import tarfile
import urllib.request
import unicodedata

FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"

LANG_MAP = {
    "eng": "eng_Latn",
    "hin": "hin_Deva",
    "kan": "kan_Knda",
    "tam": "tam_Taml",
    "tel": "tel_Telu",
}

def download_and_extract(output_dir: str, num_sentences: int = 100):
    os.makedirs(output_dir, exist_ok=True)
    print(f"Fetching FLORES-200 dataset from {FLORES_URL}...")
    req = urllib.request.Request(FLORES_URL, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req) as resp:
        tar_bytes = resp.read()
    
    print(f"Downloaded {len(tar_bytes)} bytes. Extracting parallel sentences...")
    corpus_lines = {}
    
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        for lang, flores_code in LANG_MAP.items():
            target_path = f"./flores200_dataset/dev/{flores_code}.dev"
            f = tar.extractfile(target_path)
            if f is None:
                raise FileNotFoundError(f"Could not find {target_path} in tar archive")
            
            raw_lines = f.read().decode("utf-8").splitlines()
            # Clean and normalize lines
            cleaned = []
            for line in raw_lines:
                line = line.strip()
                if not line:
                    continue
                line = unicodedata.normalize("NFC", line)
                cleaned.append(line)
            
            corpus_lines[lang] = cleaned[:num_sentences]
            print(f"  - Extracted {len(corpus_lines[lang])} sentences for {lang} ({flores_code})")

    # Verify alignment
    lengths = [len(lines) for lines in corpus_lines.values()]
    assert len(set(lengths)) == 1, f"Mismatch in extracted sentence counts: {lengths}"
    print(f"All {len(LANG_MAP)} languages strictly aligned with {lengths[0]} parallel sentences.")

    # Write files
    for lang, lines in corpus_lines.items():
        out_path = os.path.join(output_dir, f"{lang}.txt")
        with open(out_path, "w", encoding="utf-8") as out_f:
            for line in lines:
                out_f.write(line + "\n")
        print(f"Saved: {out_path}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_dir = os.path.normpath(os.path.join(script_dir, "..", "corpus"))
    download_and_extract(corpus_dir, num_sentences=100)
