# RUN SUMMARY — V2-PAPER-20260911-132109

- status: **COMPLETE**
- start_utc: 2026-09-11T13:21:09.894958+00:00
- end_utc: 2026-09-11T13:22:01.428551+00:00
- execution_mode: PAPER
- code_commit: `1a389d0998e34c5573c8bb96fb3f7702ca956d3d`
- config_hash: `eec4330cbf6c1a826340e1859adeafef183663a8ab3233c3077d22e16dabfd81`
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
- events: 2 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: {'reason': 'PAPER_REPLAY_MISMATCH', 'detail': {'balance': False, 'equity': False}, 'ts': '2026-09-11T13:22:01.425552+00:00'}

## Integrity
- replay state_hash: `6f56a93a25fa3c6cfacf1256551d49b1e12306383854341eafa23afd6d276988`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-11T13:22:01.418408+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_1b87dc88a999", "window": "2026-09-11T13:15Z", "execution_result": null}
