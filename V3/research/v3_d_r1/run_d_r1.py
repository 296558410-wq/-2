# -*- coding: utf-8 -*-
"""V3 D-R1: event-microstructure measurement on the frozen PIT2 snapshot.

Reads ONLY the immutable snapshot + the two frozen calendar vintages.
No orders. No live feed. Protocol frozen before evaluation.

Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_d_r1/run_d_r1.py
"""
from __future__ import annotations
import glob, hashlib, json, os, sys
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
SNAP = os.path.join(V3, "data", "snapshots", "V3-SNAP-PIT2-20261001T131500Z")
PROTO = os.path.join(HERE, "FROZEN_PROTOCOL.json")
OUT = os.path.join(HERE, "results_d_r1.json")
CST = timezone(timedelta(hours=8))
GAP_MS = 60_000
SEED = 20261001


# ---------- load ----------
def load_ticks():
    files = sorted(glob.glob(os.path.join(SNAP, "raw_ticks", "*.parquet")))
    parts = [pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files]
    df = pd.concat(parts, ignore_index=True).sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    ts = df["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
    return ts, df["bid"].to_numpy(np.float64), df["ask"].to_numpy(np.float64)


def segment_ids(ts):
    d = np.diff(ts, prepend=ts[0])
    return np.cumsum((d <= 0) | (d > GAP_MS)) - 1


def load_events():
    ev = []
    vint = os.path.join(HERE, "..", "v3_pit_supplement_r1", "vintages")
    vint = os.path.normpath(vint)
    for fn in sorted(os.listdir(vint)):
        if not fn.endswith(".json"):
            continue
        v = json.load(open(os.path.join(vint, fn), encoding="utf-8"))
        for e in v["events"]:
            pt = e.get("pub_time")
            if not pt:
                continue
            try:
                t = datetime.strptime(pt, "%Y-%m-%d %H:%M").replace(tzinfo=CST).astimezone(timezone.utc)
            except Exception:  # noqa: BLE001
                continue
            ev.append({"vintage": fn, "name": e.get("event_name"), "country": e.get("country"),
                       "importance": e.get("importance"), "pub_utc": t,
                       "ts_ms": int(t.timestamp() * 1000)})
    prior = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(V3)), "v3_long_history_data", "V3_JIN10_EVENT_PIT.json"))
    if os.path.exists(prior):
        pj = json.load(open(prior, encoding="utf-8"))
        for e in pj["events"]:
            pu = e.get("pub_time_utc")
            if not pu:
                continue
            t = datetime.fromisoformat(pu)
            ev.append({"vintage": "V3_JIN10_EVENT_PIT.json", "name": e.get("event_name"),
                       "country": e.get("country"), "importance": e.get("importance"),
                       "pub_utc": t, "ts_ms": int(t.timestamp() * 1000)})
    ev.sort(key=lambda x: x["ts_ms"])
    return ev


# ---------- stats ----------
def signflip_perm_p(x, reps=2000, chunk=250):
    n = len(x)
    if n < 5:
        return None
    base = abs(float(np.mean(x)))
    rng = np.random.default_rng(SEED)
    ge = 0; done = 0; xf = x.astype(np.float32)
    while done < reps:
        c = min(chunk, reps - done)
        s = rng.integers(0, 2, size=(c, n)).astype(np.int8) * 2 - 1
        m = np.abs((xf[None, :] * s).mean(axis=1)).astype(np.float64)
        ge += int(np.sum(m >= base)); done += c
    return float((ge + 1) / (reps + 1))


