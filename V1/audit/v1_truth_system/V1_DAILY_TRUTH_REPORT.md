# V1 Daily Truth Report — 2026-10-02 (UTC)

> **FACTS_ONLY** — numbers below are computed from raw evidence (ledger + broker facts). No interpretation.

- generated: 2026-10-02T04:26:56.150490+00:00 · protocol v1-truth-1

| metric | value |
|---|---|
| cycles | 19 |
| signals | 2 |
| wait | 17 |
| risk_block | 3 |
| orders | 2 |
| mt5_rejects | 0 |
| fills | 2 |
| closes | 3 |
| open_positions | 0 |
| pnl_price_component | -25.41 |
| commission | 0.0 |
| swap | 0.0 |
| net | -25.41 |

## risk blocks by reason
```json
{
 "MAX_POSITION": 4,
 "MAX_DAILY_LOSS": 3,
 "MAX_CONSECUTIVE_LOSS": 3
}
```
## spread / slippage
```json
{
 "spread_bps": {
  "n": 19,
  "max": 0.434,
  "mean": 0.4323
 },
 "slippage_bps": [
  -0.8446,
  1.4464
 ]
}
```
## integrity
```json
{
 "ledger": {
  "ok": true,
  "entries": 622,
  "bad": null
 },
 "snapshots": {
  "ok": true,
  "entries": 0
 },
 "incidents_file": {
  "ok": true,
  "entries": 21
 }
}
```
## incidents today (index)
```json
[
 {
  "incident_id": "V1I-RISK_BLOCK-93E45412",
  "type": "RISK_BLOCK",
  "severity": "LOW"
 },
 {
  "incident_id": "V1I-RISK_BLOCK-03C4B119",
  "type": "RISK_BLOCK",
  "severity": "LOW"
 },
 {
  "incident_id": "V1I-RISK_BLOCK-70DC8557",
  "type": "RISK_BLOCK",
  "severity": "LOW"
 },
 {
  "incident_id": "V1I-RECONCILIA-7FAD46F6",
  "type": "RECONCILIATION_MISMATCH",
  "severity": "HIGH"
 },
 {
  "incident_id": "V1I-PNL_MISMAT-E884A812",
  "type": "PNL_MISMATCH",
  "severity": "HIGH"
 },
 {
  "incident_id": "V1I-RECONCILIA-7FAD46F6",
  "type": "RECONCILIATION_MISMATCH",
  "severity": "HIGH"
 },
 {
  "incident_id": "V1I-PNL_MISMAT-E884A812",
  "type": "PNL_MISMATCH",
  "severity": "HIGH"
 }
]
```

## UNKNOWNs
- legacy events (before the Truth System) carry **no** cycle_id/decision_id; links use time_adjacency and are marked as such.
- broker_facts is a latest-state cache, not an append-only log.
- decision snapshots start with the first live cycle after enablement.
