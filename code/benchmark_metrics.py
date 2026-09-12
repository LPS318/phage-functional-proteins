#!/usr/bin/env python3
# 冻结基准集评测指标（D2）
import csv, numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, precision_recall_curve
def load_labels(path):
    rows=list(csv.DictReader(open(path),delimiter='\t'))
    y=[int(r['gold']) for r in rows]; ids=[r['protein_id'] for r in rows]
    return ids, np.array(y)
def load_scores(path):
    # 输入：protein_id<TAB>score（越大越优先）
    s={}
    for r in csv.DictReader(open(path),delimiter='\t'):
        try: s[r['protein_id']]=float(r['score'])
        except Exception: pass
    return s
def evaluate(path_labels, path_scores, topk=(10,30,50,100)):
    ids,y=load_labels(path_labels); sc=load_scores(path_scores)
    scores=np.array([sc.get(i, -1e9) for i in ids]); order=np.argsort(-scores)
    y_rank=y[order]
    out={}
    for k in topk:
        tp=int(y_rank[:k].sum()); out[f'top{k}_precision']=tp/k if k else 0; out[f'top{k}_recall']=tp/max(1,y.sum())
    try: out['auc_roc']=roc_auc_score(y,scores)
    except Exception: out['auc_roc']=float('nan')
    try: out['aupr']=average_precision_score(y,scores)
    except Exception: out['aupr']=float('nan')
    return out
if __name__=='__main__':
    import sys, json
    print(json.dumps(evaluate(sys.argv[1],sys.argv[2]),indent=1))
