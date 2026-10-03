# -*- coding: utf-8 -*-
"""V3 R3: temporal integrity + event-loader rebuild + event/tick rebuild + X3 market-neutral redesign.

Protocol frozen before computation. Read-only. No orders. No new Alpha Sweep hypothesis.
Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_r3_integrity/run_r3.py
"""
from __future__ import annotations
import glob, hashlib, json, math, os, sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
S_MAIN = os.path.join(V3, "data", "snapshots", "V3-SNAP-20260922T025312Z")
S_PIT2 = os.path.join(V3, "data", "snapshots", "V3-SNAP-PIT2-20261001T131500Z")
PROTO = os.path.join(HERE, "V3_R3_FROZEN_PROTOCOL.json")
COST = 0.914
GAP = 60_000
N = 20
SEED = 20261004
DAY = 86_400_000


def load_df(snap):
    files = sorted(glob.glob(os.path.join(snap, "*", "*.parquet")))
    return pd.concat([pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files], ignore_index=True)


def arrays(d):
    d = d.sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    return (d["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64"),
            d["bid"].to_numpy(np.float64), d["ask"].to_numpy(np.float64))


def segments(ts):
    dd = np.diff(ts, prepend=ts[0])
    return np.cumsum((dd <= 0) | (dd > GAP)) - 1


def bars_from(ts, mid, seg):
    b = pd.DataFrame({"ts": ts, "mid": mid, "seg": seg})
    b["minute"] = b["ts"] // 60000
    g = b.groupby(["seg", "minute"], sort=True).agg(close=("mid", "last"), close_ts=("ts", "last")).reset_index()
    g = g.sort_values("close_ts").reset_index(drop=True)
    g["ret1"] = np.nan; g["sig20"] = np.nan; g["rv5"] = np.nan; g["ch60"] = np.nan
    for s, idx in g.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx); c = g["close"].to_numpy()[idx]
        srs = pd.Series(c); r1 = srs.pct_change()
        g.iloc[idx, g.columns.get_loc("ret1")] = r1.to_numpy()
        g.iloc[idx, g.columns.get_loc("sig20")] = r1.rolling(N, min_periods=N).std().shift(1).to_numpy()
        g.iloc[idx, g.columns.get_loc("rv5")] = r1.rolling(5, min_periods=5).std().to_numpy()
        g.iloc[idx, g.columns.get_loc("ch60")] = srs.pct_change(60).to_numpy()
    g["z5"] = g["close"].pct_change(5) / (g["sig20"] * math.sqrt(5))
    q67 = np.full(len(g), np.nan); rv = g["rv5"].to_numpy()
    for s, idx in g.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx)
        q67[idx] = pd.Series(rv[idx]).expanding(min_periods=100).quantile(0.67).to_numpy()
    g["q67"] = q67
    return g


def onset(c):
    return c & ~np.concatenate([[False], c[:-1]])


