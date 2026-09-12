#!/usr/bin/env bash
###############################################################################
# D6-B · dbCAN（CAZyme 官方注释）——在能联网的阿里云节点运行
# 本机 DNS 解析不了 pro.unl.edu，故下载/运行放节点。
# 依赖：conda（bioconda: dbcan, hmmer, diamond）
# 用法：bash run_d6_dbcan.sh   （需 query.fasta 在同目录）
###############################################################################
set -u
WORK=${WORK:-/mnt/workspace/d6}
OUT=$WORK/dbcan
DB=${DB:-/mnt/workspace/dbCAN_db}   # 放在工作区（phage-D6 系统盘 350GB，足够）
Q=${Q:-$WORK/query.fasta}
mkdir -p "$OUT" "$DB"
source /root/miniforge3/etc/profile.d/conda.sh 2>/dev/null || true
conda create -n dbcan python=3.11 -y 2>/dev/null || true
conda activate dbcan 2>/dev/null || conda activate base
which run_dbcan >/dev/null 2>&1 || conda install -c conda-forge -c bioconda -y dbcan hmmer diamond 2>&1 | tail -3
echo "run_dbcan: $(run_dbcan version 2>&1 | head -1)"

echo "== 1) 下载 dbCAN 库到 $DB =="
if [ ! -f "$DB/CAZy.dmnd" ] && [ ! -f "$DB/dbCAN.hmm" ]; then
  run_dbcan database --db_dir "$DB" 2>&1 | tail -8 || echo "[warn] 下载失败（DNS?）"
fi
ls "$DB" | head

echo "== 2) CAZyme 注释（protein 模式）=="
run_dbcan CAZyme_annotation --mode protein --input_raw_data "$Q" --db_dir "$DB" \
  --output_dir "$OUT" --methods diamond,hmm --threads 16 2>&1 | tail -8

echo "== 3) 汇总 =="
find "$OUT" -maxdepth 1 -type f | head -20
tar -czf "$WORK/d6_dbcan_results.tar.gz" -C "$WORK" dbcan 2>/dev/null
echo "完成 -> $WORK/d6_dbcan_results.tar.gz"
