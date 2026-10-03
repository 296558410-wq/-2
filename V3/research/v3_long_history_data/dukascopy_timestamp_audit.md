# Dukascopy M1 candle — timestamp semantics audit (machine summary)

`ts_utc = 2026-09-25T09:29:43.831903+00:00`

```text
DUKASCOPY_CANDLE_TIMESTAMP_SEMANTICS = UNRESOLVED
A timezone            = CODE_ASSERTS_UTC / INDEPENDENT VERIFICATION FAILED
B minute identity     = RESOLVED (day + sec, 1440 bars/day, 00:00..23:59, all multiples of 60)
C bar open/close      = UNKNOWN (structural evidence suggests interval-start; no documentation; no independent minute source)
SCALE                 = 1000 (parser applies it; confirmed in code)
ASSET STATUS          = REFERENCE_ONLY (must not enter V3 event research)
```

## Key numbers

```json
{
 "offset_population": {
  "n": 187200,
  "unique_offsets": 1440,
  "min": 0,
  "max": 86340,
  "all_multiples_of_60": true,
  "contains_86400": false,
  "contains_0": true,
  "contains_86340": true,
  "interpretation_if_1440_per_day": "offsets 0..86340 with exactly 1440 per day means each calendar day carries bars stamped at 00:00..23:59 -> the stamp coincides with the INTERVAL START of the final bar of the day (a close-stamp series would need a 24:00/86400 stamp for its last bar)"
 },
 "flat_stats_2025": {
  "rows": 1272960,
  "flat_rows": 413512,
  "flat_pct": 32.484,
  "real_rows": 859448,
  "days_total": 320,
  "days_with_real_bars": 274,
  "fully_flat_days": 46
 },
 "best_alignment": {
  "server_offset_hours_to_utc": 3,
  "n": 3218,
  "corr": 0.0224
 },
 "duka_2025_h1_vol_bp": 24.92,
 "mt5_2025_h1_vol_bp": 23.96
}
```

## Why UNRESOLVED (per task §15, all six must pass)

```text
timezone明确        ✗ (code says UTC; independent confirmation failed)
minute identity明确 ✓
open/close明确      ✗ (UNKNOWN)
parser 可追溯       ✓ (dukascopy.py -> duka_download.py -> duka_assemble.py, commit 04dfc40)
git/source 可追溯   ✓
独立样本验证通过    ✗ (cross-validation did not succeed)
=> UNRESOLVED
```