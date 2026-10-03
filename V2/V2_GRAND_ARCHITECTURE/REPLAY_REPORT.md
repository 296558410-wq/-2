# REPLAY_REPORT

历史回放（Section 二十一）：用 V1_OLD / V1_NEW 可验证历史重放 Factory/Brain 机制。
**历史只用于 architecture/replay/mechanism 研究，绝不当未来训练标签。**

## V1 真实成交（来自券商事实库）
```
{
  "V1_OLD": {
    "n_trades": 109,
    "net_total": -42.91999999999999,
    "win_rate": 0.44036697247706424,
    "entry_ts_min": "2026-09-07T16:11:21+00:00",
    "entry_ts_max": "2026-09-28T03:49:17+00:00"
  },
  "V1_NEW": {
    "n_trades": 32,
    "net_total": -17.860000000000007,
    "win_rate": 0.375,
    "entry_ts_min": "2026-09-28T18:35:14+00:00",
    "entry_ts_max": "2026-10-02T04:48:02+00:00"
  }
}
```

## V1 Capture Replication (Experiment F)
```
{
  "v1_old_trades": 109,
  "replayed": 109,
  "captured_by_factory_ge2_agree": 33,
  "capture_rate": 0.30275229357798167,
  "verdict": "NOT_SUPPORTED",
  "note": "PIT features at V1 entry timestamps; no V1 outcome used as label"
}
```