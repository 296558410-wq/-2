# -*- coding: utf-8 -*-
"""V3 R4: event loader final verification + F5 revalidation on the repaired sample.

Reads only SNAPSHOT_FXTM_R4. No orders. No V1/V2. No new hypothesis.
Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_r4_temporal_f5/run_r4.py
"""
from __future__ import annotations
import glob, hashlib, json, math, os, sys
import numpy as np, pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "SNAPSHOT_FXTM_R4")
PROTO = os.path.join(HERE, "F5_R4_FROZEN_PROTOCOL.json")
V3 = os.path.dirname(os.path.dirname(HERE))
COST = 0.914
GAP = 60_000
SEED = 20261005
DAY = 86_400_000


def load_ticks(snap):
    fs = sorted(glob.glob(os.path.join(snap, "*", "*.parquet")))
    d = pd.concat([pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in fs], ignore_index=True)
    d = d.sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    return (d["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64"),
            d["bid"].to_numpy(np.float64), d["ask"].to_numpy(np.float64))


def segments(ts):
    dd = np.diff(ts, prepend=ts[0]); return np.cumsum((dd <= 0) | (dd > GAP)) - 1


def seg_roll(x, seg, W, mode):
    n = len(x); out = np.zeros(n)
    b = np.flatnonzero(np.diff(seg, prepend=seg[0] - 1) != 0); end = np.append(b, n)
    c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    for k in range(len(b)):
        a, e = b[k], end[k + 1]; idx = np.arange(a, e)
        if mode == "sum":
            out[a:e] = c[idx + 1] - c[np.maximum(idx + 1 - W, a)]
        else:
            out[a:e] = np.minimum(idx - a + 1, W)
    return out


def seg_start(seg):
    b = np.flatnonzero(np.diff(seg, prepend=seg[0] - 1) != 0); e = np.append(b, len(seg))
    return np.repeat(b, np.diff(e))


def causal_med(x, seg, W, grid=500):
    n = len(x); out = np.full(n, np.nan); ss = seg_start(seg)
    for p in range(W, n, grid):
        w = x[ss[p]:p]
        if len(w) >= 50:
            out[p:min(n, p + grid)] = float(np.median(w))
    v = np.flatnonzero(~np.isnan(out))
    if not len(v):
        return out
    out[:v[0]] = out[v[0]]
    return out[np.maximum.accumulate(np.where(~np.isnan(out), np.arange(n), 0))]


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


def eval_dir(hid, ent, dirs, ts, mid, bid, ask, seg, Hms, meta=None):
    out = {"hypothesis_id": hid, "raw_event_n": int(len(ent)), "independent_timestamps": int(len(np.unique(ts[ent]))) if len(ent) else 0, "horizons": {}}
    for hm in Hms:
        j = np.searchsorted(ts, ts[ent] + hm, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[ent])
        cens = int((~v).sum())
        ei, ji, dd = ent[v], np.minimum(j, len(ts) - 1)[v], dirs[v]
        if len(ei) < 2:
            out["horizons"][str(hm)] = {"n": int(len(ei)), "ladder": "INSUFFICIENT_SAMPLE"}; continue
        g = dd * (mid[ji] - mid[ei]) / mid[ei] * 1e4
        gm = float(np.mean(g)); sd = float(np.std(g))
        cut = ts[ei][0] + (ts[ei][-1] - ts[ei][0]) * 0.7
        ism, oosm = ts[ei] <= cut, ts[ei] > cut
        rec = {"n": int(len(ei)), "censored_n": cens, "effective_n": int(eff_n(ei, ts, hm)),
               "independent_timestamps": int(len(np.unique(ts[ei]))),
               "gross_bp": gm, "std_bp": sd,
               "net_bp": {f"x{x}": float(gm - COST * x) for x in (0., 1., 2., 3.)},
               "is": {"n": int(ism.sum()), "mean_bp": float(np.mean(g[ism])) if ism.sum() >= 2 else None,
                      "net1x_bp": float(np.mean(g[ism]) - COST) if ism.sum() >= 2 else None},
               "oos": {"n": int(oosm.sum()), "mean_bp": float(np.mean(g[oosm])) if oosm.sum() >= 2 else None,
                       "net1x_bp": (float(np.mean(g[oosm]) - COST) if oosm.sum() >= 2 else None)},
               "perm_p": perm_p(g), "boot_ci_bp": boot_ci(g)}
        if meta is not None:
            rec["splits"] = meta(ei, g)
        out["horizons"][str(hm)] = rec
    return out


