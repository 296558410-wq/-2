# FINAL_CONCLUSION

> Read-only / shadow. Stopped at **RESEARCH_COMPLETE**. No production change. `order_send = 0`.
> This conclusion is bounded by the evidence: 2 trade-bearing systems (1 independent), 141 trades,
> ~24 days; V2/V3 have 0 executed trades.

## Required answer block

```text
历史系统数量                : 85 registered dirs; 2 real trade-bearing systems
                              (V1_OLD magic 90002 = Hermes LLM candidate; V1_NEW magic 90011 = BASELINE control arm);
                              V2 magic 90003 & V3 = 0 executed trades; rest = research/calibration/unverifiable
真实可用 episode 数         : 2 (V1_OLD 109 closed trades / 2026-09-07..09-28;
                              V1_NEW 32 closed trades / 2026-09-28..10-02);
                              44 raw episodes registered (incl. restarts/switches/non-trade runs)
Fresh-Start Effect          : INCONCLUSIVE
                              (V1_OLD early-late p=0.064, fails FDR=0.43; V1_NEW p=0.90; placebo split p=0.19)
Cross-System Replication    : NOT_ESTABLISHED (only 1 independent Hermes system; V1_NEW is a control arm)
Universal Decay Time        : NOT_ESTABLISHED (peak age 167.9h vs 64.2h; no shared constant)
Estimated Decay Distribution: NOT_ESTABLISHED (n=2 systems; V1_OLD curve non-monotone)
Pre-Exhaustion Signal       : INCONCLUSIVE (in-sample only; no OOS; zero-crossings unstable)
Reset Effect                : INCONCLUSIVE (post-reset vs pre-reset first-72h p=0.27)
48h Hypothesis              : INCONCLUSIVE / NOT_SUPPORTED (V1_OLD p=0.92; V1_NEW p=0.19)
Evolution OOS               : NOT_EVALUABLE (precondition not met; V2 0 executed trades)
V2 当前状态                  : NO_CHANGE
生产修改                     : 0
order_send                  : 0
```

## One clear sentence

**We are not finding a fixed strategy and we are not yet finding a strategy-lifecycle /
fast-market-adaptation mechanism either — the evidence base is too small and too confounded
(2 systems, 1 independent; V2 has zero executed trades) to support any decay, fresh-start, or
adaptation mechanism, so the correct outcome is a bounded INCONCLUSIVE with no production change.**

## Why (short)

1. The real executed-trade history is only **V1_OLD (Hermes candidate) + V1_NEW (control arm)**;
   V2/V3 never traded, so the system the question is really about is **NOT_EVALUABLE**.
2. V1_OLD does *look* like profit-then-decay at day level, but the effect **fails FDR**
   (adj p = 0.43) and **fails the placebo split test** (random splits do nearly as well, p = 0.19).
3. V1_OLD and V1_NEW are **different strategies**, so no clean fresh-start comparison exists.
4. No universal decay time: the two systems peak at 168 h vs 64 h.

## What would change this

A **forward, PIT-complete, executed** episode series from a real system (V2/V3 once it actually
trades) with preserved inputs and closed roundtrips — replayable, age-aligned, and long enough to
power a decay test. Until then, no Evolution mechanism is warranted.

## Boundary attestation

- READ-ONLY / SHADOW: nothing written outside this lab dir; no historical ledger/state modified.
- V2 left RUNNING; `order_send = 0`; no BROKER_DEMO connection.
- No V1/V2/V3 code, strategy, threshold, cost, risk, sizing, prompt, discovery or Phase-3 baseline change.
- **STOP. Awaiting explicit user authorization; do not auto-advance.**
