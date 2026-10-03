# RUN SUMMARY — V2-PAPER-20260928-200702-bde3

- status: **COMPLETE**
- start_utc: 2026-09-28T20:07:02.917814+00:00
- end_utc: 2026-09-29T20:22:02.623156+00:00
- execution_mode: BROKER_DEMO
- code_commit: `f412ad484bb974be4016c595821c595bb203b6f9`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 97 (TRADE 13 / WAIT 82 / REJECT 2)
## Execution
- attempts: 13 / executed: 5 / rejected: 8
## Positions / PnL
- opened: 5 closed: 5 open_remaining: 0
- gross: -31.11 commission: -1.0 swap: 0.0 net: -32.11
- max_open_positions: 1 max_drawdown_frac: 0.052025
## Ledger
- events: 256 verify_ledger: True conservation_ok: True
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `f6ffeb47e75c919639c703d4a83e19bec5c1e44ba6558bf57d29caf6513c1c43`
- Paper Account == Replay: PASS

## Data
- last_decision: {"ts": "2026-09-29T20:08:22.187743+00:00", "decision": "TRADE", "decision_id": "DEC-ctx_224f93236c99", "window": "2026-09-29T20:00Z", "execution_result": "REJECTED:PRECHECK_REJECT"}
