# M03 Cross-Market Shock — tradability closeout

`ts_utc = 2026-09-25T12:21:11.545572+00:00`

```text
M03_TRADABILITY_STATUS = NOT_PROMISING
FREQUENCY_GATE       = FAIL (0.775 < 1.0 per week)
MECHANISM_READ       = STATISTICALLY_INTERESTING_BUT_NOT_HIGH_FREQUENCY_TRADABLE
CANDIDATE_RESEARCH   = 0
DISPOSITION          = RESEARCH_ARCHIVE
```

| item | value |
|---|---|
| M03 input events | 63 |
| testable / not testable | 63 / 0 |
| sources | DXY 13 · VIX 5 · UST10Y_PROXY 10 · MULTI_SOURCE 35 |
| raw n / effective n | 63 / 21 |
| gross edge | +26.7942 bp |
| net edge 1x / 2x / 3x | +25.8802 / +24.9662 / +24.0522 bp |
| CI95 | [10.5104, 49.9205] bp |
| WF folds | +8.2659 / +19.1354 / +50.2393 bp (CONSISTENT) |
| permutation p | p=0.0065 |
| events/week | 0.7753 |
| holding | 6 h |
| net edge per hour | +4.3134 bp |
| direction mirror | ARITHMETIC_IDENTITY |
| negative control | PASS_WITH_LIMITATION |
| execution | FEASIBLE_UNDER_FROZEN_RULE |
| timestamp sensitivity | POSITIVE_BUT_SENSITIVE |
| TNX proxy dependency | NOT_PROXY_DEPENDENT (^TNX remains a PROXY) |
| data semantics | XAUUSD_DEFINITION/BAR_OPEN_CLOSE/LICENSE = UNKNOWN |
| freeze hash | 2116ec8e812c322a34604e51eaf03b1682f07bbdeae6b8087c94c4f549d75b20 |

```text
Not a profit proof. Not a future-return guarantee. Not alpha certification.
Not live-execution validation. Not a high-frequency strategy. Not 63 independent trade samples.
```
