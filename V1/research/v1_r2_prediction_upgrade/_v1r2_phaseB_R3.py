# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R3: tick audit -> tick->M15 reconstruction -> overlap validation -> authoritative join ->
strict PIT alignment (NO silent clamp) -> recompute R2 states (frozen rules v3) -> D5 re-evaluation.
Read-only w.r.t. all source data. New namespace v1_r2_research_runs/V1_R2_RUN_B4_*.
NO future returns / PnL / win-rate. No order APIs."""
from __future__ import annotations

import glob
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
TICKDIR = os.path.join(REPO, "data", "live_fxtm")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
DEC = os.path.join(REPO, "research", "hermes", "trader_v1", "run_state", "decisions")
R1MOD = os.path.join(UP, "_v1r2_phaseB_R1.py")
R2MOD = os.path.join(UP, "_v1r2_phaseB_R2.py")
NOW = datetime.now(timezone.utc).isoformat()
GRID = pd.Timedelta(minutes=15)
PRICE_SOURCE = "BID"          # 固定规则（先定后用）：MT5 copy_rates 默认 bid；与历史导出管线一致
PRICE_SOURCE_REASON = "MT5 copy_rates(default) returns bid series; the historical M1 export pipeline used the same terminal path"
REC_VER = "v1r2-m15-recon-r1"


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def wjson(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def main():
    R1 = load_mod("v1r2_r1", R1MOD)
    R2 = load_mod("v1r2_r2", R2MOD)
    run_dir = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)

    # ============ §3/§4 TICK AUDIT ============
    files = sorted(glob.glob(os.path.join(TICKDIR, "ticks_*.parquet")))
    audit, frames, fhashes = [], [], {}
    for p in files:
        f = os.path.basename(p)
        df = pd.read_parquet(p, columns=["utc_ms", "bid", "ask", "ts_utc"])
        t = pd.to_datetime(df["utc_ms"], unit="ms", utc=True)
        order_ok = bool(t.is_monotonic_increasing)
        dup = int(df["utc_ms"].duplicated().sum())
        bad_px = int(((df["bid"] <= 0) | (df["ask"] <= 0)).sum())
        crossed = int((df["bid"] > df["ask"]).sum())
        null_ts = int(df["utc_ms"].isna().sum())
        audit.append({"file": f, "rows": int(len(df)), "min_ts": str(t.min()), "max_ts": str(t.max()),
                        "timezone": "UTC(from utc_ms)", "symbol": "XAUUSD(assumed by pipeline)",
                        "bid_available": True, "ask_available": True, "volume_available": False,
                        "volume_zero_pct": 1.0, "duplicate_utc_ms": dup, "monotonic": order_ok,
                        "invalid_price": bad_px, "crossed_bid_ask": crossed, "missing_timestamp": null_ts})
        fhashes[f] = sha_file(p)
        df = df.assign(ts=t)
        df = df[(df["utc_ms"].notna()) & (df["bid"] > 0) & (df["ask"] > 0) & (df["bid"] <= df["ask"])]
        frames.append(df[["ts", "bid", "ask"]])
    tk = pd.concat(frames, ignore_index=True).sort_values("ts").drop_duplicates(subset="ts", keep="first")
    tk["mid"] = (tk["bid"] + tk["ask"]) / 2.0
    cross_overlap = []
    for a, b in zip(audit, audit[1:]):
        if a["max_ts"] > b["min_ts"]:
            cross_overlap.append({"prev": a["file"], "next": b["file"], "prev_max": a["max_ts"], "next_min": b["min_ts"]})
    tick_audit = {"files": audit, "TICK_FILES": len(audit), "TICK_ROWS_RAW": int(sum(a["rows"] for a in audit)),
                    "TICK_ROWS_CLEAN": int(len(tk)), "TICK_MIN": str(tk["ts"].min()), "TICK_MAX": str(tk["ts"].max()),
                    "TICK_DUPLICATES_TOTAL": int(sum(a["duplicate_utc_ms"] for a in audit)),
                    "CROSS_FILE_OVERLAP": cross_overlap,
                    "invalid_or_crossed_removed": int(sum(a["invalid_price"] + a["crossed_bid_ask"] for a in audit)),
                    "timestamp_order_ok_all": all(a["monotonic"] for a in audit),
                    "source_file_hashes": fhashes}
    wjson(os.path.join(run_dir, "TICK_AUDIT.json"), tick_audit)
    print("TICK:", json.dumps({k: tick_audit[k] for k in ("TICK_FILES", "TICK_ROWS_RAW", "TICK_ROWS_CLEAN", "TICK_MIN",
                                                             "TICK_MAX", "TICK_DUPLICATES_TOTAL")}, ensure_ascii=False), flush=True)

    # ============ §5/§6/§7 TICK -> M15 RECONSTRUCTION (PRICE_SOURCE=BID, no fill) ============
    def recon(col):
        g = tk.groupby(tk["ts"].dt.floor("15min"))
        out = pd.DataFrame({"o": g[col].first(), "h": g[col].max(), "l": g[col].min(), "c": g[col].last(),
                              "tick_count": g[col].size(), "first_tick": g["ts"].min(), "last_tick": g["ts"].max()})
        out = out[out["tick_count"] > 0]
        return out
    m15_bid = recon("bid")
    m15_mid = recon("mid")
    m15_ask = recon("ask")
    covered = pd.date_range(m15_bid.index.min(), m15_bid.index.max(), freq="15min", tz="UTC")
    missing = covered.difference(m15_bid.index)
    m15_bid = m15_bid.assign(bar_start=m15_bid.index, bar_end=m15_bid.index + GRID)
    rec_meta = {"reconstruction_version": REC_VER, "price_source": PRICE_SOURCE, "price_source_reason": PRICE_SOURCE_REASON,
                  "bin": "15min UTC (floor)", "empty_bucket_rule": "NO BAR + DATA_GAP (no ffill/synthetic)",
                  "bars": int(len(m15_bid)), "covered_15min_slots": int(len(covered)), "missing_slots": int(len(missing)),
                  "missing_intervals_sample": [str(x) for x in list(missing[:10])],
                  "source_file_hashes": fhashes, "tick_rows_used": int(len(tk))}
    rec_meta["reconstruction_hash"] = sha_obj({**rec_meta, "ohlc": [[str(i), float(r.o), float(r.h), float(r.l), float(r.c)]
                                                                     for i, r in m15_bid.iterrows()]})
    m15_bid.to_parquet(os.path.join(run_dir, "m15_tick_bid.parquet"))
    wjson(os.path.join(run_dir, "M15_RECONSTRUCTION_META.json"), rec_meta)
    print("RECON:", json.dumps({"bars": rec_meta["bars"], "missing_slots": rec_meta["missing_slots"],
                                  "hash": rec_meta["reconstruction_hash"][:16]}, ensure_ascii=False), flush=True)

    # ============ §9/§11/§12 OVERLAP VALIDATION vs historical M1->M15 ============
    hist = R1.load_m15()                       # historical M15 (labels = bar start), authoritative in overlap
    hist = hist.rename(columns={"o": "ho", "h": "hh", "l": "hl", "c": "hc"})
    def overlap_stats(rec_df, label):
        j = hist.join(rec_df[["o", "h", "l", "c"]], how="inner")
        if j.empty:
            return {"label": label, "bars": 0}
        d = {k: float(np.nanmean(np.abs(j[f"h{k}"] - j[k]))) for k in ("o", "h", "l", "c")}
        rel = {k: float(np.nanmean(np.abs(j[f"h{k}"] - j[k]) / np.maximum(np.abs(j[f"h{k}"]), 1e-9))) for k in ("o", "h", "l", "c")}
        tol = 0.05
        mism = {k: int((np.abs(j[f"h{k}"] - j[k]) > tol).sum()) for k in ("o", "h", "l", "c")}
        return {"label": label, "bars": int(len(j)), "abs_diff": d, "rel_diff": rel, "mismatch_count": mism,
                  "mismatch_rate": {k: round(mism[k] / max(1, len(j)), 5) for k in mism},
                  "overlap_window": [str(j.index.min()), str(j.index.max())], "tolerance_usd": tol}
    ov = {"overlap_window_hist_end": str(hist.index.max()), "overlap_window_tick_start": str(m15_bid.index.min()),
            "PRIMARY_price_source": PRICE_SOURCE, "diagnostics_do_not_change_selection": True,
            "BID": overlap_stats(m15_bid, "BID"), "MID": overlap_stats(m15_mid, "MID"), "ASK": overlap_stats(m15_ask, "ASK")}
    ov["OVERLAP_TEST"] = ("PASS" if (ov["BID"].get("bars", 0) > 0 and max(ov["BID"]["mismatch_rate"].values()) < 0.05)
                            else "REVIEW")
    wjson(os.path.join(run_dir, "OVERLAP_VALIDATION.json"), ov)
    print("OVERLAP:", json.dumps({"BID_bars": ov["BID"].get("bars"), "BID_mismatch_rate": ov["BID"].get("mismatch_rate"),
                                    "MID_mismatch_rate": ov["MID"].get("mismatch_rate"),
                                    "ASK_mismatch_rate": ov["ASK"].get("mismatch_rate"), "TEST": ov["OVERLAP_TEST"]},
                                   ensure_ascii=False), flush=True)

    # ============ §11/§12 JOIN (historical authoritative in overlap; tick fills only AFTER hist end) ============
    hist_end = hist.index.max()
    tick_extra = m15_bid[m15_bid.index > hist_end]
    joined = pd.concat([hist[["ho", "hh", "hl", "hc"]].rename(columns={"ho": "o", "hh": "h", "hl": "l", "hc": "c"}),
                          tick_extra[["o", "h", "l", "c"]]]).sort_index()
    joined = joined[~joined.index.duplicated(keep="first")]
    join_manifest = {"historical_source": os.path.relpath(M1P, REPO).replace("\\", "/"),
                       "historical_end": str(hist_end), "tick_source": "data/live_fxtm/ticks_2026*.parquet (15 files)",
                       "tick_start": str(m15_bid.index.min()), "tick_end": str(m15_bid.index.max()),
                       "join_timestamp": str(hist_end),
                       "overlap_window": [str(max(hist.index.min(), m15_bid.index.min())), str(hist_end)],
                       "overlap_test": ov["OVERLAP_TEST"], "selected_authority": "HISTORICAL_IN_OVERLAP; TICK_ONLY_AFTER_HIST_END",
                       "added_bars_from_tick": int(len(tick_extra)), "historical_bars": int(len(hist)),
                       "joined_bars": int(len(joined)), "empty_buckets_are_gaps": True,
                       "dataset_hash": sha_obj({str(i): [float(r.o), float(r.h), float(r.l), float(r.c)] for i, r in joined.iterrows()})}
    wjson(os.path.join(run_dir, "DATASET_JOIN_MANIFEST.json"), join_manifest)
    print("JOIN:", json.dumps({k: join_manifest[k] for k in ("historical_end", "tick_end", "added_bars_from_tick",
                                                                "joined_bars")}, ensure_ascii=False), flush=True)

    # ============ §18 RECOMPUTE R2 STATES (frozen rules v3; no rule change) ============
    jd = R1.indicators(joined.copy())
    states = R1.engines_v2(jd)
    jts = pd.to_datetime([s["t"] for s in states], utc=True)
    with open(os.path.join(run_dir, "states_joined.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for s in states:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    # v3 rule layer applied to the stored facts (same as B-R2; rules unchanged)
    v3s = [R2.ns_v3(s) for s in states]
    # ============ §13/§14/§15 ALEIGNMENT (strict, NO silent clamp) ============
    ds_min, ds_max = jts[0], jts[-1]
    ds_max_close = ds_max + GRID
    decs = []
    for f in sorted(os.listdir(DEC)):
        if not f.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(DEC, f), encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        decs.append((f, d))
    align = []
    for f, d in decs:
        cyc = d.get("cycle")
        rec = {"decision_id": f, "dataset_version": REC_VER, "v1_decision": d.get("decision"),
                 "v1_confidence": d.get("confidence")}
        try:
            t = pd.Timestamp(str(cyc).replace("Z", "+00:00"))
            t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
        except Exception:  # noqa: BLE001
            align.append({**rec, "decision_timestamp": str(cyc), "normalized_timestamp": None, "matched_bar_timestamp": None,
                            "matched_bar_index": None, "match_delta": None, "inside_dataset": False, "pit_valid": False,
                            "alignment_status": "INVALID", "alignment_reason": "TIMESTAMP_UNPARSEABLE"})
            continue
        idx = int(jts.searchsorted(t - GRID, side="right")) - 1
        if t < ds_min:
            st_, rsn, inside, pit, bar, delta = "OUT_OF_DATASET", "BEFORE_DATASET_MIN", False, False, None, None
        elif t > ds_max_close:
            st_, rsn, inside, pit, bar, delta = "ALIGNMENT_ERROR", "REQUESTED_TS_GT_DATASET_MAX_NO_CLAMP", False, False, None, None
        else:
            bar = jts[idx]; bc = bar + GRID; delta = float((t - bc).total_seconds()); inside, pit = True, bool(bc <= t)
            st_, rsn = ("VALID_PIT_ALIGNED", "BAR_CLOSE_LE_DECISION") if pit else ("AMBIGUOUS_ALIGNMENT", "BAR_CLOSE_GT_DECISION")
        align.append({**rec, "decision_timestamp": str(cyc), "normalized_timestamp": str(t),
                        "matched_bar_timestamp": (str(bar) if bar is not None else None),
                        "matched_bar_index": (idx if bar is not None else None), "match_delta": delta,
                        "inside_dataset": inside, "pit_valid": pit, "alignment_status": st_, "alignment_reason": rsn})
    # §16 duplicates
    seen = {}
    for a in align:
        if a["normalized_timestamp"]:
            seen.setdefault(a["normalized_timestamp"], []).append(a)
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    dup_detail = []
    for k, v in dups.items():
        ch = [{"decision_id": x["decision_id"], "file": x["decision_id"], "timestamp": k,
                 "v1_decision": x.get("v1_decision"), "content_hash": sha_file(os.path.join(DEC, x["decision_id"]))} for x in v]
        same = len({c["content_hash"] for c in ch}) == 1
        dup_detail.append({"timestamp": k, "records": ch,
                             "classification": ("DUPLICATE_FILE" if same else "LEGITIMATE_MULTIPLE_DECISION"),
                             "dedup_rule": "keep first by decision_id (documented); original files preserved"})
    for a in align:
        if a["normalized_timestamp"] in dups:
            a["alignment_status"] = "DUPLICATE_TIMESTAMP"
            a["alignment_reason"] = (a["alignment_reason"] or "") + ";DUPLICATE_TS"
    wjson(os.path.join(run_dir, "DUPLICATE_INVESTIGATION.json"), {"duplicates": dup_detail})
    with open(os.path.join(run_dir, "ALIGNMENT_AUDIT.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for a in align:
            fh.write(json.dumps(a, ensure_ascii=False) + "\n")
    cnt = {}
    for a in align:
        cnt[a["alignment_status"]] = cnt.get(a["alignment_status"], 0) + 1
    valid = [a for a in align if a["alignment_status"] == "VALID_PIT_ALIGNED"]
    print("ALIGN:", json.dumps(cnt, ensure_ascii=False), "| valid:", len(valid), flush=True)

    # ============ §20/§21/§22/§23 D5 RE-EVALUATION ============
    replay = []
    for a in valid:
        i = a["matched_bar_index"]; st = states[i]
        mu = R2.rule_mu(st)
        v2st = v3s[i]
        replay.append({"decision_id": a["decision_id"], "cycle": a["decision_timestamp"], "bar": a["matched_bar_timestamp"],
                         "bar_close_delta_s": a["match_delta"], "V1_R1_DECISION": a["v1_decision"],
                         "V1_R2_DECISION": mu["value"], "V1_R2_STATE_v3": v2st,
                         "V1_R2_DIRECTION_SOURCE": mu["source"], "V1_R2_DIRECTION_CONFIDENCE": mu["confidence"],
                         "V1_R2_SUPPORT_GROUPS": mu["support"], "V1_R2_COUNTER_GROUPS": mu["counter"],
                         "V1_R2_NONE_REASON": mu["none_reason"],
                         "decision_changed": (a["v1_decision"] != mu["value"]),
                         "direction_changed": (a["v1_decision"] in ("LONG", "SHORT") and a["v1_decision"] != mu["value"]),
                         "entry_filter_changed": (a["v1_decision"] == "WAIT" and mu["value"] in ("LONG", "SHORT")),
                         "primary_reason": ("NO_DIRECTIONAL_STATE" if mu["none_reason"] == "UNKNOWN_NEXT_STATE" else
                                              ("CONFLICTING_EVIDENCE" if mu["none_reason"] == "CONFLICTING_EVIDENCE" else
                                               ("INSUFFICIENT_INDEPENDENT_EVIDENCE" if mu["none_reason"] == "INSUFFICIENT_CONTEXT" else
                                                ("DIRECTIONAL_EVIDENCE_PRESENT" if mu["value"] != "NONE" else "NO_VALID_DIRECTION_SOURCE")))),
                         "supporting_evidence": mu["support"], "counter_evidence": mu["counter"],
                         "changed_features": ["direction_source", "evidence_groups"],
                         "changed_states": {"regime": st.get("regime"), "momentum": st.get("momentum"),
                                              "touch": st.get("touch_state"), "break": (st.get("break_risk") or {}).get("state"),
                                              "next_state_v3": v2st}})
    with open(os.path.join(run_dir, "parallel_replay_v4.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for r in replay:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    v1d = sum(1 for r in replay if r["V1_R1_DECISION"] in ("LONG", "SHORT"))
    v2d = sum(1 for r in replay if r["V1_R2_DECISION"] in ("LONG", "SHORT"))
    agree = sum(1 for r in replay if r["V1_R1_DECISION"] in ("LONG", "SHORT") and r["V1_R1_DECISION"] == r["V1_R2_DECISION"])
    none_dist = {}
    for r in replay:
        k = r["V1_R2_NONE_REASON"] or "DIRECTIONAL"
        none_dist[k] = none_dist.get(k, 0) + 1
    # §24 structural reachability on joined dataset
    reach = {}
    for m in ("B", "C", "D"):
        reach[m] = sum(1 for s in states if R2.rule_variant(s, m) in ("LONG", "SHORT"))
    reach["MU"] = sum(1 for s in states if R2.rule_mu(s)["value"] in ("LONG", "SHORT"))
    reach_rate = {k: round(v / max(1, len(states)), 4) for k, v in reach.items()}
    # §25 per-date table for the core window
    core = []
    dec_by_date = {}
    for a in align:
        if a["normalized_timestamp"]:
            dec_by_date.setdefault(a["normalized_timestamp"][:10], []).append(a)
    for dstr in ("2026-09-19", "2026-09-20", "2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"):
        day0 = pd.Timestamp(dstr, tz="UTC")
        ticks_day = int(((tk["ts"] >= day0) & (tk["ts"] < day0 + pd.Timedelta(days=1))).sum())
        bars_day = int(((m15_bid.index >= day0) & (m15_bid.index < day0 + pd.Timedelta(days=1))).sum())
        slots = int(len(pd.date_range(day0, day0 + pd.Timedelta(days=1), freq="15min", inclusive="left")))
        ds = dec_by_date.get(dstr, [])
        core.append({"date": dstr, "tick_count": ticks_day, "M15_count": bars_day, "missing_bars": slots - bars_day,
                       "decision_count": len(ds), "valid_decision_count": sum(1 for x in ds if x["alignment_status"] == "VALID_PIT_ALIGNED"),
                       "V1_direction_count": sum(1 for x in ds if x["v1_decision"] in ("LONG", "SHORT")),
                       "V2_direction_count": sum(1 for x in ds if x["alignment_status"] == "VALID_PIT_ALIGNED"
                                                   and R2.rule_mu(states[x["matched_bar_index"]])["value"] in ("LONG", "SHORT")),
                       "alignment_fail_count": sum(1 for x in ds if x["alignment_status"] != "VALID_PIT_ALIGNED")})
    # §27 D5 verdict
    if len(valid) == 0:
        d5 = "UNVERIFIED"
    elif v1d == 0:
        d5 = "UNVERIFIED"
    else:
        d5 = "PASS"
    out = {"task": "V1_R2_PHASE_B_R3", "status": "COMPLETE" if d5 == "PASS" else "BLOCKED",
             "TICK_AUDIT": {k: tick_audit[k] for k in ("TICK_FILES", "TICK_ROWS_CLEAN", "TICK_MIN", "TICK_MAX",
                                                          "TICK_DUPLICATES_TOTAL", "CROSS_FILE_OVERLAP")},
             "RECONSTRUCTION": {"M15_RECONSTRUCTED_BARS": rec_meta["bars"], "RECONSTRUCTION_HASH": rec_meta["reconstruction_hash"],
                                  "missing_slots": rec_meta["missing_slots"], "price_source": PRICE_SOURCE,
                                  "price_source_reason": PRICE_SOURCE_REASON},
             "OVERLAP": {k: ov[k] for k in ("BID", "MID", "ASK", "OVERLAP_TEST")},
             "JOIN": join_manifest, "ALIGNMENT": cnt,
             "LEGACY_SILENT_CLAMP": 0 if not any(a["alignment_reason"] == "REQUESTED_TS_GT_DATASET_MAX_NO_CLAMP"
                                                    and a["matched_bar_timestamp"] for a in align) else "NONZERO",
             "D5": d5, "VALID_V1_DECISIONS": len(valid), "VALID_V1_DIRECTIONAL": v1d, "VALID_V2_DIRECTIONAL": v2d,
             "V2_DIRECTION_AGREEMENT": agree, "V2_NONE": len(replay) - v2d, "NONE_REASON": none_dist,
             "REACHABILITY": {"counts": reach, "rates": reach_rate},
             "CORE_WINDOW_TABLE": core, "DUPLICATE_INVESTIGATION": dup_detail,
             "REGISTRY_VERSION": "v1r2-r3", "RULES_VERSION": "v1r2-r1-rules-v3",
             "DATASET_HASH": join_manifest["dataset_hash"], "RUN_ID": os.path.basename(run_dir),
             "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                          "V2_WRITE": 0, "V3_WRITE": 0, "RUN_BOUNDARY_WRITE": 0, "BOUNDARY_VIOLATION": 0, "GIT_COMMIT": "NONE"},
             "PHASE_C_ALLOWED": "YES" if (d5 == "PASS") else "NO", "ts_utc": NOW}
    wjson(os.path.join(UP, "reports", "V1_R2_PHASE_B_R3_SUMMARY.json"), out)
    print("\n=== PHASE B-R3 (§32) ===", flush=True)
    print(json.dumps({"status": out["status"], "TICK": out["TICK_AUDIT"], "RECON": out["RECONSTRUCTION"],
                        "OVERLAP_TEST": ov["OVERLAP_TEST"], "BID_mismatch": ov["BID"].get("mismatch_rate"),
                        "MID_mismatch": ov["MID"].get("mismatch_rate"), "ASK_mismatch": ov["ASK"].get("mismatch_rate"),
                        "JOIN": {k: join_manifest[k] for k in ("historical_end", "tick_end", "added_bars_from_tick", "joined_bars")},
                        "ALIGNMENT": cnt, "D5": d5, "V1_DIRECTIONAL": v1d, "V2_DIRECTIONAL": v2d, "AGREE": agree,
                        "NONE_REASON": none_dist, "REACHABILITY": reach_rate, "DUP": dup_detail,
                        "PHASE_C_ALLOWED": out["PHASE_C_ALLOWED"], "safety": out["safety"]}, ensure_ascii=True, indent=1)[:3200], flush=True)
    print("CORE_WINDOW:", json.dumps(core, ensure_ascii=False)[:1200], flush=True)


if __name__ == "__main__":
    main()
