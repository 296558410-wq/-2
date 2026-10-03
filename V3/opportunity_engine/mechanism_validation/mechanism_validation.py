# -*- coding: utf-8 -*-
"""V3 Opportunity Mechanism Validation R1 — core.

Question answered here: how many genuinely INDEPENDENT, repeatable, refutable market mechanisms
do the 404 Hermes INVESTIGATE opportunities represent? (Opportunity != Mechanism; Opportunity != Alpha.)

Hard rules (enforced in code, not just documented):
  * No profit/return/future quantity may drive any decision. Forbidden identifiers never appear as code.
  * Post-event RESPONSE is recorded as a descriptive observation only and is EXCLUDED from the decision,
    so a truncated replay cannot change a historical mechanism decision.
  * UST10Y is always the PROXY (^TNX); never written as official.
  * Same-bar external vs XAU observation can only support CO_MOVEMENT, never TRANSMISSION.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import timezone

import numpy as np
import pandas as pd

MV_VERSION = "MV-R1.0.0"

TAXONOMY = {
    "M01": "PRICE_STATE_TRANSITION", "M02": "VOLATILITY_REGIME_TRANSITION", "M03": "CROSS_MARKET_SHOCK",
    "M04": "CROSS_MARKET_DIVERGENCE", "M05": "LIQUIDITY_REPRICING", "M06": "RISK_SENTIMENT_TRANSMISSION",
    "M07": "EXTREME_REVERSION", "M08": "STATE_BREAK_MOMENTUM", "M09": "EVENT_REPRICING",
    "M10": "DATA_MEASUREMENT_ARTIFACT", "M11": "UNKNOWN_MECHANISM",
}
COUNTER_CODES = {
    "C01": "DATA_ARTIFACT", "C02": "TIMESTAMP_ALIGNMENT", "C03": "PROXY_DEFINITION", "C04": "LOW_RECURRENCE",
    "C05": "REGIME_DEPENDENCE", "C06": "SESSION_DEPENDENCE", "C07": "CROSSMARKET_NON_CONFIRMATION",
    "C08": "SAME_EVENT_DUPLICATION", "C09": "ALTERNATIVE_MECHANISM", "C10": "UNKNOWN",
}
LIFECYCLE = ["DISCOVERED", "UNDER_REVIEW", "SUPPORTED", "UNCERTAIN", "REJECTED", "SUPERSEDED"]

REGISTRY = {
    "version": MV_VERSION,
    "taxonomy": TAXONOMY,
    "event_separation_window": {"unit": "bars_on_the_records_own_grid", "value": 6,
                                  "cross_grid_merge": {"rule": "same mechanism_id and |dt| <= 2h -> one cross_grid_event",
                                                        "value_hours": 2}},
    "minimum_independent_events": 8,
    "stability_windows": {"split": "event time thirds", "names": ["EARLY", "MIDDLE", "LATE"],
                           "rules": {"HIGH": "all three non-empty and no third > 70% of events",
                                      "MEDIUM": "two thirds non-empty", "LOW": "otherwise"}},
    "counter_evidence_rules": {
        "artifact_codes": ["C01", "C02", "C03"],
        "fatal_codes": ["C08"],
        "severity": "HIGH if any artifact code or C07 dominates; MEDIUM for C04/C05/C06/C09; LOW otherwise",
        "strongest_counter_evidence_required": True, "count_alone_is_not_enough": True},
    "artifact_rules": {
        "checks": ["timestamp artifact", "bar construction artifact", "proxy artifact", "source artifact",
                    "selection artifact", "duplicate detection"],
        "proxy_dependency_high_when": "the only cross-market confirmation is UST10Y_PROXY (^TNX)",
        "artifact_first": "if the best explanation is a data artifact -> REJECTED or UNCERTAIN, never CANDIDATE"},
    "candidate_entry_rules": {"requires": ["MECHANISM_SUPPORTED",
                                             "independent_event_count >= minimum_independent_events",
                                             "artifact_risk != HIGH", "strongest_counter_evidence != C08"],
                               "thresholds_frozen_before_run": True},
    "negative_control_definition": {"method": "shuffle the detected_at timestamps across opportunities (types and "
                                              "feature values kept), rebuild clusters and events, re-decide",
                                     "pass_if": "SUPPORTED count is not materially above the real run",
                                     "no_future_return": True},
    "response_observation": {"window_bars": 3, "excluded_from_decision": True,
                              "reason": "post-event data is descriptive only; keeping it out of the decision makes "
                                        "historical decisions stable under truncation"},
    "causality_levels": ["CO_MOVEMENT", "TEMPORAL_PRECEDENCE", "MECHANISTIC_HYPOTHESIS", "CAUSALITY_UNPROVEN"],
    "causality_default": "CO_MOVEMENT for same-bar external/XAU observations; TEMPORAL_PRECEDENCE requires strict "
                          "timestamp ordering, which a bar-aligned grid cannot demonstrate",
    "forbidden_identifiers": ["future_return", "future_pnl", "pnl", "win_rate", "sharpe", "profit_factor",
                                "expected_profit", "expected_return", "profit_score", "win_probability",
                                "order_send", "order_check", "metatrader5", "broker", "execution"],
    "lifecycle": {k: [] for k in LIFECYCLE},
}


def registry_hash() -> str:
    return hashlib.sha256(json.dumps(REGISTRY, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ------------------------------------------------------------------ signatures

def signature(rec: dict) -> dict:
    fv = rec.get("feature_values", {})
    t = rec["opportunity_type"]
    vs = str(rec.get("market_state", {}).get("vol_state"))
    sess = str(rec.get("market_state", {}).get("session_bucket"))
    ez = {nm: abs(float(fv.get(f"{nm}_RETURN_60M_z") or 0.0)) for nm in ("DXY", "VIX", "UST10Y_PROXY")}
    conf = [nm for nm, z in ez.items() if z >= 2.0]
    trig = ("PRICE_EXTREME" if abs(float(fv.get("return_60m") or 0.0)) >= 300 else
            "VOL_EXTREME" if float(fv.get("vol_pct_240") or 0.0) >= 0.95 else
            "VOL_EXPANSION" if float(fv.get("vol_pct_240") or 0.0) >= 0.90 else
            "DXY_SHOCK" if ez["DXY"] >= 2 else "VIX_SHOCK" if ez["VIX"] >= 2 else
            "UST10Y_PROXY_SHOCK" if ez["UST10Y_PROXY"] >= 2 else "STATE_BREAK")
    transmission = ("CROSSMARKET" if conf else ("DIRECT" if t in ("OPP_STATE_BREAK", "OPP_STATE_TRANSITION",
                                                                    "OPP_VOL_TRANSITION") else "UNKNOWN"))
    return {"trigger_signature": trig, "transmission_signature": transmission,
             "response_signature": "UNKNOWN",           # filled as an observation later
             "time_signature": sess, "market_state_signature": vs,
             "crossmarket_signature": "+".join(sorted(conf)) if conf else "NONE",
             "artifact_signature": ("PROXY_DEPENDENT" if conf == ["UST10Y_PROXY"] else
                                     ("MULTI_SOURCE" if len(conf) > 1 else "SINGLE_SOURCE"))}


def classify(sig: dict, rec: dict) -> str:
    """Fixed taxonomy mapping. Anything not confidently classifiable -> M11."""
    t = rec["opportunity_type"]
    vs = sig["market_state_signature"]
    vp = float(rec.get("feature_values", {}).get("vol_pct_240") or 0.0)
    r5 = float(rec.get("feature_values", {}).get("vol_ratio_5_30") or 1.0)
    if t == "OPP_CROSSMARKET_SHOCK":
        return "M03"
    if t == "OPP_CROSSMARKET_DIVERGENCE":
        return "M04"
    if t == "OPP_STATE_TRANSITION":
        return "M02"
    if t == "OPP_VOL_TRANSITION":
        return "M07" if (vp > 0.9 and r5 <= 0.5) else "M02"
    if t == "OPP_STATE_BREAK":
        if sig["trigger_signature"] == "PRICE_EXTREME":
            return "M08" if vs == "VOL_EXPANSION" else "M01"
        if sig["trigger_signature"] in ("VOL_EXTREME", "VOL_EXPANSION"):
            return "M02"
    return "M11"


def cluster_key(sig: dict, mech: str) -> str:
    """Interpretable cluster: mechanism x trigger x cross-market x state-band x session-band."""
    sess = "NY" if sig["time_signature"] in ("NewYork", "Overlap") else sig["time_signature"]
    band = "LOWVOL" if sig["market_state_signature"] in ("VOL_CONTRACTION", "VOL_NORMAL") else "HIGHVOL"
    return f"{mech}|{sig['trigger_signature']}|{sig['crossmarket_signature']}|{band}|{sess}"


# ------------------------------------------------------------------ events

def build_events(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Cluster -> independent events (within-grid separation) -> cross-grid merge."""
    groups: dict[str, list[dict]] = {}
    for r in records:
        groups.setdefault(r["cluster_key"], []).append(r)
    events = []
    for ck, rs in sorted(groups.items()):            # sorted -> group order cannot depend on input order
        rs = sorted(rs, key=lambda x: x["detected_at"])
        cur = None
        for r in rs:
            t = pd.Timestamp(r["detected_at"])
            if cur is None or (t - cur["last_t"]) > pd.Timedelta(hours=(6 if r["grid"] == "1h" else 0.5)):
                # CONTENT-DERIVED id: a truncated replay must not renumber a historical event
                eid = "EVT-" + hashlib.sha1(f"{ck}|{r['detected_at']}".encode()).hexdigest()[:10]
                cur = {"independent_event_id": eid, "cluster_key": ck, "mechanism_id": r["mechanism_id"],
                        "event_start": r["detected_at"], "event_end": r["detected_at"], "last_t": t,
                        "opportunities": [r], "grids": {r["grid"]}, "states": {r["market_state_signature"]},
                        "crossmarket": {r["crossmarket_signature"]}, "sessions": {r["time_signature"]}}
                events.append(cur)
            else:
                cur["opportunities"].append(r)
                cur["event_end"] = r["detected_at"]
                cur["last_t"] = t
                cur["grids"].add(r["grid"])
                cur["states"].add(r["market_state_signature"])
                cur["crossmarket"].add(r["crossmarket_signature"])
                cur["sessions"].add(r["time_signature"])
    # cross-grid merge: same mechanism, |dt| <= 2h and different grids only
    merged, used = [], set()
    events_sorted = sorted(events, key=lambda e: e["event_start"])
    for i, e in enumerate(events_sorted):
        if i in used:
            continue
        for j in range(i + 1, len(events_sorted)):
            f = events_sorted[j]
            if j in used:
                continue
            if f["mechanism_id"] != e["mechanism_id"]:
                continue
            dt = abs((pd.Timestamp(f["event_start"]) - pd.Timestamp(e["event_start"])).total_seconds())
            if dt <= 7200 and (e["grids"] | f["grids"]) == {"1h", "5m"}:
                e["opportunities"] += f["opportunities"]
                e["grids"] |= f["grids"]
                e["states"] |= f["states"]
                e["crossmarket"] |= f["crossmarket"]
                e["sessions"] |= f["sessions"]
                e["event_end"] = max(e["event_end"], f["event_end"], key=lambda s: pd.Timestamp(s))
                e["cross_grid_merged_with"] = f["independent_event_id"]
                used.add(j)
        merged.append(e)
    for e in merged:
        e["grids_involved"] = sorted(e["grids"])
        e["opportunities_merged"] = len(e["opportunities"])
        e["cross_grid_event_id"] = f"XG-{e['independent_event_id']}"
    return events_sorted, merged


