# PUBLISH_MANIFEST.md

> 生成时间（UTC）：2026-09-19T01:54:01.212195+00:00
> 生成方式：**只读审计**（扫描工作树 + Git 状态 + Git 历史）。
> 本文件仅用于人工审计；**未 push、未改历史、未改代码、未启动交易**。

## 1. 发布目标
```text
Repository:        https://github.com/296558410-wq/-.git  (repo name = '-' ; 已确认)
Remote:            未添加（本阶段不 add remote / 不 push）
Visibility:        Private
Target branch:     main
Strategy:          A — 干净快照（不携带本地 249 提交历史）
Scope:             V1 / V2 / V3 / Hermes 相关（代码/配置模板/研究/审计/文档/任务记录）
Local history:     保留不动（不 rewrite / 不 delete）
```

## 2. 候选文件统计

- 范围内文件（扫描总数）：**27808**
- **发布候选：612 个 / 3.63 MB**
- 排除（运行态/敏感/生成物）：**27196** 个

| 类别 | 文件数 | 大小 (MB) |
|---|---:|---:|
| Audit | 51 | 0.27 |
| Configuration templates | 2 | 0.00 |
| Documentation | 51 | 0.87 |
| Hermes | 141 | 0.60 |
| Research report | 43 | 0.33 |
| V1 | 104 | 0.36 |
| V2 | 198 | 1.05 |
| V3 | 22 | 0.14 |

按下层目录细分：

- **Audit**：`reports/phase9_data_audit.md`×1, `reports/r1_prime/g1_implementation_audit.md`×1, `reports/r1_prime/taxonomy`×1, `research/hermes/cand01_gvz`×3, `research/hermes/crawler`×2, `research/hermes/reports`×5, `research/hermes/v1_audit`×38
- **Configuration templates**：`configs/environment_requirements.txt`×1, `configs/requirements-lock.txt`×1
- **Documentation**：`PROJECT_COLLABORATION.md`×1, `README.md`×1, `architecture/compute_architecture.md`×1, `architecture/data_architecture.md`×1, `architecture/v1_trading_system/00_ARCHITECTURE_MASTER.md`×1, `architecture/v1_trading_system/01_EXECUTION_DATA_GAP.md`×1, `architecture/v1_trading_system/02_EXECUTION_PATHWAY_OANDA.md`×1, `architecture/v1_trading_system/DASHBOARD_v2.png`×1, `architecture/v1_trading_system/DASHBOARD_v3.png`×1, `architecture/v1_trading_system/DASHBOARD_v4.png`×1, `architecture/v1_trading_system/STATUS.md`×1, `architecture/v1_trading_system/SYSTEM_ARCHITECTURE.html`×1, `architecture/v1_trading_system/SYSTEM_ARCHITECTURE.png`×1, `docs/architecture.md`×1, `docs/software_stack.md`×1, `reports/cpu_gpu_benchmark.md`×1, `reports/environment_baseline.md`×1, `reports/environment_health.md`×1, `reports/gpu_benchmark.md`×1, `reports/hft_edge_map/HFT_EDGE_MAP_HANDOFF.md`×1, `reports/hft_edge_map/HFT_RESEARCH_ROADMAP.md`×1, `reports/hft_edge_map/HFT_SYSTEM_BLUEPRINT.md`×1, `reports/hft_edge_map/XAUUSD_HFT_EDGE_MAP.md`×1, `reports/machine_baseline.md`×1, `reports/market_representation/MARKET_REPRESENTATION_FRAMEWORK.md`×1, `reports/market_representation/MARKET_REPRESENTATION_PHASE2_RESULTS.md`×1, `reports/overnight_report.md`×1, `reports/phase1_research_engine_report.md`×1, `reports/phase2_alpha_discovery_report.md`×1, `reports/phase3_autonomous_alpha_research_report.md`×1, `reports/phase3_crossperiod.md`×1, `reports/phase4_microstructure_execution_alpha_report.md`×1, `reports/phase5_execution_alpha_report.md`×1, `reports/phase6_autopsy_sample.md`×1, `reports/phase6_xauusd_market_understanding_report.md`×1, `reports/phase7_market_drivers_report.md`×1, `reports/phase8_candlestick_report.md`×1, `reports/phase8_framework_candlestick.md`×1, `reports/phase9_framework.md`×1, `reports/phase9_gate.md`×1, `reports/phase9_preregistration.md`×1, `reports/pipeline_report.md`×1, `reports/r1_prime/final_preregistration.md`×1, `reports/r1_prime/g1_fvt_replay_comparison.md`×1, `reports/r1_prime/g1_registry_drift_evidence.md`×1, `reports/r1_prime/g1_state_machine_conformance.md`×1, `reports/r1_prime/g1_tsleak_truncation_evidence.md`×1, `reports/r1_prime/gate_report.md`×1, `reports/round1_summary.md`×1, `reports/rq_h1/RQ-H1_DISCOVERY_REPORT.md`×1, `reports/xauusd_baseline.md`×1
- **Hermes**：`research/hermes/autonomous_hunt`×5, `research/hermes/benchmarks`×1, `research/hermes/cand01_gvz`×15, `research/hermes/crawler`×14, `research/hermes/cron_backup_20260912.json`×1, `research/hermes/cron_backup_20260913_v2_broker.json`×1, `research/hermes/data_hunt`×4, `research/hermes/edge_archaeology`×8, `research/hermes/frontier`×4, `research/hermes/global_intelligence`×12, `research/hermes/hft_map_adversarial`×4, `research/hermes/integration`×6, `research/hermes/knowledge_upgrade`×20, `research/hermes/memory`×11, `research/hermes/reports`×25, `research/hermes/trading_craft`×9, `research/hermes/trading_hours.py`×1
- **Research report**：`reports/env_baseline_info.json`×1, `reports/env_smoke_backtest.json`×1, `reports/env_smoke_deepseek.json`×1, `reports/env_smoke_duka.json`×1, `reports/env_smoke_git.json`×1, `reports/env_smoke_gpu_bench.json`×1, `reports/env_smoke_ml.json`×1, `reports/env_smoke_mt5.json`×1, `reports/env_smoke_results.json`×1, `reports/env_smoke_stats.json`×1, `reports/env_smoke_summary.txt`×1, `reports/env_smoke_tick.json`×1, `reports/env_smoke_ts_leak.json`×1, `reports/hft_edge_map/ACCESSIBILITY_MATRIX.yaml`×1, `reports/hft_edge_map/EVIDENCE_CONVERGENCE.yaml`×1, `reports/hft_edge_map/HFT_RESEARCH_PORTFOLIO.yaml`×1, `reports/hft_edge_map/LOCAL_RESEARCH_MAPPING.yaml`×1, `reports/hft_edge_map/MECHANISM_UNIVERSE.yaml`×1, `reports/hft_edge_map/OBSERVABILITY_MATRIX.yaml`×1, `reports/hft_edge_map/SYSTEM_BOTTLENECKS.yaml`×1, `reports/hft_edge_map/TOP_RESEARCH_QUESTIONS.yaml`×1, `reports/market_representation/REPRESENTATION_REGISTRY.yaml`×1, `reports/market_representation/phase2_evidence.json`×1, `reports/phase3_spread_info.json`×1, `reports/phase4_ic_decay_matrix.csv`×1, `reports/phase4_stage2_frozen.json`×1, `reports/phase4_stage3_session.json`×1, `reports/phase4_stage4_tradability.json`×1, `reports/phase4_stage5_nonoverlap.json`×1, `reports/phase5_liquidity_timing.json`×1, `reports/phase5_voltarget.json`×1, `reports/phase6_transition_pred.json`×1, `reports/phase7_drivers_evidence.json`×1, `reports/phase8_candles_evidence.json`×1, `reports/r1_prime/autopsy`×1, `reports/r1_prime/discovery`×1, `reports/r1_prime/g1_evidence`×1, `reports/r1_prime/taxonomy`×2, `reports/round1_baselines.json`×1, `reports/round1_details.json`×1, `reports/round1_duka2023_details.json`×1, `reports/rq_h1/RQ-H1_DISCOVERY_EVIDENCE.json`×1
- **V1**：`research/hermes/trader_v1`×97, `research/hermes/trader_v1_panel`×7
- **V2**：`research/hermes/trader_v2`×198
- **V3**：`research/hermes/trader_v3`×22