def perm_p(x, reps=2000):
    n = len(x)
    if n < 5:
        return None
    base = abs(float(np.mean(x))); rng = np.random.default_rng(SEED); f = x.astype(np.float32)
    ge = 0; done = 0; chunk = max(1, min(250, max(1, 4_000_000 // max(1, n))))
    while done < reps:
        c = min(chunk, reps - done)
        s = rng.integers(0, 2, size=(c, n)).astype(np.int8) * 2 - 1
        ge += int(np.sum(np.abs((f[None, :] * s).mean(axis=1)) >= base)); done += c
    return float((ge + 1) / (reps + 1))


def boot_ci(x, reps=2000, nblocks=50):
    n = len(x)
    if n < 10:
        return None
    bs = max(1, n // nblocks); nb = int(np.ceil(n / bs))
    pad = np.concatenate([x, np.full(nb * bs - n, np.nan)])
    blk = np.nanmean(pad.reshape(nb, bs), axis=1)
    rng = np.random.default_rng(SEED + 1)
    m = blk[rng.integers(0, nb, size=(reps, nb))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def eff_n(ei, ts, hm):
    if not len(ei):
        return 0
    t = ts[ei]; c = 1; last = t[0]
    for x in t[1:]:
        if x - last >= hm:
            c += 1; last = x
    return c


def max_dd(x):
    if not len(x):
        return None
    c = np.cumsum(x); return float(np.min(c - np.maximum.accumulate(c)))


def marks(ts, mid, seg, ent, dirs, hm):
    j = np.searchsorted(ts, ts[ent] + hm, side="left")
    v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[ent])
    ei, ji, dd = ent[v], np.minimum(j, len(ts) - 1)[v], dirs[v]
    if len(ei) < 2:
        return ei, np.array([])
    return ei, dd * (mid[ji] - mid[ei]) / mid[ei] * 1e4


def block_stats(ts, ret, key):
    out = {}
    for k in np.unique(key):
        m = key == k
        if m.sum() < 2:
            out[str(k)] = {"n": int(m.sum())}
            continue
        g = ret[m]
        out[str(k)] = {"n": int(m.sum()), "gross_bp": float(np.mean(g)),
                       "net1x_bp": float(np.mean(g) - COST), "std_bp": float(np.std(g))}
    return out


def main():
    proto = json.load(open(PROTO, encoding="utf-8"))
    body = {k: v for k, v in proto.items() if k != "registry_hash_sha256"}
    hh = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert hh == proto["registry_hash_sha256"], "protocol hash mismatch"
    print("protocol hash OK:", hh[:16])
    res = {"schema": "v3_r3_results/1", "protocol_hash": hh, "cost_bp": COST}

    print("loading snapshots ...")
    dm, dp = load_df(S_MAIN), load_df(S_PIT2)
    du = pd.concat([dm, dp], ignore_index=True).drop_duplicates(subset=["ts_utc", "bid", "ask"])
    du = du.sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    ts, bid, ask = arrays(du)
    mid = (bid + ask) / 2.0; seg = segments(ts)
    bars = bars_from(ts, mid, seg)
    print(f"  UNION ticks={len(ts)} segments={int(seg[-1])+1} bars={len(bars)}")

    # ================= W1 temporal audit =================
    print("W1 temporal audit ...")
    dt = pd.to_datetime(ts, unit="ms", utc=True)
    day = (ts // DAY)
    days = np.unique(day)
    tsm = pd.to_datetime(bars["close_ts"].to_numpy(), unit="ms", utc=True)
    bhour = ((bars["close_ts"].to_numpy() // 3600000) % 24)
    bdate = bars["close_ts"].to_numpy() // DAY
    W1 = {
        "earliest_utc": str(dt[0]), "latest_utc": str(dt[-1]),
        "span_days": float((ts[-1] - ts[0]) / DAY),
        "active_trading_days": int(len(days)),
        "ticks_per_day": {str(pd.to_datetime(d, unit="D", utc=True).date()): int((day == d).sum()) for d in days},
        "ticks_per_month": {},
        "segments": int(seg[-1]) + 1,
        "day_gap_gt_60s_count": int((np.diff(ts) > GAP).sum()),
    }
    per_month = {}
    for k, v in pd.Series(day).groupby(pd.to_datetime(day, unit="D", utc=True).strftime("%Y-%m")).size().items():
        per_month[str(k)] = int(v)
    W1["ticks_per_month"] = per_month
    wk = pd.Series(pd.to_datetime(day, unit="D", utc=True)).dt.strftime("%Y-W%W")
    W1["ticks_per_week"] = {str(k): int(v) for k, v in pd.Series(day).groupby(wk).size().items()}
    # market phase coverage: session bucket per active day
    hr = ((ts // 3600000) % 24)
    W1["session_tick_share"] = {"ASIA(0-8)": float(np.mean(hr < 8)), "LONDON(8-16)": float(np.mean((hr >= 8) & (hr < 16))), "NY(16-24)": float(np.mean(hr >= 16))}
    res["W1"] = W1
    print(f"  span={W1['span_days']:.1f}d active_days={W1['active_trading_days']} months={list(per_month)}")

    # P3 per-block temporal stability @60m (definition inherited, no threshold change)
    rv = bars["rv5"].to_numpy(); q = bars["q67"].to_numpy()
    prev = np.concatenate([[False], (rv >= q)[:-1]])
    pmask = (rv >= q) & ~prev & np.isfinite(rv) & np.isfinite(q)
    pidx = np.flatnonzero(pmask); bts = bars["close_ts"].to_numpy()
    pe = np.searchsorted(ts, bts[pidx] + 1, "left"); ok = pe < len(ts); pe = pe[ok]; pidx = pidx[ok]
    pd_ = np.sign(np.nan_to_num(bars["ret1"].to_numpy()[pidx])).astype(int)
    H60 = 3600_000
    pei, pret = marks(ts, mid, seg, pe.astype(int), pd_, H60)
    bday = ts[pei] // DAY
    bmon = pd.to_datetime(bday * DAY, unit="ms", utc=True).strftime("%Y-%m")
    bweek = pd.to_datetime(bday * DAY, unit="ms", utc=True).strftime("%Y-W%W")
    P3T = {"n": int(len(pei)), "eff_n_raw": int(eff_n(pei, ts, H60))}
    P3T["monthly"] = block_stats(ts, pret, bmon.to_numpy())
    P3T["weekly"] = block_stats(ts, pret, bweek.to_numpy())
    order = np.argsort(ts[pei]); roll = []
    days_sorted = np.sort(np.unique(bday))
    for k in range(20, len(days_sorted), 5):
        win = set(days_sorted[k - 20:k])
        m = np.isin(bday, list(win))
        if m.sum() >= 5:
            roll.append({"window_end_day": str(pd.to_datetime(days_sorted[k - 1] * DAY, unit="ms", utc=True).date()),
                         "n": int(m.sum()), "net1x_bp": float(np.mean(pret[m]) - COST)})
    P3T["rolling_20d"] = {"windows": len(roll), "positive_share": float(np.mean([r["net1x_bp"] > 0 for r in roll])) if roll else None,
                          "detail_first5": roll[:5], "detail_last5": roll[-5:]}
    msign = [v for v in P3T["monthly"].values() if v.get("n", 0) >= 50]
    overall = float(np.mean(pret)) if len(pret) else 0.0
    P3T["monthly_consistency"] = {"months_with_n_ge_50": len(msign),
                                  "matching_overall_sign": int(sum(1 for v in msign if (v["gross_bp"] > 0) == (overall > 0))),
                                  "overall_gross_bp": overall}
    res["W1"]["P3_60m_temporal"] = P3T
    gate = {"G1_coverage": W1["span_days"] >= 90 and W1["active_trading_days"] >= 40,
            "G2_monthly_consistency": (P3T["monthly_consistency"]["months_with_n_ge_50"] > 0 and
                                       P3T["monthly_consistency"]["matching_overall_sign"] / max(1, P3T["monthly_consistency"]["months_with_n_ge_50"]) >= 2/3),
            "G3_rolling_stability": (P3T["rolling_20d"]["positive_share"] is not None and P3T["rolling_20d"]["positive_share"] >= 0.60)}
    gate["G1_detail"] = {"span_days": round(W1["span_days"], 1), "active_days": W1["active_trading_days"]}
    res["W1"]["TEMPORAL_GATE"] = gate
    res["W1"]["TEMPORAL_VERDICT"] = ("TEMPORAL_EVIDENCE_INSUFFICIENT" if not gate["G1_coverage"]
                                     else ("TIME_INSTABILITY" if not (gate["G2_monthly_consistency"] and gate["G3_rolling_stability"]) else "PASS"))
    print("  temporal gate:", {k: v for k, v in gate.items() if k != "G1_detail"}, "->", res["W1"]["TEMPORAL_VERDICT"])

    # ================= W2 event loader rebuild =================
    print("W2 event loader rebuild ...")
    vd = os.path.join(V3, "research", "v3_pit_supplement_r1", "vintages")
    rows = []
    for fp in sorted(glob.glob(os.path.join(vd, "*.json"))):
        j = json.load(open(fp, encoding="utf-8"))
        for e in j.get("events", []):
            rows.append({**e, "_source_file": os.path.basename(fp)})
    def pt(e):
        p = e.get("pub_time") or e.get("pub_time_utc")
        if not p:
            return None
        try:
            return int(pd.Timestamp(p, tz="Asia/Shanghai").tz_convert("UTC").value // 10**6)
        except Exception:
            try:
                return int(pd.Timestamp(p).value // 10**6)
            except Exception:
                return None
    keyed = []
    for e in rows:
        t = pt(e)
        if t is None:
            continue
        k = (t, str(e.get("title")), e["_source_file"])
        keyed.append({"ts": t, "key": k, "row": {kk: e.get(kk) for kk in ("pub_time", "title", "star", "actual", "consensus", "previous", "affect_txt")}})
    seen = {}; uniq = []; true_dup = 0
    for r in keyed:
        if r["key"] in seen:
            true_dup += 1
        else:
            seen[r["key"]] = True; uniq.append(r)
    byts = {}
    for r in uniq:
        byts.setdefault(r["ts"], []).append(r)
    concurrent = sum(len(v) - 1 for v in byts.values() if len(v) > 1)
    inwin = [r for r in uniq if ts[0] <= r["ts"] <= ts[-1]]
    pre_ok = [r for r in inwin if r["ts"] - 60_000 >= ts[0]]
    post_ok = [r for r in pre_ok if r["ts"] + 15 * 60_000 <= ts[-1]]
    W2 = {"raw_rows": len(rows), "pit_qualified_rows": len(keyed), "true_duplicates": true_dup,
          "unique_events": len(uniq), "concurrent_distinct_events": concurrent,
          "distinct_timestamps": len(byts), "simultaneous_groups": sum(1 for v in byts.values() if len(v) > 1),
          "inside_union_tick_window": len(inwin), "with_complete_pre_post": len(post_ok),
          "final_researchable_rows": len(post_ok),
          "final_researchable_distinct_timestamps": len({r["ts"] for r in post_ok}),
          "loss_reasons": {
              "no_parseable_pub_time": len(rows) - len(keyed),
              "outside_tick_window": len(uniq) - len(inwin),
              "incomplete_pre_or_post_window": len(inwin) - len(post_ok),
              "note": "no synthetic events were created and no window was widened"},
          "unique_key": "(pub_time_utc, title, source_file)  [the vintage carries title/star, NOT event_name/country]",
          "true_duplicate_definition": "two rows identical on the unique key (i.e. the same indicator at the same minute from the same file)",
          "concurrent_definition": "rows sharing the same pub_time but with a DIFFERENT title",
          "implementation_errors_recorded": [
              {"where": "R1 Alpha Sweep event loader", "error": "dedup on (ts, filename) collapsed 283 rows into 75 distinct timestamps",
               "impact": "the whole F5 family was under-counted; E1/E2/E4 ran on n=38..50", "status": "recorded, not overwritten"},
              {"where": "R3 W2 attempt 1 (this round)", "error": "the key used event_name/country, which do not exist in the vintage schema, so 208 CONCURRENT DISTINCT events were misreported as TRUE DUPLICATES (true_dup=208, concurrent=0)",
               "impact": "wrong accounting in the first R3 pass", "correction": "key changed to (pub_time, title, source_file)", "status": "corrected in attempt 2; the failed attempt is kept here"}
          ],
          "measured": {"byte_identical_duplicate_rows": 0, "distinct_on_pub_time_only": 75, "distinct_on_pub_time_and_title": 283}}
    reg = [{"ts_utc": str(pd.to_datetime(r["ts"], unit="ms", utc=True)), "key": list(map(str, r["key"])), **r["row"]} for r in post_ok]
    reg_sorted = sorted(reg, key=lambda x: (x["ts_utc"], str(x["key"])))
    reg_sha = hashlib.sha256(json.dumps(reg_sorted, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    W2["registry_sha256"] = reg_sha
    json.dump(reg_sorted, open(os.path.join(HERE, "EVENT_REGISTRY.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    res["W2"] = W2
    res["W3"] = {"scope": "data integrity only; no F5 return conclusion is inherited",
                 "researchable_rows": len(post_ok),
                 "researchable_distinct_timestamps": W2["final_researchable_distinct_timestamps"],
                 "r1_used": 75, "r1_defect": "dedup on (ts, filename) collapsed 283 -> 75",
                 "comparison": f"rows {len(post_ok)} vs R1's 75 timestamp-level entries"}
    print(f"  raw={len(rows)} true_dup={true_dup} unique={len(uniq)} concurrent={concurrent} researchable={len(post_ok)} distinct_ts={W2['final_researchable_distinct_timestamps']}")

    # ================= W4 X3 market-neutral =================
    print("W4 X3 market-neutral ...")
    if str(bhour.dtype) == "":
        pass
    z5 = np.nan_to_num(bars["z5"].to_numpy()); ch60 = np.nan_to_num(bars["ch60"].to_numpy())
    trig = np.abs(z5) >= 2.0
    bsel = np.flatnonzero(trig)
    dirs = np.where(ch60[bsel] > 0, 1, np.where(ch60[bsel] < 0, -1, 0)).astype(int)
    keep = dirs != 0
    bsel = bsel[keep]; dirs = dirs[keep]
    ent = np.searchsorted(ts, bts[bsel] + 1, "left")
    ok = ent < len(ts); ent = ent[ok]; dirs = dirs[ok]
    nL = int((dirs > 0).sum()); nS = int((dirs < 0).sum())
    X = {"n_entries": int(len(ent)), "n_LONG": nL, "n_SHORT": nS,
         "definition": "|z5|>=2; regime 60-bar change sign picks the side (long if >0, short if <0)",
         "horizons": {}}
    Hms = [60_000, 300_000, 900_000, 1_800_000, 3_600_000]
    for hm in Hms:
        ei, r = marks(ts, mid, seg, ent.astype(int), dirs, hm)
        if len(ei) < 5:
            X["horizons"][str(hm)] = {"n": int(len(ei))}
            continue
        leg = np.where(np.isin(ei, ei[dirs[:len(ei)] > 0]), "L", "S") if False else None
        # recompute legs cleanly
        j = np.searchsorted(ts, ts[ent] + hm, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[ent])
        e2, j2, d2 = ent[v], np.minimum(j, len(ts) - 1)[v], dirs[v]
        r2 = d2 * (mid[j2] - mid[e2]) / mid[e2] * 1e4
        isL = d2 > 0
        # matched exposure baseline: +7 days, same minute-of-day/weekday, same direction
        ctrl_t = ts[e2] + 7 * DAY
        ci = np.searchsorted(ts, ctrl_t, side="left")
        cv = (ci < len(ts)) & (seg[np.minimum(ci, len(ts) - 1)] == seg[np.minimum(ci, len(ts) - 1)])
        ci = np.minimum(ci, len(ts) - 1)
        cj = np.searchsorted(ts, ts[ci] + hm, side="left")
        cv2 = (cj < len(ts)) & (seg[np.minimum(cj, len(ts) - 1)] == seg[ci])
        c_ret = np.full(len(e2), np.nan)
        good = cv2 & (ts[ci] > ts[e2])
        c_ret[good] = d2[good] * (mid[np.minimum(cj, len(ts) - 1)[good]] - mid[ci[good]]) / mid[ci[good]] * 1e4
        alpha_meb = float(np.nanmean(r2) - np.nanmean(c_ret)) if np.isfinite(c_ret).sum() > 5 else None
        cut = ts[e2][0] + (ts[e2][-1] - ts[e2][0]) * 0.7
        ism, oosm = ts[e2] <= cut, ts[e2] > cut
        X["horizons"][str(hm)] = {
            "n": int(len(e2)), "effective_n": int(eff_n(e2, ts, hm)),
            "gross_bp": float(np.mean(r2)), "std_bp": float(np.std(r2)), "max_drawdown_bp": max_dd(r2),
            "net_bp": {f"x{x}": float(np.mean(r2) - COST * x) for x in (0., 1., 2., 3.)},
            "LONG": {"n": int(isL.sum()), "mean_bp": float(np.mean(r2[isL])) if isL.sum() else None,
                     "net1x_bp": float(np.mean(r2[isL]) - COST) if isL.sum() else None},
            "SHORT": {"n": int((~isL).sum()), "mean_bp": float(np.mean(r2[~isL])) if (~isL).sum() else None,
                      "net1x_bp": float(np.mean(r2[~isL]) - COST) if (~isL).sum() else None},
            "is": {"n": int(ism.sum()), "mean_bp": float(np.mean(r2[ism])) if ism.sum() >= 2 else None},
            "oos": {"n": int(oosm.sum()), "mean_bp": float(np.mean(r2[oosm])) if oosm.sum() >= 2 else None,
                    "net1x_bp": (float(np.mean(r2[oosm]) - COST) if oosm.sum() >= 2 else None)},
            "perm_p": perm_p(r2), "boot_ci_bp": boot_ci(r2),
            "alpha_matched_exposure_bp": alpha_meb,
            "meb_n": int(np.isfinite(c_ret).sum()),
            "temporal_blocks_monthly": {k: v for k, v in list(block_stats(ts, r2, pd.to_datetime((ts[e2] // DAY) * DAY, unit="ms", utc=True).strftime("%Y-%m").to_numpy()).items())},
        }
    res["W4"] = X
    blocked = nS < 30 or eff_n(ent[dirs < 0], ts, 3_600_000) < 30
    res["W4"]["X3MN_VERDICT"] = ("X3_REDESIGN_BLOCKED" if blocked else "COMPUTED")
    print(f"  X3MN n={len(ent)} L={nL} S={nS} verdict={res['W4']['X3MN_VERDICT']}")
    for hm, z in X["horizons"].items():
        if z.get("gross_bp") is not None:
            print(f"   h={int(hm)//60000:>3}m n={z['n']:>5} eff={z['effective_n']:>5} gross={z['gross_bp']:+.4f} "
                  f"net1x={z['gross_bp']-COST:+.4f} L={z['LONG']['mean_bp']} S={z['SHORT']['mean_bp']} "
                  f"IS={z['is']['mean_bp']} OOS={z['oos']['mean_bp']} p={z['perm_p']} CI={[round(x,2) for x in (z['boot_ci_bp'] or [])]} "
                  f"alpha_MEB={z['alpha_matched_exposure_bp']}")

    # ================= registries =================
    res["DATA_REGISTRY"] = {
        "UNION": {"snapshot": "union(MAIN,PIT2) deduped on (ts_utc,bid,ask)", "ticks": int(len(ts)),
                  "segments": int(seg[-1]) + 1, "bars_1m": int(len(bars)),
                  "span_utc": [str(dt[0]), str(dt[-1])], "active_days": int(len(days))},
        "MAIN": {"snapshot": "V3-SNAP-20260922T025312Z", "ticks": int(len(dm))},
        "PIT2": {"snapshot": "V3-SNAP-PIT2-20261001T131500Z", "ticks": int(len(dp))},
        "calendar": {"files": [os.path.basename(f) for f in sorted(glob.glob(os.path.join(vd, "*.json")))],
                     "raw_rows": len(rows)},
        "volume": "0 on 100% of ticks; no bid/ask size => TRUE_OFI_DATA_UNAVAILABLE",
        "sha256": {"main_manifest": "13fb5d1720a3b25768d0bca59eda897e85e66ba6d7741d538fc32ed33ef8eb54",
                   "event_registry": reg_sha}
    }
    json.dump(res["DATA_REGISTRY"], open(os.path.join(HERE, "DATA_REGISTRY.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(res, open(os.path.join(HERE, "results_v3_r3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("wrote results_v3_r3.json, DATA_REGISTRY.json, EVENT_REGISTRY.json")


if __name__ == "__main__":
    main()
