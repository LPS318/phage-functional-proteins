#!/usr/bin/env python3
"""
D1 · Frozen-split evaluation of PLM embeddings vs a k-mer baseline.
Trains a linear probe (LogisticRegression) and an MLP head on ESM-2/ProtT5
embeddings; compares to an amino-acid/k-mer baseline on the SAME frozen split.

Usage:
  python train_eval.py --emb emb_esm2.npz --meta data/meta.tsv --out out_esm2
Outputs: metrics.json, scores.tsv, per_class.tsv, Fig_D1_<tag>.png
"""
import argparse, json, os, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score,
                             confusion_matrix, classification_report)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def read_meta(path):
    import csv
    m = {}
    for r in csv.DictReader(open(path), delimiter="\t"):
        m[r["protein_id"]] = (r["class"], r["split"])
    return m

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--fasta", default="data/sequences.fasta")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    d = np.load(a.emb, allow_pickle=True)
    ids = [str(x) for x in d["ids"]]; E = d["emb"]
    meta = read_meta(a.meta)
    keep = [i for i, x in enumerate(ids) if x in meta]
    ids = [ids[i] for i in keep]; E = E[keep]
    y = np.array([meta[i][0] for i in ids])
    sp = np.array([meta[i][1] for i in ids])
    classes = sorted(set(str(v) for v in y))
    print("classes:", classes, "n=", len(ids))
    print("split counts:", {s: int((sp == s).sum()) for s in set(sp)})

    # leakage check
    tr_ids = set(i for i, s in zip(ids, sp) if s == "train")
    te_ids = set(i for i, s in zip(ids, sp) if s == "test")
    leak = len(tr_ids & te_ids)

    tr = sp == "train"; va = sp == "val"; te = sp == "test"
    scaler = StandardScaler().fit(E[tr])
    Xtr, Xva, Xte = scaler.transform(E[tr]), scaler.transform(E[va]), scaler.transform(E[te])

    results = {}
    # 1) linear probe
    clf = LogisticRegression(max_iter=3000, C=1.0, n_jobs=-1, class_weight="balanced").fit(Xtr, y[tr])
    results["linear_probe"] = clf
    # 2) MLP head
    mlp = MLPClassifier(hidden_layer_sizes=(512, 128), max_iter=600,
                        early_stopping=True, random_state=0).fit(Xtr, y[tr])
    results["mlp"] = mlp

    summary = {"n_total": len(ids), "classes": classes, "leak_train_test_ids": leak}
    for tag, model in results.items():
        pv = model.predict(Xva); pt = model.predict(Xte)
        summary[tag] = {
            "val_acc": float(accuracy_score(y[va], pv)),
            "val_macro_f1": float(f1_score(y[va], pv, average="macro")),
            "test_acc": float(accuracy_score(y[te], pt)),
            "test_macro_f1": float(f1_score(y[te], pt, average="macro")),
        }
        try:
            pr = model.predict_proba(Xte)
            summary[tag]["test_auc_ovr"] = float(roc_auc_score(y[te], pr, multi_class="ovr", average="macro"))
        except Exception as e:
            summary[tag]["test_auc_ovr"] = None

    # 3) baseline: k-mer composition + logistic regression
    def seqs_map():
        m = {}
        cur = None; buf = []
        for line in open(a.fasta):
            line = line.rstrip()
            if line.startswith(">"):
                if cur: m[cur] = "".join(buf)
                cur = line[1:].split()[0].split("|")[0]; buf = []
            elif line: buf.append(line)
        if cur: m[cur] = "".join(buf)
        return m
    sm = seqs_map()
    k = 3
    from collections import Counter
    aas = "ACDEFGHIKLMNPQRSTVWY"
    def kvec(s):
        c = Counter(s[i:i+k] for i in range(len(s)-k+1)); t = sum(c.values()) or 1
        return [c.get(aas[i]+aas[j], 0)/t for i in range(len(aas)) for j in range(len(aas))]
    Xk = np.array([kvec(sm.get(i, "")) for i in ids])
    sk = StandardScaler().fit(Xk[tr])
    kb = LogisticRegression(max_iter=3000, n_jobs=-1).fit(sk.transform(Xk[tr]), y[tr])
    pt = kb.predict(sk.transform(Xk[te]))
    summary["kmer_baseline"] = {
        "test_acc": float(accuracy_score(y[te], pt)),
        "test_macro_f1": float(f1_score(y[te], pt, average="macro")),
    }

    # 4) binary: antibacterial (depolymerase/lysin/holin) vs decoy
    if "decoy" in classes:
        from sklearn.metrics import roc_auc_score as _auc, average_precision_score as _ap
        yb = (y != "decoy").astype(int)
        clfb = LogisticRegression(max_iter=3000, n_jobs=-1, class_weight="balanced").fit(Xtr, yb[tr])
        pb = clfb.predict_proba(Xte)[:, 1]
        summary["binary_vs_decoy"] = {
            "test_auroc": float(_auc(yb[te], pb)),
            "test_auprc": float(_ap(yb[te], pb)),
        }
        with open(os.path.join(a.out, "binary_scores.tsv"), "w") as f:
            f.write("protein_id\tscore\n")
            te_idx = np.where(te)[0]
            for j, sc in zip(te_idx, pb):
                f.write(f"{ids[j]}\t{sc:.4f}\n")

    # scores + per-class report
    best = max(["linear_probe", "mlp"], key=lambda k: summary[k]["val_macro_f1"])
    pr = results[best].predict_proba(Xte)
    with open(os.path.join(a.out, "scores.tsv"), "w") as f:
        f.write("protein_id\t" + "\t".join(f"p_{c}" for c in classes) + "\n")
        for i, row in zip([ids[j] for j in np.where(te)[0]], pr):
            f.write(i + "\t" + "\t".join(f"{v:.4f}" for v in row) + "\n")
    rep = classification_report(y[te], results[best].predict(Xte), target_names=classes, output_dict=True)
    json.dump({"summary": summary, "per_class": rep}, open(os.path.join(a.out, "metrics.json"), "w"), indent=2)
    with open(os.path.join(a.out, "per_class.tsv"), "w") as f:
        f.write("class\tprecision\trecall\tf1\tsupport\n")
        for c in classes:
            r = rep[c]; f.write(f"{c}\t{r['precision']:.3f}\t{r['recall']:.3f}\t{r['f1-score']:.3f}\t{int(r['support'])}\n")

    # figure
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    cm = confusion_matrix(y[te], results[best].predict(Xte), labels=classes)
    im = ax[0].imshow(cm, cmap="Blues")
    ax[0].set_xticks(range(len(classes))); ax[0].set_xticklabels(classes, rotation=30, ha="right")
    ax[0].set_yticks(range(len(classes))); ax[0].set_yticklabels(classes)
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax[0].text(j, i, cm[i, j], ha="center", va="center",
                       color="white" if cm[i, j] > cm.max()/2 else "black")
    ax[0].set_title(f"Confusion matrix ({best}, test)"); ax[0].set_xlabel("predicted"); ax[0].set_ylabel("true")
    keys = ["kmer_baseline", "linear_probe", "mlp"]
    vals = [summary[k]["test_macro_f1"] for k in keys]
    ax[1].bar(keys, vals, color=["#999999", "#4C72B0", "#DD8452"])
    ax[1].set_ylim(0, 1); ax[1].set_ylabel("test macro-F1")
    ax[1].set_title("Method comparison (frozen test)")
    for i, v in enumerate(vals): ax[1].text(i, v+0.01, f"{v:.3f}", ha="center")
    fig.tight_layout()
    tag = os.path.basename(a.emb).replace("emb_", "").replace(".npz", "")
    fig.savefig(os.path.join(a.out, f"Fig_D1_{tag}.png"), dpi=300, facecolor="white")
    print(json.dumps(summary, indent=1))

if __name__ == "__main__":
    main()
