"""Phase 2 shared paths, IO helpers, and read-only production accessors.

Everything here is READ-ONLY with respect to V2 production. Writes are confined
to PHASE2_LIVE_EVIDENCE/ (the Phase-2 directory) as required by the brief.
"""
from __future__ import annotations
import json
import os
import sys
import glob
from datetime import datetime, timezone

# --- repository layout -----------------------------------------------------
# P2 is the Phase-2 output root. Imports (GA) always resolve from the REAL
# runner location, but outputs can be redirected for an isolated verification
# run via V2_PHASE2_ROOT (used by OPTIMIZATION_REPORT's open-branch self-test;
# unset in normal operation -> real PHASE2 dir, unchanged behaviour).
_RUNNER_DIR = os.path.dirname(os.path.abspath(__file__))
_REAL_P2 = os.path.dirname(_RUNNER_DIR)
P2 = os.environ.get("V2_PHASE2_ROOT") or _REAL_P2
GA = os.path.dirname(_REAL_P2)                # V2_GRAND_ARCHITECTURE (imports stay real)
SHADOW = os.path.join(P2, "shadow")

if GA not in sys.path:
    sys.path.insert(0, GA)

from common import hashing  # noqa: E402  (Phase 1 reusable hashing)

# --- production (read-only) locations -------------------------------------
TRADER_V2 = r"C:\AIQuant\research\hermes\trader_v2"
LIVE_TICKS = r"C:\AIQuant\data\live_fxtm"
HEALTH_JSON = os.path.join(TRADER_V2, "state", "v2_run_health.json")
ACTIVE_JSON = os.path.join(TRADER_V2, "state", "runs", "ACTIVE.json")
RUNS_DIR = os.path.join(TRADER_V2, "research", "runs")
V1_TRADE_DB = r"C:\AIQuant\research\hermes\audit\hermes_alpha_drift_pit\V1_HERMES_TRADE_DATABASE.jsonl"

# --- Phase-2 deliverables --------------------------------------------------
STREAM = os.path.join(P2, "LIVE_EVIDENCE_STREAM.jsonl")
OUTCOMES = os.path.join(P2, "OUTCOMES.jsonl")
SCORECARD = os.path.join(P2, "STRATEGY_SCORECARD.jsonl")
LIFECYCLE = os.path.join(P2, "STRATEGY_LIFECYCLE.jsonl")
REGIME_MATRIX = os.path.join(P2, "REGIME_STRATEGY_MATRIX.json")
V1_REFERENCE = os.path.join(P2, "V1_REFERENCE_COMPARISON.jsonl")
PROD_VS_SHADOW = os.path.join(P2, "PRODUCTION_VS_SHADOW.md")
REVIEW48 = os.path.join(P2, "48H_REVIEW.jsonl")
DEGRADATION = os.path.join(P2, "DEGRADATION_MONITOR.md")
EVOLUTION_PROPOSALS = os.path.join(P2, "EVOLUTION_PROPOSALS.jsonl")
CANDIDATE_QUEUE = os.path.join(P2, "CANDIDATE_QUEUE.jsonl")
FALSE_ALPHA = os.path.join(P2, "FALSE_ALPHA_REPORT.md")
OOS_PROGRESS = os.path.join(P2, "OOS_PROGRESS.md")
STAT_PROGRESS = os.path.join(P2, "STATISTICAL_PROGRESS.md")
GPU_REPORT = os.path.join(P2, "GPU_USAGE_REPORT.md")
DATA_MANIFEST = os.path.join(P2, "DATA_MANIFEST.json")
REPLAY_REPORT = os.path.join(P2, "REPLAY_REPORT.md")
SHA256SUMS = os.path.join(P2, "SHA256SUMS.txt")
FINAL_REPORT = os.path.join(P2, "FINAL_REPORT.md")
LIVE_ARCH = os.path.join(P2, "LIVE_SHADOW_ARCHITECTURE.md")
LIFETIME_DATASET = os.path.join(P2, "V2_STRATEGY_LIFETIME_DATASET.jsonl")
SHADOW_REGISTRY = os.path.join(SHADOW, "SHADOW_REGISTRY.jsonl")
RUN_LOG = os.path.join(SHADOW, "run_log.jsonl")
STATE = os.path.join(SHADOW, "state.json")

SEED = 20261003

SCHED_TASK = r"\OpenClaw\hermes-v2-shadow-evidence"

# cycle horizons in MINUTES (spec section 3)
HORIZONS_MIN = [15, 30, 60, 240]
# calibration horizon in 15m bars (~60 min) used for PIT-safe confidence
CALIB_BARS = 4
CALIB_WINDOW = 60


