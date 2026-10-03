# RUN SUMMARY — V2-PAPER-20260920-200702-f507

- status: **COMPLETE**
- start_utc: 2026-09-20T20:07:02.342923+00:00
- end_utc: 2026-09-21T20:07:03.256410+00:00
- execution_mode: BROKER_DEMO
- code_commit: `88f722849c739577543e0317328c902b87001581`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 96 (TRADE 11 / WAIT 84 / REJECT 1)
## Execution
- attempts: 11 / executed: 2 / rejected: 9
## Positions / PnL
- opened: 2 closed: 2 open_remaining: 0
- gross: -1.42 commission: -0.44 swap: 0.0 net: -1.86
- max_open_positions: 1 max_drawdown_frac: 0.031114
## Ledger
- events: 229 verify_ledger: True conservation_ok: False
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `382530aa4f51fa24917233e61ca657f715acbcd42a47b2c109931004d922a4ba`
- Paper Account == Replay: MISMATCH

## Data
- last_decision: {"ts": "2026-09-21T19:53:20.762673+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_ede9e8a3bc8c", "window": "2026-09-21T19:45Z", "execution_result": null}
