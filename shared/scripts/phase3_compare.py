# -*- coding: utf-8 -*-
"""phase3_compare.py — 跨期对比：2026(FXTM M1) vs 2023-24(DUKA M1) 同一 69 假设。

输出 reports/phase3_crossperiod.md：按 family 汇总 IC/方向一致性；重点候选逐项。
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "C:/AIQuant")

R1 = json.load(open("C:/AIQuant/reports/round1_details.json", encoding="utf-8"))
R2 = json.load(open("C:/AIQuant/reports/round1_duka2023_details.json", encoding="utf-8"))


def ic_map(r):
    out = {}
    # survivors carry perm; 非 survivors 未存 → 从 alpha registry 补 (ic_oos)
    for s in r.get("survivors", []):
        out[s["hypothesis_id"]] = {"ic": s["ic_oos"], "p": s["p"], "q": s["q"]}
    return out


A, B = ic_map(R1), ic_map(R2)
rows = []
for hid in sorted(set(A) | set(B)):
    a = A.get(hid)
    b = B.get(hid)
    rows.append({"hypothesis_id": hid,
                 "ic_2026": a["ic"] if a else None, "q_2026": a["q"] if a else None,
                 "ic_2023_24": b["ic"] if b else None, "q_2023_24": b["q"] if b else None})
df = pd.DataFrame(rows)
df["sign_consistent"] = df.apply(lambda r: (r["ic_2026"] or 0) * (r["ic_2023_24"] or 0) > 0
                                 if pd.notna(r["ic_2026"]) and pd.notna(r["ic_2023_24"]) else None, axis=1)

L = ["# Phase 3 跨期复验：同一冻结 69 假设", "",
     f"- 2026 窗口：FXTM M1 {R1['dataset_meta']['start']} → {R1['dataset_meta']['end']}（100k bars）",
     f"- 2023-24 窗口：DUKA M1 {R2['dataset_meta']['start']} → {R2['dataset_meta']['end']}（229k bars）",
     f"- 2026 funnel: raw {R1['funnel']['n_raw_sig']} / FDR {R1['funnel']['n_fdr_sig']} / SUPPORTED 0",
     f"- 2023-24 funnel: raw {R2['funnel']['n_raw_sig']} / FDR {R2['funnel']['n_fdr_sig']} / SUPPORTED 0",
     ""]
both = df.dropna(subset=["ic_2026", "ic_2023_24"])
L += ["## 两期均显著(FDR)且方向一致", ""]
samedir = both[(both["q_2026"] < 0.05) & (both["q_2023_24"] < 0.05) & (both["sign_consistent"] == True)]
if len(samedir):
    L.append("| hypothesis | IC 2026 | IC 2023-24 |")
    L.append("|---|---|---|")
    for _, r in samedir.sort_values("ic_2026", ascending=False).iterrows():
        L.append(f"| {r['hypothesis_id']} | {r['ic_2026']:.4f} | {r['ic_2023_24']:.4f} |")
else:
    L.append("（无）")
L += ["", "## 方向反转或消失的重点项", ""]
rev = both[(both["sign_consistent"] == False)]
for _, r in rev.iterrows():
    L.append(f"- {r['hypothesis_id']}: 2026 IC={r['ic_2026']:.4f} → 2023-24 IC={r['ic_2023_24']:.4f}")
if not len(rev):
    L.append("（无反转）")
L += ["", "## 分 family 方向一致率", ""]
fam = both.copy()
fam["family"] = fam["hypothesis_id"].str.extract(r"^(H\d+_\w+)")
g = fam.groupby("family").agg(n=("sign_consistent", "size"),
                              consistent=("sign_consistent", "sum")).reset_index()
L.append("| family | 两期都显著对数 | 方向一致数 |")
L.append("|---|---|---|")
for _, r in g.iterrows():
    L.append(f"| {r['family']} | {int(r['n'])} | {int(r['consistent'])} |")
Path("C:/AIQuant/reports/phase3_crossperiod.md").write_text("\n".join(L), encoding="utf-8")
print("crossperiod report written")
