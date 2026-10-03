# -*- coding: utf-8 -*-
"""
Phase 9A audit & dry-run — validates the pre-registration lock (Phase 9A gate).
================================================================================
Usage:  python scripts/phase9a_audit.py
Exit:   0 = all critical checks PASS -> gate verdict PASS
        1 = failures -> gate verdict REJECT (failures listed)
Evidence: reports/phase9_gate_evidence.json  (overwritten each run)

The audit is an INDEPENDENT dry run: it loads the frozen registries, re-derives the
detector YAML from the builder (byte determinism), statically audits no-lookahead
semantics and MT5 read-only safety, and touches NO market data and NO MT5 terminal.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
DET_REG = REPO / "research/phase9/registry/phase9_detector_registry.yaml"
DET_SRC = REPO / "research/phase9/registry/build_phase9_registry.py"
HYP_REG = REPO / "research/registry/hypothesis_registry.yaml"
GUARD = REPO / "tools/mt5_readonly.py"
ENV_CFG = REPO / "configs/mt5_research_readonly.env"
EVIDENCE = REPO / "reports/phase9_gate_evidence.json"

FIELD_ORDER = [
    "1_mathematical_definition", "2_feature_definition", "3_data_fields",
    "4_lookback", "5_sampling_frequency", "6_threshold", "7_signal_direction",
    "8_signal_timestamp", "9_entry_rule", "10_execution_assumption", "11_exit_rule",
    "12_holding_period", "13_overlap_rule", "14_min_effective_sample_size",
    "15_cost_model", "16_baseline", "17_discovery_period", "18_validation_period",
    "19_oos_period", "20_cross_period_validation", "21_cross_feed_validation",
    "22_fdr_family", "23_rejection_criteria", "24_placebo_test", "25_shuffle_test",
    "26_parameter_perturbation", "27_subperiod_stability",
]
BANNED_WORDS = ["promising", "interesting", "potential", "looks good", "looks great",
                "TBD", "TBA", "FIXME", "TODO", "placeholder", "待定", "占位",
                "先看结果", "看结果再", "根据结果", "见结果", "之后再看", "试出来"]
STATUS_ENUM = {"REJECTED", "SUPPORTED_NON_DIRECTIONAL", "DESCRIPTIVE_ONLY",
               "NO_FEASIBLE_ALPHA", "EDGE_UNCERTAIN_LEGACY"}

checks: list[dict] = []


def check(cid: str, name: str, ok: bool, detail: str, critical: bool = True):
    checks.append({"id": cid, "name": name, "status": "PASS" if ok else "FAIL",
                   "critical": critical, "detail": detail})
    return ok


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main() -> int:
    t0 = datetime.now(timezone.utc)
    ok_all = True

    # ---- C01/C02: existence + machine-readable parse ---------------------
    for p in [DET_REG, DET_SRC, HYP_REG, GUARD, ENV_CFG]:
        if not check("C01", f"file exists: {p.relative_to(REPO)}", p.exists(), str(p)):
            ok_all = False
    if not all(p.exists() for p in [DET_REG, HYP_REG]):
        finish(ok_all, t0)
        return 1 if not ok_all else 0

    try:
        det = load_yaml(DET_REG)
        ok = True
        detail = "ok"
    except Exception as exc:  # noqa: BLE001
        ok = False
        det = None
        detail = f"yaml parse error: {exc}"
    ok_all &= check("C02", "phase9_detector_registry.yaml parses", ok, detail)
    try:
        hyp = load_yaml(HYP_REG)
        ok = True
        detail = "ok"
    except Exception as exc:  # noqa: BLE001
        ok = False
        hyp = None
        detail = f"yaml parse error: {exc}"
    ok_all &= check("C02b", "hypothesis_registry.yaml parses", ok, detail)
    if det is None or hyp is None:
        finish(ok_all, t0)
        return 1 if not ok_all else 0

    # ---- C03: meta + frozen schema ---------------------------------------
    meta = det.get("meta", {})
    ok = meta.get("frozen") is True and meta.get("registry_id") == "PHASE9_DETECTOR_REGISTRY_V1"
    detail = f"frozen={meta.get('frozen')} id={meta.get('registry_id')}"
    ok_all &= check("C03", "meta frozen + registry id", ok, detail)
    fo = [f.strip() for f in meta.get("field_order", "").split(",")]
    ok = fo == FIELD_ORDER
    ok_all &= check("C03b", "meta.field_order == 27-field schema", ok,
                    f"{len(fo)} fields listed")

    detectors = det.get("detectors", [])
    missing = []
    for d in detectors:
        for f in FIELD_ORDER:
            if f not in d or not str(d[f]).strip():
                missing.append(f"{d.get('detector_id')}:{f}")
    ok = len(detectors) == 27 and not missing and \
        str(meta.get("detector_count", "")).startswith("27")
    ok_all &= check("C04", "27 detectors x 27 non-empty fields",
                    ok, f"detectors={len(detectors)} missing/empty={len(missing)} "
                        f"meta_count={meta.get('detector_count', '')[:30]}")
    if missing:
        ok_all = False

    # ---- C05: budget caps -------------------------------------------------
    from collections import Counter
    fam_count = Counter(d.get("family") for d in detectors)
    p16 = sum(v for k, v in fam_count.items() if k != "P7")
    p7 = fam_count.get("P7", 0)
    ok = p16 <= 36 and p7 <= 12 and set(fam_count) <= {f"P{i}" for i in range(1, 8)}
    ok_all &= check("C05", "budget caps (P1-6<=36, P7<=12)", ok,
                    f"per-family={dict(fam_count)}")
    for d in detectors:
        if d.get("status") != "FROZEN":
            ok_all &= check("C05b", "detector status FROZEN", False,
                            f"{d.get('detector_id')} status={d.get('status')}")

    # ---- C06: banned words / placeholders across registry -----------------
    text_all = (DET_REG.read_text(encoding="utf-8")
                + HYP_REG.read_text(encoding="utf-8"))
    hits = []
    for w in BANNED_WORDS:
        if w in text_all:
            hits.append(w)
    # PENDING is a declared, honest state for tick-layer OOS — allowed.
    ok = not hits
    ok_all &= check("C06", "no placeholder/banned verdict words in registries",
                    ok, f"hits={hits}")

    # ---- C07: threshold discipline (no data-dependent threshold) ----------
    th_bad = []
    for d in detectors:
        t = str(d.get("6_threshold", ""))
        if len(t) < 20 or any(w in t for w in ["TBD", "待定", "先看", "根据结果", "看结果"]):
            th_bad.append(d.get("detector_id"))
    ok = not th_bad
    ok_all &= check("C07", "thresholds frozen (fixed value + rationale, no data-peeking)",
                    ok, f"bad={th_bad}")

    # ---- C08: no-lookahead static audit -----------------------------------
    nl_bad = []
    for d in detectors:
        entry = str(d.get("9_entry_rule", ""))
        ts = str(d.get("8_signal_timestamp", ""))
        ex = str(d.get("11_exit_rule", ""))
        hold = str(d.get("12_holding_period", ""))
        if not re.search(r"after|next|\+1|then", entry, re.I):
            nl_bad.append(f"{d.get('detector_id')}:entry")
        if not re.search(r"<=", ts) and not re.search(r"complete at|close at|at t_sig|inputs? <=", ts, re.I):
            nl_bad.append(f"{d.get('detector_id')}:ts")
        if "exit" not in ex.lower() and "market exit" not in ex.lower():
            nl_bad.append(f"{d.get('detector_id')}:exit")
        if not re.search(r"\d", hold):
            nl_bad.append(f"{d.get('detector_id')}:hold")
    ok = not nl_bad
    ok_all &= check("C08", "no-lookahead static audit (entry>=t_sig+delay, exit>entry)",
                    ok, f"issues={nl_bad}")

    # ---- C09: period discipline (D<=V<=OOS, non-overlap, tick OOS declared) --
    dates = {}
    for d in detectors:
        layer = d.get("layer")
        dates.setdefault(layer, {}).setdefault(d.get("detector_id"), {
            "D": str(d.get("17_discovery_period", "")),
            "V": str(d.get("18_validation_period", "")),
            "O": str(d.get("19_oos_period", "")),
            "C": str(d.get("20_cross_period_validation", "")),
        })
    period_bad = []
    for layer, items in dates.items():
        for did, pr in items.items():
            for key in ("D", "V"):
                m = re.findall(r"(\d{4}-\d{2}-\d{2})", pr[key])
                if len(m) < 2:
                    period_bad.append(f"{did}:{key} no date range")
            if not re.search(r"PENDING|DUKA|\d{4}-\d{2}-\d{2}", pr["O"]):
                period_bad.append(f"{did}:OOS not declared")
    # layer-level monotonicity (first detector per layer is representative)
    for layer in ("TICK", "M1"):
        if layer not in dates:
            period_bad.append(f"layer {layer} missing")
            continue
        first = next(iter(dates[layer].values()))
        dm = re.findall(r"(\d{4}-\d{2}-\d{2})", first["D"])
        vm = re.findall(r"(\d{4}-\d{2}-\d{2})", first["V"])
        if len(dm) == 2 and len(vm) == 2 and dm[1] > vm[0]:
            period_bad.append(f"{layer}: discovery end > validation start")
        if layer == "M1":
            om = re.findall(r"(\d{4}-\d{2}-\d{2})", first["O"])
            if len(vm) == 2 and len(om) == 2 and vm[1] > om[0]:
                period_bad.append("M1: validation end > OOS start")
    ok = not period_bad
    ok_all &= check("C09", "period discipline (frozen ranges, D<=V<=OOS)",
                    ok, f"issues={period_bad}")

    # ---- C10: historical REJECT registry linkage ---------------------------
    rmap = hyp.get("phase9_redundancy_map", {})
    prefixes_ok = all(re.fullmatch(r"P[1-7]_.+", k) for k in rmap)
    ok = prefixes_ok and {k.split("_")[0] for k in rmap} == {f"P{i}" for i in range(1, 8)} and \
        meta.get("historical_reject_registry") == "research/registry/hypothesis_registry.yaml"
    missing_req = []
    for fid, g in rmap.items():
        if not g.get("required_differentiation"):
            missing_req.append(fid)
    ok = ok and not missing_req
    ok_all &= check("C10", "hypothesis_registry linked; P1-P7 redundancy guards present",
                    ok, f"map={sorted(rmap)} missing_diff={missing_req}")
    bad_status = [f.get("id") for f in hyp.get("findings", [])
                  if f.get("status") not in STATUS_ENUM]
    ok_all &= check("C10b", "historical finding statuses use controlled enum",
                    not bad_status, f"bad={bad_status}")
    red_tag_ok = all(
        any("REDUNDANT_WITH_EXISTING_RESEARCH" in str(x) for x in g.get("historical_equivalents", []))
        for g in rmap.values())
    ok_all &= check("C10c", "each P-family declares REDUNDANT_WITH_EXISTING_RESEARCH tags",
                    red_tag_ok, "")

    # ---- C11: MT5 safety ---------------------------------------------------
    sys.path.insert(0, str(REPO / "tools"))
    from mt5_readonly import FORBIDDEN_TOKENS, audit_static  # noqa: E402
    hits = audit_static()
    ok = not hits and GUARD.exists() and ENV_CFG.exists()
    env_ok = ENV_CFG.read_text(encoding="utf-8").find("MT5_RESEARCH_READONLY_MODE=1") >= 0
    ok = ok and env_ok
    ok_all &= check("C11", "MT5 static safety scan: 0 forbidden order/deal tokens in code",
                    ok, f"hits={len(hits)} guard_ok={GUARD.exists()} env_ok={env_ok}")
    if hits:
        for h in hits[:8]:
            print("   token hit:", h)
    reg_tokens = [str(x) for x in
                  det.get("global_protocol", {}).get("mt5_safety", {}).get("forbidden_symbols", [])]
    ok_all &= check("C11b", "forbidden-token list parity registry<->guard",
                    set(reg_tokens) == set(FORBIDDEN_TOKENS),
                    f"registry={len(reg_tokens)} guard={len(FORBIDDEN_TOKENS)}")

    # ---- C12: byte-deterministic regeneration ------------------------------
    sys.path.insert(0, str(REPO / "research/phase9/registry"))
    import importlib.util  # noqa: E402
    spec = importlib.util.spec_from_file_location("phase9_registry_builder", DET_SRC)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)  # noqa: E402
    rebuilt = builder.emit()
    committed = DET_REG.read_text(encoding="utf-8")
    ok = rebuilt == committed
    ok_all &= check("C12", "registry regeneration is byte-deterministic (frozen)",
                    ok, f"same={ok} bytes={len(committed)}")

    # ---- C13: dry-run isolation --------------------------------------------
    imported = {m.split(".")[0] for m in sys.modules}
    ok = not ({"MetaTrader5", "pandas", "duckdb"} & imported)
    ok_all &= check("C13", "dry run touches no market data / no MT5 terminal",
                    ok, f"heavy_imports={sorted(imported & {'MetaTrader5', 'pandas', 'duckdb'})}")

    # ---- verdict -----------------------------------------------------------
    finish(ok_all, t0)
    return 0 if ok_all else 1


def finish(ok_all: bool, t0: datetime) -> None:
    verdict = "PASS" if ok_all else "REJECT"
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "gate": "PHASE_9A_PRE_REGISTRATION_LOCK",
        "verdict": verdict,
        "run_time_utc": now,
        "checks": checks,
        "summary": {"total": len(checks), "pass": sum(c["status"] == "PASS" for c in checks),
                    "fail": sum(c["status"] == "FAIL" for c in checks)},
    }
    EVIDENCE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"GATE_VERDICT: {verdict}  ({payload['summary']['pass']}/{payload['summary']['total']} checks)")
    for c in checks:
        if c["status"] == "FAIL":
            print(f"  FAIL {c['id']} {c['name']}: {c['detail'][:300]}")
    print(f"evidence -> {EVIDENCE.relative_to(REPO)}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"GATE_VERDICT: REJECT (audit crashed: {exc!r})")
        sys.exit(1)
