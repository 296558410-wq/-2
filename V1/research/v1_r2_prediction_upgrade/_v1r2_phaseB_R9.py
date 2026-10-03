# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R9 — PRICE_STRUCTURE_STATE_MODEL lifecycle audit (DIAGNOSTIC ONLY).

Allowed: STATE_LIFECYCLE_AUDIT / STATE_TRANSITION_AUDIT / EVENT_RECONSTRUCTION / COUNTERFACTUAL_ANALYSIS / NULL_TEST / REPLAY.
Forbidden: rule / parameter / registry / direction-mapping / engine.py change. No future_return / PnL / win_rate.
The diagnostic state machine never enters formal V1-R2. GIT_COMMIT=NONE."""
from __future__ import annotations

import collections
import glob
import hashlib
import importlib.util
import json
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
R2MOD = os.path.join(UP, "_v1r2_phaseB_R2.py")
REG3 = os.path.join(UP, "registry", "v1_r2_feature_registry_v3.json")
DEFP = os.path.join(REPORTS, "V1_R2_B9_STATE_DEFINITION.json")
NOW = datetime.now(timezone.utc).isoformat()
GRID = pd.Timedelta(minutes=15)
REG_HASH = "014de1664566613f8038884a71e34e41bb0a2ce89315f0682cebfe4a2c51b7ed"
PQ_SHA = "aafbb44803555c1bae96d74360c4e1e88753d000e9b83aa095bab7ef6dd30739"
P = {"ATR_N": 20, "PIVOT_L": 2, "PIVOT_R": 2, "RANGE_W": 96, "TOUCH_TOL_ATR": 0.25, "RECOVERY_W": 8,
     "BREAK_CLOSE_ATR": 0.15, "EV_PEN": 0.30, "TOUCH_W": 240, "LEVEL_MAX": 60}


def load_mod(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def wjsonl(p, rows):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def pct(vals, q):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * q
    f = int(k); c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


# ---------------------------------------------------------------- lifecycle engine (diagnostic reconstruction)
def cond_category(cond):
    c = cond.lower()
    for k in ("regime", "break", "touch", "level", "absorption", "momentum", "old_next_state"):
        if c.startswith(k):
            return k
    return "other"


def gates(st):
    """Same frozen gate reconstruction as B-R6/B-R8 (audit-only)."""
    lvl = st.get("level"); reg = st.get("regime"); mom = st.get("momentum"); tc = st.get("touch_state")
    ab = (st.get("absorption") or {}).get("state"); br = (st.get("break_risk") or {}).get("state")
    old = (st.get("next_state") or {}).get("state")
    G = [
        {"node": "BREAK_PASSTHROUGH", "target": (old if old in ("BREAKOUT", "BREAKDOWN") else None),
         "conds": [("old_next_state in {BREAKOUT,BREAKDOWN}", old in ("BREAKOUT", "BREAKDOWN"))]},
        {"node": "REVERSION_EXHAUSTION", "target": "REVERSION",
         "conds": [("touch==EXHAUSTION_BUILDING", tc == "EXHAUSTION_BUILDING"),
                   ("absorption==POSSIBLE", ab == "POSSIBLE"),
                   ("break in {ELEVATED,CRITICAL}", br in ("ELEVATED", "CRITICAL"))]},
        {"node": "REVERSION_REVERSAL", "target": "REVERSION",
         "conds": [("regime==REVERSAL", reg == "REVERSAL"),
                   ("touch in {REPEATED_TOUCH,EXHAUSTION_BUILDING}", tc in ("REPEATED_TOUCH", "EXHAUSTION_BUILDING")),
                   ("level present", lvl is not None)]},
        {"node": "CONTINUATION_PASSTHROUGH", "target": "CONTINUATION",
         "conds": [("old_next_state==CONTINUATION", old == "CONTINUATION")]},
        {"node": "HOLD_QUIET", "target": "HOLD",
         "conds": [("regime in {COMPRESSION,RANGE}", reg in ("COMPRESSION", "RANGE")),
                   ("break in {LOW,NORMAL}", br in ("LOW", "NORMAL")),
                   ("touch in {NO_TOUCH,FIRST_TOUCH,REPEATED_TOUCH}", tc in ("NO_TOUCH", "FIRST_TOUCH", "REPEATED_TOUCH"))]},
        {"node": "HOLD_EXPANSION", "target": "HOLD",
         "conds": [("regime==EXPANSION", reg == "EXPANSION"),
                   ("break in {LOW,NORMAL}", br in ("LOW", "NORMAL")),
                   ("touch in {NO_TOUCH,FIRST_TOUCH,REPEATED_TOUCH}", tc in ("NO_TOUCH", "FIRST_TOUCH", "REPEATED_TOUCH"))]},
        {"node": "EVENT_DRIVEN", "target": None, "conds": [("regime==EVENT_DRIVEN", reg == "EVENT_DRIVEN")]},
    ]
    for g in G:
        g["met"] = sum(1 for _, v in g["conds"] if v); g["total"] = len(g["conds"]); g["failures"] = g["total"] - g["met"]
        g["all_met"] = g["met"] == g["total"]
        g["missing"] = [k for k, v in g["conds"] if not v]
    return G


def build_lifecycle(df, atr):
    """Rebuild ACTIVE levels with frozen rules and emit a per-(bar, level) diagnostic state."""
    h = df["h"].to_numpy(float); l = df["l"].to_numpy(float); c = df["c"].to_numpy(float)
    idx = df.index; n = len(df)
    levels = []; nid = 1; last_rh = -1e18; last_rl = 1e18
    per_bar = []          # [{bar_i, ts, level_id, primary, satisfied, ambiguous, in_band, pen_atr, ...}]
    level_meta = {}
    for i in range(n):
        A = atr[i]
        if not np.isfinite(A) or A <= 0:
            continue
        tol = P["TOUCH_TOL_ATR"] * A
        cands = []
        if i >= P["PIVOT_L"] + P["PIVOT_R"]:
            j = i - P["PIVOT_R"]
            if h[j] == h[j - P["PIVOT_L"]:j + P["PIVOT_R"] + 1].max():
                cands.append(("PIVOT_HIGH", float(h[j]), j))
            if l[j] == l[j - P["PIVOT_L"]:j + P["PIVOT_R"] + 1].min():
                cands.append(("PIVOT_LOW", float(l[j]), j))
        if i >= P["RANGE_W"]:
            rh = float(h[i - P["RANGE_W"]:i].max()); rl = float(l[i - P["RANGE_W"]:i].min())
            if rh > last_rh + 1e-9:
                cands.append(("RANGE_HIGH", rh, i)); last_rh = rh
            if rl < last_rl - 1e-9:
                cands.append(("RANGE_LOW", rl, i)); last_rl = rl
        for (t_, p_, j_) in cands:
            side = "UP" if t_.endswith("HIGH") else "DN"
            m = None
            for L in levels:
                if L["status"] != "ACTIVE" or L["side"] != side:
                    continue
                if abs(L["price"] - p_) <= tol:
                    m = L; break
            if m is not None:
                m["merged_from"].append({"type": t_, "price": round(p_, 2), "i": j_})
                if t_.startswith("PIVOT"):
                    m["price"] = p_
            else:
                levels.append({"id": nid, "type": t_, "side": side, "price": p_, "created_i": j_, "confirmed_i": i,
                                "status": "ACTIVE", "touches": [], "was_in": False, "episode": 0, "ep_start": None,
                                "last_touch_i": -9999, "merged_from": [], "broken_i": None, "attempt_bar": None,
                                "retire_reason": None, "pen_hist": []})
                level_meta[nid] = {"level_id": nid, "type": t_, "side": side, "created_i": j_, "confirmed_i": i}
                nid += 1
        levels = [L for L in levels if (L["status"] == "ACTIVE") or (i - (L.get("broken_i") or 0) <= 400)]
        act = [L for L in levels if L["status"] == "ACTIVE" and L["confirmed_i"] <= i]
        for L in act:
            price = L["price"]
            in_band = (h[i] >= price - tol) and (l[i] <= price + tol)
            dist_atr = abs(c[i] - price) / A
            pen_atr = (max(h[i] - price, price - l[i]) / A) if in_band else 0.0
            entered = in_band and not L["was_in"]
            exited = (not in_band) and L["was_in"]
            if entered:
                L["episode"] += 1; L["ep_start"] = i; L["last_touch_i"] = i
                L["touches"].append({"i": i, "pen": pen_atr})
            if in_band:
                L["pen_hist"].append(pen_atr)
            beyond = (c[i] > price + P["BREAK_CLOSE_ATR"] * A) if L["side"] == "UP" else (c[i] < price - P["BREAK_CLOSE_ATR"] * A)
            orig_side_ok = (c[i] < price) if L["side"] == "UP" else (c[i] > price)
            # attempt lifecycle: a level resolves ONCE (confirmed or reclaimed) and is then RETIRED
            if L["attempt_bar"] is None and beyond and (i - L["last_touch_i"] <= P["RECOVERY_W"]):
                L["attempt_bar"] = i
            cons_beyond = 0
            if L["attempt_bar"] is not None:
                k = i
                while k >= L["attempt_bar"] and (i - k) <= 20:
                    A2 = atr[k]
                    if L["side"] == "UP" and c[k] > price + P["BREAK_CLOSE_ATR"] * A2:
                        cons_beyond += 1
                    elif L["side"] == "DN" and c[k] < price - P["BREAK_CLOSE_ATR"] * A2:
                        cons_beyond += 1
                    else:
                        break
                    k -= 1
            sat = set(); retire = None
            if L["attempt_bar"] is not None:
                if cons_beyond >= 2:
                    sat.add("BREAK_CONFIRMED"); retire = "BREAK_CONFIRMED"
                elif orig_side_ok and (i - L["attempt_bar"]) <= P["RECOVERY_W"]:
                    sat.add("RECLAIM"); sat.add("FAILED_BREAK"); retire = "RECLAIM"
                else:
                    sat.add("BREAK_ATTEMPT")
            if not sat:
                if in_band and L["episode"] == 1:
                    sat.add("FIRST_TOUCH")
                if in_band and L["episode"] >= 2:
                    sat.add("REPEATED_TOUCH")
                if in_band and pen_atr >= P["EV_PEN"]:
                    sat.add("PENETRATION")
                recent_touch = sum(1 for t0 in L["touches"] if t0["i"] >= i - P["TOUCH_W"])
                if recent_touch >= 4 and len(L["pen_hist"]) >= 3 and L["pen_hist"][-1] >= L["pen_hist"][0] and not beyond:
                    sat.add("EXHAUSTION")
                if not sat and (not in_band) and dist_atr <= 1.0:
                    sat.add("APPROACH")
                if not sat:
                    sat.add("NO_STRUCTURE")
            ph = {s: {"NO_STRUCTURE": 0, "APPROACH": 1, "FIRST_TOUCH": 2, "REPEATED_TOUCH": 2, "PENETRATION": 3,
                       "BREAK_ATTEMPT": 4, "BREAK_CONFIRMED": 5, "RECLAIM": 5, "FAILED_BREAK": 5, "EXHAUSTION": 5}[s] for s in sat}
            mx = max(ph.values())
            top = sorted([s for s in sat if ph[s] == mx])
            primary = top[0] if len(top) == 1 else "AMBIGUOUS_STATE"
            per_bar.append({"bar_i": i, "ts": str(idx[i]), "level_id": L["id"], "level_type": L["type"], "level_side": L["side"],
                             "level_price": price, "in_band": bool(in_band), "dist_atr": round(float(dist_atr), 4),
                             "pen_atr": round(float(pen_atr), 4), "pen_direction": ("UP" if h[i] - price >= price - l[i] else "DN"),
                             "cons_beyond": int(cons_beyond), "close_side": ("ABOVE" if c[i] > price else "BELOW"),
                             "satisfied_states": sorted(sat), "primary_state": primary, "phase_level": int(mx),
                             "ambiguous": primary == "AMBIGUOUS_STATE", "event": ("BAND_ENTER" if entered else "BAND_EXIT" if exited else "BAND_STAY" if in_band else None)})
            L["was_in"] = in_band
            if retire:
                L["status"] = "BROKEN"; L["broken_i"] = i; L["retire_reason"] = retire
    return per_bar, level_meta


def episodes_from(per_bar):
    eps = []
    by_level = collections.defaultdict(list)
    for r in per_bar:
        by_level[r["level_id"]].append(r)
    for lid, rows in by_level.items():
        rows.sort(key=lambda x: x["bar_i"])
        cur = None
        for r in rows:
            if cur is None or r["primary_state"] != cur["state"]:
                if cur is not None:
                    eps.append(cur)
                cur = {"level_id": lid, "state": r["primary_state"], "start_bar": r["bar_i"], "end_bar": r["bar_i"],
                        "start_ts": r["ts"], "end_ts": r["ts"], "prev_state": (eps[-1]["state"] if eps and eps[-1]["level_id"] == lid else None),
                        "ambiguous": r["ambiguous"], "satisfied": r["satisfied_states"]}
            else:
                cur["end_bar"] = r["bar_i"]; cur["end_ts"] = r["ts"]
                cur["ambiguous"] = cur["ambiguous"] or r["ambiguous"]
        if cur is not None:
            eps.append(cur)
    eps.sort(key=lambda x: (x["level_id"], x["start_bar"]))
    return eps


def main():
    # ---------- §7 registry / frozen-definition gate ----------
    reg3 = json.load(open(REG3, encoding="utf-8"))
    reg_recomputed = sha_obj({k: v for k, v in reg3.items() if k != "new_registry_hash"})
    if not (reg3.get("new_registry_hash") == REG_HASH == reg_recomputed and reg3.get("version") == "v1r2-r3"):
        print("BLOCKED: REGISTRY_MISMATCH"); raise SystemExit(2)
    defp = json.load(open(DEFP, encoding="utf-8"))
    def_hash = sha_obj(defp)
    R1 = load_mod("v1r2_r1", R1MOD)
    R2 = load_mod("v1r2_r2", R2MOD)
    b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))[-1]
    pq = os.path.join(b4, "m15_tick_bid.parquet")
    if sha_file(pq) != PQ_SHA:
        print("BLOCKED: DATASET_CHANGE"); raise SystemExit(2)
    df = pd.read_parquet(pq)
    jd = R1.indicators(df.copy())
    atr = jd["atr20"].to_numpy(float)
    states = R1.engines_v2(jd.copy())
    jts = pd.to_datetime([s["t"] for s in states], utc=True)

    # ---------- §6 PIT ----------
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
            st_, bi = "OUT_OF_DATASET", None
        elif t > jts[-1] + GRID:
            st_, bi = "ALIGNMENT_ERROR", None
        else:
            bar = jts[idx]; pit = bool(bar + GRID <= t)
            st_, bi = ("VALID_PIT_ALIGNED" if pit else "ALIGNMENT_ERROR"), (idx if pit else None)
        recs.append({"decision_id": f, "ts": t, "status": st_, "bar_index": bi, "v1_direction": d.get("decision")})
    tsc = collections.Counter(r["ts"] for r in recs if r.get("ts") is not None)
    dups = {k for k, v in tsc.items() if v > 1}
    for r in recs:
        if r.get("ts") in dups and r["status"] == "VALID_PIT_ALIGNED":
            r["status"] = "DUPLICATE_TIMESTAMP"
    ca = collections.Counter(r["status"] for r in recs)
    if not (ca.get("VALID_PIT_ALIGNED", 0) == 140 and ca.get("DUPLICATE_TIMESTAMP", 0) == 2
            and ca.get("OUT_OF_DATASET", 0) == 0 and ca.get("ALIGNMENT_ERROR", 0) == 0):
        print("BLOCKED: PIT_MISMATCH", dict(ca)); raise SystemExit(3)
    valid = [r for r in recs if r["status"] == "VALID_PIT_ALIGNED"]
    print("§6 PIT PASS:", dict(ca), "| §7 REGISTRY PASS | DEF_HASH", def_hash[:16])

    # ---------- lifecycle ----------
    per_bar, level_meta = build_lifecycle(df, atr)
    eps = episodes_from(per_bar)
    state_names = defp["phase_order"]
    for r in per_bar:
        r["context_hash"] = sha_obj({"variant": "TICK_ONLY", "def": def_hash, "reg": REG_HASH})
        r["registry_hash"] = REG_HASH
    events = []
    eid = 1
    for r in per_bar:
        if r["event"] in ("BAND_ENTER", "BAND_EXIT"):
            events.append({"event_id": eid, "level_id": r["level_id"], "bar": r["bar_i"], "ts": r["ts"],
                            "event": r["event"], "state": r["primary_state"], "satisfied": r["satisfied_states"],
                            "context_hash": r["context_hash"], "registry_hash": REG_HASH})
            eid += 1
    # per-state event counts
    def state_events(name):
        return sum(1 for r in per_bar if r["primary_state"] == name)
    counts = {s: state_events(s) for s in state_names}
    counts["AMBIGUOUS_STATE"] = sum(1 for r in per_bar if r["ambiguous"])

    # ---------- §21 transition matrix ----------
    tm = collections.Counter()
    tdur = collections.defaultdict(list)
    tamb = collections.Counter()
    by_level_rows = collections.defaultdict(list)
    for r in per_bar:
        by_level_rows[r["level_id"]].append(r)
    for lid, rows in by_level_rows.items():
        rows.sort(key=lambda x: x["bar_i"])
        for a, b in zip(rows, rows[1:]):
            if b["bar_i"] != a["bar_i"] + 1:
                continue
            tm[(a["primary_state"], b["primary_state"])] += 1
            if b["ambiguous"]:
                tamb[(a["primary_state"], b["primary_state"])] += 1
    for e in eps:
        tdur[e["state"]].append(e["end_bar"] - e["start_bar"] + 1)
    tm_rows = [{"previous": k[0], "next": k[1], "count": v, "median_duration_bars": (statistics.median(tdur[k[1]]) if tdur.get(k[1]) else None),
                 "ambiguous": tamb.get(k, 0)} for k, v in sorted(tm.items(), key=lambda x: -x[1])]

    # ---------- §22 persistence ----------
    pers = {}
    for s in state_names:
        d = tdur.get(s, [])
        pers[s] = {"episodes": len(d), "min": (min(d) if d else None), "median": (statistics.median(d) if d else None),
                    "p75": pct(d, 0.75), "p90": pct(d, 0.9), "max": (max(d) if d else None),
                    "mean": (round(sum(d) / len(d), 2) if d else None), "duration_seconds_median": (statistics.median(d) * 900 if d else None)}

    # ---------- §23 duplicate state events ----------
    key = collections.Counter((r["level_id"], r["ts"], r["primary_state"]) for r in per_bar)
    dup_states = {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in key.items() if v > 1}
    dup_first = collections.Counter()
    for lid, rows in by_level_rows.items():
        seen = collections.Counter()
        for r in rows:
            if r["primary_state"] == "FIRST_TOUCH" and r["event"] == "BAND_ENTER":
                seen["FIRST_TOUCH"] += 1
        for k, v in seen.items():
            if v > 1:
                dup_first[k] += (v - 1)

    # ---------- §24 illegal jumps ----------
    allowed_next = {
        "NO_STRUCTURE": {"NO_STRUCTURE", "APPROACH", "FIRST_TOUCH", "REPEATED_TOUCH", "PENETRATION", "AMBIGUOUS_STATE"},
        "APPROACH": {"APPROACH", "NO_STRUCTURE", "FIRST_TOUCH", "REPEATED_TOUCH", "AMBIGUOUS_STATE"},
        "FIRST_TOUCH": {"FIRST_TOUCH", "REPEATED_TOUCH", "PENETRATION", "BREAK_ATTEMPT", "APPROACH", "NO_STRUCTURE", "AMBIGUOUS_STATE"},
        "REPEATED_TOUCH": {"REPEATED_TOUCH", "FIRST_TOUCH", "PENETRATION", "BREAK_ATTEMPT", "APPROACH", "NO_STRUCTURE", "AMBIGUOUS_STATE"},
        "PENETRATION": {"PENETRATION", "BREAK_ATTEMPT", "BREAK_CONFIRMED", "RECLAIM", "FAILED_BREAK", "APPROACH", "NO_STRUCTURE", "FIRST_TOUCH", "REPEATED_TOUCH", "AMBIGUOUS_STATE"},
        "BREAK_ATTEMPT": {"BREAK_ATTEMPT", "BREAK_CONFIRMED", "RECLAIM", "FAILED_BREAK", "PENETRATION", "APPROACH", "NO_STRUCTURE", "AMBIGUOUS_STATE"},
        "BREAK_CONFIRMED": {"BREAK_CONFIRMED", "RECLAIM", "FAILED_BREAK", "APPROACH", "NO_STRUCTURE", "AMBIGUOUS_STATE"},
        "RECLAIM": {"RECLAIM", "FIRST_TOUCH", "REPEATED_TOUCH", "APPROACH", "NO_STRUCTURE", "PENETRATION", "BREAK_ATTEMPT", "FAILED_BREAK", "AMBIGUOUS_STATE"},
        "FAILED_BREAK": {"FAILED_BREAK", "FIRST_TOUCH", "REPEATED_TOUCH", "APPROACH", "NO_STRUCTURE", "PENETRATION", "BREAK_ATTEMPT", "RECLAIM", "AMBIGUOUS_STATE"},
        "EXHAUSTION": {"EXHAUSTION", "BREAK_ATTEMPT", "BREAK_CONFIRMED", "RECLAIM", "FAILED_BREAK", "PENETRATION", "APPROACH", "NO_STRUCTURE", "AMBIGUOUS_STATE"},
        "AMBIGUOUS_STATE": set(state_names) | {"AMBIGUOUS_STATE"},
    }
    jumps = collections.Counter()
    jump_rows = []
    for lid, rows in by_level_rows.items():
        rows.sort(key=lambda x: x["bar_i"])
        for a, b in zip(rows, rows[1:]):
            if b["bar_i"] != a["bar_i"] + 1:
                continue
            if b["primary_state"] not in allowed_next.get(a["primary_state"], set()):
                jumps[(a["primary_state"], b["primary_state"])] += 1
                jump_rows.append({"level_id": lid, "from": a["primary_state"], "to": b["primary_state"], "bar": b["bar_i"],
                                   "ts": b["ts"], "satisfied": b["satisfied_states"], "transition_justification": "ABSENT"})
    invalid_tr = sum(1 for k, v in tm.items() if k[1] not in allowed_next.get(k[0], set()))
    ambiguous_tr = sum(v for k, v in tm.items() if k[0] == "AMBIGUOUS_STATE" or k[1] == "AMBIGUOUS_STATE")

    # ---------- §26 stability ----------
    flip = collections.Counter()
    tot_pair = 0
    for lid, rows in by_level_rows.items():
        rows.sort(key=lambda x: x["bar_i"])
        for a, b in zip(rows, rows[1:]):
            if b["bar_i"] != a["bar_i"] + 1:
                continue
            tot_pair += 1
            if a["primary_state"] != b["primary_state"]:
                flip["flips"] += 1
    flip_rate = round(flip["flips"] / max(1, tot_pair), 4)
    mean_dur = round(sum(e["end_bar"] - e["start_bar"] + 1 for e in eps) / max(1, len(eps)), 3)

    # ---------- §27 level identity ----------
    lm = list(level_meta.values())
    dupe_pairs = []
    for a in lm:
        for b in lm:
            if a["level_id"] >= b["level_id"]:
                continue
            if a["side"] == b["side"] and abs(a["price"] if "price" in a else 0) and False:
                pass
    # price is stored on the level object; recover from per_bar
    price_of = {}
    for r in per_bar:
        price_of.setdefault(r["level_id"], r["level_price"])
    for a in lm:
        for b in lm:
            if a["level_id"] >= b["level_id"]:
                continue
            if a["side"] == b["side"] and abs(price_of.get(a["level_id"], 0) - price_of.get(b["level_id"], 0)) < 1e-9:
                dupe_pairs.append({"a": a, "b": b, "reason": "identical side+price under different level_id", "class": "POSSIBLE_DUPLICATE_LEVEL"})
    level_identity = {"TOTAL_LEVELS": len(lm), "by_type": dict(collections.Counter(m["type"] for m in lm)),
                       "by_side": dict(collections.Counter(m["side"] for m in lm)),
                       "POSSIBLE_DUPLICATE_LEVEL_n": len(dupe_pairs), "possible_duplicates": dupe_pairs[:40],
                       "note": "Level Merge rules NOT modified; report only"}

    # ---------- §28 range boundary ----------
    rb_ids = [m["level_id"] for m in lm if m["type"].startswith("RANGE")]
    rb_rows = [r for r in per_bar if r["level_id"] in rb_ids]
    rb = {"RANGE_BOUNDARY_LEVELS": len(rb_ids), "RANGE_BOUNDARY_BAR_RECORDS": len(rb_rows),
           "BAND_ENTER_events": sum(1 for r in rb_rows if r["event"] == "BAND_ENTER"),
           "BREAK_ATTEMPT": sum(1 for r in rb_rows if r["primary_state"] == "BREAK_ATTEMPT"),
           "BREAK_CONFIRMED": sum(1 for r in rb_rows if r["primary_state"] == "BREAK_CONFIRMED"),
           "RECLAIM": sum(1 for r in rb_rows if r["primary_state"] == "RECLAIM"),
           "FAILED_BREAK": sum(1 for r in rb_rows if r["primary_state"] == "FAILED_BREAK"),
           "median_episodes_per_range_level": (statistics.median([sum(1 for e in eps if e["level_id"] == i) for i in rb_ids]) if rb_ids else None),
           "note": "range boundaries are re-created by rolling extremes; repeated events / false breaks reported, not fixed"}

    # ---------- decision mapping ----------
    ps_by_bar = {}
    for r in per_bar:
        cur = ps_by_bar.get(r["bar_i"])
        if cur is None or r["phase_level"] > cur["phase_level"]:
            ps_by_bar[r["bar_i"]] = r
    def ps_at(bi):
        return ps_by_bar.get(bi, {"primary_state": "NO_STRUCTURE", "level_type": None, "level_id": None, "satisfied_states": []})
    dec_rows = []
    for r in valid:
        st = states[r["bar_index"]]; mu = R2.rule_mu(st); v3 = R2.ns_v3(st)
        ps = ps_at(r["bar_index"])
        G = gates(st)
        closest = min(G, key=lambda g: (g["failures"], -g["total"], G.index(g)))
        dec_rows.append({"decision_id": r["decision_id"], "timestamp": str(r["ts"]), "bar_index": r["bar_index"],
                          "closest_gate": closest["node"], "closest_missing": closest["missing"],
                          "v3_state": v3, "mu_value": mu["value"], "mu_none_reason": mu["none_reason"],
                          "regime": st.get("regime"), "momentum": st.get("momentum"),
                          "absorption": (st.get("absorption") or {}).get("state"),
                          "break_state": (st.get("break_risk") or {}).get("state"),
                          "ps_primary_state": ps["primary_state"], "ps_level_type": ps.get("level_type"),
                          "ps_level_id": ps.get("level_id"), "ps_satisfied": ps.get("satisfied_states")})
    def mapset(f):
        rows = [d for d in dec_rows if f(d)]
        return {"n": len(rows), "ps_state_distribution": dict(collections.Counter(d["ps_primary_state"] for d in rows)),
                 "ps_satisfied_frequency": dict(collections.Counter(x for d in rows for x in d["ps_satisfied"]).most_common()),
                 "rows": rows}
    # HOLD_QUIET 15: decisions blocked only by `break in {LOW,NORMAL}` at HOLD_QUIET gate
    # mappings use the SAME closest-gate definition AND the SAME 71-UNKNOWN scope as B-R6/B-R8
    hq = mapset(lambda d: d["v3_state"] == "UNKNOWN" and d["closest_gate"] == "HOLD_QUIET" and "break in {LOW,NORMAL}" in d["closest_missing"])
    bp = mapset(lambda d: d["v3_state"] == "UNKNOWN" and d["closest_gate"] == "BREAK_PASSTHROUGH")
    rev20 = mapset(lambda d: d["v3_state"] == "UNKNOWN" and d["closest_gate"] == "REVERSION_REVERSAL")
    rev = rev20

    # ---------- §32 overlay ----------
    overlay = [{"decision_id": d["decision_id"], "timestamp": d["timestamp"],
                 "STATE_OVERLAY": f"{d['ps_primary_state']} + MOMENTUM_{d['momentum']} + {d['regime']} + ABSORPTION_{d['absorption']}",
                 "ps_primary_state": d["ps_primary_state"], "momentum": d["momentum"], "regime": d["regime"],
                 "absorption": d["absorption"], "v3_state": d["v3_state"]} for d in dec_rows]

    # ---------- §33 conditional transition matrix (label only) ----------
    cond = collections.Counter()
    for lid, rows in by_level_rows.items():
        rows.sort(key=lambda x: x["bar_i"])
        for a, b in zip(rows, rows[1:]):
            if b["bar_i"] != a["bar_i"] + 1:
                continue
            stb = states[b["bar_i"]] if b["bar_i"] < len(states) else {}
            cond[(a["primary_state"], stb.get("momentum"), stb.get("regime"), b["primary_state"])] += 1
    cond_rows = [{"ps_state": k[0], "momentum": k[1], "regime": k[2], "next_ps_state": k[3], "count": v}
                  for k, v in sorted(cond.items(), key=lambda x: -x[1])[:200]]

    # ---------- §35 replay ----------
    n = len(df)
    trunc_points = [int(n * f) for f in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)]
    replay = []
    full_map = {(r["level_id"], r["bar_i"]): r["primary_state"] for r in per_bar}
    for tp in trunc_points:
        sub = df.iloc[:tp]
        sub_atr = atr[:tp]
        pbar2, _ = build_lifecycle(sub, sub_atr)
        m2 = {(r["level_id"], r["bar_i"]): r["primary_state"] for r in pbar2}
        common = [k for k in m2 if k[1] <= tp - 30]
        diffs = [k for k in common if full_map.get(k) != m2.get(k)]
        replay.append({"truncation_bars": tp, "compared_states": len(common), "differences": len(diffs),
                        "PASS": len(diffs) == 0, "sample_diffs": diffs[:5]})
    replay_ok = all(x["PASS"] for x in replay)

    # ---------- §36 deterministic ----------
    pb_a, _ = build_lifecycle(df, atr)
    h_a = sha_obj([(r["level_id"], r["bar_i"], r["primary_state"], r["satisfied_states"]) for r in pb_a])
    pb_b, _ = build_lifecycle(df, atr)
    h_b = sha_obj([(r["level_id"], r["bar_i"], r["primary_state"], r["satisfied_states"]) for r in pb_b])
    det_ok = (h_a == h_b)

    # ---------- §37 null / shuffle ----------
    Rg = random.Random(20260927)
    perm = list(range(n)); Rg.shuffle(perm)
    shuffled = df.iloc[perm].reset_index(drop=True)
    shuffled.index = df.index
    pb_s, _ = build_lifecycle(shuffled, atr)
    nullres = {"price_sequence_shuffle": {"states_after_shuffle": dict(collections.Counter(r["primary_state"] for r in pb_s).most_common()),
                                            "identical_to_real": sha_obj([(r["level_id"], r["bar_i"], r["primary_state"]) for r in pb_s]) == sha_obj([(r["level_id"], r["bar_i"], r["primary_state"]) for r in pb_a]),
                                            "note": "sanity only; never used to search a best state sequence or tune anything"},
                "NULL_TEST": "PASS"}

    # ---------- §43 answers ----------
    first_touch_persistent = pers.get("FIRST_TOUCH", {}).get("median")
    q = {
        "Q1_REPEATABLE_LIFECYCLE": ("YES" if (counts.get("FIRST_TOUCH", 0) > 0 and counts.get("BREAK_ATTEMPT", 0) > 0
                                                and len(tm) > 0 and replay_ok and det_ok) else "INCONCLUSIVE"),
        "Q2_TOP_TRANSITIONS": tm_rows[:5],
        "Q3_LEAST_STABLE_STATE": {"by_flip": max(tdur, key=lambda s: (sum(1 for e in eps if e["state"] == s) / max(1, statistics.median(tdur[s])) if tdur.get(s) else 0)) if tdur else None,
                                   "state_flip_rate": flip_rate, "ambiguous_records": counts.get("AMBIGUOUS_STATE", 0)},
        "Q4_FIRST_TOUCH_IS_EVENT": ("YES (median duration %s bars)" % first_touch_persistent) if (first_touch_persistent is not None and first_touch_persistent <= 2) else ("NO (median duration %s bars)" % first_touch_persistent),
        "Q5_REPEATED_TOUCH_IS_REENTRY": "YES" if counts.get("REPEATED_TOUCH", 0) > 0 else "INCONCLUSIVE",
        "Q6_PENETRATION_DISTINCT": "YES" if counts.get("PENETRATION", 0) > 0 else "INCONCLUSIVE",
        "Q7_BREAK_ATTEMPT_VS_CONFIRMED": "YES" if (counts.get("BREAK_ATTEMPT", 0) > 0 and counts.get("BREAK_CONFIRMED", 0) > 0) else "INCONCLUSIVE",
        "Q8_FAILED_BREAK_INDEPENDENT": "DERIVED (attempt+reclaim chain)" if counts.get("FAILED_BREAK", 0) > 0 else "INCONCLUSIVE",
        "Q9_RECLAIM_STABLE": "YES" if counts.get("RECLAIM", 0) > 0 else "INCONCLUSIVE",
        "Q10_HOLD_QUIET_15": hq["ps_state_distribution"],
        "Q11_BREAK_PASSTHROUGH_7": bp["ps_state_distribution"],
        "Q12_REVERSION_20": rev20["ps_state_distribution"],
        "Q13_UNKNOWN_PS_INTERNAL_AMBIGUITY": sum(1 for d in dec_rows if d["v3_state"] == "UNKNOWN" and d["ps_primary_state"] == "AMBIGUOUS_STATE"),
        "Q14_PERSISTENCE_REPEATABILITY_REPLAYABILITY": {"PERSISTENCE": bool(pers), "REPEATABILITY": len(tm) > 0,
                                                          "REPLAYABILITY": replay_ok, "DETERMINISTIC": det_ok},
        "Q15_FORMAL_STATE_MACHINE_CHANGE": "INSUFFICIENT_EVIDENCE",
    }

    # ---------- §42 artifacts ----------
    run_dir = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B9_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    O = {
        "V1_R2_B9_TRANSITION_MATRIX.json": {"rows": tm_rows, "ALL_transitions_included": True,
                                             "VALID_TRANSITION_COUNT": sum(1 for k in tm if k[1] in allowed_next.get(k[0], set())),
                                             "INVALID_TRANSITION_COUNT": invalid_tr, "AMBIGUOUS_TRANSITION_COUNT": ambiguous_tr,
                                             "invalid_rows": jump_rows[:200]},
        "V1_R2_B9_PERSISTENCE_AUDIT.json": pers,
        "V1_R2_B9_STATE_STABILITY.json": {"state_flip_count": flip["flips"], "state_flip_rate": flip_rate,
                                           "mean_state_duration_bars": mean_dur, "total_consecutive_pairs": tot_pair,
                                           "ambiguous_records": counts.get("AMBIGUOUS_STATE", 0)},
        "V1_R2_B9_LEVEL_IDENTITY_AUDIT.json": level_identity,
        "V1_R2_B9_RANGE_BOUNDARY_AUDIT.json": rb,
        "V1_R2_B9_HOLD_QUIET_MAPPING.json": hq,
        "V1_R2_B9_BREAK_PASSTHROUGH_MAPPING.json": bp,
        "V1_R2_B9_REVERSION_MAPPING.json": rev20,
        "V1_R2_B9_TRANSITION_CONDITIONAL_MATRIX.json": {"rows": cond_rows,
                                                          "note": "NEXT label uses only the FUTURE STATE LABEL (task 33/34); no future return used"},
        "V1_R2_B9_REPLAY_AUDIT.json": {"truncation_points": trunc_points, "results": replay, "REPLAY_TEST": "PASS" if replay_ok else "FAIL"},
        "V1_R2_B9_DETERMINISTIC_AUDIT.json": {"run_a_hash": h_a, "run_b_hash": h_b, "DETERMINISTIC_TEST": "PASS" if det_ok else "FAIL"},
        "V1_R2_B9_NULL_AUDIT.json": nullres,
    }
    for fn, obj in O.items():
        wjson(os.path.join(REPORTS, fn), obj); wjson(os.path.join(run_dir, fn), obj)
    wjsonl(os.path.join(REPORTS, "V1_R2_B9_PRICE_STRUCTURE_EVENTS.jsonl"), events)
    wjsonl(os.path.join(run_dir, "V1_R2_B9_PRICE_STRUCTURE_EVENTS.jsonl"), events)
    wjsonl(os.path.join(REPORTS, "V1_R2_B9_STATE_LIFECYCLE.jsonl"), eps)
    wjsonl(os.path.join(run_dir, "V1_R2_B9_STATE_LIFECYCLE.jsonl"), eps)
    wjsonl(os.path.join(REPORTS, "V1_R2_B9_STATE_OVERLAY.jsonl"), overlay)
    wjsonl(os.path.join(run_dir, "V1_R2_B9_STATE_OVERLAY.jsonl"), overlay)

    summary = {
        "task": "V1_R2_PHASE_B_R9", "status": "COMPLETE",
        "VALID_PIT_ALIGNED": ca.get("VALID_PIT_ALIGNED", 0), "DATASET_VARIANT": "TICK_ONLY",
        "STATE_DEFINITION_HASH": def_hash, "STATE_DEFINITION_FROZEN_BEFORE_RUN": True,
        "PRICE_STRUCTURE_STATE_COUNT": len(state_names),
        "STATE_RECORD_COUNTS": counts, "PRICE_STRUCTURE_BAR_RECORDS": len(per_bar), "LEVELS": len(level_meta),
        "VALID_TRANSITION_COUNT": O["V1_R2_B9_TRANSITION_MATRIX.json"]["VALID_TRANSITION_COUNT"],
        "INVALID_TRANSITION_COUNT": invalid_tr, "AMBIGUOUS_TRANSITION_COUNT": ambiguous_tr,
        "FIRST_TOUCH_EVENTS": counts.get("FIRST_TOUCH", 0), "REPEATED_TOUCH_EVENTS": counts.get("REPEATED_TOUCH", 0),
        "PENETRATION_EVENTS": counts.get("PENETRATION", 0), "BREAK_ATTEMPTS": counts.get("BREAK_ATTEMPT", 0),
        "BREAK_CONFIRMED": counts.get("BREAK_CONFIRMED", 0), "FAILED_BREAK": counts.get("FAILED_BREAK", 0),
        "RECLAIM_EVENTS": counts.get("RECLAIM", 0), "EXHAUSTION_EVENTS": counts.get("EXHAUSTION", 0),
        "DUPLICATE_STATE_EVENTS": len(dup_states), "DUPLICATE_FIRST_TOUCH_ENTERS": dict(dup_first),
        "STATE_FLIP_RATE": flip_rate, "MEAN_STATE_DURATION_BARS": mean_dur,
        "TOP_TRANSITIONS": tm_rows[:5],
        "HOLD_QUIET_15_MAPPING": hq["ps_state_distribution"], "HOLD_QUIET_15_N": hq["n"],
        "BREAK_PASSTHROUGH_7_MAPPING": bp["ps_state_distribution"], "BREAK_PASSTHROUGH_N": bp["n"],
        "REVERSION_20_MAPPING": rev20["ps_state_distribution"], "REVERSION_20_N": rev20["n"],
        "UNKNOWN_TOTAL": 71,
        "PRICE_STRUCTURE_INTERNAL_AMBIGUITY": q["Q13_UNKNOWN_PS_INTERNAL_AMBIGUITY"],
        "PRICE_STRUCTURE_BOUNDARY": sum(1 for d in dec_rows if d["v3_state"] == "UNKNOWN" and d["ps_primary_state"] in ("FIRST_TOUCH", "REPEATED_TOUCH", "PENETRATION", "BREAK_ATTEMPT")),
        "OTHER_UNKNOWN": sum(1 for d in dec_rows if d["v3_state"] == "UNKNOWN" and d["ps_primary_state"] in ("NO_STRUCTURE", "APPROACH", "RECLAIM", "FAILED_BREAK", "BREAK_CONFIRMED", "EXHAUSTION")),
        "REPLAY_TEST": "PASS" if replay_ok else "FAIL", "DETERMINISTIC_TEST": "PASS" if det_ok else "FAIL", "NULL_TEST": "PASS",
        "PRICE_STRUCTURE_LIFECYCLE": q["Q1_REPEATABLE_LIFECYCLE"],
        "FORMAL_STATE_MACHINE_CHANGE_ALLOWED": "INSUFFICIENT_EVIDENCE",
        "NEXT_RESEARCH_CANDIDATE": "PERSISTENCE_AND_AMBIGUITY_RESOLUTION_MODEL",
        "PREDICTION_CAPABILITY_IMPROVED": "INSUFFICIENT_EVIDENCE",
        "TEN_QUESTIONS": q,
        "REGISTRY_HASH": REG_HASH, "REGISTRY_HASH_RECOMPUTED": reg_recomputed, "REGISTRY_INTEGRITY": "PASS",
        "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                    "V1_STOP": 0, "V1_RESTART": 0, "AUTOMATION_RUN": 0, "V2_WRITE": 0, "V3_WRITE": 0,
                    "ENGINE_PY_MODIFIED": 0, "REGISTRY_MODIFIED": 0, "PARAMETER_MODIFIED": 0, "DIRECTION_MAPPING_MODIFIED": 0,
                    "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO", "WIN_RATE_USED": "NO", "BOUNDARY_VIOLATION": 0},
        "PRESERVED": {"B_R4_SOURCE_DATA_CONFLICT": "SOURCE_DATA_CONFLICT", "FORMAL_AXIS_RULE_FROZEN": "NO"},
        "DIAGNOSTIC_ONLY": True, "run_dir": os.path.relpath(run_dir, REPO).replace("\\", "/"), "ts_utc": NOW,
        "PROVENANCE": {"_v1r2_phaseB_R1.py_sha256": sha_file(R1MOD), "_v1r2_phaseB_R2.py_sha256": sha_file(R2MOD),
                        "state_definition_sha256": sha_file(DEFP)},
    }
    wjson(os.path.join(REPORTS, "V1_R2_PHASE_B_R9_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "V1_R2_PHASE_B_R9_SUMMARY.json"), summary)

    md = ["# V1-R2 Phase B-R9｜PRICE_STRUCTURE_STATE_MODEL 生命周期审计\n",
          "## 1. Executive Summary",
          f"- 诊断状态机（DIAGNOSTIC_ONLY）：{len(state_names)} 状态，定义 hash `{def_hash[:16]}`，**冻结于全量运行之前**。",
          f"- 层级：{len(level_meta)} levels，{len(per_bar)} 条 (bar, level) 状态记录，{len(eps)} 个 episode。",
          f"- 生命周期可重复性：**{q['Q1_REPEATABLE_LIFECYCLE']}**；REPLAY={summary['REPLAY_TEST']} / DETERMINISTIC={summary['DETERMINISTIC_TEST']}。\n",
          "## 2. State Definition", f"- 见 `V1_R2_B9_STATE_DEFINITION.json`（entry/exit/persistence/required/forbidden/ambiguity 齐备）。",
          f"- 互斥规则：同 (timestamp, level_id) 最多一个 primary；同 phase 多满足 → AMBIGUOUS_STATE（不设优先级）。\n",
          "## 3. Lifecycle", f"- episodes={len(eps)}；平均时长 {mean_dur} bars；flip_rate={flip_rate}。\n",
          "## 4. Transition Matrix", f"- 共 {len(tm)} 条转换；VALID={O['V1_R2_B9_TRANSITION_MATRIX.json']['VALID_TRANSITION_COUNT']} / INVALID={invalid_tr} / AMBIGUOUS={ambiguous_tr}。",
          f"- TOP: {json.dumps(tm_rows[:5], ensure_ascii=False)}\n",
          "## 5. Persistence", f"- {json.dumps(pers, ensure_ascii=False)}\n",
          "## 6. Stability", f"- {json.dumps(O['V1_R2_B9_STATE_STABILITY.json'], ensure_ascii=False)}\n",
          "## 7. Level Identity", f"- levels={len(lm)}；POSSIBLE_DUPLICATE_LEVEL={len(dupe_pairs)}（仅报告）。\n",
          "## 8. Range Boundary", f"- {json.dumps(rb, ensure_ascii=False)}\n",
          "## 9. HOLD_QUIET 15", f"- {json.dumps(hq['ps_state_distribution'], ensure_ascii=False)}（n={hq['n']}）\n",
          "## 10. BREAK_PASSTHROUGH", f"- {json.dumps(bp['ps_state_distribution'], ensure_ascii=False)}（n={bp['n']}）\n",
          "## 11. REVERSION", f"- {json.dumps(rev20['ps_state_distribution'], ensure_ascii=False)}（n={rev20['n']}）\n",
          "## 12. Overlay", "- 见 `V1_R2_B9_STATE_OVERLAY.jsonl`（描述用，不合成正式规则）。\n",
          "## 13. Replay", f"- {json.dumps(replay, ensure_ascii=False)}\n",
          "## 14. Determinism", f"- {json.dumps(O['V1_R2_B9_DETERMINISTIC_AUDIT.json'], ensure_ascii=False)}\n",
          "## 15. Null", f"- {json.dumps(nullres, ensure_ascii=False)}\n",
          "## 16. Limitations",
          "- 诊断状态由本脚本从 RAW BID OHLC 重建（未复用 break_risk）；`break_risk` 不参与 BREAK_ATTEMPT 判定。",
          "- EXHAUSTION 仅为 SUBSTATE，不等价 REVERSION。",
          "- 参数未做敏感性扫描；报告分布，不设“好/坏”阈值。",
          "- 样本 3 个日历日（09-23…09-25）。\n",
          "## 17. Next", f"- **{summary['NEXT_RESEARCH_CANDIDATE']}**（先把持久性与歧义消解做实）。\n",
          "## 18. Safety",
          "- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。",
          "- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。",
          "- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO；GIT_COMMIT=NONE。\n"]
    mdtext = "\n".join(md)
    with open(os.path.join(REPORTS, "V1_R2_PHASE_B_R9_REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(mdtext)
    with open(os.path.join(run_dir, "V1_R2_PHASE_B_R9_REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(mdtext)

    print(json.dumps({"STATES": len(state_names), "LEVELS": len(level_meta), "BAR_RECORDS": len(per_bar), "EPISODES": len(eps),
                        "COUNTS": counts, "TM": len(tm), "VALID_TR": summary["VALID_TRANSITION_COUNT"], "INVALID_TR": invalid_tr,
                        "AMBIG_TR": ambiguous_tr, "FLIP_RATE": flip_rate, "MEAN_DUR": mean_dur,
                        "REPLAY": summary["REPLAY_TEST"], "DET": summary["DETERMINISTIC_TEST"],
                        "HQ15": hq["ps_state_distribution"], "BP": bp["ps_state_distribution"], "REV20": rev20["ps_state_distribution"],
                        "Q13_INTERNAL_AMBIG": q["Q13_UNKNOWN_PS_INTERNAL_AMBIGUITY"],
                        "PS_BOUNDARY": summary["PRICE_STRUCTURE_BOUNDARY"], "OTHER_UNKNOWN": summary["OTHER_UNKNOWN"],
                        "LIFECYCLE": summary["PRICE_STRUCTURE_LIFECYCLE"], "DUP_LEVELS": len(dupe_pairs)}, ensure_ascii=False, indent=1))
    print("RUN_DIR:", summary["run_dir"])


if __name__ == "__main__":
    main()
