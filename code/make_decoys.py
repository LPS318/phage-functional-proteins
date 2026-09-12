#!/usr/bin/env python3
"""
D1-binary · Build a reproducible background decoy set (node-side, needs network).
Downloads reviewed bacterial reference proteins from UniProt (host/related
organisms), length-matches them to the positives, removes decoys with high
k-mer overlap to any positive, and assigns train/val/test splits.

Output: data/decoys.fasta  (>DECOY_<acc>|decoy)  and  data/decoys_meta.tsv
Usage:  python make_decoys.py --pos data/sequences.fasta --n 4117 --seed 0
"""
import argparse, random, re, urllib.parse, urllib.request
from collections import Counter

QUERIES = [
    "organism_id:562 AND reviewed:true",   # E. coli
    "organism_id:573 AND reviewed:true",   # Klebsiella pneumoniae
    "organism_id:1423 AND reviewed:true",  # Bacillus subtilis
    "organism_id:287 AND reviewed:true",   # Pseudomonas aeruginosa (PA host)
]

def fetch_fasta(query):
    url = "https://rest.uniprot.org/uniprotkb/stream?format=fasta&query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "d1-decoys"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read().decode("utf-8", "ignore")

def parse(fa):
    out = []; cur = None; buf = []
    for line in fa.splitlines():
        if line.startswith(">"):
            if cur: out.append((cur, "".join(buf)))
            cur = line[1:].split("|")[1] if "|" in line else line[1:].split()[0]; buf = []
        elif line:
            buf.append(line.strip())
    if cur: out.append((cur, "".join(buf)))
    return out

def k5(s): return set(s[i:i+5] for i in range(len(s)-4))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pos", default="data/sequences.fasta")
    ap.add_argument("--n", type=int, default=4117)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--minlen", type=int, default=200)
    ap.add_argument("--maxlen", type=int, default=1600)
    ap.add_argument("--out", default="data/decoys.fasta")
    a = ap.parse_args()
    random.seed(a.seed)

    # positives for homology filtering
    pos = []
    cur = None; buf = []
    for line in open(a.pos):
        line = line.rstrip()
        if line.startswith(">"):
            if cur: pos.append("".join(buf))
            cur = line[1:]; buf = []
        elif line: buf.append(line)
    if cur: pos.append("".join(buf))
    posk = [k5(s) for s in pos if len(s) >= 5]

    pool = []
    for q in QUERIES:
        try:
            fa = fetch_fasta(q)
            ents = parse(fa)
            print(f"[{q}] fetched {len(ents)}")
            pool += [s for _, s in ents]
        except Exception as e:
            print(f"[warn] query failed {q}: {e}")
    pool = [s for s in pool if a.minlen <= len(s) <= a.maxlen]
    print("pool after length filter:", len(pool))

    random.shuffle(pool)
    decoys = []
    for s in pool:
        if len(decoys) >= a.n: break
        ks = k5(s) if len(s) >= 5 else set()
        # drop if >30% of its 5-mers appear in any single positive (likely homolog)
        bad = False
        for pk in posk:
            if ks and len(ks & pk) / len(ks) > 0.30: bad = True; break
        if not bad: decoys.append(s)
    print("decoys selected:", len(decoys))
    if len(decoys) < a.n:
        print(f"[warn] only {len(decoys)} decoys; relax overlap threshold if needed")

    with open(a.out, "w") as f:
        for i, s in enumerate(decoys):
            f.write(f">DECOY_{i:05d}|decoy\n{s}\n")
    with open(a.out.replace(".fasta", "_meta.tsv"), "w") as f:
        f.write("protein_id\tclass\tsplit\tlength\n")
        for i, s in enumerate(decoys):
            r = random.random(); sp = "train" if r < 0.70 else ("val" if r < 0.85 else "test")
            f.write(f"DECOY_{i:05d}\tdecoy\t{sp}\t{len(s)}\n")
    print("saved", a.out)

if __name__ == "__main__":
    main()