## 3. 准备发布文件（完整相对路径）

> 均为相对 `C:\AIQuant` 的路径。SHA256 见第 10 节抽样（全量哈希在生成时已计算，如需可另出清单）。

### Audit（51）
```text
reports/phase9_data_audit.md
reports/r1_prime/g1_implementation_audit.md
reports/r1_prime/taxonomy/label_audit_evidence.json
research/hermes/cand01_gvz/R1_VALUE_AUDIT.yaml
research/hermes/cand01_gvz/REDUNDANCY_AUDIT.yaml
research/hermes/cand01_gvz/REGIME_AUDIT.yaml
research/hermes/crawler/repository_audit.yaml
research/hermes/crawler/stress_test/repository_deep_audit.yaml
research/hermes/reports/HERMES-03_SELF_AUDIT.md
research/hermes/reports/HERMES_02_SELF_AUDIT.md
research/hermes/reports/HERMES_ENVIRONMENT_AUDIT.md
research/hermes/reports/HERMES_LOCAL_MODEL_AUDIT.md
research/hermes/reports/HERMES_SELF_AUDIT.md
research/hermes/v1_audit/V1_ANALYSIS_ELIGIBILITY.json
research/hermes/v1_audit/V1_AUDIT_DATA_REGISTRY.json
research/hermes/v1_audit/V1_AUDIT_EXPERIMENT_REGISTRY.json
research/hermes/v1_audit/V1_AUDIT_PHASE_A_REPORT.md
research/hermes/v1_audit/V1_AUDIT_PHASE_B_REPORT.md
research/hermes/v1_audit/V1_AUDIT_PHASE_B_SUMMARY.json
research/hermes/v1_audit/V1_AUDIT_PHASE_C_SHA256.json
research/hermes/v1_audit/V1_AUDIT_PHASE_D_SHA256.json
research/hermes/v1_audit/V1_AUDIT_PROTOCOL.md
research/hermes/v1_audit/V1_BASELINE_ANALYSIS.json
research/hermes/v1_audit/V1_COST_ANALYSIS.json
research/hermes/v1_audit/V1_COVERAGE_MATRIX.csv
research/hermes/v1_audit/V1_DIRECTIONAL_PERIODS.json
research/hermes/v1_audit/V1_EARLY_RECENT_PATH_COMPARISON.json
research/hermes/v1_audit/V1_ENTRY_VS_EXIT_EVIDENCE.json
research/hermes/v1_audit/V1_FULL_LIFECYCLE_AUDIT_REPORT.md
research/hermes/v1_audit/V1_FULL_LIFECYCLE_SHA256.json
research/hermes/v1_audit/V1_INFORMATION_BOUNDARY.json
research/hermes/v1_audit/V1_LIFECYCLE_DATA_REGISTRY.json
research/hermes/v1_audit/V1_LIFECYCLE_TIMELINE.json
research/hermes/v1_audit/V1_LOSS_STREAK.json
research/hermes/v1_audit/V1_LOSS_TRADE_AUTOPSY.json
research/hermes/v1_audit/V1_MARKET_REGIME.json
research/hermes/v1_audit/V1_OUTCOME_ANALYSIS.json
research/hermes/v1_audit/V1_PHASE_D_REPORT.md
research/hermes/v1_audit/V1_PNL_SERIES.json
research/hermes/v1_audit/V1_RECENT_3DAY_AUTOPSY.json
research/hermes/v1_audit/V1_TICK_QUALITY.json
research/hermes/v1_audit/V1_TRADE_AUTOPSY_REPORT.md
research/hermes/v1_audit/V1_TRADE_AUTOPSY_SHA256.json
research/hermes/v1_audit/V1_TRADE_RECONSTRUCTION_STATUS.json
research/hermes/v1_audit/V1_V2_OVERNIGHT_HEALTH_CHECK.md
research/hermes/v1_audit/tools/v1_audit_autopsy.py
research/hermes/v1_audit/tools/v1_audit_lifecycle.py
research/hermes/v1_audit/tools/v1_audit_phaseA.py
research/hermes/v1_audit/tools/v1_audit_phaseB.py
research/hermes/v1_audit/tools/v1_audit_phaseC.py
research/hermes/v1_audit/tools/v1_audit_phaseD.py
```

### Configuration templates（2）
```text
configs/environment_requirements.txt
configs/requirements-lock.txt
```

### Documentation（51）
```text
PROJECT_COLLABORATION.md
README.md
architecture/compute_architecture.md
architecture/data_architecture.md
architecture/v1_trading_system/00_ARCHITECTURE_MASTER.md
architecture/v1_trading_system/01_EXECUTION_DATA_GAP.md
architecture/v1_trading_system/02_EXECUTION_PATHWAY_OANDA.md
architecture/v1_trading_system/DASHBOARD_v2.png
architecture/v1_trading_system/DASHBOARD_v3.png
architecture/v1_trading_system/DASHBOARD_v4.png
architecture/v1_trading_system/STATUS.md
architecture/v1_trading_system/SYSTEM_ARCHITECTURE.html
architecture/v1_trading_system/SYSTEM_ARCHITECTURE.png
docs/architecture.md
docs/software_stack.md
reports/cpu_gpu_benchmark.md
reports/environment_baseline.md
reports/environment_health.md
reports/gpu_benchmark.md
reports/hft_edge_map/HFT_EDGE_MAP_HANDOFF.md
reports/hft_edge_map/HFT_RESEARCH_ROADMAP.md
reports/hft_edge_map/HFT_SYSTEM_BLUEPRINT.md
reports/hft_edge_map/XAUUSD_HFT_EDGE_MAP.md
reports/machine_baseline.md
reports/market_representation/MARKET_REPRESENTATION_FRAMEWORK.md
reports/market_representation/MARKET_REPRESENTATION_PHASE2_RESULTS.md
reports/overnight_report.md
reports/phase1_research_engine_report.md
reports/phase2_alpha_discovery_report.md
reports/phase3_autonomous_alpha_research_report.md
reports/phase3_crossperiod.md
reports/phase4_microstructure_execution_alpha_report.md
reports/phase5_execution_alpha_report.md
reports/phase6_autopsy_sample.md
reports/phase6_xauusd_market_understanding_report.md
reports/phase7_market_drivers_report.md
reports/phase8_candlestick_report.md
reports/phase8_framework_candlestick.md
reports/phase9_framework.md
reports/phase9_gate.md
reports/phase9_preregistration.md
reports/pipeline_report.md
reports/r1_prime/final_preregistration.md
reports/r1_prime/g1_fvt_replay_comparison.md
reports/r1_prime/g1_registry_drift_evidence.md
reports/r1_prime/g1_state_machine_conformance.md
reports/r1_prime/g1_tsleak_truncation_evidence.md
reports/r1_prime/gate_report.md
reports/round1_summary.md
reports/rq_h1/RQ-H1_DISCOVERY_REPORT.md
reports/xauusd_baseline.md
```

