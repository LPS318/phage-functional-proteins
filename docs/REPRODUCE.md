# Reproduction guide

Everything is runnable from this repository. Steps are grouped by the work
packages used in the manuscript (D1/D4/D5/D6). Compute: a CPU machine for L0/D5
and a single **A100** node for D1/PLM embeddings and structure prediction.

---

## D1 — Sequence-level AI prediction (ESM-2 / ProtT5) + frozen-set evaluation

Data: `data/frozen_splits.tsv` (cluster-disjoint), `data/frozen_benchmark_labels.tsv`.

```bash
# ~ the released candidate sequences are in data/candidates_v2.0.csv (protein_id column);
# build per-task FASTAs from your sequence source, then:
python code/embed_plm.py --fasta seqs.fasta --model esm2   --out emb_esm2.npz  --bs 8   # or prott5
python code/train_eval.py --emb emb_esm2.npz --meta meta.tsv --fasta seqs.fasta --out out_esm2
```

- `code/run_d1_a100.sh` — 3-family classification (depolymerase/lysin/holin).
- `code/run_d1_binary.sh` — antibacterial vs. background decoy; uses the official
  frozen decoys (`data/` of the D1 package) or `code/make_decoys.py` (UniProt
  host/related background) as a fallback.
- Metrics written to `out_*/metrics.json` (accuracy, macro-F1, AUC-OVR, and
  `binary_vs_decoy` AUROC/AUPRC). Published numbers: see `results/d1/metrics_*.json`.

Notes: models download from HuggingFace on first run (ESM-2 ≈2.5 GB, ProtT5-XL
≈11.3 GB). Set `HF_HOME` to a disk with space. The split is **cluster-disjoint**
(no cluster spans train/test).

---

## D4 — Strict APBS electrostatics & conservation

```bash
# strict APBS: PDB2PQR(AMBER/PROPKA) -> APBS(LPBE, mg-manual auto-enclosing grid)
bash code/run_d4_strict.sh /path/to/structures
python code/gen_apbs_in.py in.pqr out.in out_prefix 1.5     # (used inside the script)
python code/render_apbs_strict.py --pqr <pqr_dir> --dx <dx_dir> --out figs_apbs

# conservation from an enriched MSA (37 seqs) -> per-residue grade -> PDB B-factor
python code/make_conservation.py
python code/render_conservation.py --pdb <graded_pdb_dir> --out figs_consurf
```

Dependencies: `pdb2pqr`, `apbs`, `propka` (conda-forge); `mafft` (bioconda) for
MSA; PyMOL for rendering. Grid parameters for elongated β-helix depolymerases
(160–260 Å) are auto-sized per axis so the whole molecule is enclosed.

---

## D5 — Host / serotype linking

```bash
bash code/run_d5.sh          # Kaptive (A. baumannii K/OC loci) + PAst/PAST (P. aeruginosa O)
```

Output: `results/d5/serotype.tsv`. Requires `kaptive`, `pasty`/PAST, and NCBI
`datasets` (downloads genomes at run time).

---

## D6 — Full-library novelty (AlphaFold DB) + dbCAN CAZyme annotation

### D6-A · Sequence novelty vs. the entire AlphaFold DB

```bash
# build DIAMOND DBs from the AFDB FASTA (split into ~8 GB chunks), then:
AFDB=/path/to/AFDB Q=query.fasta bash code/run_d6_afdb_novelty_local.sh
```

Rule for "novel": **no non-self hit with ≥30% identity over ≥50% of the query**.
The script copies each DB chunk to local SSD before searching (external-drive
random reads dominate otherwise). Output: `d6_afdb_novelty.tsv`.

### D6-B · dbCAN CAZyme annotation

```bash
bash code/run_d6_dbcan.sh               # on a networked node (downloads dbCAN DB)
bash code/download_dbcan_large.sh       # resume CAZy.dmnd / dbCAN-sub.hmm if interrupted
```

Uses `run_dbcan CAZyme_annotation --methods diamond,hmm` (dbCAN-sub is optional
and only affects substrate prediction). Output: `overview.tsv` with per-query
HMM/DIAMOND/consensus CAZy assignments.

---

## L0 — Evaluation scaffold

```bash
python code/benchmark_metrics.py data/frozen_benchmark_labels.tsv your_scores.tsv
# -> top-k precision/recall, AUC-ROC, AUPR
```

---

## Environment summary

| Component | Tool |
|---|---|
| PLM embeddings | `torch`, `transformers`, `sentencepiece` |
| Heads / metrics | `scikit-learn`, `numpy`, `matplotlib` |
| Structure/electrostatics | `pdb2pqr`, `apbs`, `propka`, PyMOL |
| Sequence search | `diamond`, `mmseqs2` (optional) |
| MSA | `mafft` |
| CAZyme | `dbcan` (run_dbcan), `hmmer` |
| Serotyping | `kaptive`, `pasty`/PAST, `ncbi-datasets-cli` |
| Web app | `fastapi`, `uvicorn` |

Third-party databases are **not** redistributed; download them with the scripts
and commands above (all support resume).
