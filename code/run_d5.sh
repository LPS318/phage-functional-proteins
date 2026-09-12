#!/usr/bin/env bash
# D5 · 宿主血清型一键流程（在阿里云 D6/任一联网节点运行）
# 装 numba/kaptive -> 下 NCBI 基因组 -> 下 Kaptive 库 -> 跑 AB(Kaptive)/PA(PAst) -> 汇总 serotype.tsv
set -u
WORK=/mnt/workspace/d5
OUT=$WORK/results
mkdir -p "$WORK" "$OUT"
LOGS=$WORK/logs; mkdir -p "$LOGS"

echo "== 环境准备：conda + python 3.11 + 工具 =="
source /root/miniforge3/etc/profile.d/conda.sh
conda create -n d5 python=3.11 -y 2>/dev/null || conda activate d5
conda activate d5
echo "conda env: $CONDA_DEFAULT_ENV"
pip install -U -q numba kaptive 2>&1 | tail -2
echo "kaptive:"; kaptive --version 2>&1 | head -2 || echo "kaptive 未装，请 pip install kaptive"
# NCBI datasets CLI（若未有则用 conda 装；仍失败则提示手动下）
which datasets >/dev/null 2>&1 || conda install -c conda-forge -y ncbi-datasets-cli 2>&1 | tail -2 || echo "[提示] datasets 不可用：请到 NCBI RefSeq 手动下载，并放入 $WORK/ab/、$WORK/pa/"

echo "== 下载宿主基因组（NCBI datasets，AB/PA 各取参考/前几株）=="
cd "$WORK"
# AB：鲍曼不动杆菌
if which datasets >/dev/null 2>&1; then
  datasets download genome taxon "Acinetobacter baumannii" --reference --assembly-source RefSeq --filename ab.zip 2>&1 | tail -3 \
    || echo "[提示] AB datasets 失败：请手动下到 $WORK/ab/"
  [ -f ab.zip ] && unzip -o -q ab.zip -d ab 2>/dev/null
fi
ls ab/*/*.fna 2>/dev/null | head -5 || echo "[提示] 未有 .fna，请检查 ab/ 下结构"

echo "== 下载 Kaptive-AB 参考库（GitHub；若失败请手动下再 scp）=="
mkdir -p "$WORK/refs"
for u in \
  "https://raw.githubusercontent.com/katholt/Kaptive/master/reference/Kaptive_AB_K_locus.fa" \
  "https://raw.githubusercontent.com/katholt/Kaptive/master/reference/Kaptive_AB_OC_locus.fa"; do
  f=$(basename "$u"); [ -f "$WORK/refs/$f" ] || curl -sL -o "$WORK/refs/$f" "$u"
  [ -s "$WORK/refs/$f" ] && echo "OK $f" || echo "[提示] 未下到 $f -> 请到 github.com/katholt/Kaptive 的 reference 下载后 scp 到 $WORK/refs/"
done
KDB=$(ls "$WORK"/refs/*K_locus* 2>/dev/null | head -1); OCDB=$(ls "$WORK"/refs/*OC_locus* 2>/dev/null | head -1)

echo "== 运行 Kaptive（AB）=="
cd "$WORK"
for fa in $(ls ab/*/*.fna 2>/dev/null | head -6); do
  name=$(basename "$fa" .fna); p="$OUT/$name"; mkdir -p "$p"
  if [ -n "$KDB" ] && [ -n "$OCDB" ]; then
    kaptive_run.py -k "$KDB" -o "$OCDB" -g "$fa" -p "$p/" > "$LOGS/$name.kaptive.log" 2>&1 && echo "OK $name" \
      || echo "[失败] $name 见 $LOGS/$name.kaptive.log"
  else
    echo "[跳过] $name：缺 Kaptive 参考库"
  fi
done

echo "== PAst（PA O-抗原）：如已装则跑，未装给提示 =="
python -c "import past" 2>/dev/null && for fa in $(ls pa/*/*.fna 2>/dev/null | head -4); do
  name=$(basename "$fa" .fna); past "$fa" "$OUT/$name" > "$LOGS/$name.past.log" 2>&1 && echo "OK $name" || echo "[失败] $name"
done || echo "[提示] PAst 未安装：请按 PAst 文档安装（pip install past 或官网），或改用 Kaptive 的 O-locus 分型"

echo "== 汇总 serotype.tsv =="
CSSV=$WORK/serotype.tsv; echo -e "genome\tbest_match(serotype)\ttype\tscore" > "$CSSV"
for d in "$OUT"/*/; do
  name=$(basename "$d")
  # kaptive 结果通常在 $d/kaptive_results.tsv 或 *.tab（best-match K/OC）
  tab=$(ls "$d"/*.tab "$d"/*K*.tsv "$d"/*OC*.tsv 2>/dev/null | head -1)
  if [ -n "$tab" ]; then
    match=$(awk -F'\t' 'NR>1{print $1}' "$tab" 2>/dev/null | head -1)
    sero=$(awk -F'\t' 'NR>1{print $2}' "$tab" 2>/dev/null | head -1)
    echo -e "$name\t$match\tKaptive\t$sero" >> "$CSSV"
  else
    echo -e "$name\tNA\tNA\tNA" >> "$CSSV"
  fi
done
echo "===== serotype.tsv ====="; cat "$CSSV"
echo "D5 done. 结果在 $WORK/serotype.tsv 与 $OUT/"
