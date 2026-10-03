# RUN SUMMARY — V2-PAPER-20260914-230705-8618

- status: **COMPLETE**
- start_utc: 2026-09-14T23:07:05.929933+00:00
- end_utc: 2026-09-14T23:14:00.241347+00:00
- execution_mode: BROKER_DEMO
- code_commit: `fa935489743c69f6ecb3434dd55dc47ee92a7fc3`
- config_hash: `ad8ccb185686d3e88d8d121fc7280d644949abff8aca5453b588eba55493bd26`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: yahoo GC=F + sina/tencent/eastmoney + CFTC/BLS/新闻

## Decisions
- total: 1 (TRADE 0 / WAIT 1 / REJECT 0)
## Execution
- attempts: 0 / executed: 0 / rejected: 0
## Positions / PnL
- opened: 0 closed: 0 open_remaining: 0
- gross: 0.0 commission: 0.0 swap: 0.0 net: 0.0
- max_open_positions: 0 max_drawdown_frac: 0.0
## Ledger
- events: 3 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `efff924c79faf2318299e517280857a0d66475a909b5b9c6204d22f73f2a2227`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-14T23:08:12.790332+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_15500b258fc2", "window": "2026-09-14T23:00Z", "execution_result": null}
