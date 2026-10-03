# DUPLICATE AUDIT (freeze-002)

`generated_utc = 2026-09-22T06:25:00Z` — three levels counted **separately**; `drop_duplicates()` is never applied.

| level | definition | count at/after TEST_START |
|---|---|---|
| DUP_TIMESTAMP | identical `ts_utc` | **0** |
| DUP_QUOTE | identical `(ts_utc, bid, ask)` | **0** |
| DUP_EVENT | identical event identity | **DATA_GAP** |

```text
DUP_TIMESTAMP is NOT equated with DUP_EVENT.
EVENT_IDENTITY = DATA_GAP (no event id in the feed; (ts,bid,ask) cannot prove identity)
(the feed carries no event id; (ts,bid,ask) cannot prove uniqueness, and no event id was invented)
Pre-boundary baseline (informational, NOT TEST): DUP_TIMESTAMP 1014 / DUP_QUOTE 1014 / DUP_EVENT 0.
```
