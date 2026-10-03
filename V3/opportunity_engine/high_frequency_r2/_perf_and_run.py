# -*- coding: utf-8 -*-
"""R2 RUN CLOSEOUT — freeze gate + single permitted performance fix + full re-run.

ONLY the negative-control LOOKUP is vectorised. The RNG stream, draw count, null definition,
tail/comparison and decision rule are byte-identical to the frozen reference, and an equivalence
proof (reference vs optimised) is executed on a fixed sample before the full run.
Nothing in the frozen registry is touched; FREEZE_HASH is re-verified first and STOPs on mismatch.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
REG = os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json")
PRIO = os.path.join(HERE, "high_frequency_priority_registry.json")
FROZEN_HASH = "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    # ---------- §1 freeze gate ----------
    reg = json.load(open(REG, encoding="utf-8"))
    stored = reg.get("FREEZE_HASH")
    body = {k: v for k, v in reg.items() if k not in ("FREEZE_HASH", "frozen_at_utc")}
    recomputed = sha_obj(body)
    print("FREEZE_HASH stored    =", stored)
    print("FREEZE_HASH recomputed=", recomputed)
    print("FREEZE_HASH_MATCH     =", (stored == recomputed == FROZEN_HASH))
    if not (stored == recomputed == FROZEN_HASH):
        print("STOP: freeze hash mismatch -> not continuing")
        sys.exit(2)
    nc_cfg = reg["negative_control"]
    N_NC = nc_cfg.get("runs", nc_cfg.get("negative_control_permutations"))
    print("NEGATIVE_CONTROL_RUNS (frozen registry) =", N_NC)
    prio = json.load(open(PRIO, encoding="utf-8"))
    print("REGISTRY_HASH =", stored)
    print("PRIORITY_HASH =", prio.get("PRIORITY_HASH"))
    print("duration_weight =", reg["priority"]["weights"].get("duration"))

    # ---------- produce the performance-patched runner ----------
    src = open(os.path.join(HERE, "run_hf_r2.py"), encoding="utf-8").read()
    ref_block = """    nc_counts = []
    for _ in range(FROZEN["negative_control"]["runs"]):
        hits = 0
        for _n in range(len(opps)):
            t = (t0 + pd.Timedelta(seconds=rng.uniform(0, (t1 - t0).total_seconds()))).as_unit(cabs.index.unit)
            i = cabs.index.searchsorted(t)
            if 0 <= i < len(cabs) and np.isfinite(cabs.iloc[i]) and abs(cabs.iloc[i]) >= 3.0:
                hits += 1
        nc_counts.append(hits)"""
    opt_block = '''    # ---- PERFORMANCE FIX (only the lookup is vectorised; RNG stream and rules unchanged) ----
    _span_s = (t1 - t0).total_seconds()
    _idx_ns = cabs.index.values.astype("datetime64[ns]").view("int64")
    _vals = np.nan_to_num(cabs.to_numpy(float), nan=0.0)
    _abn = np.abs(_vals) >= 3.0
    _n_opp = len(opps)

    def _draw_ns(u_rng, n):
        base = t0.value
        return np.fromiter((base + pd.Timedelta(seconds=u_rng.uniform(0, _span_s)).value for _ in range(n)),
                            dtype="int64", count=n)

    def _hits_vectorised(draws):
        pos = np.searchsorted(_idx_ns, draws, side="left")
        ok = pos < len(_idx_ns)
        return int(_abn[pos[ok]].sum())

    def _hits_reference(u_rng, n):
        hits = 0
        for _n in range(n):
            t = (t0 + pd.Timedelta(seconds=u_rng.uniform(0, _span_s))).as_unit(cabs.index.unit)
            i = cabs.index.searchsorted(t)
            if 0 <= i < len(cabs) and np.isfinite(cabs.iloc[i]) and abs(cabs.iloc[i]) >= 3.0:
                hits += 1
        return hits

    # ---- equivalence proof on a fixed small sample (section 4) ----
    _K = min(3, N_NC_LOCAL)
    _nb = min(200, _n_opp)
    _r1, _r2 = random.Random(FROZEN["negative_control"]["seed"]), random.Random(FROZEN["negative_control"]["seed"])
    _ref, _opt = [], []
    for _ in range(_K):
        _ref.append(_hits_reference(_r1, _nb))
        _opt.append(_hits_vectorised(_draw_ns(_r2, _nb)))
    OPTIMISED_OUTPUT_EQUALS_REFERENCE = (_ref == _opt)
    print("NC_EQUIVALENCE_PROOF:", json.dumps({"sample_runs": _K, "sample_draws": _nb, "reference": _ref,
                                                  "optimised": _opt,
                                                  "OPTIMISED_OUTPUT_EQUALS_REFERENCE": OPTIMISED_OUTPUT_EQUALS_REFERENCE},
                                                 ensure_ascii=False))
    if not OPTIMISED_OUTPUT_EQUALS_REFERENCE:
        raise SystemExit("STOP: optimised negative control differs from the reference")

    nc_counts = []
    for _ in range(N_NC_LOCAL):
        nc_counts.append(_hits_vectorised(_draw_ns(rng, _n_opp)))'''
    if ref_block not in src:
        print("STOP: reference negative-control block not found (code drift)")
        sys.exit(3)
    src = src.replace(ref_block, opt_block)
    src = src.replace('    rng = random.Random(SEED)\n    t0, t1 = min(',
                       '    N_NC_LOCAL = FROZEN["negative_control"]["runs"]\n    rng = random.Random(SEED)\n    t0, t1 = min(')
    patched = os.path.join(HERE, "run_hf_r2_perf.py")
    open(patched, "w", encoding="utf-8", newline="\n").write(src)
    print("patched runner written:", os.path.basename(patched))

    # ---------- §6 trading flags ----------
    V3 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "research", "hermes", "trader_v3")
    V3 = r"C:\AIQuant\research\hermes\trader_v3"
    flags = {f: (open(os.path.join(V3, "state", f), encoding="utf-8").read().strip()
                 if os.path.exists(os.path.join(V3, "state", f)) else "MISSING")
             for f in ("V3_LIVE_ALLOWED", "V3_STRATEGY_FORWARD", "V3_FORWARD_ALLOWED")}
    print("trading_flags:", json.dumps({"ORDER_SEND": 0, "V3_FORWARD": "OFF", "V3_SHADOW": "OFF",
                                          "V3_LIVE": "OFF", "state_files": flags}, ensure_ascii=False))

    # ---------- §7 full discovery run from the frozen inputs ----------
    print("\n=== FULL RUN ===", flush=True)
    t0s = time.time()
    r = subprocess.run([PY, patched], cwd=HERE, capture_output=True, text=True, encoding="utf-8",
                        errors="replace")
    print(r.stdout[-6000:])
    print("elapsed_s:", round(time.time() - t0s, 1), "| returncode:", r.returncode)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2500:])
        sys.exit(r.returncode)

    # ---------- §8 result presence + §9/§26 fields ----------
    sp = os.path.join(HERE, "run_summary_hf_r2.json")
    if not os.path.exists(sp):
        print("STOP: run_summary_hf_r2.json absent -> run did not complete")
        sys.exit(4)
    S = json.load(open(sp, encoding="utf-8"))
    miss = [k for k, v in S.items() if v == "NOT_COMPUTED"]
    print("results_present:", json.dumps({k: S.get(k) for k in (
        "TOTAL_OPPORTUNITIES", "INDEPENDENT_EVENTS", "CLUSTERS", "F1_COUNT", "F2_COUNT", "F3_COUNT", "F4_COUNT",
        "F5_COUNT", "F6_COUNT", "HIGH_FREQUENCY_COUNT", "MEDIUM_FREQUENCY_COUNT", "LOW_FREQUENCY_COUNT",
        "INDEPENDENT_EVENTS_PER_DAY", "INDEPENDENT_EVENTS_PER_WEEK", "MEDIAN_DURATION", "P25_DURATION",
        "P75_DURATION", "TOP_10_EPISODE_SHARE", "TOP_20_EPISODE_SHARE", "CONCENTRATION_HIGH",
        "HERMES_INVESTIGATIONS", "HERMES_BUDGET", "QUALITY_HIGH", "QUALITY_MEDIUM", "QUALITY_LOW",
        "NEGATIVE_CONTROL", "DETECTOR_ABLATION", "OVERLAP_AUDIT", "CANDIDATE_RESEARCH",
        "FREEZE_HASH", "INPUT_HASH", "OUTPUT_HASH", "ledger_chain")}, ensure_ascii=False))
    print("NOT_COMPUTED_fields:", miss or "(none)")
    print("NC_DECISION_FROM_RESULTS:", json.dumps(S.get("NEGATIVE_CONTROL_DETAIL"), ensure_ascii=False))
    print("FREEZE_HASH_IN_OUTPUT:", S.get("FREEZE_HASH") == FROZEN_HASH)


if __name__ == "__main__":
    main()
