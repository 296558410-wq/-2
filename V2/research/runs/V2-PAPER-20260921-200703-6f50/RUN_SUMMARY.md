# RUN SUMMARY — V2-PAPER-20260921-200703-6f50

- status: **COMPLETE**
- start_utc: 2026-09-21T20:07:03.263316+00:00
- end_utc: 2026-09-22T20:22:02.721732+00:00
- execution_mode: BROKER_DEMO
- code_commit: `ff3f24ac70999091dbaa822fc43dd682393d3c94`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 96 (TRADE 11 / WAIT 83 / REJECT 2)
## Execution
- attempts: 11 / executed: 3 / rejected: 8
## Positions / PnL
- opened: 3 closed: 3 open_remaining: 0
- gross: -11.74 commission: -0.66 swap: 0.0 net: -12.4
- max_open_positions: 1 max_drawdown_frac: 0.039364
## Ledger
- events: 236 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `238965231f3dc2bb44ebe5f10bdbe11e3fdd6347ae293c4dfbce29f0cbc94f99`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-22T20:07:41.062633+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_cf2c3d7b00a1", "window": "2026-09-22T20:00Z", "execution_result": null}
