#!/usr/bin/env python3
"""
D4 收尾 · 基于 Class 1B 五酶真实 MSA 的逐残基保守性（ConSurf-style grade 1-9）。
输入：CClass1B_x_aln.faa（5 酶已比对）+ 各酶 chain-A PDB。
输出：<酶>_consurf.pdb（B-factor = 保守性 grade 1-9，供 PyMOL spectrum 着色）。
说明：家族仅 5 个成员，同源受限；保守性以该 MSA 计算，论文需注明。
用法：python3 make_conservation.py
"""
import os, math, glob
from collections import defaultdict

AA = set("ACDEFGHIKLMNPQRSTVWY")

def read_aln(path):
    aln = {}; cur = None; seq = []
    for line in open(path):
        line = line.strip()
        if line.startswith(">"):
            if cur: aln[cur] = "".join(seq)
            cur = line[1:].strip(); seq = []
        elif line:
            seq.append(line)
    if cur: aln[cur] = "".join(seq)
    return aln

def grade_from_entropy(counts, n):
    """Shannon entropy -> conservation score 0..1 -> grade 1..9 (9=most conserved)."""
    if n == 0: return 5.0
    H = 0.0
    for c in counts:
        if c > 0:
            p = c / n
            H -= p * math.log2(p)
    Hmax = math.log2(len([c for c in counts if c > 0])) if sum(1 for c in counts if c > 0) > 1 else 1.0
    Hmax = max(Hmax, 1e-6)
    score = max(0.0, 1.0 - H / Hmax)   # 0=variable, 1=conserved
    return 1.0 + 8.0 * score            # grade 1..9

LOOP = "ACDEFGHIKLMNPQRSTVWY"
def main():
    aln = read_aln("work/d4_result/consurf_msa/CClass1B_x_aln.faa")
    names = list(aln.keys())
    nseq = len(names)
    # per-column residue counts across all seqs (ignore gaps)
    cols = len(next(iter(aln.values())))
    col_counts = [defaultdict(int) for _ in range(cols)]
    for s in aln.values():
        for j, ch in enumerate(s):
            if ch in AA:
                col_counts[j][ch] += 1
    os.makedirs("outputs/consurf_msa_grade", exist_ok=True)
    pdb_dir = "outputs/d4_consurf_submit/pdb"
    for name in names:
        pdb = os.path.join(pdb_dir, name + "_chainA.pdb")
        if not os.path.exists(pdb):
            print("[skip] no pdb", name); continue
        seq = aln[name]
        resi = 0
        grade_by_resi = {}
        for j, ch in enumerate(seq):
            if ch == "-":
                continue
            resi += 1
            g = grade_from_entropy(col_counts[j].values(), nseq)
            grade_by_resi[resi] = g
        # write B-factor PDB
        out = f"outputs/consurf_msa_grade/{name}_consurf.pdb"
        with open(pdb) as f:
            lines = f.read().splitlines()
        out_lines = []
        for line in lines:
            if line.startswith(("ATOM", "HETATM")):
                r = int(line[22:26])
                b = grade_by_resi.get(r, 5.0)
                line = line[:60] + f"{b:6.2f}" + line[66:]
            out_lines.append(line)
        with open(out, "w") as f:
            f.write("\n".join(out_lines) + "\n")
        gv = list(grade_by_resi.values())
        print(f"{name:12s} resi={len(gv)} mean_grade={sum(gv)/len(gv):.2f} min={min(gv):.1f} max={max(gv):.1f} -> {out}")

if __name__ == "__main__":
    main()