### Hermes（141）
```text
research/hermes/autonomous_hunt/HERMES-07_AUTONOMOUS_HUNT_REPORT.md
research/hermes/autonomous_hunt/HERMES-07_HANDOFF.md
research/hermes/autonomous_hunt/hunt_decision_log.yaml
research/hermes/autonomous_hunt/hunt_registry.yaml
research/hermes/autonomous_hunt/research_value_assessment.yaml
research/hermes/benchmarks/bench_ollama.py
research/hermes/cand01_gvz/CAND01_REPORT.md
research/hermes/cand01_gvz/DATA_DEFINITION.yaml
research/hermes/cand01_gvz/DECISION.yaml
research/hermes/cand01_gvz/DIRECTIONAL_PROBE.yaml
research/hermes/cand01_gvz/ECONOMIC_VALUE.yaml
research/hermes/cand01_gvz/HERMES_ESCALATION.yaml
research/hermes/cand01_gvz/KILL_TESTS.yaml
research/hermes/cand01_gvz/OPENCLAW_HANDOFF.md
research/hermes/cand01_gvz/PREREGISTRATION.yaml
research/hermes/cand01_gvz/PRIMARY_RESULTS.yaml
research/hermes/cand01_gvz/RESULTS.json
research/hermes/cand01_gvz/RESULTS_SUPP.json
research/hermes/cand01_gvz/manifest_cand01.yaml
research/hermes/cand01_gvz/run_cand01.py
research/hermes/cand01_gvz/run_cand01_supp.py
research/hermes/crawler/HERMES-05_CRAWLER_MISSION.md
research/hermes/crawler/HERMES-05_HANDOFF.md
research/hermes/crawler/access_restrictions.yaml
research/hermes/crawler/counter_evidence.yaml
research/hermes/crawler/crawler_architecture.md
research/hermes/crawler/crawler_benchmark.yaml
research/hermes/crawler/global_deep_crawl_report.md
research/hermes/crawler/source_graph.yaml
research/hermes/crawler/stress_test/HERMES-06_HANDOFF.md
research/hermes/crawler/stress_test/HERMES-06_STRESS_TEST_REPORT.md
research/hermes/crawler/stress_test/crawler_capability_score.yaml
research/hermes/crawler/stress_test/depth_results.yaml
research/hermes/crawler/stress_test/route_change_log.yaml
research/hermes/crawler/stress_test/target_registry.yaml
research/hermes/cron_backup_20260912.json
research/hermes/cron_backup_20260913_v2_broker.json
research/hermes/data_hunt/DATA_SOURCE_REGISTRY.yaml
research/hermes/data_hunt/DATA_UNLOCK_PRIORITY.yaml
research/hermes/data_hunt/HERMES-12_REPORT.md
research/hermes/data_hunt/OPENCLAW_HANDOFF.md
research/hermes/edge_archaeology/HERMES-13_REPORT.md
research/hermes/edge_archaeology/KNOWN_UNKNOWN_MAP.yaml
research/hermes/edge_archaeology/NOVEL_MECHANISMS.yaml
research/hermes/edge_archaeology/OPENCLAW_CANDIDATES.yaml
research/hermes/edge_archaeology/OPENCLAW_HANDOFF.md
research/hermes/edge_archaeology/cand01/HERMES_CAND01_BOUNDARY_REPORT.md
research/hermes/edge_archaeology/cand01/HERMES_CAND01_EVIDENCE.yaml
research/hermes/edge_archaeology/cand01/OPENCLAW_HANDOFF.md
research/hermes/frontier/CROSS_REGIME_CANDIDATES.yaml
research/hermes/frontier/CROSS_REGIME_EVIDENCE.yaml
research/hermes/frontier/CROSS_REGIME_MONEY_REPORT.md
research/hermes/frontier/OPENCLAW_HANDOFF.md
research/hermes/global_intelligence/accessibility_matrix.yaml
research/hermes/global_intelligence/contradiction_updates.yaml
research/hermes/global_intelligence/contradictions.yaml
research/hermes/global_intelligence/failure_updates.yaml
research/hermes/global_intelligence/failures.yaml
research/hermes/global_intelligence/mechanisms.yaml
research/hermes/global_intelligence/mechanisms_deep.yaml
research/hermes/global_intelligence/research_lineage.yaml
research/hermes/global_intelligence/research_lineage_update.yaml
research/hermes/global_intelligence/research_queue.yaml
research/hermes/global_intelligence/research_queue_update.yaml
research/hermes/global_intelligence/sources.yaml
research/hermes/hft_map_adversarial/BELIEF_REGISTER.yaml
research/hermes/hft_map_adversarial/HERMES-11_REPORT.md
research/hermes/hft_map_adversarial/OPENCLAW_HANDOFF.md
research/hermes/hft_map_adversarial/RECLASSIFICATIONS.yaml
research/hermes/integration/HERMES-09_INTEGRATION_REPORT.md
research/hermes/integration/OPENCLAW_HANDOFF.md
research/hermes/integration/decision_benchmark.yaml
research/hermes/integration/decision_errors.yaml
research/hermes/integration/research_decision_engine.yaml
research/hermes/integration/semantic_duplication.yaml
research/hermes/knowledge_upgrade/00_ROUTE.md
research/hermes/knowledge_upgrade/01_L1_microstructure.md
research/hermes/knowledge_upgrade/02_L2_execution.md
research/hermes/knowledge_upgrade/03_L3_behavioral.md
research/hermes/knowledge_upgrade/04_L4_conditional_opportunity.md
research/hermes/knowledge_upgrade/05_gold_structure_hft.md
research/hermes/knowledge_upgrade/06_adversarial_sweep.md
research/hermes/knowledge_upgrade/07_CORE_CLAIMS.yaml
research/hermes/knowledge_upgrade/08_CORRECTIONS.md
research/hermes/knowledge_upgrade/09_UNKNOWNS.md
research/hermes/knowledge_upgrade/10_TOP10_XAUUSD_MECHANISMS.md
research/hermes/knowledge_upgrade/11_DATA_WATCHLIST.md
research/hermes/knowledge_upgrade/12_NOT_TRADEABLE.md
research/hermes/knowledge_upgrade/13_HERMES_KNOWLEDGE_UPGRADE_REPORT.md
research/hermes/knowledge_upgrade/raw/S1-MS_raw.md
research/hermes/knowledge_upgrade/raw/S2-EX_raw.md
research/hermes/knowledge_upgrade/raw/S3-BH_raw.md
research/hermes/knowledge_upgrade/raw/S4-CO_raw.md
research/hermes/knowledge_upgrade/raw/S5-GX_raw.md
research/hermes/knowledge_upgrade/raw/S6-AD_raw.md
research/hermes/memory/ACTIVE_DUTY_20260905.md
research/hermes/memory/ACTIVE_DUTY_20260907.md
research/hermes/memory/HERMES-08_HANDOFF.md
research/hermes/memory/HERMES-08_MEMORY_REPORT.md
research/hermes/memory/HERMES-10_HFT_HANDOFF.md
research/hermes/memory/claim_registry.yaml
research/hermes/memory/contradiction_registry.yaml
research/hermes/memory/dead_end_index.yaml
research/hermes/memory/failure_memory.yaml
research/hermes/memory/knowledge_graph.yaml
research/hermes/memory/research_query_api.md
research/hermes/reports/HERMES-04_GLOBAL_DEEP_SCAN.md
research/hermes/reports/HERMES_ADVERSARIAL_INTELLIGENCE.md
research/hermes/reports/HERMES_CONTRADICTION_REPORT.md
research/hermes/reports/HERMES_FAILURE_LIBRARY.md
research/hermes/reports/HERMES_FINAL_MODEL_DECISION.md
research/hermes/reports/HERMES_GLOBAL_RESEARCH_ARCHITECTURE.md
research/hermes/reports/HERMES_GLOBAL_SCAN_REPORT.md
research/hermes/reports/HERMES_LOCAL_DEPLOYMENT.md
research/hermes/reports/HERMES_MECHANISM_LIBRARY_REPORT.md
research/hermes/reports/HERMES_MODEL_BENCHMARK.md
research/hermes/reports/HERMES_MODEL_CANDIDATE_REGISTRY.yaml
research/hermes/reports/HERMES_MODEL_COMPARISON.md
research/hermes/reports/HERMES_MODEL_GLOBAL_SCAN.md
research/hermes/reports/HERMES_MODEL_HARDWARE_FIT.md
research/hermes/reports/HERMES_MODEL_SECURITY_REVIEW.md
research/hermes/reports/HERMES_OPENCLAW_HANDOFF.md
research/hermes/reports/HERMES_OPERATING_PROTOCOLS.md
research/hermes/reports/HERMES_QUANT_BENCHMARK.md
research/hermes/reports/HERMES_RESEARCH_CONSTITUTION.md
research/hermes/reports/HERMES_SOURCE_MAP.md
research/hermes/reports/HERMES_VALUE_DISCOVERY_REPORT.md
research/hermes/reports/HERMES_XAUUSD_KNOWLEDGE_MAP.md
research/hermes/reports/HERMES_XAUUSD_RESEARCH_QUEUE.md
research/hermes/reports/OPENCLAW_HANDOFF.md
research/hermes/reports/V3_UNIFIED_PLAN_20260917.md
research/hermes/trading_craft/HERMES_TRADING_CRAFT_REPORT.md
research/hermes/trading_craft/OPENCLAW_HANDOFF.md
research/hermes/trading_craft/TRADING_CRAFT_EVIDENCE.yaml
research/hermes/trading_craft/ledger/ACCESS_LOG.yaml
research/hermes/trading_craft/ledger/CLAIM_LEDGER.yaml
research/hermes/trading_craft/ledger/EVIDENCE_LEDGER.yaml
research/hermes/trading_craft/ledger/LEDGER_SUMMARY.md
research/hermes/trading_craft/ledger/NEGATIVE_EVIDENCE.yaml
research/hermes/trading_craft/ledger/SOURCE_LEDGER.yaml
research/hermes/trading_hours.py
```

