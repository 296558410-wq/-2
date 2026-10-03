# RUN SUMMARY — V2-PAPER-20260914-231126-5fe2

- status: **COMPLETE**
- start_utc: 2026-09-14T23:11:26.880416+00:00
- end_utc: 2026-09-15T11:28:56.623738+00:00
- execution_mode: BROKER_DEMO
- code_commit: `d0b02dd6e411b17b3cb47d56efadad04ee71c701`
- config_hash: `ad8ccb185686d3e88d8d121fc7280d644949abff8aca5453b588eba55493bd26`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: yahoo GC=F + sina/tencent/eastmoney + CFTC/BLS/新闻

## Decisions
- total: 24 (TRADE 1 / WAIT 23 / REJECT 0)
## Execution
- attempts: 1 / executed: 1 / rejected: 0
## Positions / PnL
- opened: 1 closed: 0 open_remaining: 1
- gross: 0.0 commission: 0.0 swap: 0.0 net: 0.0
- max_open_positions: 1 max_drawdown_frac: 0.00027
## Ledger
- events: 54 verify_ledger: True conservation_ok: False
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 1
- blocked: {'reason': 'PAPER_REPLAY_MISMATCH', 'detail': {'equity': False, 'net_pnl': False}, 'ts': '2026-09-15T04:53:31.392819+00:00'}

## Integrity
- replay state_hash: `9a7214e63b3813e58350fca71d575ae14ffbc44ec6979c21b332f61cf2a1df37`
- Paper Account == Replay: MISMATCH

## Data
- last_decision: {"ts": "2026-09-15T04:53:30.339390+00:00", "decision": "TRADE", "decision_id": "DEC-ctx_30ab864391fa", "window": "2026-09-15T04:45Z", "execution_result": "EXECUTED"}
