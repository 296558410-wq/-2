# TIMESTAMP AUDIT (freeze-002)

`generated_utc = 2026-09-22T06:25:00Z` · `utc_now = 2026-09-22 06:22:35.045508+00:00`

| check | value |
|---|---|
| timezone | UTC |
| timestamp_unit | ms (proven by value) |
| declared dtype | `datetime64[ms, UTC]` |
| interpretation proof | ms → 2026-09-07 01:05:00+00:00 · us → 1970-01-21 16:52:23+00:00 · ns → 1970-01-01 00:29:48+00:00 |
| TEST timestamp_min | `None` |
| TEST timestamp_max | `None` |
| out_of_order_count (post-TEST_START) | **0** |

```text
Pre-boundary baseline (informational, NOT TEST): out_of_order = 11 on the pre-TEST live feed.
OUT_OF_ORDER elements are recorded, never auto-deleted.
```