### Research report（43）
```text
reports/env_baseline_info.json
reports/env_smoke_backtest.json
reports/env_smoke_deepseek.json
reports/env_smoke_duka.json
reports/env_smoke_git.json
reports/env_smoke_gpu_bench.json
reports/env_smoke_ml.json
reports/env_smoke_mt5.json
reports/env_smoke_results.json
reports/env_smoke_stats.json
reports/env_smoke_summary.txt
reports/env_smoke_tick.json
reports/env_smoke_ts_leak.json
reports/hft_edge_map/ACCESSIBILITY_MATRIX.yaml
reports/hft_edge_map/EVIDENCE_CONVERGENCE.yaml
reports/hft_edge_map/HFT_RESEARCH_PORTFOLIO.yaml
reports/hft_edge_map/LOCAL_RESEARCH_MAPPING.yaml
reports/hft_edge_map/MECHANISM_UNIVERSE.yaml
reports/hft_edge_map/OBSERVABILITY_MATRIX.yaml
reports/hft_edge_map/SYSTEM_BOTTLENECKS.yaml
reports/hft_edge_map/TOP_RESEARCH_QUESTIONS.yaml
reports/market_representation/REPRESENTATION_REGISTRY.yaml
reports/market_representation/phase2_evidence.json
reports/phase3_spread_info.json
reports/phase4_ic_decay_matrix.csv
reports/phase4_stage2_frozen.json
reports/phase4_stage3_session.json
reports/phase4_stage4_tradability.json
reports/phase4_stage5_nonoverlap.json
reports/phase5_liquidity_timing.json
reports/phase5_voltarget.json
reports/phase6_transition_pred.json
reports/phase7_drivers_evidence.json
reports/phase8_candles_evidence.json
reports/r1_prime/autopsy/autopsy_evidence.json
reports/r1_prime/discovery/discovery_evidence.json
reports/r1_prime/g1_evidence/g1_evidence.json
reports/r1_prime/taxonomy/portability_evidence.json
reports/r1_prime/taxonomy/taxonomy_evidence.json
reports/round1_baselines.json
reports/round1_details.json
reports/round1_duka2023_details.json
reports/rq_h1/RQ-H1_DISCOVERY_EVIDENCE.json
```

### V1（104）
```text
research/hermes/trader_v1/00_TRADER_PROTOCOL.md
research/hermes/trader_v1/AUDIT_REPORT_20260907.md
research/hermes/trader_v1/DESIGN_V11.md
research/hermes/trader_v1/V12_FINAL_REPORT.md
research/hermes/trader_v1/broker_mt5_demo.py
research/hermes/trader_v1/candlestick.py
research/hermes/trader_v1/contracts/DECISION_CONTRACT.yaml
research/hermes/trader_v1/contracts/MEMORY_CONTRACT.yaml
research/hermes/trader_v1/contracts/REVIEW_CONTRACT.yaml
research/hermes/trader_v1/contracts/TRADE_PLAN_CONTRACT.yaml
research/hermes/trader_v1/contracts/TRIGGER_CONTRACT.yaml
research/hermes/trader_v1/engine.py
research/hermes/trader_v1/invariants.py
research/hermes/trader_v1/ledger.py
research/hermes/trader_v1/memory/reviews/RV-TP-20260907T2355Z-20260908042648.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T0532Z-20260908060402.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T063856-20260908080419.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T092012-20260908094850.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T100753-20260908103425.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T105022-20260908111826.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T113739-20260908121823.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T131419-20260908134842.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T140456-20260908154821.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T142140-20260908150341.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T152001-20260908153345.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T163554-20260908183329.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T185008-20260908193340.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260908T233624-20260909000439.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260909T002041-20260909014847.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260909T0402Z-20260909053318.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260909T0547Z-20260909134621.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260909T1532Z-20260909170510.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260909T1547Z-20260909190814.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260909T2202Z-20260910000322.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260910T0202Z-20260910044741.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260910T0502Z-20260910053241.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260910T0732Z-20260910081743.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260910T0917Z-20260910101929.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260910T1102ZB-20260910120409.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260910T133408-20260910180332.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260910T1902Z-20260911010534.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260911T0132Z-20260911033417.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260911T0432Z-20260911055102.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260911T0547Zb-20260911075001.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260911T0802Z-20260911110441.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260911T1117Z-20260911121901.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260911T1302Z-20260911140431.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260911T1432Z-20260911163321.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260911T1632Z-20260911200314.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260913T2217Z-20260914000316.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260914T001808-20260914011904.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260914T0117Z-20260914030250.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260914T031902-20260914074855.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260914T090414-20260914124908.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260914T1247Z-20260914131750.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260914T1447Z-20260914161822.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260914T1502Zb-20260914164835.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260914T1517Z-20260914153353.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0002Z-20260915020338.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0032Z-20260915012010.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0217Z-20260915054755.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0632Z-20260915074754.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0917Z-20260915130557.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260915T1317Z-20260915181811.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260915T230323-20260916023330.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260916T0302Z-20260916131823.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260916T1417Z-20260916154733.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260916T1917Z-20260917001855.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260917T0017Z-20260917072121.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260917T0847Z-20260917105028.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260917T1047Z-20260917123559.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260917T1302Z-20260917203420.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260917T2232Z-20260918010335.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260918T0347Z-20260918060358.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260918T0647Z-20260918094904.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260918T1102Z-20260918123630.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260918T1302Z-20260918140348.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260918T1417Z-20260918161910.json
research/hermes/trader_v1/memory/reviews/RV-TP-20260918T1747Z-20260918184903.json
research/hermes/trader_v1/metrics.py
research/hermes/trader_v1/opportunity.py
research/hermes/trader_v1/position.py
research/hermes/trader_v1/position_decision.py
research/hermes/trader_v1/replay_study.py
research/hermes/trader_v1/review.py
research/hermes/trader_v1/state_package.py
research/hermes/trader_v1/stop_authority.py
research/hermes/trader_v1/tests/test_faults.py
research/hermes/trader_v1/tests/test_integration.py
research/hermes/trader_v1/tests/test_l0_idempotency.py
research/hermes/trader_v1/tests/test_l1_position.py
research/hermes/trader_v1/tests/test_l2_decision.py
research/hermes/trader_v1/tests/test_l3_candles.py
research/hermes/trader_v1/tests/test_l3_invariants.py
research/hermes/trader_v1/trader_core.py
research/hermes/trader_v1/trader_summary.txt
research/hermes/trader_v1/trigger.py
research/hermes/trader_v1_panel/README.md
research/hermes/trader_v1_panel/datasource.py
research/hermes/trader_v1_panel/run_v1_panel.cmd
research/hermes/trader_v1_panel/server.py
research/hermes/trader_v1_panel/static/app.js
research/hermes/trader_v1_panel/static/index.html
research/hermes/trader_v1_panel/static/style.css
```

