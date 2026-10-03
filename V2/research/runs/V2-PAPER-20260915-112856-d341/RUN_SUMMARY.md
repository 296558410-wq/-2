# RUN SUMMARY — V2-PAPER-20260915-112856-d341

- status: **BLOCKED**
- start_utc: 2026-09-15T11:28:56.626718+00:00
- end_utc: 2026-09-16T11:04:02.630468+00:00
- execution_mode: BROKER_DEMO
- code_commit: `31138015f1bbe034759e46a5ee322c069fd57d26`
- config_hash: `ad8ccb185686d3e88d8d121fc7280d644949abff8aca5453b588eba55493bd26`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: yahoo GC=F + sina/tencent/eastmoney + CFTC/BLS/新闻

## Decisions
- total: 56 (TRADE 1 / WAIT 55 / REJECT 0)
## Execution
- attempts: 1 / executed: 1 / rejected: 0
## Positions / PnL
- opened: 1 closed: 1 open_remaining: 0
- gross: 14.85 commission: -0.22 swap: 0.0 net: 14.63
- max_open_positions: 1 max_drawdown_frac: 0.005435
## Ledger
- events: 122 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: {'reason': 'PAPER_REPLAY_MISMATCH', 'detail': {'net_pnl': False, 'trade_count': False, 'commission': False}, 'ts': '2026-09-16T01:08:07.547758+00:00'}

## Integrity
- replay state_hash: `8dc200fc0a3528f3eb3b61871d22a1574ef02f05a4100e467fdfb99d28f0fd0b`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-16T01:08:07.515976+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_99bdf2d4e13a", "window": "2026-09-16T01:00Z", "execution_result": null}
