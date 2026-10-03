# RUN SUMMARY — V2-PAPER-20260929-202202-995e

- status: **COMPLETE**
- start_utc: 2026-09-29T20:22:02.630155+00:00
- end_utc: 2026-09-30T20:37:02.466032+00:00
- execution_mode: BROKER_DEMO
- code_commit: `f412ad484bb974be4016c595821c595bb203b6f9`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 97 (TRADE 10 / WAIT 85 / REJECT 2)
## Execution
- attempts: 10 / executed: 3 / rejected: 7
## Positions / PnL
- opened: 3 closed: 3 open_remaining: 0
- gross: -34.31 commission: -0.63 swap: 0.0 net: -34.94
- max_open_positions: 1 max_drawdown_frac: 0.050842
## Ledger
- events: 236 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `6eee4c353bd1472402bcefb0b7e853e78242b115b9d2f082e1e7985794ff8973`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-30T20:23:25.529686+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_954008cd488f", "window": "2026-09-30T20:15Z", "execution_result": null}