### V2（198）
```text
research/hermes/trader_v2/.gitignore
research/hermes/trader_v2/README.md
research/hermes/trader_v2/V2_ARCHITECTURE.md
research/hermes/trader_v2/V2_PHASE1_PLAN.md
research/hermes/trader_v2/agents/macro_global/agent2.py
research/hermes/trader_v2/agents/macro_global/event_trigger.py
research/hermes/trader_v2/agents/macro_global/evidence.py
research/hermes/trader_v2/agents/macro_global/release_registry.py
research/hermes/trader_v2/agents/macro_global/sources.py
research/hermes/trader_v2/agents/technical/agent1.py
research/hermes/trader_v2/agents/technical/features.py
research/hermes/trader_v2/agents/technical/market_data.py
research/hermes/trader_v2/config/data_router.enabled
research/hermes/trader_v2/config/price_space.json
research/hermes/trader_v2/config/v2_config.json
research/hermes/trader_v2/dashboard/README.md
research/hermes/trader_v2/dashboard/acc_probe.py
research/hermes/trader_v2/dashboard/datasource.py
research/hermes/trader_v2/dashboard/run_v2_dashboard.cmd
research/hermes/trader_v2/dashboard/server.py
research/hermes/trader_v2/dashboard/static/app.js
research/hermes/trader_v2/dashboard/static/index.html
research/hermes/trader_v2/dashboard/static/style.css
research/hermes/trader_v2/dashboard/v2_dashboard_startup.vbs
research/hermes/trader_v2/dashboard/v2_dashboard_supervisor.cmd
research/hermes/trader_v2/data_sources/__init__.py
research/hermes/trader_v2/data_sources/adapters_macro.py
research/hermes/trader_v2/data_sources/adapters_market.py
research/hermes/trader_v2/data_sources/audit.py
research/hermes/trader_v2/data_sources/cache.py
research/hermes/trader_v2/data_sources/health.py
research/hermes/trader_v2/data_sources/local_bars.py
research/hermes/trader_v2/data_sources/mt5_market.py
research/hermes/trader_v2/data_sources/net.py
research/hermes/trader_v2/data_sources/pit_cache.py
research/hermes/trader_v2/data_sources/registry.py
research/hermes/trader_v2/data_sources/router.py
research/hermes/trader_v2/data_sources/validate.py
research/hermes/trader_v2/execution/broker_demo_executor.py
research/hermes/trader_v2/execution/broker_interface.py
research/hermes/trader_v2/execution/broker_validate.py
research/hermes/trader_v2/execution/fxtm_demo_adapter.py
research/hermes/trader_v2/execution/fxtm_demo_calibration.py
research/hermes/trader_v2/execution/fxtm_demo_one_shot.py
research/hermes/trader_v2/execution/hermes_paper_adapter.py
research/hermes/trader_v2/execution/hermes_paper_loop.py
research/hermes/trader_v2/execution/paper_executor.py
research/hermes/trader_v2/execution/price_space.py
research/hermes/trader_v2/hermes/PROMPT.md
research/hermes/trader_v2/hermes/context.py
research/hermes/trader_v2/hermes/discovery.py
research/hermes/trader_v2/hermes/hermes.py
research/hermes/trader_v2/ledger/ledger.py
research/hermes/trader_v2/ledger/migrate_demo_calibration.py
research/hermes/trader_v2/ledger/replay.py
research/hermes/trader_v2/research/AGENT2_AUDIT.md
research/hermes/trader_v2/research/AGENT2_PHASE1_5.md
research/hermes/trader_v2/research/AUDIT_BASELINE_20260915.md
research/hermes/trader_v2/research/BASELINE_AUDIT_20260914.md
research/hermes/trader_v2/research/DATA_HEALTH_REPORT.md
research/hermes/trader_v2/research/DATA_SOURCES_CN.md
research/hermes/trader_v2/research/DATA_SOURCE_MATRIX.md
research/hermes/trader_v2/research/FAILOVER_TEST_REPORT.md
research/hermes/trader_v2/research/FXTM_DEMO_CALIBRATION_PHASE1.md
research/hermes/trader_v2/research/FXTM_DEMO_CALIBRATION_PHASE2.md
research/hermes/trader_v2/research/FXTM_DIRECT_API_INVESTIGATION.md
research/hermes/trader_v2/research/GPU_V2_BENCHMARK.md
research/hermes/trader_v2/research/GPU_V2_INTEGRATION_REPORT.md
research/hermes/trader_v2/research/ISSUE_20260915_replay_block.md
research/hermes/trader_v2/research/ISSUE_20260916_broker_auto_close_block.md
research/hermes/trader_v2/research/ISSUE_GC_SPOT_PRICE_SPACE_MISMATCH.md
research/hermes/trader_v2/research/MODULE_3_PRE_AUDIT.md
research/hermes/trader_v2/research/MODULE_3_REPORT.md
research/hermes/trader_v2/research/MODULE_4_PRE_AUDIT.md
research/hermes/trader_v2/research/MODULE_4_REPORT.md
research/hermes/trader_v2/research/MODULE_5_FINAL_REPORT.md
research/hermes/trader_v2/research/MODULE_5_FRESHNESS_DIAGNOSTIC.md
research/hermes/trader_v2/research/MODULE_5_PRE_AUDIT.md
research/hermes/trader_v2/research/MODULE_6_REPORT.md
research/hermes/trader_v2/research/MT5_MULTI_INSTANCE_AUDIT.md
research/hermes/trader_v2/research/OPPORTUNITY_DEGENERATION_DIAG_20260915.md
research/hermes/trader_v2/research/PIT_VALIDATION_REPORT.md
research/hermes/trader_v2/research/PRICE_SPACE_AUDIT.md
research/hermes/trader_v2/research/PRICE_SPACE_FIX_AUDIT.md
research/hermes/trader_v2/research/PRICE_SPACE_IMPACT_REPORT.md
research/hermes/trader_v2/research/PRICE_SPACE_SHADOW_REPORT.md
research/hermes/trader_v2/research/REGRESSION_REPORT.md
research/hermes/trader_v2/research/SIZING_FIX_20260912.md
research/hermes/trader_v2/research/TRADE_SIZING_REJECT_AUDIT_20260915.md
research/hermes/trader_v2/research/V2_BROKER_DEMO_ENABLE_20260918.md
research/hermes/trader_v2/research/V2_BROKER_PRECHECK_REPORT_20260917.md
research/hermes/trader_v2/research/V2_BROKER_SPEC_20260917.md
research/hermes/trader_v2/research/V2_DASHBOARD_AUDIT_20260917.md
research/hermes/trader_v2/research/V2_DASHBOARD_FULL_CHAIN_AUDIT_20260917.md
research/hermes/trader_v2/research/V2_DASHBOARD_FULL_CHAIN_REPORT_20260917.md
research/hermes/trader_v2/research/V2_DASHBOARD_REBUILD_REPORT_20260917.md
research/hermes/trader_v2/research/V2_DATASOURCE_DOMESTIC_REPORT_20260917.md
research/hermes/trader_v2/research/V2_DECISION_GATE_CONTRACT.md
research/hermes/trader_v2/research/V2_FAILURE_INJECTION_REPORT_20260917.md
research/hermes/trader_v2/research/V2_FRESHNESS_HEALTH_CONTRACT.md
research/hermes/trader_v2/research/V2_FULL_AUDIT_20260917.md
research/hermes/trader_v2/research/V2_G3_DATA_FREEZE_20260917.md
research/hermes/trader_v2/research/V2_G3_EXECUTION_INCIDENT_20260918.md
research/hermes/trader_v2/research/V2_G3_FAIL.md
research/hermes/trader_v2/research/V2_G3_FINAL_SHADOW_REPORT_20260917.md
research/hermes/trader_v2/research/V2_G3_FINAL_SHADOW_REPORT_20260918.md
research/hermes/trader_v2/research/V2_G3_RUN_LINEAGE.md
research/hermes/trader_v2/research/V2_G3_VERDICT.json
research/hermes/trader_v2/research/V2_INSTRUMENT_CONTRACT.md
research/hermes/trader_v2/research/V2_INSTRUMENT_TRUTH_20260917.md
research/hermes/trader_v2/research/V2_LLM_TOKEN_AUDIT_20260917.md
research/hermes/trader_v2/research/V2_LONG_RUN_AUDIT_20260918.md
research/hermes/trader_v2/research/V2_MACRO_PIT_REPORT_20260917.md
research/hermes/trader_v2/research/V2_P0_CORE_REPAIR_REPORT.md
research/hermes/trader_v2/research/V2_P1_REPAIR_REPORT_20260917.md
research/hermes/trader_v2/research/V2_P1_RESIDUAL_REPORT_20260917.md
research/hermes/trader_v2/research/V2_PIT_CONTRACT.md
research/hermes/trader_v2/research/V2_PRICE_SPACE_CONTRACT.md
research/hermes/trader_v2/research/V2_REPLAY_INPUT_SNAPSHOT_REPORT_20260917.md
research/hermes/trader_v2/research/V2_REPLAY_PROVENANCE_REPORT_20260917.md
research/hermes/trader_v2/research/V2_ROUTER_CONTRACT.md
research/hermes/trader_v2/research/V2_RUNTIME_PROCESS_NETWORK_AUDIT_20260918.md
research/hermes/trader_v2/research/V2_RUNTIME_TRUTH_20260917.md
research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_0417.md
research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_0822.md
research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_1237.md
research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_1637.md
research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_2052.md
research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260918_0052.md
research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260918_0507.md
research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260918_0907.md
research/hermes/trader_v2/research/V2_SHADOW_REPORT_20260917.md
research/hermes/trader_v2/research/dashboard_audit/after_app.js
research/hermes/trader_v2/research/dashboard_audit/after_index.html
research/hermes/trader_v2/research/dashboard_audit/before_app.js
research/hermes/trader_v2/research/dashboard_audit/before_index.html
research/hermes/trader_v2/research/dashboard_audit/before_snapshot.json
research/hermes/trader_v2/research_compute/README.md
research/hermes/trader_v2/research_compute/__init__.py
research/hermes/trader_v2/research_compute/_bridge.py
research/hermes/trader_v2/research_compute/benchmark.py
research/hermes/trader_v2/research_compute/chunking.py
research/hermes/trader_v2/research_compute/cpu_backend.py
research/hermes/trader_v2/research_compute/dispatcher.py
research/hermes/trader_v2/research_compute/gpu_backend.py
research/hermes/trader_v2/research_compute/gpu_v2_results.json
research/hermes/trader_v2/research_compute/rng.py
research/hermes/trader_v2/research_compute/validation.py
research/hermes/trader_v2/runtime/explain.py
research/hermes/trader_v2/runtime/replay_inputs.py
research/hermes/trader_v2/runtime/shadow_run.py
research/hermes/trader_v2/runtime/v2_scheduled_cycle.py
research/hermes/trader_v2/tests/test_broker_reconcile.py
research/hermes/trader_v2/tests/test_broker_validate.py
research/hermes/trader_v2/tests/test_dashboard_consistency.py
research/hermes/trader_v2/tests/test_dashboard_fullchain.py
research/hermes/trader_v2/tests/test_data_sources.py
research/hermes/trader_v2/tests/test_demo_calibration_readonly.py
research/hermes/trader_v2/tests/test_dxy_recursion.py
research/hermes/trader_v2/tests/test_event_trigger.py
research/hermes/trader_v2/tests/test_explain.py
research/hermes/trader_v2/tests/test_failure_injection.py
research/hermes/trader_v2/tests/test_forward_gate.py
research/hermes/trader_v2/tests/test_freshness_health.py
research/hermes/trader_v2/tests/test_instrument_contract.py
research/hermes/trader_v2/tests/test_ledger_replay.py
research/hermes/trader_v2/tests/test_llm_independence.py
research/hermes/trader_v2/tests/test_macro_failclosed.py
research/hermes/trader_v2/tests/test_macro_pit.py
research/hermes/trader_v2/tests/test_module4_loop.py
research/hermes/trader_v2/tests/test_module5_paths.py
research/hermes/trader_v2/tests/test_module5_shadow.py
research/hermes/trader_v2/tests/test_module6_broker_demo.py
research/hermes/trader_v2/tests/test_mt5_only_source.py
research/hermes/trader_v2/tests/test_opportunity_engine.py
research/hermes/trader_v2/tests/test_paper_execution.py
research/hermes/trader_v2/tests/test_paper_final_validation.py
research/hermes/trader_v2/tests/test_pit_cache.py
research/hermes/trader_v2/tests/test_pit_integrity.py
research/hermes/trader_v2/tests/test_price_space_audit.py
research/hermes/trader_v2/tests/test_price_space_conversion.py
research/hermes/trader_v2/tests/test_replay_snapshot.py
research/hermes/trader_v2/tests/test_research_compute.py
research/hermes/trader_v2/tests/test_router_contract.py
research/hermes/trader_v2/tests/test_sizing_floor.py
research/hermes/trader_v2/tests/test_v2_repair.py
research/hermes/trader_v2/tools/broker_spec_probe.py
research/hermes/trader_v2/tools/data_hardening_evidence.py
research/hermes/trader_v2/tools/g3_final_report.py
research/hermes/trader_v2/tools/g3_freeze.py
research/hermes/trader_v2/tools/price_space_audit.py
research/hermes/trader_v2/tools/price_space_impact.py
research/hermes/trader_v2/tools/price_space_validate_run.py
research/hermes/trader_v2/tools/run_v2_tests.py
research/hermes/trader_v2/tools/runtime_audit.py
research/hermes/trader_v2/tools/shadow_guardian.py
research/hermes/trader_v2/tools/source_connectivity_matrix.py
research/hermes/trader_v2/tools/v2_observer.py
```