# ------------------------------------------------------------------ counter evidence

def counter_codes(rec: dict, review: dict, event: dict | None = None) -> list[str]:
    """EVENT-LEVEL, record-specific counter-evidence codes.

    Method history (disclosed): a first version matched the QF-R1 Hermes artifact checklist by string, which
    attached C01/C02/C03 to every opportunity and made the artifact dimension a blanket veto (an ablation exposed
    it). A second version still measured duplication as the share of *continuation opportunities*, which double-
    penalises: those continuations were already collapsed into single events by R1 clustering AND by this stage's
    event builder. The codes below are therefore attached to the EVENT, not to raw opportunities.
    """
    codes = set()
    is_xm = rec["opportunity_type"].startswith("OPP_CROSSMARKET")
    cm_sig = rec.get("crossmarket_signature") or "NONE"
    if event is not None:
        opps = event.get("opportunities", [])
        if len(opps) > 1:
            sigs = {json.dumps(o.get("signals", {}), sort_keys=True) for o in opps}
            if len(sigs) == 1:
                codes.add("C01")              # degenerate event: merged rows carry identical signatures
    if is_xm:
        codes.add("C02")                      # two-vendor bar/timestamp alignment risk (cross-market only)
    if cm_sig == "UST10Y_PROXY":
        codes.add("C03")                      # the ONLY confirmation is the ^TNX proxy
    if is_xm and cm_sig == "NONE":
        codes.add("C07")                      # cross-market non-confirmation
    if is_xm and cm_sig == "UST10Y_PROXY":
        codes.add("C09")                      # alternative explanation: proxy-driven
    txt = json.dumps(review, ensure_ascii=False).lower()
    if "sample" in txt:
        codes.add("C04")
    if "regime" in txt:
        codes.add("C05")
    if "session" in txt:
        codes.add("C06")
    return sorted(codes) or ["C10"]


