# RUN SUMMARY — V2-PAPER-20260923-203702-4f83

- status: **COMPLETE**
- start_utc: 2026-09-23T20:37:02.724956+00:00
- end_utc: 2026-09-24T20:37:03.280491+00:00
- execution_mode: BROKER_DEMO
- code_commit: `ebce041797eca0c5043ddcd557fd5135d2f8ea8f`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 83 (TRADE 7 / WAIT 73 / REJECT 3)
## Execution
- attempts: 7 / executed: 2 / rejected: 5
## Positions / PnL
- opened: 2 closed: 1 open_remaining: 1
- gross: 15.86 commission: -0.22 swap: 0.0 net: 15.64
- max_open_positions: 1 max_drawdown_frac: 0.050565
## Ledger
- events: 191 verify_ledger: True conservation_ok: False
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `6bee97ff65d12981a31dd241088800a0e6d0ad857511a9949f7ba9216006a6c6`
- Paper Account == Replay: MISMATCH

## Data
- last_decision: {"ts": "2026-09-24T20:23:18.946595+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_01ea8144c8ac", "window": "2026-09-24T20:15Z", "execution_result": null}
