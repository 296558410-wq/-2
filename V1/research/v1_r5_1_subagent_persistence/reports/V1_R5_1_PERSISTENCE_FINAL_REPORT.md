# V1-R5.1 SUBAGENT PERSISTENCE REPAIR — FINAL REPORT

## 目标
只修"子代理结果无法可靠落盘"，不碰 R3/R4/R5，不做预测能力研究，不进入 R6。

## 定位到的根因（4 条）
RC1 **SUBOUTPUT_PERSISTENCE_FAILURE** — 子代理经常"完成但不写文件"（输出越大越糟）：R3 38 次调用落盘率低；R4 54 次调用仅 adv 5/18、post 8/18；R5 9 次首轮仅 3 落盘。
RC2 **CONCURRENCY_LIMIT_EXCEEDED** — `agents.defaults.subagents.maxChildrenPerAgent = 5`。此前一次性发射 18/38/54 个任务，远超上限（出现 `reached max active children (5/5)`）。
RC3 **VALIDATOR_HASH_BASIS_MISMATCH** — 我的第一版父进程校验用 `indent` 字节哈希对比规范化哈希，导致 HASH 恒失败（仪器错误）。
RC4 **IMPLICIT_SUCCESS_CONDITION** — 旧流程把"子代理写了文件"当成功条件，没有任何父进程侧回执校验。

## 修复（协议）
SUBAGENT → **RETURN PAYLOAD** → **PARENT VALIDATOR** → SCHEMA → **ATOMIC WRITE (.tmp+fsync+os.replace)** → **READ-BACK** → **SHA256** → **LEDGER**
子代理是否写文件**不再是成功条件**；父进程接收+校验+落盘+回读+哈希+入账才是。
批量改为 **每批 ≤5**；每条记录含 run_id / sample_id / agent_role / prompt_hash / context_hash / created_at / payload / payload_hash / write_status / readback_status。

## §8 完成闸门
CHAIN 20/20 = **20/20**（最长连续通过 20）· DUPLICATE_ACCEPTED = **0** · SILENT_DROP = **0** · CORRUPTED_PAYLOAD = **0**
COMPLETION_GATE = **PASS**

## §9 故障注入（8/8 检出）
{"empty_response": true, "malformed_response": true, "write_failure": true, "partial_write": true, "duplicate_response": true, "timeout": true, "retry": true, "late_response": true}
空响应 / 畸形 / 写失败 / 部分写 / 重复 / 超时 / 重试 / 迟到 —— 全部被检出、被记录，且未污染结果（只有合法的那条被 ACCEPTED）。

## §10 Replay / 确定性
同输入 → payload_hash 复现 = True · schema_result 复现 = True · 重复写入幂等 = True

## 账本
sha256 链 = **True** · 条目 **71** · 唯一 ACCEPTED **27** · 重复 ACCEPTED **0**

## 隔离与安全
R3 immutability = True · R4 = True · R5 = True
V1/V2/V3 ISOLATION = PASS · ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0 / FORWARD=OFF / SHADOW=OFF / LIVE=OFF · BOUNDARY_VIOLATION=0 · MT5_CALLS=0

## 测试
tests = 15/0（共 15）详见 tests/TEST_RESULTS.json

## 结论
**持久化链路已修复且可验证**：父进程权威落盘、原子写、回读、哈希、链式账本、故障全检出。
本次修复**不改变任何预测结论**（R3 = UNSUPPORTED 不变）；交易保持关闭。
GIT_HEAD = 9e8c4f94089c5700ade3b08ec528e14d83821b2e · CHANGED_FILES(本任务) = 1
