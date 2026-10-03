# RUN SUMMARY — V2-PAPER-20260913-224157-7a88

- status: **COMPLETE**
- start_utc: 2026-09-13T22:41:57.146947+00:00
- end_utc: 2026-09-14T22:56:10.323016+00:00
- execution_mode: BROKER_DEMO
- code_commit: `7cb1dea5ececcb6582be32f3fd4be6ce143e2423`
- config_hash: `ad8ccb185686d3e88d8d121fc7280d644949abff8aca5453b588eba55493bd26`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: yahoo GC=F + sina/tencent/eastmoney + CFTC/BLS/新闻

## Decisions
- total: 84 (TRADE 0 / WAIT 84 / REJECT 0)
## Execution
- attempts: 0 / executed: 0 / rejected: 0
## Positions / PnL
- opened: 0 closed: 0 open_remaining: 0
- gross: 0.0 commission: 0.0 swap: 0.0 net: 0.0
- max_open_positions: 0 max_drawdown_frac: 0.0
## Ledger
- events: 169 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 10
- blocked: None

## Integrity
- replay state_hash: `7d07b7a5f2a72fa1cac2ac02d45401efd41dacb77f92da9c66ba766d9086b397`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-14T22:14:51.567265+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_846b8ab7c0cc", "window": "2026-09-14T22:00Z", "execution_result": null}
