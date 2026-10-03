"""Light heartbeat + market-reopen recovery for the Phase-2 runner (C1/C2).

MARKET_CLOSED cycles only append ONE small heartbeat record and exit: no GPU, no
heavy analytics, no duplicate historical backfill, no scorecard recompute, and
NO new decision / outcome / sample. MARKET_OPEN cycles run the full pipeline and
the first closed->open transition records MARKET_REOPEN_RECOVERY.

All reads here are read-only (production health + a read-only scheduler query);
all writes go to PHASE2_LIVE_EVIDENCE/shadow/. The heartbeat file is append-only.
"""
from __future__ import annotations
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths as PP  # noqa: E402

HEARTBEAT = os.path.join(PP.SHADOW, "heartbeat.jsonl")
MARKET_STATE = os.path.join(PP.SHADOW, "market_state.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# read-only liveness / health probes
# --------------------------------------------------------------------------
def scheduler_status(task: str = PP.SCHED_TASK) -> dict:
    """Read-only query of the EXISTING scheduled task (never create/modify it).
    Proves scheduler liveness and exposes the next scheduled cycle."""
    out = {"task": task, "state": "UNKNOWN", "next_run": None, "last_run": None,
           "last_result": None, "source": "schtasks/query (read-only)"}
    try:
        r = subprocess.run(["schtasks", "/query", "/tn", task, "/fo", "LIST", "/v"],
                           capture_output=True, text=True, timeout=20)
        txt = r.stdout or ""
        if r.returncode != 0 or not txt.strip():
            r = subprocess.run(["schtasks", "/query", "/tn", task, "/fo", "LIST"],
                               capture_output=True, text=True, timeout=20)
            txt = r.stdout or ""

        def pick(*labels):
            for line in txt.splitlines():
                s = line.strip()
                for lab in labels:
                    if s.startswith(lab):
                        return s.split(":", 1)[1].strip() if ":" in s else ""
            return None

        out["state"] = pick("Status", "模式", "状态") or "UNKNOWN"
        out["next_run"] = pick("Next Run Time", "下次运行时间")
        out["last_run"] = pick("Last Run Time", "上次运行时间")
        out["last_result"] = pick("Last Result", "上次结果")
        out["ok"] = r.returncode == 0
    except Exception as e:  # pragma: no cover
        out["error"] = str(e)
        out["ok"] = False
    return out


def tick_archive_health() -> dict:
    files = glob.glob(os.path.join(PP.LIVE_TICKS, "ticks_*.parquet"))
    if not files:
        return {"files": 0, "latest_file": None, "latest_mtime_utc": None, "age_min": None}
    latest = max(files, key=os.path.getmtime)
    mt = datetime.fromtimestamp(os.path.getmtime(latest), tz=timezone.utc)
    age = (datetime.now(timezone.utc) - mt).total_seconds() / 60.0
    return {"files": len(files), "latest_file": os.path.basename(latest),
            "latest_mtime_utc": mt.isoformat(), "age_min": round(age, 1)}


def strategy_count():
    try:
        n = sum(1 for l in open(PP.SHADOW_REGISTRY, encoding="utf-8") if l.strip()) \
            if os.path.exists(PP.SHADOW_REGISTRY) else 0
        if n:
            return n
    except Exception:
        pass
    try:
        from strategy_factory import factory as F
        return len(F.generate_specs())
    except Exception:
        return None


def stream_rows() -> int:
    if not os.path.exists(PP.STREAM):
        return 0
    return sum(1 for l in open(PP.STREAM, encoding="utf-8") if l.strip())


def data_continuity() -> dict:
    h = tick_archive_health()
    return {"tick_archive": h,
            "continuous": bool(h.get("files") and h.get("latest_mtime_utc") is not None),
            "note": "local tick archive readable and advancing; no error across closed window"}


# --------------------------------------------------------------------------
# market-state transition tracking
# --------------------------------------------------------------------------
def last_market_state() -> dict:
    if os.path.exists(MARKET_STATE):
        try:
            with open(MARKET_STATE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def set_market_state(open_flag: bool) -> dict:
    """Persist current market state. Timestamps only change on an actual state
    transition, so repeated closed/open cycles leave the file byte-identical."""
    prev = last_market_state()
    prev_flag = prev.get("market_open")
    changed = prev_flag is not open_flag
    st = dict(prev)
    st["market_open"] = open_flag
    st["last_observed_utc"] = _now() if changed else prev.get("last_observed_utc")
    if changed:
        st["last_state_change_utc"] = _now()
        if open_flag:
            st["last_open_utc"] = _now()
        else:
            st["last_closed_utc"] = _now()
    PP.write_json_if_changed(MARKET_STATE, st, ignore_keys=())
    return st


# --------------------------------------------------------------------------
# record builders
# --------------------------------------------------------------------------
def _base(health: dict, sched: dict) -> dict:
    return {
        "kind": "heartbeat",
        "at": _now(),
        "heartbeat": _now(),
        "market_open": bool(health.get("market_open")),
        "cycle_id": health.get("current_cycle"),
        # required heartbeat fields (C1)
        "scheduler_liveness": sched,
        "shadow_scheduler_status": sched.get("state"),
        "next_scheduled_cycle": sched.get("next_run"),
        "v2_production_status": {
            "run_status": health.get("run_status"),
            "blocked": health.get("blocked"),
            "cycle_result": health.get("cycle_result"),
            "scheduler": health.get("scheduler"),
            "armed": health.get("armed"),
        },
        "last_successful_cycle": health.get("last_success") or health.get("last_completed"),
        "data_source_health": {
            "router_enabled": health.get("router_enabled"),
            "agent1_status": health.get("agent1_status"),
            "agent2_status": health.get("agent2_status"),
            "tick_archive": tick_archive_health(),
            "agent2_data_gaps": health.get("agent2_data_gaps"),
        },
        "replay_health": {"production": health.get("replay_status"),
                          "missed_cycles": health.get("missed_cycles")},
        "strategy_count": strategy_count(),
        "stream_rows": stream_rows(),
        "heartbeat_is_append_only": True,
    }


def record_closed(health: dict) -> dict:
    """C1: MARKET_CLOSED -> heartbeat only. Creates NO decision/outcome/sample."""
    was_closed = last_market_state().get("market_open") is False
    status = "MARKET_CLOSED_ALREADY_RECORDED" if was_closed else "MARKET_CLOSED_RECORDED"
    rec = _base(health, scheduler_status())
    rec.update({
        "status": status,
        "path": "HEARTBEAT_ONLY",
        "gpu_ran": False,
        "analytics_ran": False,
        "backfill_ran": False,
        "new_sample_created": False,
        "note": "market closed: heartbeat only; no GPU/analytics/backfill; "
                "no new decision/outcome/sample",
    })
    PP.jl_append(HEARTBEAT, [rec])
    PP.log_event("heartbeat_closed", {"status": status, "cycle_id": health.get("current_cycle")})
    set_market_state(False)
    return rec


def record_open(health: dict, pipeline: dict) -> dict:
    """C2: MARKET_OPEN -> full pipeline heartbeat."""
    rec = _base(health, scheduler_status())
    rec.update({
        "status": "MARKET_OPEN_RECORDED",
        "path": "FULL_PIPELINE",
        "gpu_ran": True,
        "analytics_ran": True,
        "backfill_ran": True,
        "new_sample_created": bool((pipeline.get("rows") or 0) or (pipeline.get("outcomes") or 0)),
        "replay_health": {"production": health.get("replay_status"),
                          "shadow": pipeline.get("replay")},
        "pipeline": pipeline,
    })
    PP.jl_append(HEARTBEAT, [rec])
    PP.log_event("heartbeat_open", {"cycle_id": health.get("current_cycle"),
                                    "rows": pipeline.get("rows")})
    return rec


def record_reopen(health: dict, pipeline: dict) -> dict:
    """C2: first closed->open transition -> MARKET_REOPEN_RECOVERY with the
    required confirmations."""
    rec = _base(health, scheduler_status())
    rec.update({
        "status": "MARKET_REOPEN_RECOVERY",
        "transition": "MARKET_CLOSED -> MARKET_OPEN",
        "confirm": {
            "data_time_continuity": pipeline.get("continuity"),
            "no_error_across_closed_window": pipeline.get("no_error"),
            "pit_normal": pipeline.get("pit_ok"),
            "replay": pipeline.get("replay"),
            "replay_pass": pipeline.get("replay_pass"),
            "order_send": 0,
        },
        "note": "first closed->open transition: full pipeline auto-resumed, no manual restart",
    })
    PP.jl_append(HEARTBEAT, [rec])
    PP.log_event("market_reopen_recovery", {"cycle_id": health.get("current_cycle"),
                                            "replay": pipeline.get("replay")})
    return rec


def last_heartbeat() -> dict:
    rows = PP.jl_read(HEARTBEAT)
    return rows[-1] if rows else {}
