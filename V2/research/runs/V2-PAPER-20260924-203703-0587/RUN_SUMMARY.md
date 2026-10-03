# RUN SUMMARY — V2-PAPER-20260924-203703-0587

- status: **COMPLETE**
- start_utc: 2026-09-24T20:37:03.287489+00:00
- end_utc: 2026-09-25T20:52:03.103619+00:00
- execution_mode: BROKER_DEMO
- code_commit: `7d2f485c6ffb3e64116872724d6182a1711d8b6f`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 96 (TRADE 6 / WAIT 90 / REJECT 0)
## Execution
- attempts: 6 / executed: 3 / rejected: 3
## Positions / PnL
- opened: 3 closed: 2 open_remaining: 1
- gross: 30.13 commission: -0.44 swap: 0.0 net: 29.69
- max_open_positions: 1 max_drawdown_frac: 0.032824
## Ledger
- events: 222 verify_ledger: True conservation_ok: False
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `a369362c9a71a1756f1da5cd87a988bf15c09d8d961c7783e091b74b08ed9b51`
- Paper Account == Replay: MISMATCH

## Data
- last_decision: {"ts": "2026-09-25T20:38:18.792034+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_cbcb7cb37442", "window": "2026-09-25T20:30Z", "execution_result": null}