def block_boot_ci(x, reps=2000, nblocks=50):
    n = len(x)
    if n < 10:
        return None
    bs = max(1, n // nblocks); nb = int(np.ceil(n / bs))
    pad = np.concatenate([x, np.full(nb * bs - n, np.nan)])
    blocks = np.nanmean(pad.reshape(nb, bs), axis=1)
    rng = np.random.default_rng(SEED + 1)
    return [float(np.percentile(blocks[rng.integers(0, nb, size=(reps, nb))].mean(axis=1), 2.5)),
            float(np.percentile(blocks[rng.integers(0, nb, size=(reps, nb))].mean(axis=1), 97.5))]


def effective_n(ei, ts, horizon_ms):
    if len(ei) == 0:
        return 0
    t = ts[ei]; cnt = 1; last = t[0]
    for x in t[1:]:
        if x - last >= horizon_ms:
            cnt += 1; last = x
    return cnt


def ladder(eff, gross, net1x, net2x, p, oos1x, std):
    if eff < 30:
        return "INSUFFICIENT_SAMPLE"
    if gross < 0.914:
        return "COST_INSUFFICIENT"
    if net1x <= 0:
        return "REJECT"
    if p is None or p >= 0.05 or (oos1x is not None and oos1x <= 0):
        return "EDGE_UNCERTAIN"
    if net2x <= 0:
        return "EDGE_UNCERTAIN"
    if std > 5 * abs(gross):
        return "EXECUTION_UNREALISTIC"
    return "CANDIDATE"


def main():
    proto = json.load(open(PROTO, encoding="utf-8"))
    body = {k: v for k, v in proto.items() if k != "registry_hash_sha256"}
    h = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert h == proto["registry_hash_sha256"], "protocol hash mismatch"
    print("protocol hash OK:", h[:16])

    ts, bid, ask = load_ticks()
    mid = (bid + ask) / 2.0
    seg = segment_ids(ts)
    spread_bp = (ask - bid) / mid * 1e4
    print("ticks", len(ts), "segments", int(seg[-1]) + 1)

    events = load_events()
    lo, hi = ts[0], ts[-1]
    inwin = [e for e in events if lo <= e["ts_ms"] <= hi]
    print("events total", len(events), "in snapshot window", len(inwin))

    cost = proto["cost_model"]["REAL_RT_COST_BP"]
    HOR = proto["frozen_thresholds"]["horizons_s"]
    LOOK = proto["frozen_thresholds"]["pre_event_lookback_s"]

    # entry tick per event (first tick >= pub_time, same segment for lookback)
    recs = []
    for e in inwin:
        i = int(np.searchsorted(ts, e["ts_ms"], side="left"))
        if i >= len(ts):
            continue
        recs.append({**e, "i": i})
    print("events with an entry tick:", len(recs))

    res = {"schema": "v3_d_r1_results/1", "protocol_hash": h,
           "snapshot": "V3-SNAP-PIT2-20261001T131500Z", "ticks": int(len(ts)),
           "window_utc": [str(pd.to_datetime(lo, unit="ms", utc=True)), str(pd.to_datetime(hi, unit="ms", utc=True))],
           "events_total": len(events), "events_in_window": len(inwin), "events_with_entry": len(recs),
           "hypotheses": {}}

    # ---- D1 directional ----
    ev_i = np.array([r["i"] for r in recs], dtype=int)
    e_ts = ts[ev_i]
    lb_target = ts[ev_i] - LOOK * 1000
    lb_i = np.searchsorted(ts, lb_target, side="left")
    same = seg[np.minimum(lb_i, len(ts) - 1)] == seg[ev_i]
    pre_dir = np.sign(mid[ev_i] - mid[np.minimum(lb_i, len(ts) - 1)])
    print("events with a valid 60s pre-window:", int(same.sum()), "non-zero pre_dir:", int((pre_dir[same] != 0).sum()))

    for hid, sign in (("D1_EVENT_DRIFT_CONT", +1), ("D1_EVENT_DRIFT_FADE", -1)):
        entry = {"hypothesis_id": hid, "horizons": {}}
        m = same & (pre_dir != 0)
        idx = ev_i[m]; d = (sign * pre_dir[m]).astype(int)
        for hs in HOR:
            hm = hs * 1000
            j = np.searchsorted(ts, ts[idx] + hm, side="left")
            v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[idx])
            cens = int((~v).sum())
            ei, ji, dd = idx[v], np.minimum(j, len(ts) - 1)[v], d[v]
            if len(ei) < 1:
                entry["horizons"][str(hs)] = {"n": 0}
                continue
            g = dd * (mid[ji] - mid[ei]) / mid[ei] * 1e4
            eff = effective_n(ei, ts, hm)
            cut = ts[ei][0] + (ts[ei][-1] - ts[ei][0]) * 0.7
            ism, oosm = ts[ei] <= cut, ts[ei] > cut
            gm = float(np.mean(g))
            entry["horizons"][str(hs)] = {
                "n": int(len(ei)), "censored_n": cens, "effective_n": int(eff),
                "mid_mean_bp": gm, "mid_median_bp": float(np.median(g)), "mid_std_bp": float(np.std(g)),
                "net_mean_bp_by_cost": {f"x{x}": float(gm - cost * x) for x in (0.0, 1.0, 2.0, 3.0)},
                "is": {"n": int(ism.sum()), "mean_bp": float(np.mean(g[ism])) if ism.sum() >= 2 else None},
                "oos": {"n": int(oosm.sum()), "mean_bp": float(np.mean(g[oosm])) if oosm.sum() >= 2 else None},
                "perm_p": signflip_perm_p(g), "boot_ci": block_boot_ci(g),
                "ladder": ladder(eff, gm, gm - cost, gm - 2 * cost, signflip_perm_p(g),
                                 (float(np.mean(g[oosm]) - cost) if oosm.sum() >= 2 else None), float(np.std(g))),
            }
        entry["events_used"] = int(m.sum())
        res["hypotheses"][hid] = entry

    # ---- D2 non-directional magnitude vs baseline ----
    base_idx = np.arange(0, len(ts), 50)
    d2 = {"hypothesis_id": "D2_EVENT_MAGNITUDE", "baseline_n": int(len(base_idx)), "horizons": {}}
    for hs in HOR:
        hm = hs * 1000
        def mag(idx):
            j = np.searchsorted(ts, ts[idx] + hm, side="left")
            v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[idx])
            a, b = idx[v], np.minimum(j, len(ts) - 1)[v]
            return a, np.abs(mid[b] - mid[a]) / mid[a] * 1e4
        ae, av = mag(ev_i)
        be, bv = mag(base_idx)
        if len(av) < 10 or len(bv) < 10:
            d2["horizons"][str(hs)] = {"status": "INSUFFICIENT_SAMPLE", "n": int(len(av))}
            continue
        hit, bhit = float(np.mean(av > cost)), float(np.mean(bv > cost))
        rng = np.random.default_rng(SEED)
        diffs = np.array([float(np.mean(av[rng.integers(0, len(av), len(av))] > cost)
                               - np.mean(bv[rng.integers(0, len(bv), len(bv))] > cost)) for _ in range(2000)])
        lo_, hi_ = float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))
        d2["horizons"][str(hs)] = {"n": int(len(av)), "mean_abs_move_bp": float(np.mean(av)),
                                   "baseline_mean_abs_move_bp": float(np.mean(bv)),
                                   "p_gt_cost": hit, "baseline_p_gt_cost": bhit, "lift": hit - bhit,
                                   "boot_ci_lift": [lo_, hi_],
                                   "verdict": "MORE_VOLATILE" if lo_ > 0 else "NOT_MORE_VOLATILE"}
    res["hypotheses"]["D2_EVENT_MAGNITUDE"] = d2

    # ---- D3 spread response (descriptive) ----
    W = 3000
    starts = np.flatnonzero(np.diff(seg, prepend=seg[0] - 1) != 0)
    bounds = np.append(starts, len(seg))
    seg_start = np.repeat(starts, np.diff(bounds))
    med = np.full(len(ts), np.nan)
    for p in range(W, len(ts), 500):
        a = int(seg_start[p])
        w = spread_bp[a:p]
        if len(w) >= 50:
            med[p:min(len(ts), p + 500)] = float(np.median(w))
    valid = np.flatnonzero(~np.isnan(med))
    med = med[np.maximum.accumulate(np.where(~np.isnan(med), np.arange(len(ts)), 0))] if len(valid) else med
    ratio = spread_bp[ev_i] / np.where(med[ev_i] > 0, med[ev_i], np.nan)
    d3 = {"hypothesis_id": "D3_EVENT_SPREAD_RESPONSE", "n": int(np.sum(np.isfinite(ratio))),
          "spread_ratio_median": float(np.nanmedian(ratio)), "spread_ratio_mean": float(np.nanmean(ratio)),
          "frac_above_1p10": float(np.nanmean(ratio > 1.10)), "frac_below_0p90": float(np.nanmean(ratio < 0.90))}
    res["hypotheses"]["D3_EVENT_SPREAD_RESPONSE"] = d3

    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT)
    for k, v in res["hypotheses"].items():
        if k.startswith("D1"):
            print(f"{k}: used={v['events_used']}")
            for hs, z in v["horizons"].items():
                if z.get("n"):
                    print(f"   h={hs:>4}s n={z['n']:>4} eff={z['effective_n']:>4} mean={z['mid_mean_bp']:+.4f}bp p={z['perm_p']} -> {z['ladder']}")
        elif k == "D2_EVENT_MAGNITUDE":
            for hs, z in v["horizons"].items():
                print(f"   D2 h={hs:>4}s {z.get('verdict')} lift={z.get('lift')}")
        else:
            print(k, json.dumps(v, ensure_ascii=False)[:200])


if __name__ == "__main__":
    main()