### V3（22）
```text
research/hermes/trader_v3/V3_ADVERSARIAL_AUDIT.md
research/hermes/trader_v3/V3_ALPHA_MAP.md
research/hermes/trader_v3/V3_MULTIPLE_TESTING_LEDGER.yaml
research/hermes/trader_v3/V3_RESOLUTION_AUDIT.md
research/hermes/trader_v3/config/v3_config.json
research/hermes/trader_v3/mt5/v3_adapter.py
research/hermes/trader_v3/research/V3_C31_FINALIZATION.md
research/hermes/trader_v3/research/V3_CANONICALIZATION_SPEC.md
research/hermes/trader_v3/research/V3_CURRENT_STATE.md
research/hermes/trader_v3/research/V3_DATA_SPEC.md
research/hermes/trader_v3/research/V3_DUKA_COMPARE.md
research/hermes/trader_v3/research/V3_VALID_DAY_AUDIT.md
research/hermes/trader_v3/research/c31_frozen/FINGERPRINT.json
research/hermes/trader_v3/research/c31_frozen/canon_p2_latency_ladder_r31_selftest.csv
research/hermes/trader_v3/research/c31_frozen/canon_p2_summary_r31_selftest.json
research/hermes/trader_v3/tools/v3_acceptance.py
research/hermes/trader_v3/tools/v3_c31_diff.py
research/hermes/trader_v3/tools/v3_canonicalize.py
research/hermes/trader_v3/tools/v3_capability_audit.py
research/hermes/trader_v3/tools/v3_control_init.py
research/hermes/trader_v3/tools/v3_duka_compare.py
research/hermes/trader_v3/tools/v3_valid_day_audit.py
```

## 4. 明确排除文件

### 4.1 规则（用于生成快照时的 .gitignore/拷贝排除）
```text
state/**
run_state/**
**/runs/**
**/snapshots/**
**/observations/**
**/data_cache/**
**/demo_calibration/**
**/logs/**
**/cache/**
**/data/**
*.jsonl
*.log
*.pid
*.tmp
*.parquet
*.env
.env.*
**/credential*
**/*secret*
*_latest.json
evidence_registry*
opportunity_ledger*
macro_releases*
paper_account*
paper_executions*
agent1_latest*
agent2_latest*
```

### 4.2 被 Git tracking 的运行态/敏感具体文件（逐条，必须先排除）

> 共 **149** 个 tracked 运行态文件；另有 **27047** 个未跟踪的运行态/缓存文件（不纳入任何快照）。

