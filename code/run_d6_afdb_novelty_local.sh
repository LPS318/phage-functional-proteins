#!/usr/bin/env bash
###############################################################################
# D6 · 全库序列新颖性（本地，用 Elements 上的 AFDB DIAMOND 库）
# 522 条查询 vs 完整 AFDB（chunk_00..14.dmnd）→ 每条查询的最佳非自身命中与同源数
# 依赖：diamond（conda install -c conda-forge -c bioconda diamond）
# 用法：bash run_d6_afdb_novelty_local.sh
###############################################################################
set -u
AFDB=${AFDB:-/Volumes/Elements/AFDB}
Q=${Q:-/mnt/workspace/d6/query.fasta}          # 522 条查询序列（若无则用 /tmp/d6_queries.fasta）
[ -s "$Q" ] || Q=/tmp/d6_queries.fasta
OUT=${OUT:-/Users/zhangwei/Documents/Codex/2026-08-30/ni-h/work/d6_full}
mkdir -p "$OUT"
THREADS=${THREADS:-8}
which diamond >/dev/null 2>&1 || { echo "[FATAL] 未装 diamond：conda install -c conda-forge -c bioconda -y diamond"; exit 1; }
echo "diamond: $(diamond --version 2>&1 | head -1)  queries: $Q  AFDB: $AFDB"

echo "== 逐 chunk DIAMOND blastp =="
TMPDB=${TMPDB:-/tmp/d6_chunk.dmnd}   # 拷到内盘再搜（外置盘随机读太慢）
for d in "$AFDB"/chunk_*.dmnd; do
  b=$(basename "$d" .dmnd)
  [ -s "$OUT/$b.m8" ] && { echo "skip $b"; continue; }
  echo "-- $b (copy to SSD)"
  cp "$d" "$TMPDB"
  diamond blastp --query "$Q" --db "$TMPDB" --out "$OUT/$b.m8" \
    --outfmt 6 qseqid sseqid pident length evalue bitscore qlen slen \
    --evalue 1e-3 --max-target-seqs 50 --threads "$THREADS" --fast 2>&1 | tail -2
done
cat "$OUT"/chunk_*.m8 > "$OUT/d6_afdb_all.m8"
echo "== 汇总 =="
python3 - "$OUT/d6_afdb_all.m8" "$OUT/d6_afdb_novelty.tsv" "$Q" <<'PY'
import sys, csv
from collections import defaultdict
m8, out, qfa = sys.argv[1], sys.argv[2], sys.argv[3]
qlen={}
cur=None;n=0
for line in open(qfa):
    if line.startswith('>'):
        if cur: qlen[cur]=n
        cur=line[1:].split()[0]; n=0
    else: n+=len(line.strip())
if cur: qlen[cur]=n
hits=defaultdict(list)
for line in open(m8):
    p=line.rstrip().split('\t')
    if len(p)<9: continue
    q,t,pid,ln,ev,bs,ql,sl=p[0],p[1],float(p[2]),int(p[3]),float(p[4]),float(p[5]),int(p[6]),int(p[7])
    hits[q].append((bs,pid,ln,ev,t,ql,sl))
rows=[]
for q in sorted(set(list(qlen)+list(hits))):
    hs=sorted(hits.get(q,[]),reverse=True)
    ql=qlen.get(q,0)
    # self-like hits: identity>=95 and coverage>=0.95
    nonself=[h for h in hs if not (h[1]>=95 and h[2]>=0.95*(ql or h[2]))]
    best=hs[0] if hs else None
    bn=nonself[0] if nonself else None
    n_hom=sum(1 for h in nonself if h[1]>=30 and h[2]>=0.5*max(ql,1))
    rows.append((q, len(hs), (bn[4] if bn else 'NONE'), round(bn[1],1) if bn else 0.0,
                 round(100*bn[2]/max(ql,1),0) if bn else 0.0, round(bn[5],1) if bn else 0.0,
                 n_hom, n_hom==0))
with open(out,'w',newline='') as f:
    w=csv.writer(f,delimiter='\t')
    w.writerow(['query','n_hits','best_nonself_target','best_nonself_pident','best_nonself_cov%','bits','n_homologs(>=30%id,>=50%cov)','novel'])
    w.writerows(rows)
nn=sum(1 for r in rows if r[-1])
print(f"queries={len(rows)}  novel(无同源)={nn} -> {out}")
PY
echo "完成 -> $OUT/d6_afdb_novelty.tsv"
