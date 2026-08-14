# 噬菌体功能蛋白候选数据库 v1.0

- 候选条目：4117（解聚酶/内溶素类/穿孔素，按六维评分排序）
- 数据文件：候选数据库_v1.0.csv（4117 行）／ 候选数据库_v1.0.sqlite（表 candidates）

## 字段说明

- category：功能类别；host_raw/host_domain/genome_family：宿主与分类
- best_evalue/n_pfam/n_cdd/n_superfamily/cazy_layer：功能注释证据
- tmhmm_predhel_approx/signal_peptide_approx：拓扑/分泌注记（启发式，approx）
- fold_homolog/mean_plddt/n_pockets：结构证据
- substrate_inferred：底物推断（in silico inferred，非确定）
- novelty/transfer_value/total_score：六维评分的新颖性/转化价值/总分

## SQLite 复现查询

```sql
-- Top-100 高价值候选（临床重点菌）
SELECT protein_id, category, host_raw, total_score FROM candidates
WHERE host_domain='bacteria' ORDER BY total_score DESC LIMIT 100;
-- 高新颖性解聚酶（无强同源）
SELECT protein_id, novelty, fold_homolog FROM candidates
WHERE category='depolymerase' AND novelty>=0.9;
```

> 注意：本库为预测级候选（in silico predicted），底物为推断口径；GitHub/Zenodo 预登记待网络与凭证就绪后执行（见工作区 README 第十二~十五节）。
