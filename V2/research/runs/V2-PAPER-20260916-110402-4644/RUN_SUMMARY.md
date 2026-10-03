# RUN SUMMARY — V2-PAPER-20260916-110402-4644

- status: **COMPLETE**
- start_utc: 2026-09-16T11:04:02.649080+00:00
- end_utc: 2026-09-17T01:13:16.165547+00:00
- execution_mode: BROKER_DEMO
- code_commit: `b56f1f61c8c7c1d3d34d584b1f36de417de47c85`
- config_hash: `ad8ccb185686d3e88d8d121fc7280d644949abff8aca5453b588eba55493bd26`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: yahoo GC=F + sina/tencent/eastmoney + CFTC/BLS/新闻

## Decisions
- total: 57 (TRADE 6 / WAIT 51 / REJECT 0)
## Execution
- attempts: 6 / executed: 1 / rejected: 5
## Positions / PnL
- opened: 1 closed: 1 open_remaining: 0
- gross: -26.34 commission: -0.22 swap: 0.0 net: -26.56
- max_open_positions: 1 max_drawdown_frac: 0.025281
## Ledger
- events: 134 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 1
- blocked: None

## Integrity
- replay state_hash: `d2af09d8da366a6568b2aaabeb9e86e3d70947a0419a723dbadcb98c7dd998b7`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-17T01:07:38.516015+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_338fa8092d9d", "window": "2026-09-17T01:00Z", "execution_result": null}
