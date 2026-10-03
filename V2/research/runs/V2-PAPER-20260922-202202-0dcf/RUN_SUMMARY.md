# RUN SUMMARY — V2-PAPER-20260922-202202-0dcf

- status: **COMPLETE**
- start_utc: 2026-09-22T20:22:02.727642+00:00
- end_utc: 2026-09-23T20:37:02.718784+00:00
- execution_mode: BROKER_DEMO
- code_commit: `ebce041797eca0c5043ddcd557fd5135d2f8ea8f`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 97 (TRADE 13 / WAIT 83 / REJECT 1)
## Execution
- attempts: 13 / executed: 9 / rejected: 4
## Positions / PnL
- opened: 9 closed: 8 open_remaining: 1
- gross: -9.0 commission: -1.76 swap: 0.0 net: -10.76
- max_open_positions: 1 max_drawdown_frac: 0.048536
## Ledger
- events: 280 verify_ledger: True conservation_ok: False
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `e5ff37b1647c3fa341df26eafe3483d62d435a0d427fd939e8ee1e36b1baf71c`
- Paper Account == Replay: MISMATCH

## Data
- last_decision: {"ts": "2026-09-23T20:22:46.020208+00:00", "decision": "TRADE", "decision_id": "DEC-ctx_c52c6a65b454", "window": "2026-09-23T20:15Z", "execution_result": "REJECTED:POSITION_BUSY"}
