# -*- coding: utf-8 -*-
"""enumerate_deletions.py — repo-wide DELETION/RENAME commits filtered to hermes/v1 (READ-ONLY)."""
import json, os, re, subprocess
REPO = r"C:\AIQuant"
OUT = os.path.join(REPO, "research", "hermes", "trader_v1", "audit", "v1_zombie_code_forensics")
os.makedirs(OUT, exist_ok=True)
def git(*a): return subprocess.run(["git","-C",REPO,*a],capture_output=True,text=True,encoding="utf-8",errors="replace").stdout
raw = git("log","--all","--no-merges","--date=short","--pretty=format:\x01%h|%ad|%an|%s","--name-status","--diff-filter=DR")
cur=None; out=[]
for ln in raw.split("\n"):
    if ln.startswith("\x01"):
        h,ad,an,s = ln[1:].split("|",3); cur={"hash":h,"date":ad,"author":an,"subject":s,"paths":[]}; out.append(cur)
    elif ln.strip() and cur is not None:
        parts=ln.split("\t")
        if len(parts)>=2: cur["paths"].append({"status":parts[0],"path":parts[-1]})
pat=re.compile(r"(hermes|trader_v1|/v1|v1_)",re.I)
hits=[c for c in out if any(pat.search(p["path"]) for p in c["paths"])]
print("deletion/rename commits (repo):", len(out), "| filtered hermes/v1:", len(hits))
for c in hits:
    print(f"\n{c['hash']}|{c['date']}|{c['author']}| {c['subject'][:100]}")
    for p in c["paths"][:20]:
        print(f"    {p['status']} {p['path']}")
    if len(c["paths"])>20: print(f"    ... +{len(c['paths'])-20} more")
json.dump({"schema":"zombie_deletions/1","n_all":len(out),"n_hermes":len(hits),"hits":hits},
          open(os.path.join(OUT,"git_deletions_raw.json"),"w",encoding="utf-8",newline="\n"),ensure_ascii=False)
