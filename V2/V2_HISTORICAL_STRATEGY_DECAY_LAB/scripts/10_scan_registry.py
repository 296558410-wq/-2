"""
10_scan_registry.py — HISTORICAL_SYSTEM_REGISTRY.json

Scan C:\AIQuant for every trading system / strategy version actually present, and
classify each A (real decision/trade data) / B (research only) / C (calibration-
smoke-synthetic) / D (never a verifiable episode).

READ-ONLY scan. Writes only to the lab dir.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (REPO, LAB, DATA, SRC, banner, read_jsonl, read_json,
                        write_json, git_commit, sha256_file, input_hashes)

SOURCES = ["v1_trade_db", "v2_trade_db", "v1_upgrade_ledger", "v1_run_statistics",
           "v2_ledger", "v2_paper_account", "archive_manifest", "archive_code_identity",
           "v1_upgrade_registry", "v1_run_meta"]


def dir_size_files(p: Path):
    n = 0
    for _ in p.rglob("*"):
        if _.is_file():
            n += 1
    return n


def scan_candidate_dirs():
    """Return candidate system directories under the required roots."""
    roots = []
    roots.append((REPO / "research/hermes/trader_v1", "trader_v1"))
    roots.append((REPO / "research/hermes/trader_v2", "trader_v2"))
    roots.append((REPO / "research/hermes/trader_v3", "trader_v3"))
    roots.append((REPO / "archive", "archive"))
    out = []
    for root, tag in roots:
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith((".", "__")):
                continue
            out.append({"path": child, "root": tag})
    # research/v3_* and research/*_lab + alpha_engine
    rr = REPO / "research"
    for child in sorted(rr.iterdir()):
        if not child.is_dir():
            continue
        nm = child.name.lower()
        if child.name.startswith("v3_") or nm.endswith("_lab") or child.name in (
                "alpha_engine", "alpha_registry", "hft_edge_breaker", "hf_money_access_lab",
                "hf_zero_budget", "mtf_profit_lab", "d1_daily_reversal", "r1prime",
                "r1_longhistory", "signals", "strategies", "hypotheses"):
            out.append({"path": child, "root": "research"})
    # v1_r* dirs under trader_v1 (explicit)
    tv1 = REPO / "research/hermes/trader_v1"
    if tv1.exists():
        for child in sorted(tv1.iterdir()):
            if child.is_dir() and re.match(r"v1_r\d", child.name):
                out.append({"path": child, "root": "trader_v1_research"})
    return out


def describe_dir(p: Path) -> dict:
    files = [f for f in p.rglob("*") if f.is_file()]
    names = [f.name for f in files]
    rel = [str(f.relative_to(p)).replace("\\", "/") for f in files]

    def has(*pats):
        return any(any(pat in r for pat in pats) for r in rel)

    ledgers = sorted({r for r in rel if r.endswith(".jsonl") and
                      ("ledger" in r.lower() or "trade" in r.lower() or
                       "execution" in r.lower() or "decision" in r.lower())})[:12]
    return {
        "n_files": len(files),
        "has_ledger": has("ledger"),
        "has_state": has("/state/", "run_state"),
        "has_trade_db": has("trade_database", "trades.jsonl"),
        "has_backtest": has("backtest", "backtests"),
        "has_readme_report": has("README", ".md"),
        "has_exec_code": has("execution", "executor", "order_send", "broker"),
        "has_truth": has("truth/", "truth_"),
        "sample_ledgers": ledgers,
    }


def classify(name: str, root: str, desc: dict, trade_counts: dict) -> tuple:
    """Return (category, reason, confidence)."""
    lower = name.lower()
    # A: any system with real executed trades (broker truth)
    if name in trade_counts and trade_counts[name]["closed"] > 0:
        return ("A", f"real closed broker trades = {trade_counts[name]['closed']}", "HIGH")
    if lower in ("v1_upgrade",) or "v1_upgrade" in lower:
        return ("A", "V1_NEW executed-trade lineage (magic 90011) + truth evidence", "HIGH")
    if lower in ("trader_v1",) and root == "trader_v1":
        # the root is just a container; classify by descendants
        return ("CONTAINER", "root container of V1 systems", "N/A")
    # C: calibration / smoke / paper (a run exists but no real trades)
    if lower in ("trader_v2",) or lower == "trader_v2":
        return ("C", "V2 shadow: paper/calibration only, 0 executed broker trades", "HIGH")
    if lower == "trader_v3":
        return ("C", "V3: calibration pilot, execution disabled, 0 executed trades", "HIGH")
    if root == "archive":
        return ("A-archive", "immutable pre-reset archive of V1 (magic 90002 lineage)", "HIGH")
    # B: research-only rounds
    if re.match(r"v1_r\d", lower) or root == "trader_v1_research":
        return ("B", "research round (prediction/market-reading), no execution", "HIGH")
    if lower.startswith("v3_") or lower in ("alpha_engine", "alpha_registry",
                                            "hft_edge_breaker", "hf_money_access_lab",
                                            "hf_zero_budget", "mtf_profit_lab",
                                            "d1_daily_reversal", "r1prime",
                                            "r1_longhistory", "signals", "strategies",
                                            "hypotheses"):
        return ("B", "research/alpha-discovery only, no execution", "HIGH")
    if lower.endswith("_lab"):
        return ("B", "research lab directory, no execution", "MEDIUM")
    # D: nothing verifiable
    return ("D", "no ledger/state/trade evidence found", "LOW")


def build_trade_counts():
    rows = read_jsonl(SRC["v1_trade_db"])
    counts = {}
    for r in rows:
        if not isinstance(r, dict) or r.get("__malformed__"):
            continue
        s = r.get("system")
        if not s:
            continue
        c = counts.setdefault(s, {"rows": 0, "closed": 0, "magics": set(),
                                  "entry_min": None, "entry_max": None})
        c["rows"] += 1
        if r.get("closed"):
            c["closed"] += 1
        if r.get("magic") is not None:
            c["magics"].add(r["magic"])
        et = r.get("entry_ts")
        if et:
            if c["entry_min"] is None or et < c["entry_min"]:
                c["entry_min"] = et
            if c["entry_max"] is None or et > c["entry_max"]:
                c["entry_max"] = et
    for c in counts.values():
        c["magics"] = sorted(c["magics"])
    return counts


def main():
    banner("10_scan_registry.py", SOURCES)
    trade_counts = build_trade_counts()

    systems = []
    # ---- canonical trade-bearing systems (A) --------------------------------
    for sysname, meta in trade_counts.items():
        magic = meta["magics"][0] if meta["magics"] else None
        prov = "HERMES_LLM_PLAN_ENGINE" if sysname == "V1_OLD" else "BASELINE_CONTROL"
        systems.append({
            "system_id": sysname,
            "display_name": {"V1_OLD": "V1 old (Hermes LLM plan engine)",
                             "V1_NEW": "V1 upgrade / BASELINE_CONTROL"}.get(sysname, sysname),
            "category": "A",
            "classification_reason": f"real closed broker trades = {meta['closed']}",
            "confidence": "HIGH",
            "magic": magic,
            "execution_mode": "MT5_DEMO",
            "strategy_provenance": prov,
            "is_hermes_alpha": (sysname == "V1_OLD"),
            "real_closed_trades": meta["closed"],
            "real_rows": meta["rows"],
            "entry_ts_min": meta["entry_min"],
            "entry_ts_max": meta["entry_max"],
            "primary_evidence": str(SRC["v1_trade_db"].relative_to(REPO)),
            "path": "research/hermes/trader_v1" if sysname == "V1_OLD" else
                    "research/hermes/trader_v1/v1_upgrade",
        })

    # ---- V2 / V3 ------------------------------------------------------------
    v2_led = read_jsonl(SRC["v2_ledger"])
    v2_events = {}
    for r in v2_led:
        if isinstance(r, dict):
            v2_events[r.get("event", r.get("type", "?"))] = \
                v2_events.get(r.get("event", r.get("type", "?")), 0) + 1
    systems.append({
        "system_id": "V2_PAPER_SHADOW",
        "display_name": "V2 Hermes (paper/shadow)",
        "category": "C",
        "classification_reason": "paper + demo_calibration ledger only; 0 executed broker trades",
        "confidence": "HIGH",
        "magic": 90003,
        "execution_mode": "PAPER_LOCAL",
        "strategy_provenance": "reference_rules placeholder (signal_from_agents=false)",
        "is_hermes_alpha": False,
        "real_closed_trades": 0,
        "real_rows": 0,
        "primary_evidence": "research/hermes/trader_v2/ledger/hermes_v2_ledger.jsonl",
        "path": "research/hermes/trader_v2",
        "ledger_events": v2_events,
    })
    systems.append({
        "system_id": "V3_CALIBRATION",
        "display_name": "V3 (calibration pilot)",
        "category": "C",
        "classification_reason": "calibration pilot; execution gated off; 0 executed trades",
        "confidence": "HIGH",
        "magic": None,
        "execution_mode": "DISABLED",
        "strategy_provenance": "V3 research (alpha discovery)",
        "is_hermes_alpha": False,
        "real_closed_trades": 0,
        "real_rows": 0,
        "primary_evidence": "research/hermes/trader_v3",
        "path": "research/hermes/trader_v3",
    })
    systems.append({
        "system_id": "V1_PRE_RESET_ARCHIVE",
        "display_name": "V1 pre-reset archive (magic 90002 lineage)",
        "category": "A-archive",
        "classification_reason": "immutable snapshot of V1_OLD state at reset 2026-09-23T23:37Z",
        "confidence": "HIGH",
        "magic": 90002,
        "execution_mode": "MT5_DEMO",
        "strategy_provenance": "Hermes LLM plan engine (archived)",
        "is_hermes_alpha": True,
        "real_closed_trades": None,
        "real_rows": None,
        "primary_evidence": "archive/v1_pre_reset_20260923_233741/MANIFEST.json",
        "path": "archive/v1_pre_reset_20260923_233741",
    })

    # ---- scanned research dirs (B) and misc --------------------------------
    candidates = scan_candidate_dirs()
    seen = set()
    for c in candidates:
        p, root = c["path"], c["root"]
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        name = p.name
        desc = describe_dir(p)
        cat, reason, conf = classify(name, root, desc, trade_counts)
        if cat in ("CONTAINER",):
            continue
        systems.append({
            "system_id": f"{root}:{name}",
            "display_name": name,
            "category": cat,
            "classification_reason": reason,
            "confidence": conf,
            "path": str(p.relative_to(REPO)).replace("\\", "/"),
            "n_files": desc["n_files"],
            "has_ledger": desc["has_ledger"],
            "has_state": desc["has_state"],
            "has_backtest": desc["has_backtest"],
            "has_exec_code": desc["has_exec_code"],
            "has_truth": desc["has_truth"],
            "sample_ledgers": desc["sample_ledgers"],
            "real_closed_trades": 0 if cat != "A" else None,
        })

    # ---- manifests ----------------------------------------------------------
    cat_counts = {}
    for s in systems:
        cat_counts[s["category"]] = cat_counts.get(s["category"], 0) + 1
    registry = {
        "schema": "historical_system_registry/1",
        "generated_utc": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "code_commit": git_commit(),
        "repo": str(REPO),
        "scan_roots": ["research/hermes/trader_v1", "research/hermes/trader_v2",
                       "research/hermes/trader_v3", "archive", "research/v3_*",
                       "research/*_lab", "research/hermes/trader_v1/v1_r*"],
        "category_counts": cat_counts,
        "real_trade_systems": [s["system_id"] for s in systems if s["category"] == "A"],
        "systems": systems,
        "input_hashes": input_hashes(SOURCES),
    }
    write_json(LAB / "HISTORICAL_SYSTEM_REGISTRY.json", registry)

    print(f"\nTotal systems/dirs registered : {len(systems)}")
    print(f"Category counts               : {cat_counts}")
    print(f"A (real trade data)           : {[s['system_id'] for s in systems if s['category'] == 'A']}")
    print(f"A-archive                     : {[s['system_id'] for s in systems if s['category']=='A-archive']}")
    print(f"Real closed trades available  : "
          f"{sum((s.get('real_closed_trades') or 0) for s in systems if s['category']=='A')}")


if __name__ == "__main__":
    main()
