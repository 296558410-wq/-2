# -*- coding: utf-8 -*-
"""phase3_version_integrity.py — Phase-3 任务 D：把 V2 未提交代码 + 未跟踪件纳入 Git；产出 SHA256 manifest。
注：V2 state/*.jsonl 为运行期输出，正常每 15min 变动；"clean" 为提交时刻状态。
"""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
REPO = r"C:\AIQuant"
V2 = Path(REPO) / "research" / "hermes" / "trader_v2"
OUT = V2 / "V2_EVOLUTION_PHASE3"


def git(*a):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True)
    return (r.stdout or b"").decode("utf-8", "replace")


before = git("status", "--porcelain", "research/hermes/trader_v2").strip().splitlines()
print("dirty before:", len(before))
git("add", "-A", "research/hermes/trader_v2")
r = subprocess.run(["git", "-C", REPO, "commit", "-q", "-m",
                    "feat(v2-phase3): discovery rank/select shadow + outcome engine + execution-mode unify to PAPER_LOCAL + version integrity (order_send=0)",
                    "--", "research/hermes/trader_v2"], capture_output=True)
print("commit rc:", r.returncode, (r.stderr or b"").decode("utf-8", "replace")[:200])
head = git("rev-parse", "HEAD").strip()
after = git("status", "--porcelain", "research/hermes/trader_v2").strip().splitlines()

# production-code manifest (code only; excludes state outputs/data)
code_exts = (".py", ".json", ".md", ".yaml", ".ps1", ".txt")
man = {}
for p in sorted(V2.rglob("*")):
    if not p.is_file() or "__pycache__" in p.parts:
        continue
    rel = p.relative_to(V2).as_posix()
    if rel.startswith(("state/", "data_cache/", "observations/")):
        continue
    if p.suffix.lower() in code_exts:
        man[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
res = {"git_head": head, "dirty_before": len(before), "dirty_after": len(after),
       "dirty_after_files": after[:20], "code_files_hashed": len(man), "manifest": man}
(OUT / "V2_CODE_MANIFEST.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("HEAD:", head, "| dirty_after:", len(after), "| code files hashed:", len(man))