def strongest(codes: dict[str, int]) -> tuple[str, str]:
    order = ["C08", "C01", "C02", "C03", "C07", "C04", "C05", "C06", "C09", "C10"]
    for c in order:
        if codes.get(c):
            return c, COUNTER_CODES[c]
    return "C10", COUNTER_CODES["C10"]


# ------------------------------------------------------------------ evidence + decision

def evidence_matrix(events: list[dict], mech: str, codes: dict[str, int], dq: dict[str, int]) -> dict:
    ev = [e for e in events if e["mechanism_id"] == mech]
    n = len(ev)
    if n == 0:
        return {"independent_events": "LOW"}
    trig = {}
    for e in ev:
        k = e["cluster_key"].split("|")[1]
        trig[k] = trig.get(k, 0) + 1
    trig_cons = max(trig.values()) / n
    times = sorted(pd.Timestamp(e["event_start"]) for e in ev)
    lo, hi = times[0], times[-1]
    thirds = [(lo, lo + (hi - lo) / 3), (lo + (hi - lo) / 3, lo + 2 * (hi - lo) / 3), (lo + 2 * (hi - lo) / 3, hi)]
    counts = [sum(1 for t in times if a <= t <= b) for a, b in thirds]
    nonempty = sum(1 for c in counts if c > 0)
    time_stab = ("HIGH" if nonempty == 3 and max(counts) <= 0.7 * n else ("MEDIUM" if nonempty == 2 else "LOW"))
    sess = {}
    for e in ev:
        for s in e["sessions"]:
            sess[s] = sess.get(s, 0) + 1
    sess_stab = "LOW" if (len(sess) <= 1 or max(sess.values()) > 0.7 * n) else "HIGH"
    st = {}
    for e in ev:
        for s in e["states"]:
            st[s] = st.get(s, 0) + 1
    state_stab = "LOW" if max(st.values()) > 0.7 * n else "HIGH"
    sc, sname = strongest(codes)
    c01, c02, c03 = codes.get("C01", 0), codes.get("C02", 0), codes.get("C03", 0)
    artifact = ("HIGH" if n and (c01 >= 0.5 * n or c03 >= 0.5 * n) else ("MEDIUM" if c02 else "LOW"))
    # C08 is residual duplication at EVENT level; by construction the event builder prevents it, so it is
    # computed here rather than assumed
    ck_counts: dict[str, int] = {}
    for e in ev:
        ck_counts[e["cluster_key"]] = ck_counts.get(e["cluster_key"], 0) + 1
    c08 = 0
    seen: dict[str, list] = {}
    for e in sorted(ev, key=lambda x: x["event_start"]):
        k = e["cluster_key"]
        for prev in seen.get(k, []):
            dt = abs((pd.Timestamp(e["event_start"]) - pd.Timestamp(prev)).total_seconds())
            if dt <= 6 * 3600:
                c08 += 1
        seen.setdefault(k, []).append(e["event_start"])
    codes = dict(codes)
    if c08:
        codes["C08"] = c08
    sc, sname = strongest(codes)
    cev = "HIGH" if (sc == "C08" or artifact == "HIGH") else ("MEDIUM" if codes else "LOW")
    rec_lab = "HIGH" if n >= 20 else ("MEDIUM" if n >= 8 else "LOW")
    tx = "UNKNOWN"           # bar-aligned grid cannot prove precedence
    return {"TRIGGER_CONSISTENCY": ("HIGH" if trig_cons >= 0.7 else "MEDIUM" if trig_cons >= 0.4 else "LOW"),
             "TRANSMISSION_CONSISTENCY": tx, "RESPONSE_CONSISTENCY": "UNKNOWN",
             "RECURRENCE": rec_lab, "INDEPENDENT_EVENTS": ("SUFFICIENT" if n >= REGISTRY["minimum_independent_events"] else "LOW"),
             "TIME_STABILITY": time_stab, "SESSION_STABILITY": sess_stab, "STATE_STABILITY": state_stab,
             "DATA_QUALITY": ("UNKNOWN" if dq.get("UNKNOWN") else ("VERIFIED" if not dq.get("PARTIAL") else "PARTIAL")),
             "COUNTER_EVIDENCE": cev, "ARTIFACT_RISK": artifact, "counter_codes_used": codes,
             "detail": {"events": n, "trigger_consistency_ratio": round(trig_cons, 3), "third_counts": counts,
                         "session_distribution": sess, "state_distribution": st, "strongest_counter": [sc, sname]}}


