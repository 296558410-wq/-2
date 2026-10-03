# -*- coding: utf-8 -*-
"""Generate SHA256_MANIFEST.json for the R4 round (R3-style schema).
Raw parquet sequences are NOT listed individually here (they are covered by SNAPSHOT_FXTM_R4/MANIFEST.json)
and are not committed to git by repo convention (150.6 MB); their per-file hashes live in that manifest."""
import hashlib, json, os, datetime as dt

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = ("SNAPSHOT_FXTM_R4/staging_fxtm", "SNAPSHOT_FXTM_R4/live_fxtm")
EXCLUDE = ("SHA256_MANIFEST.json",)

files = {}
for dp, dn, fn in os.walk(D):
    rel = os.path.relpath(dp, D).replace("\\", "/")
    if any(rel.startswith(s) for s in SKIP_DIRS):
        continue
    for f in fn:
        rp = (rel + "/" + f) if rel != "." else f
        rp = rp.replace("\\", "/")
        if rp in EXCLUDE or any(rp.startswith(s + "/") for s in SKIP_DIRS):
            continue
        p = os.path.join(dp, f)
        files[rp] = {"sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(), "bytes": os.path.getsize(p)}

snap_man = os.path.join(D, "SNAPSHOT_FXTM_R4", "MANIFEST.json")
snap = json.load(open(snap_man, encoding="utf-8"))
doc = {
    "schema": "v3_r4_sha256_manifest/1",
    "task_id": "V3-R4-F5",
    "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "note": "hashes of this round's artifacts; R1/R2/R3 artifacts are deliberately NOT listed and NOT modified",
    "files": files,
    "snapshot": {
        "dir": "SNAPSHOT_FXTM_R4",
        "manifest_sha256": hashlib.sha256(open(snap_man, "rb").read()).hexdigest(),
        "files_covered": len(snap["files"]),
        "total_rows": snap["TOTAL_ROWS"],
        "span": [snap["MIN_TIMESTAMP"], snap["MAX_TIMESTAMP"]],
        "raw_sequences_in_git": False,
        "raw_sequences_note": "44 parquet files (~150.6 MB) are NOT committed to git by repo convention; per-file sha256 are inside SNAPSHOT_FXTM_R4/MANIFEST.json and can be re-verified against the on-disk snapshot",
    },
}
out = os.path.join(D, "SHA256_MANIFEST.json")
json.dump(doc, open(out, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print("wrote", out)
print("files listed:", len(files))
for k in sorted(files):
    print(f"  {files[k]['sha256'][:16]}  {files[k]['bytes']:>8}  {k}")
print("snapshot manifest sha256:", doc["snapshot"]["manifest_sha256"][:16], "files:", doc["snapshot"]["files_covered"])
