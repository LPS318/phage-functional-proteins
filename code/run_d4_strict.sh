#!/usr/bin/env bash
###############################################################################
# D4 收尾 · APBS 严格化静电（在能联网的阿里云节点运行）
# -----------------------------------------------------------------------------
# 用途：把论文里"近似口径"的 APBS 静电表面升级为严格口径
#       流程 = PDB2PQR(AMBER + PROPKA 质子化) -> APBS(LPBE, sdh, smol, spl2)
#       输出 .pqr + .dx 电位网格 -> 回本地用 PyMOL 渲染正式静电图
# 用法：bash run_d4_strict.sh [PDB目录]
#       PDB目录默认给 5 个 Class 1B 代表酶；若不传则自动在 /mnt/workspace 找
###############################################################################
set -u

# ---------- 0) 环境 ----------
WORK=/mnt/workspace/d4strict
OUT=$WORK/apbs_out
CDIR=$WORK/class1b          # 只对 5 个 Class 1B 代表酶做严格静电
mkdir -p "$WORK" "$OUT" "$CDIR"
source /root/miniforge3/etc/profile.d/conda.sh 2>/dev/null || true

# ---------- 1) 创建并激活 d4 环境 ----------
conda create -n d4 python=3.11 -y 2>/dev/null || true
conda activate d4 2>/dev/null || conda activate base
echo "== 安装 apbs / pdb2pqr / propka =="
conda install -c conda-forge -y apbs pdb2pqr propka 2>&1 | tail -4 || {
  echo "[!] conda 安装失败，尝试 pip 兜底"; pip install pdb2pqr propka 2>&1 | tail -3; }
export PATH="$(conda info --base)/envs/d4/bin:$PATH"
which pdb2pqr >/dev/null 2>&1 || { echo "[FATAL] pdb2pqr 不可用"; exit 1; }
which apbs    >/dev/null 2>&1 || { echo "[FATAL] apbs 不可用（可 apt 装 libumfpack 或改用 conda 装）"; exit 1; }

# ---------- 2) 定位 5 个 Class 1B 代表酶 ----------
CLASS1B="KLEO13gp10 KP24gp300 FKANgp232 184_43 S2-2"
SRC="${1:-}"
if [ -z "$SRC" ]; then
  for cand in /mnt/workspace/d4_cloud/structures /mnt/workspace/d4/structures /mnt/workspace/structures; do
    [ -d "$cand" ] && SRC="$cand" && break
  done
fi
[ -z "$SRC" ] && { echo "[FATAL] 未找到 PDB 目录，请传入：bash run_d4_strict.sh /路径/structures"; exit 1; }
echo "== 源 PDB 目录 = $SRC"
for n in $CLASS1B; do
  srcf="$(find "$SRC" -maxdepth 2 -iname "${n}.pdb" | head -1)"
  if [ -n "$srcf" ]; then cp -f "$srcf" "$CDIR/$n.pdb"; else echo "[跳过] 未找到 $n.pdb"; fi
done
echo "== 本次处理清单 =="; ls -1 "$CDIR"/*.pdb 2>/dev/null

# ---------- 3) 逐酶 PDB2PQR -> APBS -> 电位网格 ----------
for f in "$CDIR"/*.pdb; do
  [ -f "$f" ] || continue
  b=$(basename "$f" .pdb)
  pqr="$WORK/$b.pqr"
  echo "---- $b ----"
  echo "[PDB2PQR] $f -> $pqr"
  pdb2pqr --ff=AMBER --chain --drop-water --ph=7.0 "$f" "$pqr" 2>"$WORK/$b.pdb2pqr.log" \
      || echo "[警告] pdb2pqr 返回非零，检查 $WORK/$b.pdb2pqr.log"
  [ -s "$pqr" ] || { echo "[失败] 无 $pqr"; continue; }
  echo "[APBS] 生成输入并运行"
  cat > "$WORK/$b.in" <<IN
read
 mol pqr $pqr
end
elec name mol
 mg-auto
 dime 161 161 161
 grid 0.5 0.5 0.5
 mol 1
 lpbe
 bcfl sdh
 srfm smol
 chgm spl2
 sdens 10.0
 srad 1.4
 swin 0.3
 temp 298.15
 ion charge 1 conc 0.150 radius 2.0
 ion charge -1 conc 0.150 radius 2.0
 write pot dx $OUT/$b
end
quit
IN
  apbs "$WORK/$b.in" > "$WORK/$b.apbs.log" 2>&1
  if [ -s "$OUT/$b.dx" ]; then echo "OK apbs $b"; else echo "[失败] apbs $b（见 $WORK/$b.apbs.log）"; fi
done

# ---------- 4) 汇总 ----------
python3 - <<'PY'
import glob,re,os,statistics as st
rows=[]
for dx in sorted(glob.glob("/mnt/workspace/d4strict/apbs_out/*.dx")):
    # 只读 data-follows 之后的纯数值行，跳过 object/items/counts/delta 等容器行
    vals=[]
    in_data=False
    for line in open(dx):
        s=line.strip()
        if s.lower().startswith('object') and 'data' in s.lower():
            in_data=True; continue
        if not in_data: continue
        if s=='' or s.startswith('#') or 'object' in s.lower(): continue
        # 只接受纯数字行（含科学计数），排除任何含字母的行
        toks=s.split()
        if not toks: continue
        try:
            vals.extend(float(t) for t in toks)
        except ValueError:
            continue
    if vals:
        rows.append((os.path.basename(dx)[:-3], len(vals),
                     round(st.mean(vals),3), round(st.pstdev(vals),3),
                     round(min(vals),3), round(max(vals),3)))
with open("/mnt/workspace/d4strict/apbs_summary.tsv","w") as f:
    f.write("id\tn_points\tmean_pot\tstd_pot\tmin_pot\tmax_pot\n")
    for r in rows: f.write("\t".join(map(str,r))+"\n")
print("== apbs_summary.tsv ==")
print(open("/mnt/workspace/d4strict/apbs_summary.tsv").read())
PY
echo "== 完成。产物："
echo "  PQR:   $WORK/*.pqr"
echo "  DX:    $OUT/*.dx"
echo "  汇总:  $WORK/apbs_summary.tsv"
echo "下一步：把 $WORK/*.pqr 和 $OUT/*.dx 打包下载回本地，用 render_apbs_strict.py 渲染正式静电图。"