def decide(em: dict, codes: dict[str, int]) -> tuple[str, str, str]:
    sc, sname = strongest(codes)
    if em.get("ARTIFACT_RISK") == "HIGH":
        return "MECHANISM_REJECTED", "A1", f"artifact first: strongest counter-evidence is {sc} {sname}"
    if sc == "C08":
        return "MECHANISM_REJECTED", "A2", "same-event duplication dominates"
    if em.get("INDEPENDENT_EVENTS") == "LOW":
        return "MECHANISM_UNCERTAIN", "A3", "independent event count below the frozen minimum"
    if em.get("COUNTER_EVIDENCE") == "HIGH":
        return "MECHANISM_UNCERTAIN", "A4", "counter-evidence is HIGH without being artifact-fatal"
    good = (em.get("TRIGGER_CONSISTENCY") in ("HIGH", "MEDIUM") and em.get("TIME_STABILITY") in ("HIGH", "MEDIUM"))
    if good and em.get("COUNTER_EVIDENCE") in ("LOW", "MEDIUM"):
        return "MECHANISM_SUPPORTED", "A5", "trigger consistency, time stability and counter-evidence all acceptable"
    return "MECHANISM_UNCERTAIN", "A6", "structure present but evidence is not sufficient"


# ------------------------------------------------------------------ ledger

