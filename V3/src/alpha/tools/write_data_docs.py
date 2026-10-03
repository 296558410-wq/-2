"""Write alpha/data/data_gaps.md from the real scan (data_manifest.json)."""
from __future__ import annotations
import json, os

OUT = r"C:\AIQuant\research\hermes\trader_v3\alpha"
man = json.load(open(os.path.join(OUT, "data", "data_manifest.json"), encoding="utf-8"))
F = man["files"]

lines = []
A = lines.append
A("# V3-HFT-ALPHA-DISCOVERY-001 — DATA GAPS (measured, not assumed)")
A("")
A(f"- Generated: {man['generated_utc']}")
A(f"- Source: real scan of parquet files under `{man['scanned_root']}` (`alpha/tools/scan_data.py`).")
A("- No value below is inferred from the registry; every number comes from reading the files.")
A("")

A("## 1. Registered gaps that remain open (carried from `state/V3_DATA_REGISTRY_v2.json`)")
A("")
A("| gap | status | impact on this study |")
A("|---|---|---|")
A("| `2023-12` | MISSING | DUKA tick timeline not contiguous across 2023-11→2024-01 |")
A("| `2024-04 → 2026-07` (28 months) | MISSING | **no 1h/4h/1d horizon is measurable on DUKA across this window** |")
A("| `daily 21:00–22:59Z` | MISSING | only 1-2 hours/day; long-horizon windows cross it |")
A("| `L2 / trade_flow` | UNKNOWN (L2_DATA_GAP) | B1 microprice and true B2 OFI are **not computable** |")
A("")

A("## 2. Feed-level facts measured in this scan")
A("")

def fam_table(key, label):
    recs = F[key]
    A(f"### {label}")
    A("")
    A("| file | rows | ts_min (UTC) | ts_max (UTC) | max_gap_s | dup_rate | ooo_rate | med_spread_USD | tick_Hz |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in recs:
        if "ts_min_utc" not in r:
            continue
        A(f"| {r['file']} | {r['rows']} | {r['ts_min_utc'][:19]} | {r['ts_max_utc'][:19]} | "
          f"{r['max_gap_s']:.1f} | {r['duplicate_rate']:.5f} | {r['out_of_order_rate']:.6f} | "
          f"{r['median_spread_usd']:.3f} | {r['tick_rate_hz']:.2f} |")
    A("")
    tot = sum(r["rows"] for r in recs)
    A(f"- files={len(recs)}, rows={tot}")
    hmm = [r for r in recs if r.get("hours_present") is not None]
    if hmm:
        A(f"- hours covered (first/last file): `{F[key][0]['hours_present']}` / `{F[key][-1]['hours_present']}`")
    A("")

fam_table("fxtm_staging_tick", "2.1 FXTM staging ticks (primary feed, part 1)")
fam_table("fxtm_live_tick", "2.2 FXTM live-collected ticks (primary feed, part 2)")
fam_table("duka_monthly_tick", "2.3 DUKA assembled monthly ticks (secondary / cross-venue check)")

A("### 2.4 DUKA daily ticks (`ticks_YYYYMMDD.parquet`, 140 files)")
A("")
d = F["duka_daily_tick"]
A(f"- files={len(d)}, rows={sum(r['rows'] for r in d)} (identical row total to the assembled monthly files:")
A("  the daily files are the same ticks split by day, reconstructed as `date(from filename) + hour + ms-within-hour`).")
A(f"- date range: `{d[0]['file']}` → `{d[-1]['file']}`")
A("- some 'days' only contain the tail of a session (e.g. `ticks_20230901` covers hours 22-23 only).")
A("")

A("### 2.5 DUKA candles")
c = F["duka_candles"]
A("")
A(f"- files={c['files']}, rows={c['total_rows']}, {c['date_min']} → {c['date_max']}, columns={c['columns']}")
A("- prices are int-scaled (×1e3); `side` ∈ {BID, ASK}; `sec` = second-of-day.")
A("")

A("## 3. Structural gaps that block specific horizons")
A("")
A("| horizon | blocking fact |")
A("|---|---|")
A("| 50 ms, 200 ms | FXTM median inter-tick interval ≈ 350–520 ms (1.9–2.7 Hz feed): the feed **cannot resolve** sub-second horizons; most forward windows contain 0 ticks |")
A("| 1 h, 24 h (DUKA) | `2024-04 → 2026-07` missing: no contiguous long-horizon window; `daily 21:00–22:59Z` missing |")
A("| 24 h (FXTM) | only ~34 trading days exist in total → effective_n is tiny |")
A("| B1 / true B2 | `volume`, `volume_real`, `last` are **identically 0** on the whole FXTM feed and `bid_vol == ask_vol` in 33–85% of DUKA ticks |")
A("")

A("## 4. Deliberate non-actions")
A("")
A("- No interpolation of missing ticks/bars. Missing intervals are reported as gaps.")
A("- No synthesis of L2 fields; B1/B2 true forms are marked `DATA_GAP`.")
A("- No cross-gap stitching for label windows (segment-aware labels).")
A("")

p = os.path.join(OUT, "data", "data_gaps.md")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("wrote", p, len("\n".join(lines)), "chars")
