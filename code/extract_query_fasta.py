#!/usr/bin/env python3
"""Extract protein sequences (from CA atoms) of query PDBs -> query.fasta (for dbCAN)."""
import sys, os, glob
AA3 = {'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C','GLN':'Q','GLU':'E','GLY':'G',
       'HIS':'H','ILE':'I','LEU':'L','LYS':'K','MET':'M','PHE':'F','PRO':'P','SER':'S',
       'THR':'T','TRP':'W','TYR':'Y','VAL':'V','SEC':'U','PYL':'O'}
def seq_from_pdb(p):
    res = {}
    for line in open(p, errors="ignore"):
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            try: res[int(line[22:26])] = AA3.get(line[17:20].strip(), "X")
            except ValueError: pass
    return "".join(res[k] for k in sorted(res))
def main():
    d, out = sys.argv[1], sys.argv[2]
    n = 0
    with open(out, "w") as f:
        for p in sorted(glob.glob(os.path.join(d, "*.pdb"))):
            s = seq_from_pdb(p)
            if len(s) >= 30:
                f.write(f">{os.path.basename(p)[:-4]}\n{s}\n"); n += 1
    print(f"wrote {n} sequences -> {out}")
if __name__ == "__main__":
    main()
