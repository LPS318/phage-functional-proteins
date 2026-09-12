#!/usr/bin/env bash
###############################################################################
# D6-B 补下载：dbCAN 大库（CAZy.dmnd ~2.1GB、dbCAN-sub.hmm ~4.9GB 等）
# 支持断点续传；在能联网的节点（phage-D6）运行。
# 用法：bash download_dbcan_large.sh
###############################################################################
set -u
DB=${DB:-/mnt/workspace/dbCAN_db}
BASE="https://pro.unl.edu/dbCAN2/download_file.php?file=run_dbCAN_database_total/db_current"
mkdir -p "$DB"
source /root/miniforge3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate dbcan 2>/dev/null || conda activate base

echo "== 0) 当前库内容 =="
ls -lh "$DB" 2>/dev/null | head -30

echo "== 1) run_dbcan database（自带续传，先试一次）=="
run_dbcan database --db_dir "$DB" 2>&1 | tail -10 || true

echo "== 2) curl 断点续传兜底（补齐缺失/不完整的大文件）=="
for f in CAZy.dmnd dbCAN-sub.hmm dbCAN.hmm TCDB.dmnd TF.hmm STP.hmm \
         dbCAN-PUL.faa dbCAN-PUL.tar.gz fam-substrate-mapping.tsv \
         peptidase.dmnd sulfatlas_db.dmnd CAZyDB.07292021.fa; do
  if [ ! -s "$DB/$f" ]; then
    echo "-- 续传 $f"
    curl -L -C - --retry 20 --retry-delay 5 --retry-all-errors \
         -o "$DB/$f" "$BASE/$f" \
      || echo "[warn] $f 下载失败（可再跑一次本脚本续传）"
  else
    echo "  已有 $f ($(du -h "$DB/$f" | cut -f1))"
  fi
done

echo "== 3) 再跑一次 run_dbcan database（校验/解压/补全）=="
run_dbcan database --db_dir "$DB" 2>&1 | tail -8 || true

echo "== 4) 最终库内容 =="
ls -lh "$DB" 2>/dev/null
echo "完成。若 CAZy.dmnd 与 dbCAN-sub.hmm 已完整（~2.1GB / ~4.9GB），即可重跑 run_d6_dbcan.sh 得到含 DIAMOND 与亚家族的结果。"
