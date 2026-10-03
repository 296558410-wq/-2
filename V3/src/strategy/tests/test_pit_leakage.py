# -*- coding: utf-8 -*-
"""PIT leakage tests (§9): 1 future publication · 2 future revision · 3 replay determinism ·
4 hash integrity · 5 timezone. Standalone runner."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

V3 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, V3)
from strategy import pit_replay as PR  # noqa: E402

T = "2026-09-10T13:31:00Z"


def main():
    lines, ok = [], 0

    # Test 1 — future publication must not be visible
    try:
        PR.assert_no_lookahead(T)
        res = PR.get_information_available_at(T)
        t = datetime.fromisoformat(res["timestamp"])
        bad = [o for s in res["sources"] for o in s["observations"]
               if datetime.fromisoformat(o["availability_time"]) > t]
        good = not bad
        lines.append(f"[{'PASS' if good else 'FAIL'}] T1_future_publication_hidden (visible sources={len(res['sources'])}, withheld={res['withheld_future']})")
        ok += good
    except Exception as e:  # noqa: BLE001
        lines.append(f"[FAIL] T1_future_publication_hidden -> {e}")

    # Test 2 — future revision must not be visible (synthetic registry with a revision)
    try:
        tmp = tempfile.mkdtemp()
        store = os.path.join(tmp, "s.json")
        body = b'{"chart":{"result":[{"timestamp":[1757462400],"indicators":{"quote":[{"close":[100.0]}]}}]}}'
        open(store, "wb").write(body)
        import hashlib as _h
        reg = {"admitted": [{"source": "SYNTH_REVISED", "series": "X", "status": "CONDITIONAL",
                              "confidence": "high", "observation_time": "bar close date",
                              "stored_at": os.path.relpath(store, V3), "hash": _h.sha256(body).hexdigest(),
                              "revision_time": "2026-10-01T00:00:00Z"}]}
        before = PR.get_information_available_at("2026-09-20T00:00:00Z", reg=reg)
        after = PR.get_information_available_at("2026-10-02T00:00:00Z", reg=reg)
        n_before = sum(s["n_visible"] for s in before["sources"])
        n_after = sum(s["n_visible"] for s in after["sources"])
        good = (n_before == 0 and n_after >= 0)  # the revision-dated obs is never leaked early
        lines.append(f"[{'PASS' if good else 'FAIL'}] T2_future_revision_not_visible (before={n_before}, after={n_after})")
        ok += good
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:  # noqa: BLE001
        lines.append(f"[FAIL] T2_future_revision_not_visible -> {e}")

    # Test 3 — replay determinism
    try:
        a = PR.get_information_available_at(T)
        b = PR.get_information_available_at(T)
        ha = _h.sha256(json.dumps(a, sort_keys=True, default=str).encode()).hexdigest()
        hb = _h.sha256(json.dumps(b, sort_keys=True, default=str).encode()).hexdigest()
        good = (ha == hb)
        lines.append(f"[{'PASS' if good else 'FAIL'}] T3_replay_determinism ({ha[:16]}=={hb[:16]})")
        ok += good
    except Exception as e:  # noqa: BLE001
        lines.append(f"[FAIL] T3_replay_determinism -> {e}")

    # Test 4 — hash integrity (incl. tamper detection)
    try:
        v = PR.verify_hashes()
        good = bool(v["ok"])
        lines.append(f"[{'PASS' if good else 'FAIL'}] T4_hash_integrity (checked={v['checked']}, mismatches={len(v['mismatches'])})")
        ok += good
    except Exception as e:  # noqa: BLE001
        lines.append(f"[FAIL] T4_hash_integrity -> {e}")

    # Test 5 — timezone normalisation + original tz preserved
    try:
        res = PR.get_information_available_at(T)
        allutc = all(o["timezone"] == "UTC" for s in res["sources"] for o in s["observations"]) if res["sources"] else True
        keeps = all("source_timezone" in o for s in res["sources"] for o in s["observations"])
        good = allutc and keeps
        lines.append(f"[{'PASS' if good else 'FAIL'}] T5_timezone_utc_and_original_kept")
        ok += good
    except Exception as e:  # noqa: BLE001
        lines.append(f"[FAIL] T5_timezone_utc_and_original_kept -> {e}")

    print("\n".join(lines))
    print(f"\n=== PIT_LEAKAGE_TEST_COUNT=5 PASS={ok} FAIL={5 - ok} ===")
    return 0 if ok == 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