```text
configs/mt5_research_readonly.env
reports/phase6_states.json
reports/phase9_gate_evidence.json
research/hermes/crawler/evidence_registry.yaml
research/hermes/trader_v1/run_state/E2E_REPLAY_20260907T1247.md
research/hermes/trader_v1/run_state/bars_cache.json
research/hermes/trader_v1/run_state/candle_latest.json
research/hermes/trader_v1/run_state/decisions/20260907T1146Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1203Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1217Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1232Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1247Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1304Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1317Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1338Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1353Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1402Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1417Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1432Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1447Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1502Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1510Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1517Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1520Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1525Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1532Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1547Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1602Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1617Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1632Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1647Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1702Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1717Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1732Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1755Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1802Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1817Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1832Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1847Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1902Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1917Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1932Z.json
research/hermes/trader_v1/run_state/decisions/20260907T1947Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2002Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2017Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2032Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2047Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2102Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2117Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2132Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2147Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2202Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2217Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2232Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2247Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2302Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2317Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2332Z.json
research/hermes/trader_v1/run_state/decisions/20260907T2355Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0002Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0019Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0032Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0047Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0102Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0117Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0132Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0147Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0203Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0217Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0232Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0247Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0302Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0317Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0332Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0347Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0402Z.json
research/hermes/trader_v1/run_state/decisions/20260908T0417Z.json
research/hermes/trader_v1/run_state/opportunity_frequency_study.txt
research/hermes/trader_v1/run_state/plan_ledger.jsonl
research/hermes/trader_v1/run_state/positions/POS-20260907T2355Z.json
research/hermes/trader_v1/run_state/state_package_latest.json
research/hermes/trader_v1/run_state/statistics.json
research/hermes/trader_v1/run_state/trader_summary.txt
research/hermes/trader_v1/run_state/workflow_history.jsonl
research/hermes/trader_v1/run_state/workflow_latest.json
research/hermes/trader_v2/ledger/hermes_v2_ledger.jsonl
research/hermes/trader_v2/state/V2_G3_FREEZE.json
research/hermes/trader_v2/state/agent1_latest.json
research/hermes/trader_v2/state/agent2_latest.json
research/hermes/trader_v2/state/agent2_trigger.json
research/hermes/trader_v2/state/demo_calibration/phase2/attempt1_rejected.json
research/hermes/trader_v2/state/demo_calibration/phase2/close_request.json
research/hermes/trader_v2/state/demo_calibration/phase2/close_response.json
research/hermes/trader_v2/state/demo_calibration/phase2/order_request.json
research/hermes/trader_v2/state/demo_calibration/phase2/order_response.json
research/hermes/trader_v2/state/demo_calibration/phase2/summary.json
research/hermes/trader_v2/state/demo_calibration/quotes_20260911T125221Z.jsonl
research/hermes/trader_v2/state/demo_calibration/summary_20260911T125221Z.json
research/hermes/trader_v2/state/evidence_registry.jsonl
research/hermes/trader_v2/state/macro_releases.jsonl
research/hermes/trader_v2/state/paper_account.json
research/hermes/trader_v2/state/paper_executions.jsonl
research/hermes/trader_v2/state/snapshots/agent1_20260911T1148Z.json
research/hermes/trader_v2/state/snapshots/agent1_20260911T1149Z.json
research/hermes/trader_v2/state/snapshots/agent2_20260911T1155Z.json
research/hermes/trader_v2/state/snapshots/agent2_20260911T1202Z.json
research/hermes/trader_v2/state/snapshots/agent2_TEST_EVENTTRIGGER.json
research/hermes/trader_v2/state/snapshots/agent2_TEST_PIT_T0.json
research/hermes/trader_v2/state/v2_run_health.json
research/hermes/trader_v2/tests/_tmp/S1_techUp_macroUp_a1.json
research/hermes/trader_v2/tests/_tmp/S1_techUp_macroUp_a2.json
research/hermes/trader_v2/tests/_tmp/S2_techUp_macroDown_a1.json
research/hermes/trader_v2/tests/_tmp/S2_techUp_macroDown_a2.json
research/hermes/trader_v2/tests/_tmp/S3_breakout_pricedIn_a1.json
research/hermes/trader_v2/tests/_tmp/S3_breakout_pricedIn_a2.json
research/hermes/trader_v2/tests/_tmp/S4_geo_noFollow_a1.json
research/hermes/trader_v2/tests/_tmp/S4_geo_noFollow_a2.json
research/hermes/trader_v2/tests/_tmp/S5_divergence_a1.json
research/hermes/trader_v2/tests/_tmp/S5_divergence_a2.json
research/hermes/trader_v2/tests/_tmp/S6_staleData_a1.json
research/hermes/trader_v2/tests/_tmp/S6_staleData_a2.json
research/hermes/trader_v2/tests/_tmp/S7_conflict_a1.json
research/hermes/trader_v2/tests/_tmp/S7_conflict_a2.json
research/hermes/trader_v2/tests/_tmp/S8_badRR_a1.json
research/hermes/trader_v2/tests/_tmp/S8_badRR_a2.json
research/hermes/trader_v2/tests/_tmp/z_a2.json
research/hermes/trader_v3/research/V3_MT5_ENVIRONMENT.md
research/hermes/trader_v3/research/c31_frozen/canon_p2_trades_r31_selftest.csv
research/hermes/trader_v3/state/C31_FROZEN.json
research/hermes/trader_v3/state/V3_ARTIFACT_REGISTRY.json
research/hermes/trader_v3/state/V3_DATA_REGISTRY.json
research/hermes/trader_v3/state/V3_DECISION_LOG.jsonl
research/hermes/trader_v3/state/V3_EXPERIMENT_REGISTRY.json
research/hermes/trader_v3/state/V3_FORWARD_ALLOWED
research/hermes/trader_v3/state/V3_G_AUDIT_LEDGER.jsonl
research/hermes/trader_v3/state/V3_HYPOTHESIS_REGISTRY.json
research/hermes/trader_v3/state/V3_LIVE_ALLOWED
research/hermes/trader_v3/state/V3_MT5_ACCEPTANCE.json
research/hermes/trader_v3/state/V3_MT5_ENVIRONMENT.json
research/hermes/trader_v3/state/V3_ORDER_SEND_ALLOWED
research/hermes/trader_v3/state/V3_PROJECT_STATE.json
research/hermes/trader_v3/state/V3_TASK_REGISTRY.json
research/hermes/trader_v3/state/V3_VALID_DAY_AUDIT.json
research/hermes/v1_audit/V1_MFE_MAE.jsonl
research/hermes/v1_audit/V1_TRADE_AUTOPSY.jsonl
research/hermes/v1_audit/V1_TRADE_MASTER.jsonl
research/hermes/v1_audit/V1_TRADE_REPLAY.jsonl
research/hermes/v1_audit/V1_TRADE_REPLAY_PHASE_B.jsonl
research/hermes/v1_audit/V1_TRADE_REPLAY_PHASE_D.jsonl
```

### 4.3 排除原因分类计数

| 原因前缀 | 文件数 |
|---|---:|
| runtime | 27190 |
| runtime/sensitive | 5 |
| credentials | 1 |

## 5. 敏感信息审计

