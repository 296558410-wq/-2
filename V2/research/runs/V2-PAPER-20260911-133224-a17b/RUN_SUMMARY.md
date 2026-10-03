# RUN SUMMARY — V2-PAPER-20260911-133224-a17b

- status: **COMPLETE**
- start_utc: 2026-09-11T13:32:24.436204+00:00
- end_utc: 2026-09-12T13:36:00.904622+00:00
- execution_mode: PAPER
- code_commit: `933dbd2ba81323c01e404ddfa7385f441307f7eb`
- config_hash: `eec4330cbf6c1a826340e1859adeafef183663a8ab3233c3077d22e16dabfd81`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: yahoo GC=F + sina/tencent/eastmoney + CFTC/BLS/新闻

## Decisions
- total: 61 (TRADE 2 / WAIT 59 / REJECT 0)
## Execution
- attempts: 2 / executed: 0 / rejected: 2
## Positions / PnL
- opened: 0 closed: 0 open_remaining: 0
- gross: 0.0 commission: 0.0 swap: 0.0 net: 0.0
- max_open_positions: 0 max_drawdown_frac: 0.0
## Ledger
- events: 127 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 20
- blocked: None

## Integrity
- replay state_hash: `1d57edd9481db8a010dfc249f0000649124818943ee17e29544ea2a627ee92cd`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-12T04:22:25.770918+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_34e653d9834e", "window": "2026-09-12T04:15Z", "execution_result": null}
