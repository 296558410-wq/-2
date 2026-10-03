# RUN SUMMARY — V2-PAPER-20260927-200702-cfcd

- status: **COMPLETE**
- start_utc: 2026-09-27T20:07:02.593334+00:00
- end_utc: 2026-09-28T20:07:02.909816+00:00
- execution_mode: BROKER_DEMO
- code_commit: `9e8c4f94089c5700ade3b08ec528e14d83821b2e`
- config_hash: `b0cc254b809da52844778bbbb8a298df77dd2d031a8353fec3f982dac26be0e5`
- versions: {"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}
- market_data_source: XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F

## Decisions
- total: 96 (TRADE 14 / WAIT 68 / REJECT 14)
## Execution
- attempts: 14 / executed: 2 / rejected: 12
## Positions / PnL
- opened: 2 closed: 2 open_remaining: 0
- gross: -13.82 commission: -0.4 swap: 0.0 net: -14.22
- max_open_positions: 1 max_drawdown_frac: 0.036096
## Ledger
- events: 235 verify_ledger: True conservation_ok: False
## System
- agent1_failures: 0 agent2_failures: 0 hermes_failures: 0 ledger_failures: 0
- duplicate_skips: 0
- blocked: None

## Integrity
- replay state_hash: `d30f338de7d3a167602f2d557352e3d3c29508c91ce810c203a12583541be0f0`
- Paper Account == Replay: MISMATCH

## Data
- last_decision: {"ts": "2026-09-28T19:53:43.523382+00:00", "decision": "WAIT", "decision_id": "DEC-ctx_73f6800bf2f1", "window": "2026-09-28T19:45Z", "execution_result": null}
