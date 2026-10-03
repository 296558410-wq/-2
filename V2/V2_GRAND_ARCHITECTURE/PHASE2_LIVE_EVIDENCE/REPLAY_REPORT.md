# REPLAY_REPORT

- status: **MATCH**
- cycles_checked: 80  cycles_matching: 80
- input_hash_method: sha256 of PIT window (last 200 15m bars <= decision)
- output_hash_method: sha256 of {cycle, final decision, conflict, direction, signals}
- note: deterministic re-derivation from recorded inputs; no production state read for logic

## 说明

Shadow 决策完全由记录的 PIT 输入窗口确定性重算；同输入 → 同 `output_hash`。
符合 spec §19「生产代码未修改 / 实验代码全部可追溯 / manifest 最新 / replay PASS」。
