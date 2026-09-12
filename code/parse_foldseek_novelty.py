#!/usr/bin/env python3
"""Parse Foldseek .m8 -> per-query best hit + novelty flag (novel if no hit or prob<0.5)."""
import sys, csv
from collections import defaultdict
def main():
    m8, out = sys.argv[1], sys.argv[2]
    best = defaultdict(lambda: (None, 0.0, 0.0, 0.0))
    for line in open(m8):
        p = line.rstrip().split("\t")
        if len(p) < 7:
            continue
        q, t, tm, prob, bits, seqid, ev = p[0], p[1], float(p[2]), float(p[3]), float(p[4]), float(p[5]), float(p[6])
        if best[q][1] < prob:
            best[q] = (t, prob, bits, seqid)
    rows = []
    for q, (t, prob, bits, seqid) in sorted(best.items()):
        rows.append((q, t or "NONE", round(prob, 3), bits, round(seqid, 2), (t is None) or prob < 0.5))
    with open(out, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["query", "target", "best_prob", "bits", "seqid", "novel"])
        w.writerows(rows)
    n = sum(1 for r in rows if r[-1])
    print(f"queries={len(rows)}  novel(prob<0.5 or no hit)={n} -> {out}")
if __name__ == "__main__":
    main()
