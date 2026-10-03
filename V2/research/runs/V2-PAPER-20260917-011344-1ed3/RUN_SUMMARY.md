# RUN SUMMARY — V2-PAPER-20260917-011344-1ed3

- status: **COMPLETE**
- start_utc: 2026-09-17T01:13:44.832065+00:00
- end_utc: 2026-09-17T01:34:30.950441+00:00
- execution_mode: BROKER_DEMO
- code_commit: `d143ad756dc1369d08914c4980d397a71960fcd4`
- config_hash: `ad8ccb185686d3e88d8d121fc7280d644949abff8aca5453b588eba55493bd26`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: yahoo GC=F + sina/tencent/eastmoney + CFTC/BLS/新闻

## Decisions
- total: 2 (TRADE 0 / WAIT 2 / REJECT 0)
## Execution
- attempts: 0 / executed: 0 / rejected: 0
## Positions / PnL
- opened: 0 closed: 0 open_remaining: 0
- gross: 0.0 commission: 0.0 swap: 0.0 net: 0.0
- max_open_positions: 0 max_drawdown_frac: 0.0
## Ledger
- events: 5 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `b5d270dc08df37698bf47019c116608cc238d49fa7fb9cc83b5ad32ac450aeb7`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-17T01:23:13.731177+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_431415e44feb", "window": "2026-09-17T01:15Z", "execution_result": null}
