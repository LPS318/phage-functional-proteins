#!/usr/bin/env bash
###############################################################################
# D6-A · Foldseek 全库新颖性检索（target = AFDB50）
# 522 条“家族未定/代表”结构对 AFDB50 做 3Di+AA 检索，判新折叠/新家族。
# 依赖 foldseek（conda bioconda）；磁盘建议 /mnt/data（OSS）。
# 用法：DB=/mnt/data/afdb50 QB=/mnt/workspace/d6/query_pdb bash run_d6_foldseek_full.sh
###############################################################################
set -u
WORK=${WORK:-/mnt/workspace/d6}
OUT=$WORK/foldseek_full
DBDIR=${DB:-/mnt/data/afdb50}
TMP=$WORK/tmp_fs
QB=${QB:-$WORK/query_pdb}
mkdir -p "$OUT" "$DBDIR" "$TMP"
source /root/miniforge3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate foldseek 2>/dev/null || conda activate base
which foldseek >/dev/null 2>&1 || conda install -c bioconda -c conda-forge -y foldseek 2>&1 | tail -3
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-16}

echo "== 1) 下载/定位 AFDB50（约 100-300GB，放到 $DBDIR）=="
if [ -z "$(ls "$DBDIR"/*.dbtype 2>/dev/null)" ]; then
  foldseek databases "AlphaFold/UniProt50" "$DBDIR" "$TMP" 2>&1 | tail -6
  if [ -z "$(ls "$DBDIR"/*.dbtype 2>/dev/null)" ]; then
    echo "[warn] AFDB50 下载失败（常见于 download.foldseek.com DNS 不通）；改试 PDB 兜底"
    foldseek databases "PDB" "$DBDIR" "$TMP" 2>&1 | tail -6
  fi
fi
TGT=$(ls "$DBDIR"/*.dbtype 2>/dev/null | head -1 | sed 's/\.dbtype$//')
[ -n "$TGT" ] || { echo "[FATAL] 目标库未就绪（AFDB50/PDB 都没下成）"; exit 1; }
echo "目标库 = $TGT"

echo "== 2) 建查询库（522 条）=="
foldseek createdb "$QB" "$OUT/qdb" --threads "$OMP_NUM_THREADS"

echo "== 3) 检索 3Di+AA =="
foldseek search "$OUT/qdb" "$TGT" "$OUT/result.m8" -e 1e-3 --threads "$OMP_NUM_THREADS" --format-output query,target,alntmscore,prob,bits,seqid,evalue

echo "== 4) 解析新颖性 =="
python3 parse_foldseek_novelty.py "$OUT/result.m8" "$WORK/foldseek_full_novelty.tsv"
echo "完成 -> $OUT/result.m8 与 $WORK/foldseek_full_novelty.tsv"
