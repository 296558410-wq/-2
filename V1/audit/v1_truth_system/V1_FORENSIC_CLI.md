# V1 Forensic CLI（V1_FORENSIC_CLI）

One-Command Forensics。只读；不写交易状态；不需要人工翻日志。

## 位置与调用

```text
C:\AIQuant\.venv\Scripts\python.exe C:\AIQuant\research\hermes\trader_v1\v1_upgrade\truth\v1_forensic.py <命令>
```

| 命令 | 作用 |
|---|---|
| `--trade V1T-2378322488`（或裸 position_id） | 该笔交易完整因果链（十段）+ raw broker deals + derived 一致性；生成 `CASE-V1T-*` |
| `--incident V1I-...` | Incident 档案：类型/首末次/严重度/根因/受影响 ID/证据/状态/处置 |
| `--cycle V1C-20261002T041802` | 该周期全部事件（signal/risk/order/ledger） |
| `--date 2026-10-02` | 当日 Daily Truth（FACTS_ONLY）+ incident 索引；落盘 evidence/daily/ |
| `--incidents` | 全部 Incident（最新态）列表 |
| `--index` | 证据库清单（路径/SHA256/记录数） |
| `--json` | 原始 JSON 输出（供下游使用） |

## 示例（实测输出节选）

**trade**：
```text
== CASE CASE-V1T-2378322488 ==
  signal_and_context   seq=517 ev=V1E-5177d2f27732 signal=DIRECTIONAL (time_adjacency(legacy))
  risk_evaluation      seq=517 ev=V1E-5177d2f27732 risk_allow=None reasons=[]
  decision             seq=517 ev=V1E-5177d2f27732 action=ENTER
  order_check          seq=518 ...  order_request seq=519 ...  order_send seq=520 ok_retcode=10009 slip=-0.12
  fill                 seq=521 ...  position seq=522 ...  close seq=523 reason=SL ...  pnl seq=524 pnl=-9.31
derived: {'gross_profit': -9.31, 'commission': -0.1, 'swap': 0.0, 'net': -9.41, 'consistent': True}
```

**incident**（合成夹具，显式标注）：
```text
== INCIDENT V1I-RECONCILIA-7FAD46F6 ==
  type RECONCILIATION_MISMATCH · severity HIGH · status ACKNOWLEDGED
  root_cause SYNTHETIC_FAULT_INJECTION_DEMO · evidence {"broker_only": ["SYNTH-001"], "synthetic": true}
```

**cycle**：列出该周期 DECISION/ORDER_*/FILL/POSITION 全事件。

**date**：`cycles/signals/WAIT/RISK_BLOCK/orders/fills/closes/PnL/commission/swap/spread/slippage/risk_blocks_by_reason/MT5 rejects/reconciliation/schedule gaps/incidents/ledger integrity/…` + `FACTS_ONLY`。

## 设计约束

- 只读：不触碰账本/证据（除 `--date` 落盘当日报告与 `--trade` 缓存 Case 到 evidence/cases/）。
- 证据不足时输出 `[UNKNOWN]` 阶段，**从不猜测**。
- 输出可 `--json` 管道化；ID 均为稳定确定性 ID。
