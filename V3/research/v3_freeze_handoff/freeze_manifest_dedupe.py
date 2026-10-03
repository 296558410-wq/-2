# -*- coding: utf-8 -*-
"""Dedupe protocol_hashes in V3_FREEZE_MANIFEST.json by file path (the glob matched both cases)."""
import json, os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "V3_FREEZE_MANIFEST.json")
d = json.load(open(p, encoding="utf-8"))
seen = set()
out = []
for x in d["protocol_hashes"]:
    if x["file"] in seen:
        continue
    seen.add(x["file"])
    out.append(x)
d["protocol_hashes"] = out
json.dump(d, open(p, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print("deduped protocols:", len(out))
for x in out:
    for k, v in x["declared_hashes"].items():
        print(f"  {x['file']} [{k}] = {v}")