class MechanismLedger:
    def __init__(self, path: str, reg_hash: str):
        self.path, self.reg = path, reg_hash
        self._prev = "GENESIS"
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                if line.strip():
                    self._prev = json.loads(line)["chain_hash"]

    def append(self, rec: dict) -> str:
        body = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        h = hashlib.sha256((self._prev + body).encode()).hexdigest()
        seq = (sum(1 for l in open(self.path, encoding="utf-8") if l.strip()) if os.path.exists(self.path) else 0)
        row = {"seq": seq, "prev_hash": self._prev, "chain_hash": h, "registry_hash": self.reg, "payload": rec}
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        self._prev = h
        return h

    @staticmethod
    def verify(path: str) -> dict:
        if not os.path.exists(path):
            return {"rows": 0, "chain_ok": True, "bad_seq": None}
        prev, n, ok, bad = "GENESIS", 0, True, None
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            row = json.loads(line)
            body = json.dumps(row["payload"], sort_keys=True, ensure_ascii=False)
            h = hashlib.sha256((prev + body).encode()).hexdigest()
            if h != row["chain_hash"] or row["prev_hash"] != prev:
                ok, bad = False, row["seq"]
                break
            prev, n = h, n + 1
        return {"rows": n, "chain_ok": ok, "bad_seq": bad}
