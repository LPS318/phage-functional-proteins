# Methods (concise)

## Candidate discovery
36,025 phage genomes → QC (28,932) → 1,258,230 proteins → 576,176 clusters →
**4,117 candidate antibacterial proteins** (depolymerases, endolysins, holins).
Candidates carry functional-annotation evidence (InterPro/Pfam/CDD/CAZy layer),
structural evidence (AFDB strong homology, pLDDT, pocket/charge features),
host/genome classification, in-silico substrate inference, and a six-dimension
weighted score (functional evidence, structural confidence, structural
evidence, substrate prediction, novelty, translational value).

## D1 · Non-cyclic protein-language-model prediction
- Embeddings: **ESM-2 (650M)** and **ProtT5-XL**; residue representations
  mean-pooled (long sequences chunked at 1022 aa and averaged).
- Heads: linear probe (logistic regression, balanced) and MLP; frozen split
  (train/val/test) with test never used for training or tuning.
- Split is **cluster-disjoint** (verified: 0 clusters span train/test).
- Tasks: (i) three-family classification; (ii) antibacterial vs. background
  decoy (the official frozen decoys, 20,409 sequences).
- Baselines: 3-mer composition + logistic regression.

## D2 · Frozen benchmark scaffold
87 gold positives (DposFinder/PhageDPO-level evidence) + 1,500 decoys;
`benchmark_metrics.py` reports top-k precision/recall, AUC-ROC, AUPR.

## D4 · Structural strictification
- **Electrostatics**: PDB2PQR (AMBER, pH 7.0 via PROPKA) → APBS LPBE
  (sdh boundary, smol surface, spl2 charges, pdie 2.0 / sdie 78.5, 298.15 K,
  0.15 M 1:1 ions). For elongated β-helix depolymerases (160–260 Å long axis)
  the fine grid is sized per axis to fully enclose the molecule
  (`mg-manual`, spacing 1.5 Å); potentials mapped onto the molecular surface
  (red = negative, blue = positive, ±10 kT/e).
- **Conservation**: family MSA enriched from the candidate pool (5 → 37
  sequences, MAFFT), per-column Shannon entropy normalised to a grade
  (1 = variable, 9 = conserved), written to PDB B-factors and rendered.
- **Structural comparison**: US-align (TM-score/RMSD) across OOM candidates and
  known representatives.

## D5 · Host / serotype
- *A. baumannii* K/OC loci: **Kaptive** (7 genomes).
- *P. aeruginosa* O-antigen: **PAst/PAST** (6 genomes).

## D6 · Full-library novelty and CAZyme annotation
- **Sequence novelty**: 522 queries (454 "family-undetermined" + 33 ultra-long
  OOM + 35 representatives) searched against the **entire AlphaFold DB**
  (~200 M sequences) with **DIAMOND** (fast mode; per-chunk search from local
  SSD). Novel = no non-self hit ≥30% identity over ≥50% of the query.
  Caveat: AFDB is UniProt-derived and under-represents phage proteins, so
  "no hit" is a conservative upper bound on novelty.
- **CAZyme annotation**: **dbCAN** (`CAZyme_annotation --methods diamond,hmm`)
  gives per-query CAZy families; a "consensus" call requires both HMM and
  DIAMOND support (dbCAN "Recommend Results"), otherwise the call is
  DIAMOND-similarity-only. dbCAN-sub (substrate prediction) is optional and does
  not affect family assignment.

## Reproducibility notes
- Frozen splits and the benchmark are fixed and versioned; all evaluations use
  them unchanged.
- Model heads are selected on the validation split; the test split is used only
  for final reporting.
- Third-party databases are downloaded (with resume) rather than redistributed.
- All predictions are in-silico and require wet-lab validation; substrate
  assignments and catalytic residues are inferred.
