#!/usr/bin/env python3
"""
D1 · Extract non-cyclic protein language-model embeddings.
Supports ESM-2 (facebook/esm2_t33_650M_UR50D) and ProtT5 (Rostlab/prot_t5_xl_uniref50).
Mean-pools residue representations; long sequences are chunked and averaged.

Usage:
  python embed_plm.py --fasta data/sequences.fasta --model esm2 --out emb_esm2.npz
  python embed_plm.py --fasta data/sequences.fasta --model prott5 --out emb_prott5.npz
Output: .npz with 'ids' (array of str), 'emb' (float32 [N,D]).
"""
import argparse, re, numpy as np, torch
from transformers import AutoTokenizer, AutoModel, T5EncoderModel

MODELS = {
    "esm2":    "facebook/esm2_t33_650M_UR50D",
    "prott5":  "Rostlab/prot_t5_xl_uniref50",          # fp32, ~11.3 GB
    "prott5h": "Rostlab/prot_t5_xl_half_uniref50-enc", # fp16, ~5.6 GB (磁盘紧张时用)
}

def read_fa(path):
    ids, seqs, cur, buf = [], [], None, []
    for line in open(path):
        line = line.rstrip()
        if line.startswith(">"):
            if cur: ids.append(cur); seqs.append("".join(buf))
            cur = line[1:].split()[0].split("|")[0]; buf = []
        elif line:
            buf.append(line)
    if cur: ids.append(cur); seqs.append("".join(buf))
    return ids, seqs

def chunk(seq, L):
    if len(seq) <= L: return [seq]
    return [seq[i:i+L] for i in range(0, len(seq), L)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fasta", required=True)
    ap.add_argument("--model", choices=list(MODELS), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--maxlen", type=int, default=1022, help="residues per chunk")
    ap.add_argument("--bs", type=int, default=8)
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    name = MODELS[a.model]
    print(f"[{a.model}] {name}  device={dev}")
    tok = AutoTokenizer.from_pretrained(name)
    if a.model in ("prott5", "prott5h"):
        mdl = T5EncoderModel.from_pretrained(name).to(dev).eval()
    else:
        mdl = AutoModel.from_pretrained(name).to(dev).eval()
    ids, seqs = read_fa(a.fasta)
    print(f"sequences: {len(ids)}")
    embs = [None] * len(ids)
    for i, s in enumerate(seqs):
        s = re.sub(r"[UZOB]", "X", s.upper())
        parts = chunk(s, a.maxlen)
        if a.model == "prott5":
            parts = [" ".join(list(p)) for p in parts]
        vecs = []
        for p in parts:
            with torch.no_grad():
                enc = tok(p, return_tensors="pt", truncation=True, max_length=a.maxlen + 8).to(dev)
                out = mdl(**enc).last_hidden_state[0]              # [L, D]
                mask = enc["attention_mask"][0].bool()
                v = out[mask].mean(0).float().cpu().numpy()
            vecs.append(v)
        embs[i] = np.mean(vecs, axis=0)
        if (i + 1) % 100 == 0: print(f"  {i+1}/{len(ids)}", flush=True)
    E = np.vstack(embs).astype("float32")
    np.savez_compressed(a.out, ids=np.array(ids), emb=E)
    print("saved", a.out, E.shape)

if __name__ == "__main__":
    main()
