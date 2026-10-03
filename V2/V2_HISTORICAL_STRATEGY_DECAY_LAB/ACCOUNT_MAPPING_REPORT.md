# ACCOUNT_MAPPING_REPORT

> Source: `data/ACCOUNT_MAPPING.json`, `STRATEGY_LIFECYCLE_DATABASE.json`.
> Claim under investigation: **"2026-09-23 V2 drawdown near −20%."**

## Accounts and magics found

| account | server | project | magic | execution | real trades |
|---|---|---|---|---|---|
| 160759434 | ForexTimeFXTM-Demo01 | V1 / V1_OLD | 90002 | MT5 DEMO | 109 |
| 160759434 | ForexTimeFXTM-Demo01 | V1_NEW (upgrade) | 90011 | MT5 DEMO | 32 |
| 160761384 | ForexTimeFXTM-Demo01 | **V2** | 90003 | **PAPER_LOCAL (no broker)** | **0** |
| 160766418 | ForexTimeFXTM-Demo01 | V3 calibration | 90004 | DEMO_CALIBRATION (gated) | 0 |
| 160759434 | ForexTimeFXTM-Demo01 | collect | 90001 | MT5 DEMO | 0 |

Evidence: `trader_v3/state/MT5_INSTANCE_REGISTRY.json`, `v1_upgrade_registry.json`,
`v1_upgrade/truth/evidence/broker_facts.json`.

## Tracing the claim

1. **V2 executed trades = 0.** The V2 decision DB has 1666 rows, all `executed=false`
   (`note="paper ledger has no executed non-smoke trade"`). The V2 ledger `hermes_v2_ledger.jsonl`
   (15 KB, frozen since 2026-09-11) is `demo_calibration` smoke only. There is **no V2 broker P&L or
   ledger that can carry a −20 % drawdown**.
2. **V2 paper account:** `paper_account.json` — initial 200, balance 150, drawdown 50.21 USD =
   **25.11 %**, backend `paper_local`, dated 2026-09-12. Not −20 %, not 2026-09-23, and synthetic.
3. **Nearest real figure:** V1_OLD (magic 90002, account 160759434) cumulative **after-cost** net at
   the 2026-09-23 reset = **−26.55** over 91 trades; its full-run before-cost total = **−20.43**.
   The 2026-09-23T23:37–23:39 boundary is the **V1_OLD state reset**, not a V2 event.

## Verdict

**`UNRESOLVED_ACCOUNT_MAPPING`.** The "2026-09-23 V2 ≈ −20 % drawdown" claim **cannot be attributed
to V2** — V2 has no executed trades and no broker account P&L. The figure is closest to the
**V1_OLD** (Hermes candidate, magic 90002) cumulative net around the 2026-09-23 state reset.

This claim must **not** be used as evidence about V2 strategy performance.
