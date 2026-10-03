# RUN SUMMARY — V2-SHADOW-20260917-105319-b5e4

- status: **COMPLETE**
- start_utc: 2026-09-17T10:53:19.307152+00:00
- end_utc: 2026-09-18T10:25:08.071995+00:00
- execution_mode: BROKER_DEMO
- code_commit: `8d997fb70fcde578c4bc2994ee40240fe7b33b60`
- config_hash: `7bfab969722ff38a2d5607257750f138241851b464007186ae101316eaf37aff`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 90 (TRADE 8 / WAIT 82 / REJECT 0)
## Execution
- attempts: 12 / executed: 5 / rejected: 3
## Positions / PnL
- opened: 5 closed: 0 open_remaining: 5
- gross: 0.0 commission: 0.0 swap: 0.0 net: 0.0
- max_open_positions: 5 max_drawdown_frac: 0.000105
## Ledger
- events: 220 verify_ledger: True conservation_ok: False
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `c1f6bef2ddd113274b022b104414d95a6b1371fc809b6699cd6fb474aa7a8f95`
- Paper Account == Replay: MISMATCH

## Data
- last_decision: {"ts": "2026-09-18T10:22:48.267852+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_634215a20e3b", "window": "2026-09-18T10:15Z", "execution_result": null}