| 文件 | 风险类型 | 是否进入发布 | 原因 |
|---|---|---|---|
| `research/hermes/trader_v2/research/MODULE_6_REPORT.md` | MT5 登录账号 | ❌ 否（须脱敏后） | 含真实 demo 账号数字，建议替换为占位符 |
| `research/hermes/trader_v2/research/MT5_MULTI_INSTANCE_AUDIT.md` | MT5 登录账号 | ❌ 否（须脱敏后） | 含真实 demo 账号数字，建议替换为占位符 |
| `research/hermes/trader_v1/broker_mt5_demo.py` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v2/execution/fxtm_demo_adapter.py` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v2/execution/fxtm_demo_one_shot.py` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v2/research/FXTM_DEMO_CALIBRATION_PHASE2.md` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v2/research/MODULE_6_REPORT.md` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v2/research/MT5_MULTI_INSTANCE_AUDIT.md` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v2/research/V2_BROKER_DEMO_ENABLE_20260918.md` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v2/research/V2_FULL_AUDIT_20260917.md` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v2/tests/test_broker_reconcile.py` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v2/tests/test_module6_broker_demo.py` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v3/config/v3_config.json` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/trader_v3/mt5/v3_adapter.py` | BROKER_SERVER_METADATA | ⚠️ 建议保留(去标识) | 出现 `ForexTimeFXTM-Demo01`（服务器名，非密码，但属 broker 元数据） |
| `research/hermes/cron_backup_20260912.json`、`cron_backup_20260913_v2_broker.json` | 任务/调度记录 | ⚠️ 待人工确认 | cron 备份，可能含会话键/内部 ID；建议审阅后决定 |
| `.env.mt5_demo` | 凭据（login/password/server 明文） | ❌ 否 | 已确认**未进入候选**，且从未进 Git；默认排除 `.env.*` |
| 运行态 jsonl/state（见 §4.2） | 运行私密数据 | ❌ 否 | 实时账本/证据/账户快照，按 §七 排除 |

## 6. 历史泄漏审计

- MT5 **登录账号**：历史中出现于 2 个文件：`research/hermes/trader_v2/research/MODULE_6_REPORT.md`、`research/hermes/trader_v2/research/MT5_MULTI_INSTANCE_AUDIT.md`
- MT5 **密码**：历史搜索命中文件数 = **0**（0 = 从未入库）
- 本次为**干净快照**：只取当前工作树的候选文件，不携带任何历史 commit。
- **本地历史未修改**（未执行 filter-repo / filter-branch / rebase / reset）。

## 7. 绝对路径审计

- 候选文件中出现 `C:\AIQuant\...` 的文件数：**60**
- 候选文件中出现 `C:\Users\surface\...`（含本机用户名）的文件数：**6**

处置建议（**本阶段仅标记，不修改**）：

| 文件 | 命中数 | 建议 |
|---|---:|---|
| `research/hermes/reports/HERMES_ENVIRONMENT_AUDIT.md` | 9 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v2/research/MODULE_5_FRESHNESS_DIAGNOSTIC.md` | 6 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `docs/software_stack.md` | 5 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v2/dashboard/v2_dashboard_supervisor.cmd` | 5 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v2/research/MT5_MULTI_INSTANCE_AUDIT.md` | 5 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v3/research/V3_DATA_SPEC.md` | 4 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/v1_audit/tools/v1_audit_phaseA.py` | 4 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `docs/architecture.md` | 3 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `reports/environment_baseline.md` | 3 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `reports/machine_baseline.md` | 3 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `reports/overnight_report.md` | 3 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v2/research/V2_RUNTIME_TRUTH_20260917.md` | 3 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v3/mt5/v3_adapter.py` | 3 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/v1_audit/tools/v1_audit_lifecycle.py` | 3 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/v1_audit/tools/v1_audit_phaseB.py` | 3 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/v1_audit/tools/v1_audit_phaseD.py` | 3 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/reports/HERMES_SELF_AUDIT.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/reports/V3_UNIFIED_PLAN_20260917.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v1_panel/README.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v1_panel/run_v1_panel.cmd` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v2/dashboard/README.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v2/dashboard/run_v2_dashboard.cmd` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v2/research/V2_FULL_AUDIT_20260917.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v2/research_compute/README.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v3/V3_ALPHA_MAP.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v3/V3_RESOLUTION_AUDIT.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v3/research/V3_CURRENT_STATE.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v3/tools/v3_control_init.py` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/v1_audit/V1_AUDIT_PHASE_A_REPORT.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/v1_audit/V1_AUDIT_PHASE_B_REPORT.md` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/v1_audit/tools/v1_audit_autopsy.py` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/v1_audit/tools/v1_audit_phaseC.py` | 2 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `README.md` | 1 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `reports/phase1_research_engine_report.md` | 1 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/reports/HERMES_LOCAL_DEPLOYMENT.md` | 1 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/reports/HERMES_LOCAL_MODEL_AUDIT.md` | 1 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/reports/HERMES_OPERATING_PROTOCOLS.md` | 1 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/reports/HERMES_RESEARCH_CONSTITUTION.md` | 1 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v1_panel/datasource.py` | 1 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/trader_v2/V2_ARCHITECTURE.md` | 1 | 改为相对路径/环境变量（`需要脱敏/重构`） |
| `research/hermes/reports/HERMES_ENVIRONMENT_AUDIT.md` | 3 | 含本机用户名 `surface` → `需要脱敏/重构` |
| `reports/environment_baseline.md` | 2 | 含本机用户名 `surface` → `需要脱敏/重构` |
| `reports/machine_baseline.md` | 1 | 含本机用户名 `surface` → `需要脱敏/重构` |
| `research/hermes/reports/HERMES_LOCAL_DEPLOYMENT.md` | 1 | 含本机用户名 `surface` → `需要脱敏/重构` |
| `research/hermes/trader_v3/research/V3_CURRENT_STATE.md` | 1 | 含本机用户名 `surface` → `需要脱敏/重构` |
| `research/hermes/trader_v3/tools/v3_control_init.py` | 1 | 含本机用户名 `surface` → `需要脱敏/重构` |

## 8. `.gitignore` 建议（仅建议，不修改）
```gitignore
# 运行态数据
state/
run_state/
**/runs/
**/snapshots/
**/observations/
**/data_cache/
**/demo_calibration/
*.jsonl
*_latest.json
# 凭据
.env
.env.*
!.env.example
*_credentials*.json
credentials/
secrets/
*.key
*.pem
*.pfx
```

## 9. 风险等级

| 项 | 等级 | 说明 |
|---|---|---|
| 硬编码凭据(密码/token/api_key) | CLEAR | 工作树与历史均未命中 |
| MT5 登录账号（候选内） | HIGH | 2 个候选文件含账号数字，需脱敏 |
| MT5 登录账号（历史） | MEDIUM | 历史含账号但**不进本次快照**；本地历史不动 |
| 运行态私密数据 | HIGH | 27196 个运行态文件已排除（含 16.5MB evidence_registry） |
| 本机绝对路径/用户名 | MEDIUM | 60+6 个候选文件；建议重构 |
| 真实账户信息 | HIGH | 候选含账户/服务器元数据引用，需人工确认；运行态账户快照已排除 |

## 10. 审计辅助（抽样 SHA256 / 大小）

> 关键文档抽样（完整哈希与大小可按需导出）。

| 文件 | 大小(B) | SHA256(前16) |
|---|---:|---|
| `PROJECT_COLLABORATION.md` | 4328 | `8f8595b781c42539` |
| `README.md` | 3391 | `ef8ea093d81085d4` |
| `architecture/compute_architecture.md` | 3634 | `0bde3cab7bb83361` |
| `architecture/data_architecture.md` | 3458 | `0097122c8753eaf3` |
| `architecture/v1_trading_system/00_ARCHITECTURE_MASTER.md` | 18597 | `31da15d9791410f9` |
| `architecture/v1_trading_system/01_EXECUTION_DATA_GAP.md` | 3793 | `d71cf17e06a6ef67` |
| `architecture/v1_trading_system/02_EXECUTION_PATHWAY_OANDA.md` | 4105 | `2d527e5f750ca6d9` |
| `architecture/v1_trading_system/DASHBOARD_v2.png` | 142389 | `114c279d0a1020f4` |
| `architecture/v1_trading_system/DASHBOARD_v3.png` | 161837 | `902af94a4bf925cd` |
| `architecture/v1_trading_system/DASHBOARD_v4.png` | 167363 | `b22a4b77c06e9726` |
| `architecture/v1_trading_system/STATUS.md` | 1932 | `7a9142915e668545` |
| `architecture/v1_trading_system/SYSTEM_ARCHITECTURE.html` | 10082 | `7508ea1aa5f87fce` |
| `architecture/v1_trading_system/SYSTEM_ARCHITECTURE.png` | 130752 | `e1cbef7966b2f2b8` |
| `configs/environment_requirements.txt` | 1316 | `7bbbd1e9d96edb65` |
| `configs/requirements-lock.txt` | 3408 | `0f8240518248e265` |
| `docs/architecture.md` | 4383 | `aa336d6bb6540794` |
| `docs/software_stack.md` | 14541 | `cbc6090f517c45c4` |
| `reports/cpu_gpu_benchmark.md` | 1238 | `6753ac122b365335` |
| `reports/env_baseline_info.json` | 2563 | `98aa892e85c1ad97` |
| `reports/env_smoke_backtest.json` | 1334 | `643dcdca21706abd` |
| `reports/env_smoke_deepseek.json` | 452 | `bba4a4626a24a910` |
| `reports/env_smoke_duka.json` | 1606 | `1c4e28439973be2b` |
| `reports/env_smoke_git.json` | 977 | `fd4e9d1b257dc2b3` |
| `reports/env_smoke_gpu_bench.json` | 2250 | `3386b28d8bc527a4` |
| `reports/env_smoke_ml.json` | 859 | `196d07012edeabb4` |

## 11. 最终结论（必答）

1. 是否存在凭据？ — 候选内**无**硬编码凭据；`.env.mt5_demo` 未纳入。
2. 是否存在 MT5 登录账号？ — **是**：候选 2 个文件 + 历史 2 个文件（需脱敏/不纳入）。
3. 是否存在 MT5 密码？ — **否**（历史命中 0，从未入库）。
4. 是否存在 API key/token？ — 候选/历史高危模式均未命中（需人工二核）。
5. 是否存在运行态数据？ — **是**：27196 个，已全部排除。
6. 是否存在真实账户信息？ — 候选含 broker 服务器/账户元数据引用 → 需人工确认；运行态账户快照已排除。
7. 是否存在本机敏感路径？ — **是**：60 个含 `C:\AIQuant`，6 个含 `C:\Users\surface`。
8. 是否存在历史泄漏？ — 历史含 MT5 登录账号（2 文件），但**不进本次快照**；本地历史未改。
9. 本次发布是否需要修改任何原始文件？ — 需要（脱敏登录号、本机路径重构），但**本阶段未修改**，仅在 manifest 标记。
10. 当前候选快照是否达到进入下一阶段人工审计的条件？ — 达到，但需先处理 HIGH 项（账号脱敏 + 确认账户元数据）。

**最终状态：MANIFEST_READY_FOR_REVIEW**

_注：本阶段未 push、未改历史、未改代码、未启动交易。_
