#!/usr/bin/env bash
###############################################################################
# D1 · 非循环 PLM 三分类（depolymerase/lysin/holin）+ 冻结集评测
# 可控项：
#   MODELS="esm2"          只跑 ESM-2（磁盘紧张时用，推荐）
#   MODELS="esm2 prott5"   两个都跑（ProtT5 需 ~11.3GB 磁盘）
#   HF_HOME=/大容量路径     把 HuggingFace 缓存放到有空间的盘
# 用法：MODELS=esm2 bash run_d1_a100.sh
###############################################################################
set -u
WORK=${WORK:-/mnt/workspace/d1}
cd "$WORK" || { echo "[FATAL] 未找到 $WORK"; exit 1; }
MODELS=${MODELS:-"esm2 prott5"}
if [ -n "${HF_HOME:-}" ]; then export HF_HOME; export HF_HUB_CACHE="$HF_HOME/hub"; fi
echo "MODELS=$MODELS  HF_HOME=${HF_HOME:-默认}"
df -h "$WORK" | tail -1

source /root/miniforge3/etc/profile.d/conda.sh 2>/dev/null || true
conda create -n d1 python=3.10 -y 2>/dev/null || true
conda activate d1 2>/dev/null || conda activate base
pip install -q -U transformers sentencepiece tokenizers scikit-learn matplotlib numpy 2>&1 | tail -1
python - <<'PY'
try:
    import torch; print("torch", torch.__version__, "cuda", torch.cuda.is_available())
except Exception:
    raise SystemExit("[FATAL] 缺 torch：请用带 torch 的 A100 镜像")
PY

for m in $MODELS; do
  bs=8; case "$m" in prott5|prott5h) bs=4;; esac
  echo "== 嵌入: $m =="
  python embed_plm.py --fasta data/sequences.fasta --model "$m" --out "emb_${m}.npz" --bs "$bs" || { echo "[skip] $m 嵌入失败"; continue; }
  echo "== 训练+评测: $m =="
  python train_eval.py --emb "emb_${m}.npz" --meta data/meta.tsv --fasta data/sequences.fasta --out "out_${m}"
done

echo "== 打包 =="
tar -czf /mnt/workspace/d1_results.tar.gz out_* emb_*.npz 2>/dev/null
echo "完成 -> /mnt/workspace/d1_results.tar.gz"
