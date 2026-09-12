#!/usr/bin/env bash
###############################################################################
# D1-binary · 抗菌蛋白 vs 背景 decoy（默认用官方 frozen decoy）
# 可控项：MODELS="esm2"（省磁盘，推荐）/ "esm2 prott5"；HF_HOME=/大容量路径
# 用法：MODELS=esm2 bash run_d1_binary.sh
###############################################################################
set -u
WORK=${WORK:-/mnt/workspace/d1}
cd "$WORK" || { echo "[FATAL] 未找到 $WORK"; exit 1; }
MODELS=${MODELS:-"esm2 prott5"}
if [ -n "${HF_HOME:-}" ]; then export HF_HOME; export HF_HUB_CACHE="$HF_HOME/hub"; fi
echo "MODELS=$MODELS  HF_HOME=${HF_HOME:-默认}"
df -h "$WORK" | tail -1

source /root/miniforge3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate d1 2>/dev/null || conda activate base
pip install -q -U transformers sentencepiece tokenizers scikit-learn matplotlib numpy 2>&1 | tail -1

if [ -s data/decoys_frozen.fasta ]; then
  echo "== 使用官方 frozen decoy =="; DECOY_FA=data/decoys_frozen.fasta; DECOY_META=data/decoys_frozen_meta.tsv
else
  echo "== 未找到 frozen decoy，回退 UniProt 自建 =="; python make_decoys.py --pos data/sequences.fasta --n 4117 --seed 0 --out data/decoys.fasta
  DECOY_FA=data/decoys.fasta; DECOY_META=data/decoys_meta.tsv
fi
cat data/sequences.fasta "$DECOY_FA" > data/sequences_binary.fasta
cat data/meta.tsv > data/meta_binary.tsv; tail -n +2 "$DECOY_META" >> data/meta_binary.tsv
echo "总序列: $(grep -c '>' data/sequences_binary.fasta)  类别: $(awk -F'\t' 'NR>1{print $2}' data/meta_binary.tsv | sort | uniq -c | tr '\n' ' ')"

for m in $MODELS; do
  bs=8; case "$m" in prott5|prott5h) bs=4;; esac
  echo "== 嵌入: $m =="
  python embed_plm.py --fasta data/sequences_binary.fasta --model "$m" --out "emb_${m}_bin.npz" --bs "$bs" || { echo "[skip] $m 嵌入失败"; continue; }
  echo "== 训练+评测: $m =="
  python train_eval.py --emb "emb_${m}_bin.npz" --meta data/meta_binary.tsv --fasta data/sequences_binary.fasta --out "out_binary_${m}"
done

tar -czf /mnt/workspace/d1_binary_results.tar.gz out_binary_* 2>/dev/null
echo "完成 -> /mnt/workspace/d1_binary_results.tar.gz"
