# RUN SUMMARY — V2-PAPER-20260925-205203-201b

- status: **COMPLETE**
- start_utc: 2026-09-25T20:52:03.111619+00:00
- end_utc: 2026-09-27T20:07:02.587820+00:00
- execution_mode: BROKER_DEMO
- code_commit: `0f3d5d3c88a701a80b42d520b2b510f1aa07ccf3`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

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
- replay state_hash: `c68fc831e8d31fdcc62e7e85f9d75ae263234c5d9da6061c646b413b65d9e2e0`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-25T20:53:18.788638+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_e58bbcc9a4b9", "window": "2026-09-25T20:45Z", "execution_result": null}
