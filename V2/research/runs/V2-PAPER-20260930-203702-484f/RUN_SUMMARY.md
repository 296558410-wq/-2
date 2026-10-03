# RUN SUMMARY — V2-PAPER-20260930-203702-484f

- status: **COMPLETE**
- start_utc: 2026-09-30T20:37:02.473947+00:00
- end_utc: 2026-10-01T20:52:02.493933+00:00
- execution_mode: BROKER_DEMO
- code_commit: `f412ad484bb974be4016c595821c595bb203b6f9`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 94 (TRADE 9 / WAIT 85 / REJECT 0)
## Execution
- attempts: 9 / executed: 4 / rejected: 5
## Positions / PnL
- opened: 4 closed: 3 open_remaining: 1
- gross: -43.97 commission: -0.6 swap: 0.0 net: -44.57
- max_open_positions: 1 max_drawdown_frac: 0.562688
## Ledger
- events: 231 verify_ledger: True conservation_ok: False
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 1
- blocked: None

## Integrity
- replay state_hash: `ac7dc5620d0e90b9bd8214d4d2b88dd1fc2ef08be86738cc54e450e6c7e63627`
- Paper Account == Replay: MISMATCH

## Data
- last_decision: {"ts": "2026-10-01T20:38:14.999999+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_e8a128d5fdbd", "window": "2026-10-01T20:30Z", "execution_result": null}