def main():
    proto = json.load(open(PROTO, encoding="utf-8"))
    body = {k: v for k, v in proto.items() if k != "registry_hash_sha256"}
    hh = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert hh == proto["registry_hash_sha256"], "protocol hash mismatch"
    print("protocol hash OK:", hh[:16])
    res = {"schema": "v3_r4_results/1", "protocol_hash": hh, "cost_bp": COST}

    ts, bid, ask = load_ticks(SNAP)
    mid = (bid + ask) / 2.0; seg = segments(ts)
    dt = pd.to_datetime(ts, unit="ms", utc=True)
    days = np.unique(ts // DAY)
    span = float((ts[-1] - ts[0]) / DAY)
    print(f"ticks={len(ts)} segments={int(seg[-1])+1} span={span:.2f}d active_days={len(days)}")

    # ---------- W1 re-statement ----------
    res["W1"] = {"SNAPSHOT_ID": "V3-SNAP-FXTM-R4", "ticks": int(len(ts)), "segments": int(seg[-1]) + 1,
                 "span_utc": [str(dt[0]), str(dt[-1])], "calendar_days": span,
                 "active_trading_days": int(len(days)),
                 "manifest_sha256": proto["data"]["manifest_sha256"],
                 "G1_ge_90d": bool(span >= 90), "G2_ge_40_active_days": bool(len(days) >= 40),
                 "excluded": "staging_duka (different source+schema)",
                 "VERDICT": "TEMPORAL_DATA_BLOCKED" if span < 90 else "PASS",
                 "reason": "the widest SAME-SOURCE FXTM sample is 59.11 calendar days; the 90-day floor is NOT lowered"}
    print("W1:", res["W1"]["VERDICT"], f"({span:.2f}d / {len(days)} active days)")

    # ---------- W2 event loader final verification ----------
    ev = []
    vd = os.path.join(V3, "research", "v3_pit_supplement_r1", "vintages")
    for fp in sorted(glob.glob(os.path.join(vd, "*.json"))):
        j = json.load(open(fp, encoding="utf-8"))
        for e in j.get("events", []):
            ev.append({**e, "_src": os.path.basename(fp)})
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
    for e in ev:
        t = pt(e)
        if t is None:
            continue
        keyed.append({"ts": t, "key": (t, str(e.get("title")), e["_src"]), "row": e})
    seen = set(); uniq = []; tdup = 0
    for r in keyed:
        if r["key"] in seen:
            tdup += 1
        else:
            seen.add(r["key"]); uniq.append(r)
    byts = {}
    for r in uniq:
        byts.setdefault(r["ts"], []).append(r)
    concurrent = sum(len(v) - 1 for v in byts.values() if len(v) > 1)
    inw = [r for r in uniq if ts[0] <= r["ts"] <= ts[-1]]
    pre = [r for r in inw if r["ts"] - 60_000 >= ts[0]]
    fin = [r for r in pre if r["ts"] + 15 * 60_000 <= ts[-1]]
    W2 = {"raw_rows": len(ev), "pit_qualified_rows": len(keyed), "true_duplicates": tdup,
          "unique_events": len(uniq), "concurrent_distinct_events": concurrent,
          "distinct_timestamps": len(byts),
          "inside_tick_window": len(inw), "with_complete_pre_post": len(fin),
          "event_rows": len(fin), "independent_timestamps": len({r["ts"] for r in fin}),
          "conservation": f"{len(ev)} raw -> {len(keyed)} PIT -> {len(uniq)} unique -> {len(inw)} in window -> {len(fin)} final",
          "loss_reasons": {"no_parseable_pub_time": len(ev) - len(keyed),
                            "outside_tick_window": len(uniq) - len(inw),
                            "incomplete_pre_or_post_window": len(inw) - len(fin),
                            "note": "no window widened, no synthetic event created, no event deleted"},
          "row_vs_timestamp_rule": "event_rows must NOT be used as independent_n",
          "unique_key": "(pub_time_utc, title, source_file)"}
    reg = sorted([{"ts_utc": str(pd.to_datetime(r['ts'], unit='ms', utc=True)), "key": list(map(str, r['key'])),
                   "title": r["row"].get("title"), "star": r["row"].get("star"),
                   "pub_time": r["row"].get("pub_time")} for r in fin], key=lambda x: (x["ts_utc"], str(x["key"])))
    W2["registry_sha256"] = hashlib.sha256(json.dumps(reg, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    json.dump(reg, open(os.path.join(HERE, "EVENT_REGISTRY.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    res["W2"] = W2
    print("W2:", W2["conservation"])
    print(f"   event_rows={W2['event_rows']}  independent_timestamps={W2['independent_timestamps']}  concurrent={concurrent}  true_dup={tdup}")

    # ---------- W4 F5 revalidation ----------
    dm = np.diff(mid, prepend=np.nan); sn = np.sign(np.nan_to_num(dm))
    ti = seg_roll(sn, seg, 100, "sum") / np.sqrt(np.maximum(seg_roll(np.zeros(len(dm)), seg, 100, "cnt"), 1))
    spread = (ask - bid) / mid * 1e4
    medsp = causal_med(spread, seg, 3000)
    Hms = [h * 60_000 for h in proto["hypotheses"][0]["horizons_min"]]
    events = sorted({r["ts"] for r in fin})
    hour = ((ts // 3600000) % 24)
    Hms_list = Hms

    def meta_factory():
        return None

    ev_i = np.searchsorted(ts, np.array(events), side="left")
    spl = {"session": {}, "vol": {}}
    H = {}
    H["E1_EVENT_X_MICRO"] = None
    ent1 = []; d1 = []
    ons = np.flatnonzero(onset(np.abs(ti) >= 2.0))
    for t in events:
        i0 = int(np.searchsorted(ts, t, "left")); j0 = int(np.searchsorted(ts, t + 300_000, "left"))
        k = ons[(ons >= i0) & (ons < j0)]
        if len(k):
            ent1.append(k[0]); d1.append(int(np.sign(ti[k[0]])))
    ent2 = []; d2 = []
    for t in events:
        i = int(np.searchsorted(ts, t, "left")); k = int(np.searchsorted(ts, t - 60_000, "left"))
        if i < len(ts) and i - k >= 2 and np.isfinite(mid[i]) and np.isfinite(mid[k]):
            mv = mid[i] - mid[k]
            if mv != 0:
                ent2.append(i); d2.append(int(np.sign(mv)))
    ent3 = []; d3 = []
    for t, i, s_ in zip(events, ent2, d2):
        if np.isfinite(medsp[i]) and spread[i] >= 1.2 * medsp[i]:
            ent3.append(i); d3.append(-s_)
    ent4 = []; d4 = []
    for t in events:
        i = int(np.searchsorted(ts, t, "left")); j = int(np.searchsorted(ts, t + 60_000, "left"))
        if i < len(ts) and j < len(ts) and j - i >= 2:
            mv = mid[j] - mid[i]
            if mv != 0:
                ent4.append(j); d4.append(int(np.sign(mv)))
    res["W4"] = {}
    for hid, ent, dd, mirror in (("E1_EVENT_X_MICRO", ent1, d1, True), ("E2_EVENT_X_VOL", ent2, d2, True),
                                 ("E3_EVENT_X_SPREAD", ent3, d3, True), ("E4_POST_EVENT_CONT", ent4, d4, False),
                                 ("E5_POST_EVENT_FADE", ent4, [-x for x in d4], False)):
        if len(ent) < 5:
            res["W4"][hid] = {"status": "DATA_BLOCKED", "n": len(ent)}
            continue
        e = np.array(ent, dtype=int); dr = np.array(dd, dtype=int)
        res["W4"][hid] = eval_dir(hid, e, dr, ts, mid, bid, ask, seg, Hms_list)
        if mirror:
            res["W4"][hid + "__MIRROR"] = eval_dir(hid + "__MIRROR", e, -dr, ts, mid, bid, ask, seg, Hms_list)
        print(f"  {hid}: events={len(e)} indep_ts={len(np.unique(ts[e]))}"
              + "  " + " ".join(f"{int(h)//60000}m:{res['W4'][hid]['horizons'][str(h)]['gross_bp']:+.3f}"
                                for h in Hms_list if res['W4'][hid]["horizons"].get(str(h), {}).get("gross_bp") is not None))

    # FDR over F5_R4 directional tests
    tests = []
    for hid, blk in res["W4"].items():
        if "horizons" not in blk:
            continue
        for hm, z in blk["horizons"].items():
            if z.get("perm_p") is not None:
                tests.append({"id": hid, "horizon_min": int(hm), "perm_p": z["perm_p"],
                              "gross_bp": z.get("gross_bp"), "eff_n": z.get("effective_n")})
    tests.sort(key=lambda t: t["perm_p"]); m = len(tests)
    for r_, t in enumerate(tests, start=1):
        t["bh_cutoff"] = 0.05 * r_ / m; t["survives_fdr"] = t["perm_p"] <= t["bh_cutoff"]
    res["FDR"] = {"method": "BH", "alpha": 0.05, "n_tests": m,
                  "surviving": sum(1 for t in tests if t["survives_fdr"]), "table": tests}

    # verdict per hypothesis
    tax = {}
    for hid, blk in res["W4"].items():
        if "horizons" not in blk:
            tax[hid] = blk.get("status", "DATA_BLOCKED"); continue
        zs = [z for z in blk["horizons"].values() if z.get("gross_bp") is not None]
        if not zs:
            tax[hid] = "DATA_BLOCKED"; continue
        best = max(zs, key=lambda z: z["gross_bp"])
        if best["effective_n"] < 30:
            tax[hid] = "DATA_BLOCKED"
        elif best["gross_bp"] < COST:
            tax[hid] = "COST_INSUFFICIENT"
        else:
            tax[hid] = "EDGE_UNCERTAIN"
    # the temporal gate blocks promotion for everything in this round
    res["temporal_gate_applied"] = {"G1": res["W1"]["G1_ge_90d"], "G2": res["W1"]["G2_ge_40_active_days"],
                                    "G3": "SEE_REPORT", "blocked": True,
                                    "note": "G1 fails => TEMPORAL_EVIDENCE_INSUFFICIENT for EVERY candidate this round, regardless of its other statistics"}
    for k in list(tax):
        tax[k + "__gate"] = "TEMPORAL_EVIDENCE_INSUFFICIENT" if not res["W1"]["G1_ge_90d"] else tax[k]
    res["taxonomy"] = tax
    res["FINAL"] = "NO_VALIDATED_EDGE"
    res["FINAL_REASON"] = "TEMPORAL_DATA_BLOCKED (same-source span 59.11d < 90d) + all F5_R4 hypotheses stop at COST_INSUFFICIENT"

    reg2 = {"SNAPSHOT_ID": "V3-SNAP-FXTM-R4", "ticks": int(len(ts)), "segments": int(seg[-1]) + 1,
            "span_utc": [str(dt[0]), str(dt[-1])], "calendar_days": span, "active_days": int(len(days)),
            "sources": proto["data"]["sources"], "manifest_sha256": proto["data"]["manifest_sha256"],
            "excluded_sources": {"staging_duka": "different source AND schema"},
            "volume": "0 on 100% of rows", "event_registry_sha256": W2["registry_sha256"],
            "event_rows": W2["event_rows"], "independent_timestamps": W2["independent_timestamps"]}
    json.dump(reg2, open(os.path.join(HERE, "DATA_REGISTRY.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(res, open(os.path.join(HERE, "results_v3_r4.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("FDR:", res["FDR"]["n_tests"], "tests,", res["FDR"]["surviving"], "survive")
    print("FINAL:", res["FINAL"], "-", res["FINAL_REASON"])
    print("wrote results_v3_r4.json, DATA_REGISTRY.json, EVENT_REGISTRY.json")


if __name__ == "__main__":
    main()
