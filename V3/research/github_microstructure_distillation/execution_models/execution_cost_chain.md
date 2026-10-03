# Execution Model Chain (venue-independent method; FXTM-calibrated)

## The chain (§五)

```text
Gross Edge
  -> Spread
  -> Slippage
  -> Commission
  -> Latency
  -> Adverse Selection
  -> NET EXECUTABLE EDGE
```

FXTM-calibrated numbers (measured, `CALIBRATION_20RT_20260921`):

```text
spread ~0.18 USD/RT   commission ~0.22 USD/RT   total 0.40 USD/RT ~= 0.914 bp
RTT (signal -> fill)  median ~279 ms   (signal->request 0.0002 ms, request->ack ~274 ms, ack->fill ~7 ms)
entry slippage        median 0.0 USD, p95 0.046, p99 0.183   (signed; ~half of fills favourable)
```

## What to look for in a repo (§五) — cost must be IN the objective, not adjacent to it

```text
expected_net_return        cost subtracted inside the score being optimised
implementation_shortfall   decision vs arrival price; the canonical cost-aware objective
execution_probability      P(fill) enters the expected value, not applied afterwards
fill_probability           explicit model (needs L2 queue -> DATA-DEPENDENT for FXTM)
latency_discount           signal decayed by the measured RTT before it is used
cost-aware loss            loss = -(pnl - cost) or a cost hinge in training
```

**Anti-pattern (reject):** a gross-return target with costs subtracted only in the final PnL report.
That is exactly how `PREDICTIVE_BUT_NOT_EXECUTABLE` results are produced.

## Cost-aware labelling (transferable to FXTM L1)

```text
y_net(t,h) = direction * (mid(t+h) - entry_exec_price) - cost_bp(t)
entry_exec_price = ask(t) for LONG, bid(t) for SHORT      (never mid)
cost_bp(t)       = RT_USD / mid(t) * 1e4
```
This is `B METHOD_TRANSFERABLE`: the logic is venue-independent; only the constants change.

## Decision policy vocabulary (§八)

```text
TAKE      cross the spread now (pay it) because expected net edge > cost
PASSIVE   quote inside/at the touch and wait (capture spread) - requires fill probability
WAIT      do not act yet (cost or uncertainty too high)
CANCEL    withdraw a resting quote (adverse flow detected)
EXIT      close now (edge gone / stop / inventory)
```
A model that outputs only LONG/SHORT has no execution policy and cannot express the FXTM problem.

## FXTM constraint on this chain

```text
spread, commission, latency, signed slippage ....... OBSERVABLE / PARTIAL  (usable now)
P(fill), queue position, market impact ............. DATA_GAP (no real L2/queue/MBO)
adverse selection .................................. PARTIAL (markout-based, L1 only)
```
So the *chain* is implementable on FXTM; the *passive fill* branch is not, until real depth exists.
