# RUN SUMMARY — V2-SHADOW-20260917-104824-76af

- status: **COMPLETE**
- start_utc: 2026-09-17T10:48:24.512836+00:00
- end_utc: 2026-09-17T10:53:18.117243+00:00
- execution_mode: BROKER_DEMO
- code_commit: `9b3d398ee3232a718931554f905fa3beab4cfe7e`
- config_hash: `7bfab969722ff38a2d5607257750f138241851b464007186ae101316eaf37aff`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: local_fxtm) + reference GC=F + CFTC/BLS/news

## Decisions
- total: 1 (TRADE 0 / WAIT 1 / REJECT 0)
## Execution
- attempts: 0 / executed: 0 / rejected: 0
## Positions / PnL
- opened: 0 closed: 0 open_remaining: 0
- gross: 0.0 commission: 0.0 swap: 0.0 net: 0.0
- max_open_positions: 0 max_drawdown_frac: 0.0
## Ledger
- events: 3 verify_ledger: True conservation_ok: False
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 1
- blocked: None

## Integrity
- replay state_hash: `c1f6bef2ddd113274b022b104414d95a6b1371fc809b6699cd6fb474aa7a8f95`
- Paper Account == Replay: MISMATCH

## Data
- last_decision: {"ts": "2026-09-17T10:49:30.144167+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_482605d726ec", "window": "2026-09-17T10:45Z", "execution_result": null}
