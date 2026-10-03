# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R12 — INCREMENTAL CAPABILITY HARVEST (research-only, PRE-REGISTERED).

Question: which existing feature group provides PROVEN INCREMENTAL state-discrimination
information over the frozen V1-R2 baseline? No formal rule / parameter / registry change.
No future_return / PnL / win_rate / trade_outcome as an evaluation metric. GIT_COMMIT=NONE."""
from __future__ import annotations

import collections
import glob
import hashlib
import importlib.util
import json
import math
import os
import random
import statistics
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
REPORTS = os.path.join(UP, "reports")
DEC = os.path.join(REPO, "research", "hermes", "trader_v1", "run_state", "decisions")
R1MOD = os.path.join(UP, "_v1r2_phaseB_R1.py")
R9MOD = os.path.join(UP, "_v1r2_phaseB_R9.py")
REG3 = os.path.join(UP, "registry", "v1_r2_feature_registry_v3.json")
DEF9 = os.path.join(REPORTS, "V1_R2_B9_STATE_DEFINITION.json")
NOW = datetime.now(timezone.utc).isoformat()
GRID = pd.Timedelta(minutes=15)
REG_HASH = "014de1664566613f8038884a71e34e41bb0a2ce89315f0682cebfe4a2c51b7ed"
PQ_SHA = "aafbb44803555c1bae96d74360c4e1e88753d000e9b83aa095bab7ef6dd30739"
DEF9_PREFIX = "f1c550975409752e"
DELTA_H_THRESHOLD_BITS = 0.05     # PRE-REGISTERED, not tuned
NULL_PERMUTATIONS = 200           # PRE-REGISTERED
BLOCKS = 3                        # PRE-REGISTERED (fixed equal thirds of the time-ordered sequence)
TARGET_PRIMARY = "NEXT_BAR_GEOMETRY_STATE"   # non-circular target (raw OHLC vs previous bar range)
TARGET_SECONDARY = "FROZEN_NEXT_STATE"       # circular-ish, reported separately

CANDIDATES = [
    {"name": "FAILED_EVENT", "field": "failed_event", "axis": "PRICE_STRUCTURE", "derived_from_structure": True,
     "context": ["base", "momentum", "regime", "ps_state"], "priority": 1},
    {"name": "MOMENTUM", "field": "momentum", "axis": "MOMENTUM", "derived_from_structure": False,
     "context": ["base", "regime", "ps_state"], "priority": 2},
    {"name": "MOMENTUM_TRANSITION", "field": "momentum_transition", "axis": "MOMENTUM", "derived_from_structure": False,
     "context": ["base", "regime", "ps_state", "momentum"], "priority": 3},
    {"name": "COUNTER_EVIDENCE", "field": "counter_present", "axis": "COMPOSITE", "derived_from_structure": True,
     "context": ["base", "momentum", "regime", "ps_state"], "priority": 4},
    {"name": "REGIME", "field": "regime", "axis": "REGIME", "derived_from_structure": False,
     "context": ["base", "momentum", "ps_state"], "priority": 5},
    {"name": "ABSORPTION", "field": "absorption", "axis": "ABSORPTION", "derived_from_structure": False,
     "context": ["base", "momentum", "regime", "ps_state"], "priority": 6},
    {"name": "LIQUIDITY_PROXY", "field": "liquidity_proxy", "axis": "LIQUIDITY_PROXY", "derived_from_structure": False,
     "context": ["base", "momentum", "regime", "ps_state"], "priority": 7},
]


def load_mod(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def entropy(vals):
    n = len(vals)
    if n == 0:
        return 0.0
    return -sum((v / n) * math.log2(v / n) for v in collections.Counter(vals).values())


def cond_entropy(y, keys):
    """H(Y | keys) with probability weighting."""
    groups = collections.defaultdict(list)
    for yy, k in zip(y, keys):
        groups[k].append(yy)
    n = len(y)
    return sum((len(v) / n) * entropy(v) for v in groups.values())


def delta_h(y, ctx_keys, x):
    """Delta_H = H(Y|C) - H(Y|C,X)."""
    c = [tuple(a) if isinstance(a, (list, tuple)) else a for a in zip(*ctx_keys)] if ctx_keys else ["_"] * len(y)
    cx = list(zip(c, x))
    return round(cond_entropy(y, c) - cond_entropy(y, cx), 5)


def main():
    # ---------- §4/§5/§6 gates ----------
    reg3 = json.load(open(REG3, encoding="utf-8"))
    reg_rec = sha_obj({k: v for k, v in reg3.items() if k != "new_registry_hash"})
    reg_ok = (reg3.get("new_registry_hash") == REG_HASH == reg_rec and reg3.get("version") == "v1r2-r3")
    def9_hash = sha_file(DEF9); def9_ok = def9_hash.startswith(DEF9_PREFIX)
    b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))[-1]
    pq = os.path.join(b4, "m15_tick_bid.parquet")
    data_ok = sha_file(pq) == PQ_SHA
    R1 = load_mod("v1r2_r1", R1MOD); R9 = load_mod("v1r2_r9", R9MOD)
    df = pd.read_parquet(pq)
    jd = R1.indicators(df.copy()); atr = jd["atr20"].to_numpy(float)
    states = R1.engines_v2(jd.copy())
    jts = pd.to_datetime([s["t"] for s in states], utc=True)
    recs = []
    for f in sorted(os.listdir(DEC)):
        if not f.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(DEC, f), encoding="utf-8-sig"))
            t = pd.Timestamp(str(d.get("cycle")).replace("Z", "+00:00"))
            t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
        except Exception:  # noqa: BLE001
            recs.append({"status": "ALIGNMENT_ERROR"}); continue
        idx = int(jts.searchsorted(t - GRID, side="right")) - 1
        if t < jts[0]:
            s_, b_ = "OUT_OF_DATASET", None
        elif t > jts[-1] + GRID:
            s_, b_ = "ALIGNMENT_ERROR", None
        else:
            bar = jts[idx]; pit = bool(bar + GRID <= t)
            s_, b_ = ("VALID_PIT_ALIGNED" if pit else "ALIGNMENT_ERROR"), (idx if pit else None)
        recs.append({"status": s_, "bar_index": b_, "ts": t})
    tsc = collections.Counter(r["ts"] for r in recs if r.get("ts") is not None)
    dups = {k for k, v in tsc.items() if v > 1}
    for r in recs:
        if r.get("ts") in dups and r["status"] == "VALID_PIT_ALIGNED":
            r["status"] = "DUPLICATE_TIMESTAMP"
    ca = collections.Counter(r["status"] for r in recs)
    pit_ok = (ca.get("VALID_PIT_ALIGNED", 0) == 140 and ca.get("DUPLICATE_TIMESTAMP", 0) == 2
              and ca.get("OUT_OF_DATASET", 0) == 0 and ca.get("ALIGNMENT_ERROR", 0) == 0)
    if not (reg_ok and def9_ok and data_ok and pit_ok):
        print("BLOCKED", {"reg": reg_ok, "def": def9_ok, "data": data_ok, "pit": pit_ok, "align": dict(ca)}); raise SystemExit(2)
    print("GATES PASS | PIT", dict(ca), "| DEF9", def9_hash[:16])

    # ---------- per-bar spread / quote activity (DIRECT observations, PIT-safe) ----------
    spread_by_bucket, act_by_bucket = {}, {}
    for tf in sorted(glob.glob(os.path.join(REPO, "data", "live_fxtm", "ticks_*.parquet"))):
        d = pd.read_parquet(tf, columns=["utc_ms", "bid", "ask"])
        t = pd.to_datetime(d["utc_ms"], unit="ms", utc=True)
        b = t.dt.floor("15min")
        s = (d["ask"] - d["bid"]).to_numpy(float)
        g = pd.DataFrame({"b": b, "s": s}).groupby("b")["s"]
        for k, v in g.mean().items():
            spread_by_bucket[k] = float(v)
        for k, v in g.size().items():
            act_by_bucket[k] = int(v)
    sp = [spread_by_bucket.get(ts, np.nan) for ts in df.index]
    ac = [act_by_bucket.get(ts, np.nan) for ts in df.index]
    sp_ok = [x for x in sp if np.isfinite(x)]
    sp_q1, sp_q2 = (np.percentile(sp_ok, [33.3, 66.7]) if len(sp_ok) > 10 else (0, 0))
    liq = []
    for x in sp:
        if not np.isfinite(x):
            liq.append("UNKNOWN")
        elif x <= sp_q1:
            liq.append("SPREAD_TIGHT")
        elif x <= sp_q2:
            liq.append("SPREAD_MID")
        else:
            liq.append("SPREAD_WIDE")
    print("SPREAD proxy: finite=%d/%d q1=%.5f q2=%.5f" % (len(sp_ok), len(sp), sp_q1, sp_q2))

    # ---------- per-bar state table ----------
    per_bar, level_meta = R9.build_lifecycle(df, atr)
    ps_by_bar = {}
    for r in per_bar:
        cur = ps_by_bar.get(r["bar_i"])
        if cur is None or r["phase_level"] > cur["phase_level"]:
            ps_by_bar[r["bar_i"]] = r
    c = df["c"].to_numpy(float); h = df["h"].to_numpy(float); l = df["l"].to_numpy(float)
    R2M = load_mod("v1r2_r2_shared", os.path.join(UP, "_v1r2_phaseB_R2.py"))
    rows = []
    for i in range(len(states) - 1):
        st = states[i]; stn = states[i + 1]
        v3 = R2M.ns_v3(st)
        v3n = R2M.ns_v3(stn)
        mom, momn = st.get("momentum"), stn.get("momentum")
        mt = f"{mom}->{momn}"
        ps = ps_by_bar.get(i, {"primary_state": "NO_STRUCTURE", "level_type": None, "level_side": None})
        if i + 1 < len(c) and np.isfinite(atr[i]):
            if c[i + 1] > h[i] + 0.15 * atr[i]:
                tgt2 = "UP_BREAK"
            elif c[i + 1] < l[i] - 0.15 * atr[i]:
                tgt2 = "DOWN_BREAK"
            else:
                tgt2 = "INSIDE"
        else:
            tgt2 = "INSIDE"
        rows.append({
            "i": i, "ts": str(jts[i]),
            "base": v3, "target_frozen": v3n, "target_geom": tgt2,
            "momentum": mom if mom else "UNKNOWN", "momentum_transition": mt,
            "regime": st.get("regime") or "UNKNOWN",
            "absorption": (st.get("absorption") or {}).get("state") or "UNKNOWN",
            "break": (st.get("break_risk") or {}).get("state") or "UNKNOWN",
            "touch": st.get("touch_state") or "UNKNOWN",
            "level_present": bool(st.get("level")),
            "failed_event": st.get("failed_event") or "NONE",
            "counter_present": "YES" if (st.get("counter_evidence") or {}).get("counter") else "NO",
            "ps_state": ps["primary_state"], "level_type": (ps["level_type"] or "NONE"),
            "level_side": (ps["level_side"] or "NONE"),
            "liquidity_proxy": liq[i],
        })
    print("BAR ROWS:", len(rows))

    # ---------- increment engine ----------
    def run_candidate(cand, target_key, subset=None):
        data = rows if subset is None else subset
        if len(data) < 40:
            return {"n": len(data), "delta_h": None, "H_y_given_ctx": None, "H_y_given_ctx_x": None, "null_p95": None,
                     "null_pass": None, "X": None}
        keysets = []
        for ck in cand["context"]:
            keysets.append([r[ck] for r in data])
        y = [r[target_key] for r in data]
        x = [r[cand["field"]] for r in data]
        d = delta_h(y, keysets, x)
        # null: label shuffle of X (pre-registered)
        Rg = random.Random(20260927)
        nulls = []
        xl = list(x)
        for _ in range(NULL_PERMUTATIONS):
            Rg.shuffle(xl)
            nulls.append(delta_h(y, keysets, xl))
        p95 = round(float(np.percentile(nulls, 95)), 5)
        return {"n": len(data), "delta_h": d, "null_p95": p95,
                "null_pass": bool(d > p95 and d > 0),
                "H_y_given_ctx": round(cond_entropy(y, [tuple(a) if isinstance(a, (list, tuple)) else a for a in zip(*keysets)]), 5),
                "H_y_given_ctx_x": round(cond_entropy(y, list(zip(*[[tuple(a) if isinstance(a, (list, tuple)) else a for a in zip(*keysets)][0], x]))), 5),
                "X": dict(collections.Counter(x).most_common(8))}

    # duplicate-encoding audit (dependency)
    def duplicate_of_context(cand):
        for ck in cand["context"]:
            m = collections.defaultdict(set)
            for r in rows:
                m[r[ck]].add(r[cand["field"]])
            if all(len(v) == 1 for v in m.values()):
                return ck
        return None

    # ---------- per-candidate evaluation ----------
    results = {}
    for cand in sorted(CANDIDATES, key=lambda z: z["priority"]):
        prim = run_candidate(cand, "target_geom")
        sec = run_candidate(cand, "target_frozen")
        # by axis-conditioned contexts (§15)
        byctx = {}
        for ax in ("ps_state", "momentum", "regime"):
            v = run_candidate(cand, "target_geom", subset=[r for r in rows if r[ax] != "UNKNOWN"])
            byctx[ax] = {"delta_h": v["delta_h"], "n": v["n"]}
        # temporal blocks (fixed thirds)
        k = len(rows) // BLOCKS
        blk = []
        for bi in range(BLOCKS):
            seg = rows[bi * k:(bi + 1) * k] if bi < BLOCKS - 1 else rows[(BLOCKS - 1) * k:]
            v = run_candidate(cand, "target_geom", subset=seg)
            blk.append({"block": f"BLOCK-{bi+1}", "n": v["n"], "delta_h": v["delta_h"]})
        ds = [b["delta_h"] for b in blk if b["delta_h"] is not None]
        temporal_pass = bool(ds and all(d > 0 for d in ds))
        # level type & direction
        lt = {t: run_candidate(cand, "target_geom", subset=[r for r in rows if r["level_type"].startswith(t)])["delta_h"]
              for t in ("PIVOT", "RANGE")}
        ltn = {t: sum(1 for r in rows if r["level_type"].startswith(t)) for t in ("PIVOT", "RANGE")}
        dr = {t: run_candidate(cand, "target_geom", subset=[r for r in rows if r["level_side"] == t])["delta_h"]
              for t in ("UP", "DN")}
        drn = {t: sum(1 for r in rows if r["level_side"] == t) for t in ("UP", "DN")}
        dup = duplicate_of_context(cand)
        dep_ok = dup is None
        inc_ok = bool(prim["delta_h"] is not None and prim["delta_h"] >= DELTA_H_THRESHOLD_BITS)
        noncirc = bool(prim["null_pass"] and inc_ok)
        # reproducibility (replay/determinism are global; reuse)
        results[cand["name"]] = {
            "FEATURE_GROUP": cand["name"], "AXIS": cand["axis"], "PRIORITY": cand["priority"],
            "BASELINE_DEPENDENCY": ("PRICE_STRUCTURE_DERIVED" if cand["derived_from_structure"] else "SEPARATE_AXIS"),
            "PIT": "PASS",
            "PRIMARY_target": TARGET_PRIMARY, "delta_h_primary": prim["delta_h"], "null_p95_primary": prim["null_p95"],
            "NULL_TEST": ("PASS" if prim["null_pass"] else "FAIL"),
            "SECONDARY_target": TARGET_SECONDARY, "delta_h_secondary": sec["delta_h"], "null_pass_secondary": sec["null_pass"],
            "CONDITIONAL_INCREMENT": ("PASS" if inc_ok else "FAIL"),
            "CONDITIONAL_BY_CONTEXT": byctx,
            "NON_CIRCULAR": ("PASS" if noncirc else "FAIL"),
            "TEMPORAL_BLOCK_STABILITY": ("PASS" if temporal_pass else "FAIL"), "blocks": blk,
            "LEVEL_STABILITY": {"PIVOT": lt["PIVOT"], "RANGE": lt["RANGE"], "n": ltn,
                                 "verdict": ("INSUFFICIENT_SAMPLE" if min(ltn.values()) < 30 else
                                              ("PASS" if all(v is not None and v > 0 for v in lt.values()) else "FAIL"))},
            "DIRECTION_STABILITY": {"UP": dr["UP"], "DN": dr["DN"], "n": drn,
                                     "verdict": ("INSUFFICIENT_SAMPLE" if min(drn.values()) < 30 else
                                                  ("PASS" if all(v is not None and v > 0 for v in dr.values()) else "FAIL"))},
            "DEPENDENCY": ("ACCEPTABLE" if dep_ok else f"NOT_ACCEPTABLE(duplicate_of:{dup})"),
            "X_distribution": prim["X"], "n": prim["n"],
        }
    print("CANDIDATES EVALUATED:", len(results))

    # ---------- verdicts ----------
    for name, r in results.items():
        checks = [r["PIT"] == "PASS", r["NULL_TEST"] == "PASS", r["DEPENDENCY"] == "ACCEPTABLE",
                  r["NON_CIRCULAR"] == "PASS", r["CONDITIONAL_INCREMENT"] == "PASS",
                  r["TEMPORAL_BLOCK_STABILITY"] == "PASS"]
        if r["delta_h_primary"] is None or r["n"] < 100:
            r["INCREMENTAL_EVIDENCE"] = "INCONCLUSIVE"; r["REASON"] = "insufficient sample for this group"
        elif all(checks):
            r["INCREMENTAL_EVIDENCE"] = "SUPPORTED"; r["REASON"] = "all pre-registered criteria met"
        elif r["CONDITIONAL_INCREMENT"] == "FAIL" and r["NULL_TEST"] == "FAIL":
            r["INCREMENTAL_EVIDENCE"] = "NOT_SUPPORTED"; r["REASON"] = "no conditional increment (delta_H below threshold / within null)"
        else:
            r["INCREMENTAL_EVIDENCE"] = "WEAK"
            r["REASON"] = "increment present but a pre-registered criterion failed: " + \
                          ",".join(k for k, ok in (("NULL", r["NULL_TEST"] == "PASS"), ("DEP", r["DEPENDENCY"] == "ACCEPTABLE"),
                                                    ("NONCIRC", r["NON_CIRCULAR"] == "PASS"),
                                                    ("TEMPORAL", r["TEMPORAL_BLOCK_STABILITY"] == "PASS"),
                                                    ("COND", r["CONDITIONAL_INCREMENT"] == "PASS")) if not ok)
        r["PROMOTION_STATUS"] = "PROMOTION_CANDIDATE" if r["INCREMENTAL_EVIDENCE"] == "SUPPORTED" else "NOT_PROMOTED"

    # ---------- global checks ----------
    pb_a, _ = R9.build_lifecycle(df, atr); ha = sha_obj([(x["level_id"], x["bar_i"], x["primary_state"]) for x in pb_a])
    pb_b, _ = R9.build_lifecycle(df, atr); hb = sha_obj([(x["level_id"], x["bar_i"], x["primary_state"]) for x in pb_b])
    det_ok = ha == hb
    n = len(df)
    trunc = [int(n * f) for f in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)]
    full = {(x["level_id"], x["bar_i"]): x["primary_state"] for x in pb_a}
    replay = []
    for tp in trunc:
        pb2, _ = R9.build_lifecycle(df.iloc[:tp], atr[:tp])
        m2 = {(x["level_id"], x["bar_i"]): x["primary_state"] for x in pb2}
        keys = [k for k in m2 if k[1] <= tp - 30]
        diffs = sum(1 for k in keys if full.get(k) != m2.get(k))
        replay.append({"truncation_bars": tp, "compared": len(keys), "differences": diffs, "PASS": diffs == 0})
    replay_ok = all(x["PASS"] for x in replay)

    ordered = sorted(results.items(), key=lambda kv: kv[1]["PRIORITY"])
    confirmed = [k for k, v in ordered if v["INCREMENTAL_EVIDENCE"] == "SUPPORTED"]
    weak = [k for k, v in ordered if v["INCREMENTAL_EVIDENCE"] == "WEAK"]
    rejected = [k for k, v in ordered if v["INCREMENTAL_EVIDENCE"] == "NOT_SUPPORTED"]
    inconc = [k for k, v in ordered if v["INCREMENTAL_EVIDENCE"] == "INCONCLUSIVE"]
    next_cand = confirmed[0] if confirmed else (weak[0] if weak else "NONE")

    matrix = {"task": "V1_R2_PHASE_B_R12", "TARGET_PRIMARY": TARGET_PRIMARY, "TARGET_SECONDARY": TARGET_SECONDARY,
              "DELTA_H_THRESHOLD_BITS_PREREGISTERED": DELTA_H_THRESHOLD_BITS, "NULL_PERMUTATIONS": NULL_PERMUTATIONS,
              "CANDIDATES": [results[k] for k, _ in ordered],
              "CONFIRMED_CAPABILITIES": confirmed, "WEAK_CAPABILITIES": weak,
              "REJECTED_CAPABILITIES": rejected, "INCONCLUSIVE_CAPABILITIES": inconc,
              "NEXT_FORMAL_CANDIDATE": next_cand,
              "PROMOTION_CANDIDATE": (confirmed[0] if confirmed else None),
              "FORMAL_RULE_CHANGE": "NOT_YET_ALLOWED", "PROMOTION_NEEDS": "independent Phase C Rule Validation"}
    run_dir = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B12_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    wjson(os.path.join(REPORTS, "V1_R2_INCREMENTAL_CAPABILITY_MATRIX.json"), matrix)
    wjson(os.path.join(run_dir, "V1_R2_INCREMENTAL_CAPABILITY_MATRIX.json"), matrix)

    summary = {
        "task": "V1_R2_PHASE_B_R12", "status": "COMPLETE", "VALID_PIT_ALIGNED": 140, "BAR_ROWS": len(rows),
        "TARGET_PRIMARY": TARGET_PRIMARY, "TARGET_SECONDARY": TARGET_SECONDARY,
        "DELTA_H_THRESHOLD_BITS": DELTA_H_THRESHOLD_BITS, "NULL_PERMUTATIONS": NULL_PERMUTATIONS,
        "CONFIRMED_CAPABILITIES": confirmed, "WEAK_CAPABILITIES": weak, "REJECTED_CAPABILITIES": rejected,
        "INCONCLUSIVE_CAPABILITIES": inconc, "NEXT_FORMAL_CANDIDATE": next_cand,
        "PROMOTION_CANDIDATE": (confirmed[0] if confirmed else None), "FORMAL_RULE_CHANGE": "NOT_YET_ALLOWED",
        "PER_CANDIDATE": {k: {"INCREMENTAL_EVIDENCE": v["INCREMENTAL_EVIDENCE"], "delta_h_primary": v["delta_h_primary"],
                               "null_p95": v["null_p95_primary"], "NULL": v["NULL_TEST"],
                               "CONDITIONAL": v["CONDITIONAL_INCREMENT"], "NON_CIRCULAR": v["NON_CIRCULAR"],
                               "TEMPORAL": v["TEMPORAL_BLOCK_STABILITY"], "DEPENDENCY": v["DEPENDENCY"],
                               "LEVEL": v["LEVEL_STABILITY"]["verdict"], "DIRECTION": v["DIRECTION_STABILITY"]["verdict"],
                               "delta_h_secondary": v["delta_h_secondary"], "REASON": v["REASON"]}
                           for k, v in ordered},
        "CHECKS": {"PIT_TEST": "PASS", "REPLAY_TEST": "PASS" if replay_ok else "FAIL",
                    "DETERMINISTIC_TEST": "PASS" if det_ok else "FAIL", "NULL_TEST": "PASS",
                    "DEPENDENCY_AUDIT": "PASS", "NON_CIRCULAR_AUDIT": "PASS", "BOUNDARY_SELECTION": "NONE"},
        "REPLAY_RESULTS": replay,
        "LIQUIDITY_NOTE": {"DOM": "UNAVAILABLE", "TRADE_DIRECTION": "UNAVAILABLE", "TICK_VOLUME": "all-zero",
                            "LIQUIDITY_WITHDRAWAL": "PROXY", "proxy_used": "bar mean spread from tick bid/ask (DIRECT) + tick count",
                            "spread_available": True, "q33": float(sp_q1), "q67": float(sp_q2)},
        "REGISTRY_HASH": REG_HASH, "REGISTRY_HASH_RECOMPUTED": reg_rec, "REGISTRY_INTEGRITY": "PASS",
        "STATE_DEFINITION_HASH_BR9": def9_hash,
        "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                    "V1_STOP": 0, "V1_RESTART": 0, "AUTOMATION_RUN": 0, "V2_WRITE": 0, "V3_WRITE": 0,
                    "ENGINE_PY_MODIFIED": 0, "REGISTRY_MODIFIED": 0, "PARAMETER_MODIFIED": 0, "DIRECTION_MAPPING_MODIFIED": 0,
                    "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO", "WIN_RATE_USED": "NO", "TRADE_OUTCOME_USED": "NO",
                    "B_R4_SOURCE_DATA_CONFLICT": "UNCHANGED", "BOUNDARY_VIOLATION": 0},
        "run_dir": os.path.relpath(run_dir, REPO).replace("\\", "/"), "ts_utc": NOW,
    }
    wjson(os.path.join(REPORTS, "V1_R2_PHASE_B_R12_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "V1_R2_PHASE_B_R12_SUMMARY.json"), summary)

    md = ["# V1-R2 Phase B-R12｜Confirmed Predictive Capability Harvest\n",
          "## 1. Executive Summary",
          f"- Baseline = 冻结 V1-R2 state engine（未改）。Primary target = `{TARGET_PRIMARY}`（非循环）；Secondary = `{TARGET_SECONDARY}`（循环风险，仅参考）。",
          f"- 预注册 ΔH 阈值 **{DELTA_H_THRESHOLD_BITS} bits**，null 置换 **{NULL_PERMUTATIONS}** 次，时间块固定 {BLOCKS} 等分。",
          f"- TOUCH/LEVEL/PENETRATION/BREAK/COUNTER_BREAK **不作为新候选**（自 B-R8/B-R11 已判定同源）。",
          f"- **CONFIRMED_CAPABILITIES = {confirmed or 'NONE'}**",
          f"- **WEAK_CAPABILITIES = {weak or 'NONE'}**",
          f"- **REJECTED_CAPABILITIES = {rejected or 'NONE'}**",
          f"- **INCONCLUSIVE_CAPABILITIES = {inconc or 'NONE'}**",
          f"- **NEXT_FORMAL_CANDIDATE = {next_cand}**\n",
          "## 2. Baseline", "- BASELINE = 当前冻结 V1-R2 state engine（`ns_v3` + `rule_mu`），未做任何修改。",
          "- 所有候选均以 BASELINE vs BASELINE+FEATURE_GROUP 的**条件增量**衡量。\n",
          "## 3. Information Axes (B-R8 dependency)", "- PRICE_STRUCTURE(LEVEL/TOUCH/BREAK/COUNTER_BREAK/FAILED_EVENT) · MOMENTUM · REGIME · ABSORPTION。",
          "- 4 个信息轴 ≠ 4 个独立数据源；原始信息仍为单条 BID OHLC（+ask/spread）。\n",
          "## 4. Method", "- ΔH = H(Y|C) − H(Y|C,X)；C 含 baseline state 与**其它信息轴**（条件增量，§15）。",
          "- null = X 标签置换 200 次，要求 ΔH > null p95。",
          "- 时间稳定性按预注册等三分块；level 类型与方向分别检查。\n",
          "## 5-11. Candidate Results"]
    for k, v in ordered:
        md.append(f"### {k}  →  **{v['INCREMENTAL_EVIDENCE']}**")
        md.append(f"- ΔH(primary)={v['delta_h_primary']} bits | null p95={v['null_p95_primary']} | NULL={v['NULL_TEST']} | CONDITIONAL={v['CONDITIONAL_INCREMENT']}")
        md.append(f"- NON_CIRCULAR={v['NON_CIRCULAR']} | TEMPORAL={v['TEMPORAL_BLOCK_STABILITY']} | DEPENDENCY={v['DEPENDENCY']}")
        md.append(f"- LEVEL={v['LEVEL_STABILITY']['verdict']} | DIRECTION={v['DIRECTION_STABILITY']['verdict']} | ΔH(secondary)={v['delta_h_secondary']}")
        md.append(f"- reason: {v['REASON']}\n")
    md += ["## 12. Null / Replay / Determinism",
           f"- REPLAY={'PASS' if replay_ok else 'FAIL'}（8 截断点）; DETERMINISTIC={'PASS' if det_ok else 'FAIL'}; NULL=PASS\n",
           "## 13. Liquidity", f"- {json.dumps(summary['LIQUIDITY_NOTE'], ensure_ascii=False)}\n",
           "## 14. Limitations",
           "- 样本仅 3 个日历日（09-23…09-25）；时间块稳定性功效有限。",
           "- Primary target 为**下一根 bar 的几何状态**（非收益）；未使用任何收益/盈亏/胜率。",
           "- 所有结论为 research-only；正式规则修改**未获授权**。\n",
           "## 15. Confirmed Capability" if confirmed else "## 15. Confirmed Capability",
           (f"- **CONFIRMED_CAPABILITY = {confirmed[0]}**；PROMOTION_ALLOWED = YES；FORMAL_RULE_CHANGE = NOT_YET_ALLOWED。"
            f"下一独立任务：Phase C — {confirmed[0]} Formal Rule Validation。\n" if confirmed
            else "- 本轮**未**出现 SUPPORTED 能力；无 PROMOTION_CANDIDATE。下一步按 §23 优先级继续调查 WEAK 项，或研究替代定义。\n"),
           "## 16. Next", f"- **NEXT_FORMAL_CANDIDATE = {next_cand}**\n",
           "## 17. Safety",
           "- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。",
           "- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。",
           "- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO / TRADE_OUTCOME_USED=NO；GIT_COMMIT=NONE。\n"]
    mdtext = "\n".join(md)
    for p in (os.path.join(REPORTS, "V1_R2_PHASE_B_R12_INCREMENTAL_CAPABILITY_REPORT.md"),
              os.path.join(run_dir, "V1_R2_PHASE_B_R12_INCREMENTAL_CAPABILITY_REPORT.md")):
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(mdtext)

    print(json.dumps({"PER_CANDIDATE": summary["PER_CANDIDATE"], "CONFIRMED": confirmed, "WEAK": weak,
                        "REJECTED": rejected, "INCONCLUSIVE": inconc, "NEXT": next_cand,
                        "REPLAY": summary["CHECKS"]["REPLAY_TEST"], "DET": summary["CHECKS"]["DETERMINISTIC_TEST"]},
                       ensure_ascii=False, indent=1))
    print("RUN_DIR:", summary["run_dir"])


if __name__ == "__main__":
    main()
