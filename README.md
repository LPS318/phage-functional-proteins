# Phage Functional Protein Discovery — Candidate Database v2.0
# 噬菌体功能蛋白 AI 发现 — 候选数据库 v2.0

A reproducible, prediction-level resource for **phage antibacterial proteins**
(depolymerases, endolysins/lysins, holins) discovered and ranked by an
AI-assisted pipeline, together with **sequence-level prediction models**,
**structural/electrostatic/conservation analyses**, **host–serotype** links and
**full-library novelty** evidence.

> All entries are *in silico* predictions; substrate assignments and catalytic
> residues are inferred and require wet-lab validation.

## Contents

| Directory | What |
|---|---|
| `data/` | Candidate database v2.0 (CSV + SQLite), frozen splits, D6 novelty & dbCAN tables |
| `results/` | D1 (PLM model metrics/figures), D4 (APBS + conservation), D5 (serotype), D6 (novelty + CAZyme) |
| `code/` | Reproducible scripts for D1/D4/D5/D6 + L0 evaluation scaffold |
| `figs/` | Manuscript figures |
| `web/` | Deployable FastAPI search app for the candidate database |
| `docs/` | Methods overview + reproduction guide |

## Data

- `data/candidates_v2.0.csv` / `.sqlite` — **4,117 candidates**
  (depolymerase / lysin / holin) with functional-annotation evidence,
  structural evidence (AFDB homology, pLDDT, pockets), host/genome
  classification, in-silico substrate inference, novelty/transferability, and
  six-dimension total score. SQLite table: `candidates`.
- `data/frozen_splits.tsv` — 24,702-protein **cluster-disjoint** frozen split
  (train 23,276 / val 330 / test 1,096) used for leakage-free evaluation.
- `data/frozen_benchmark_labels.tsv` — 87 gold positives + 1,500 decoys.
- `data/d6_afdb_novelty.tsv` — per-query best **non-self** hit vs. the full
  AlphaFold DB (DIAMOND).
- `data/dbcan/overview.tsv` — dbCAN CAZyme annotation (HMM + CAZy DIAMOND).

## Key results (v2.0)

- **Sequence-level prediction (D1)**: ESM-2 (650M) and ProtT5-XL, evaluated on
  the cluster-disjoint frozen split — 3-family classification macro-F1
  **0.996–0.997**; **antibacterial vs. background decoy AUROC 0.993 (ESM-2) /
  0.998 (ProtT5)**, AUPRC 0.973 / 0.994 (vs. 3-mer baseline 0.21). See
  `results/d1/`.
- **Structural strictification (D4)**: PDB2PQR(AMBER/PROPKA)+APBS(LPBE) strict
  electrostatic surfaces (grid auto-enclosing 160–260 Å β-helices) and
  enrichment-based (37-sequence MSA) conservation surfaces for the 5 Class-1B
  enzymes. See `results/d4/`.
- **Host / serotype (D5)**: Kaptive (A. baumannii, 7 genomes) + PAst
  (P. aeruginosa, 6 genomes). See `results/d5/serotype.tsv`.
- **Full-library novelty (D6)**: 522 queries vs. the **entire AlphaFold DB**
  (~200 M sequences) — 95.8% have a substantial homolog, only **0.6% are true
  singletons**; **dbCAN** assigns a CAZy family to 108/522 (20.7%, dominated by
  GH90), 179 more by DIAMOND similarity only, and 235 (45.0%) without any CAZy
  hit. Novelty is therefore framed at the **functional** level. See
  `results/d6/` and `figs/fig_d6_novelty.png`.

## Quick start

```bash
# 1) inspect the candidate database
sqlite3 data/candidates_v2.0.sqlite \
  "SELECT protein_id,category,host_raw,total_score FROM candidates
   ORDER BY CAST(total_score AS REAL) DESC LIMIT 20;"

# 2) run the search web app
cd web && pip install -r requirements.txt
CAND_DB=../data/candidates_v2.0.sqlite uvicorn app:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

## Reproduction

See [`docs/REPRODUCE.md`](docs/REPRODUCE.md) for the full pipeline
(L0 evaluation scaffold; D1 PLM models; D4 APBS/ConSurf; D5 serotyping;
D6 full-library novelty + dbCAN) and [`docs/METHODS.md`](docs/METHODS.md) for
method summaries. Compute used CPU + a single A100 node; large reference DBs
(AlphaFold DB, dbCAN) are documented with download/resume instructions.

## Citation

If you use this resource, please cite the Zenodo release (DOI in
[`CITATION.cff`](CITATION.cff) and on the release page) and the accompanying
manuscript.

## License

- **Data** (`data/`, `results/`, `figs/`): CC-BY-4.0
- **Code** (`code/`, `web/`): MIT

See [`LICENSE`](LICENSE).