def ensure_dirs() -> None:
    os.makedirs(SHADOW, exist_ok=True)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- jsonl helpers (append-only, idempotent by key) ------------------------
def jl_append(path: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return len(rows)


def jl_read(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def jl_keys(path: str, key_fn) -> set:
    return {key_fn(r) for r in jl_read(path)}


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _canon_lines(text: str, ignore_prefixes) -> str:
    return "\n".join(l for l in text.splitlines()
                     if not any(l.startswith(p) for p in ignore_prefixes))


def write_text_if_changed(path: str, text: str, ignore_prefixes=()) -> bool:
    """Write text only when its content actually changed (C3). ``ignore_prefixes``
    lets a report keep a volatile line (e.g. a generated timestamp) without
    counting as a change. Returns True when the file was (re)written."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                old = f.read()
        except Exception:
            old = None
        if old == text:
            return False
        if old is not None and ignore_prefixes and \
                _canon_lines(old, ignore_prefixes) == _canon_lines(text, ignore_prefixes):
            return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def _strip_keys(obj, keys: set):
    if isinstance(obj, dict):
        return {k: _strip_keys(v, keys) for k, v in obj.items() if k not in keys}
    if isinstance(obj, list):
        return [_strip_keys(v, keys) for v in obj]
    return obj


def write_json_if_changed(path: str, obj, ignore_keys=()) -> bool:
    """Write JSON only when the object changed, ignoring volatile keys
    (e.g. 'generated_utc'). Returns True when the file was (re)written."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    keys = set(ignore_keys)
    body = json.dumps(_strip_keys(obj, keys), ensure_ascii=False, sort_keys=True)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            if json.dumps(_strip_keys(old, keys), ensure_ascii=False, sort_keys=True) == body:
                return False
        except Exception:
            pass
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
    return True


def log_event(kind: str, payload: dict) -> None:
    jl_append(RUN_LOG, [{"at": now_utc(), "kind": kind, **payload}])


# --- read-only market signal ----------------------------------------------
def is_market_open(health: dict) -> bool:
    """Read-only branch signal (C1/C2). ``market_open`` is authoritative; the
    ``cycle_result`` string is a documented fallback. Unknown -> CLOSED (a
    research component fails cheap/closed and never invents activity)."""
    mo = health.get("market_open")
    if isinstance(mo, bool):
        return mo
    cr = str(health.get("cycle_result") or "").upper()
    if "CLOSED" in cr:
        return False
    if "OPEN" in cr:
        return True
    return False


# --- read-only production accessors ---------------------------------------
def read_health() -> dict:
    try:
        with open(HEALTH_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # pragma: no cover
        return {"_error": str(e)}


def read_active_run() -> dict:
    try:
        with open(ACTIVE_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # pragma: no cover
        return {"_error": str(e)}


def run_dir(run_id: str) -> str:
    return os.path.join(RUNS_DIR, run_id)


def production_decisions(run_id: str) -> dict:
    """Map 'YYYY-MM-DDTHH:MMZ' decision_window -> production decision summary.

    Read-only. Combines ledger DECISION events (all cycles, WAIT/TRADE) with the
    frozen decision files (TRADE detail: side / sl / tp).
    """
    out: dict[str, dict] = {}
    led = os.path.join(run_dir(run_id), "ledger.jsonl")
    if os.path.exists(led):
        with open(led, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("event_type") != "DECISION":
                    continue
                w = r.get("decision_window")
                if not w:
                    continue
                out[w] = {
                    "decision_window": w,
                    "decision_id": r.get("decision_id"),
                    "status": r.get("status"),
                    "side": None,
                    "entry": None,
                    "stop_loss": None,
                    "take_profit": None,
                    "confidence": r.get("confidence"),
                    "context_hash": r.get("context_hash"),
                }
    dd = os.path.join(run_dir(run_id), "decisions")
    for p in glob.glob(os.path.join(dd, "*.frozen.json")):
        try:
            with open(p, encoding="utf-8") as f:
                t = json.load(f)
        except Exception:
            continue
        if t.get("decision") != "TRADE":
            continue
        did = t.get("decision_id")
        # attach TRADE detail to the matching ledger window by decision_id
        for w, rec in out.items():
            if rec.get("decision_id") == did:
                rec["side"] = t.get("side")
                rec["entry"] = t.get("entry_reference")
                rec["stop_loss"] = t.get("stop_loss")
                rec["take_profit"] = t.get("take_profit")
    return out


def compute_hashes(paths: list[str]) -> dict:
    return {os.path.basename(p): hashing.sha256_file(p) for p in paths if os.path.exists(p)}
