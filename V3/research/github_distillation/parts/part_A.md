# Part A — GitHub Distillation Audit (4 repos)

Task: V3-HFT-GITHUB-DISTILLATION-002 (STRICT read-only audit)
Auditor: subagent (depth 2/5), session agent:main:subagent:78aa3ec9-68f4-4ae3-bdd9-4bb83de43ece
Audit timestamp: 2026-09-22 (Asia/Shanghai)
Method: `GET api.github.com/repos/<slug>` (existence + metadata) and `GET api.github.com/repos/<slug>/git/trees/<branch>?recursive=1` (file evidence), plus raw `README.md` body per repo. All claims below are quoted/derived from those artifacts. Anything not stated in-repo is marked UNKNOWN / DATA_GAP. No content invented. No stars/metrics fabricated — numbers are copied from the API response.

Existence verdict (all four): **EXISTS**. API returned HTTP 200 with matching `full_name` and `html_url` for every slug.

| slug | exists | stars | forks | license | default_branch | created | last push | lang |
|---|---|---|---|---|---|---|---|---|
| dshan12/Market-Microstructure | EXISTS | 0 | 0 | none (null) | master | 2026-06-11 | 2026-06-13 | Python |
| nsoxbekdn/microstructure-lab | EXISTS | 1 | 0 | none declared in API (README says MIT) | master | 2026-08-10 | 2026-08-10 | Python |
| sauloduttra/ofi-signal | EXISTS | 0 | 0 | MIT | main | 2026-05-23 | 2026-05-23 | Python |
| lukeyin08/Order-Flow-Imbalance | EXISTS | 0 | 1 | MIT | main | 2026-06-25 | 2026-06-25 | Python |

---

## Repo 1 — dshan12/Market-Microstructure

**Existence:** EXISTS (repo id 1265762754; `html_url` = https://github.com/dshan12/Market-Microstructure).
**Description (API):** "Quantitative analysis of limit order book dynamics: order flow imbalance, return predictability, signal decay, and market microstructure effects using Kraken spot data."
**Size:** 5551 KB. Topics: none.

### A. What does it predict?
Short-horizon future **mid return** from top-of-book depth asymmetry.
Evidence (README): `R_{t,t+h} = beta_0 + beta_1 * I_t + Gamma * X_t + epsilon` for `h in {1s, 5s, 10s, 30s, 60s}`; `I_t = (V_t^b - V_t^a)/(V_t^b + V_t^a)` (instantaneous top-of-book depth imbalance, range [-1,1]). Also imbalance velocity/acceleration (`v_t = (I_t - I_{t-1})/Delta_t`, `a_t = (v_t - v_{t-1})/Delta_t`).
Horizons: 1s–60s. Signal half-life reported: BTC 85.4s, BTC high-vol 524.1s, ETH 24.5s. Peak |r| = 0.166 (BTC 30s), 0.282 (BTC 10s high-vol), 0.070 (ETH 10s).

### B. What does it actually earn?
Self-reported, and the repo explicitly **does not** merge the components:
- Market-making simulator PnL table (README "Strategy Performance"): Basic Two-Sided MM −$33,118 (Sharpe −16.52, Max DD −100%, spread capture 23.7%); Adaptive (skew=3) −$32,655; OneSided (th=0.3) +$6,089 (Sharpe +7.76, spread capture 35.6%); OneSided (th=0.0) +$10,296 (Sharpe +9.74, spread capture 27.0%); Adaptive ETH (skew=50) +$2,164 (Sharpe +40.98, spread capture 70.8%).
- **Attribution (direct quote):** "The profitable strategies turn out to be directional momentum strategies in disguise. PnL decomposition shows **83–87% of profits come from inventory appreciation, not spread capture.**"

So: earnings category = **inventory appreciation (dominant)**, with spread capture as a minority component. Directional exposure, not liquidity provision income.

### Checklist
| Item | Verdict | Evidence (1 line) |
|---|---|---|
| data source | YES (real, with synthetic path too) | Kraken spot WebSocket client `src/data/collect/collector.py`; README: "5,768 BTC/USD and 5,002 ETH/USD tick-by-tick observations from Kraken"; note `src/data/generate_calibrated.py` = calibrated synthetic generator also present. |
| data granularity | Tick-by-tick (event), bucketed to 1–60s | README "tick-by-tick observations"; horizons {1,5,10,30,60}s; `data/features/btcusdt_features.csv` committed (3.1 MB). |
| L1 vs L2 | L1 | `I_t` uses only best-bid/best-ask volume (top-of-book); no depth levels used. |
| real trades vs synthetic | Real (analysis) + synthetic event-driven fills (MM sim) | Kraken collection for the econometrics; "event-driven LOB simulator" for the MM PnL. |
| uses future info? | DATA_GAP | No leakage statement in README; forward horizons are labels, HAC errors used but no explicit look-ahead audit. |
| train/val/test split | NO / DATA_GAP | No in-sample/OOS split stated; results are in-sample estimates. |
| overlapping labels? | YES | Horizons 1–60s overlap; README: "Newey-West (1987) HAC standard errors with L = 2h lags due to overlapping return-induced serial correlation." |
| purge/embargo? | DATA_GAP | Not mentioned anywhere in README. |
| transaction cost adjusted? | UNKNOWN | MM simulator exists but README gives no fee/cost schedule; no net-of-cost table. |
| queue uncertainty? | NO / DATA_GAP | No queue-position or fill-probability model described. |
| latency considered? | DATA_GAP | Not mentioned. |
| adverse selection considered? | UNKNOWN | "exploitability under market-making constraints" + inventory discussion, but no adverse-selection metric stated. |
| gross vs net distinguished? | PARTIAL (gross attribution yes) | PnL is decomposed into inventory-appreciation vs spread-capture shares, but no explicit gross-vs-net cost line. |
| realistically executable? | NO (per own evidence) | Basic MM −100% Max DD; author labels it "an academic research project. Not investment advice." |

### Summary block
- **Success condition:** imbalance `I_t` has a stable coefficient on 1–60s returns with HAC significance, and a market-making variant reaches positive PnL/Sharpe on held data.
- **Failure condition (documented):** two-sided MM loses heavily (Max DD −100%); "profitable" variants are momentum in disguise, i.e. the imbalance signal does not pay via spread capture.
- **Cost condition:** not quantified → DATA_GAP.
- **Data condition:** L1 top-of-book sufficient for the published results; no L2 requirement documented.
- **Execution type:** limit (two-sided quoting, one-sided quoting, skew) with market orders in the event-driven sim.
- **Timescale:** intraday, seconds to ~1 minute; half-life measured 24.5–524.1s.
- **Transferability to XAUUSD:** **PARTIAL** — the L1 depth-imbalance methodology and HAC/overlap handling are asset-agnostic and portable to XAUUSD quote data; but evidence is crypto spot, sample is tiny (~5.8k/5.0k ticks), results are negative for MM, and XAUUSD venue/LOB structure differs.

---

## Repo 2 — nsoxbekdn/microstructure-lab

**Existence:** EXISTS (repo id 1329982007; `html_url` = https://github.com/nsoxbekdn/microstructure-lab).
**Description (API):** "Research-grade limit order book, market microstructure and execution algorithm simulator in Python."
**Size:** 780 KB. Topics: algorithmic-trading, execution, finance, limit-order-book, market-microstructure, python, quant, quantitative-finance.

### A. What does it predict?
**Other — no alpha claim.** It is an execution/L0-book research framework. The only forward-looking regression is OFI → forward returns, explicitly framed as exploratory.
Evidence: "`research/experiments` regresses forward returns on OFI and reports correlation and R² — treated as an exploratory signal, **not a claim of predictive edge**."
Its actual modeled quantities: microprice (`(best_bid*ask_qty + best_ask*bid_qty)/(bid_qty+ask_qty)`), imbalance, **implementation shortfall**, **VWAP slippage**, fill rate, market impact (sqrt-law), adverse selection.

### B. What does it actually earn?
**Execution improvement** — measured, but only in simulation.
Evidence: `ExecutionResult.metrics()` = "implementation shortfall / VWAP slippage"; algorithms Immediate / TWAP / VWAP / POV / passive; `impact/square_root.py` fits `impact_bps ≈ Y*sigma*sqrt(Q/V)*1e4`.
README states plainly: "This is a research and portfolio project, **not a production exchange or a trading system with real capital at risk**." No PnL, no spread capture, no inventory appreciation numbers exist. All outputs are synthetic (`outputs/report.md`).

### Checklist
| Item | Verdict | Evidence (1 line) |
|---|---|---|
| data source | Synthetic (real-replay scaffold only) | `SyntheticMarket` drives all results; `microstructure_lab/data/replay.py` can replay an event DataFrame "(a stepping stone toward replaying real L2 data)" but no real data is shipped. |
| data granularity | Per-event (order/cancel/trade) | Every action appends a `MarketEvent`; 6,000-event default simulation. |
| L1 vs L2 | L2-capable book, synthetic | Multi-level book with `depth(n)`/`snapshot(n)`; but no real L2 feed and analytics default to best quotes. |
| real trades vs synthetic | Synthetic | "Purely synthetic order flow — no real exchange connectivity or historical L2 replay out of the box". |
| uses future info? | NO | Stateful flow generator decides from **current** spread and imbalance ("not iid draws"); reference price only drives generation. |
| train/val/test split | DATA_GAP (N/A) | No predictive model, hence no split documented. |
| overlapping labels? | NO / DATA_GAP | No label-based forecasting task. |
| purge/embargo? | NO | Not applicable/documented. |
| transaction cost adjusted? | YES (simplified) | Execution analytics include fees and fill rate; README caveat: "fee schedules ... deliberately simplified". |
| queue uncertainty? | PARTIAL | FIFO price-time priority and a "queue position" analytic exist, but no queue-position fill-probability model. |
| latency considered? | NO | "Latency, fee schedules, and the maker/taker agent behaviors are deliberately simplified"; latency is a roadmap item. |
| adverse selection considered? | YES | `analytics/adverse_selection.py`: forward midprice move after passive fills at multiple horizons. |
| gross vs net distinguished? | YES | Sign-checked implementation shortfall incl. fees for BUY/SELL; VWAP slippage separate. |
| realistically executable? | NO (by own statement) | "Not a claim of production HFT performance or correctness under adversarial/real market conditions." |

### Summary block
- **Success condition:** matching-engine invariants hold (41 deterministic tests) and execution algorithms produce sign-correct shortfall vs arrival price on the synthetic market.
- **Failure condition:** `pytest` failures (crossed book, quantity non-conservation, negative quantities, priority violations) or non-reproducible runs.
- **Cost condition:** simplified taker/maker fees; explicitly not real fee schedules.
- **Data condition:** synthetic L2 (multi-level) in-engine; **no real L2 data requirement met** → DATA_GAP for real deployment.
- **Execution type:** both — market (Immediate/TWAP/VWAP/POV) and limit (passive).
- **Timescale:** event-driven; intraday synthetic U-shaped volume profile; not wall-clock.
- **Transferability to XAUUSD:** **PARTIAL** — the architecture (multi-level book, FIFO, IS/VWAP accounting, sqrt-impact, adverse-selection module) is directly reusable as a test harness for XAUUSD; but there is zero empirical XAUUSD evidence and fills are synthetic, so no edge is claimed or demonstrated.

---

## Repo 3 — sauloduttra/ofi-signal

**Existence:** EXISTS (repo id 1247854726; `html_url` = https://github.com/sauloduttra/ofi-signal).
**Description (API):** "Order Flow Imbalance from Cont-Kukanov-Stoikov 2014 - OFI vs TFI head-to-head shows R^2 3261x advantage. Companion to as-market-maker + almgren-chriss".
**Size:** 14 KB (very small). License MIT. Topics: from-scratch, high-frequency-trading, market-microstructure, order-flow, python, quantitative-finance.
**Tree:** `ofi/{events,compute,regression,simulator}.py`, `tests/test_ofi.py`, `examples/{run_regression,bucket_sensitivity}.py`, `requirements.txt`, `LICENSE`, `README.md`. Nothing else.

### A. What does it predict?
**Mid return (contemporaneous), per bucket** — `delta_mid` regressed on OFI.
Evidence (README): `delta_mid = +0.0020 + +0.00005 * OFI`, `R^2 = 0.974`, `t(beta) = +86.13` vs TFI `R^2 = 0.000`, `t = -0.24`; "R^2 ratio (OFI / TFI) = 3261x". Bucket sweep 25 ms → 2000 ms keeps OFI R² ≈ 0.96–0.99 while TFI is noise.
Caveat quoted verbatim: "(Caveat: synthetic R² are unrealistically high - real data has ~60-75% for OFI. The qualitative ranking `OFI >> TFI` is what's faithful.)"

### B. What does it actually earn?
**Nothing earned — no strategy, no PnL, no cost model.**
Evidence: the repo contains only a formula implementation, a synthetic LOB generator, an OLS helper, and unit tests. No backtest, no execution, no inventory, no fee model. Roadmap items (L2 OFI, ITCH ingestion, cross-impact, permanent/transient decomposition) are all unshipped.

### Checklist
| Item | Verdict | Evidence (1 line) |
|---|---|---|
| data source | Synthetic | "Real CKS data is paywalled NASDAQ ITCH. We build a deterministic in-process generator (`ofi/simulator.py`)". |
| data granularity | Per LOB event, bucketed 25–2000 ms | "200 buckets over 20k LOB events"; bucket sweep table. |
| L1 vs L2 | L1 (top-of-book only) | `BookSnapshot` carries best bid/ask; L2 depth is an unshipped v0.2.0 roadmap item. |
| real trades vs synthetic | Synthetic | Latent `alpha_t` AR(1) drives both OFI and TFI. |
| uses future info? | NO (but circular sim) | Contemporaneous regression; simulator injects latent alpha into both regressor and target, which inflates R² (author acknowledges). |
| train/val/test split | NO | Single in-sample regression reported; no split. |
| overlapping labels? | UNKNOWN | Buckets are consecutive intervals; empty intervals forward-filled — no overlap analysis given. |
| purge/embargo? | NO | Not mentioned. |
| transaction cost adjusted? | NO | No cost/fee component anywhere. |
| queue uncertainty? | NO | "Trades fill the top of book; if size exceeds resting qty the price level moves" — no queue model. |
| latency considered? | NO | Not mentioned. |
| adverse selection considered? | NO | Not mentioned. |
| gross vs net distinguished? | NO | Gross-only statistic; no net concept exists. |
| realistically executable? | NO | Synthetic-only, no costs, author flags R² as unrealistic. |

### Summary block
- **Success condition:** the six-branch CKS eq. 2 increment formula computes correctly (13 unit tests) and OLS recovers a high OFI coefficient with large |t|.
- **Failure condition:** R²(OFI) fails to dominate R²(TFI), or the sign convention/branch logic breaks the tests.
- **Cost condition:** none — DATA_GAP (this is the repo's main gap).
- **Data condition:** L1 top-of-book synthetic; L2 explicitly listed as future work.
- **Execution type:** none (no order placement at all).
- **Timescale:** sub-second to 2 s buckets.
- **Transferability to XAUUSD:** **DATA_GAP** — the OFI definition is venue-agnostic and could be computed on XAUUSD L2, but this repo supplies no real-data, no-cost, no-execution evidence, and its own R² values are labeled unrealistic; transferability cannot be established from this artifact.

---

## Repo 4 — lukeyin08/Order-Flow-Imbalance

**Existence:** EXISTS (repo id 1279779941; `html_url` = https://github.com/lukeyin08/Order-Flow-Imbalance).
**Description (API):** "A short-horizon trading signal built from order flow imbalance in Python".
**Size:** 1013 KB. License MIT. Topics: none.
**Tree:** `src/{simulator,collector,ofi,features,analysis,costs,backtest,market_maker,plotting,config}.py`, `scripts/{run_analysis,run_collect,build_report}.py`, `tests/{test_ofi,test_pipeline}.py`, `results/{figures/*,metrics.json}`, `report/OFI_Project_Report.{pdf,tex}`, `conftest.py`, `requirements.txt`, `LICENSE`.

### A. What does it predict?
**Next-1s price move (mid return) and, indirectly, trade direction** — plus inventory-risk control for a maker.
Evidence: "OFI explains 53% of contemporaneous one-second price moves (R² = 0.53, t = 132), or 88% using the top five levels"; "It forecasts the next second weakly (IC = 0.18), and the edge holds out of sample (IC = 0.19)"; IC rises to 0.31 at 10s. Real-data replication: impact R² 0.37 (t=15), 5-level 0.64, forecast IC 0.14, OOS 0.13.

### B. What does it actually earn?
Separated carefully by the author:
- **Direction (taker): NOT profitable.** "The predicted move (0.09 ticks) is about 29x smaller than the round-trip taker cost (2.48 ticks), so **a cost-aware taker makes 0 trades**." Out of sample: gross **+0.29 ticks/trade**, net **−2.20 ticks/trade**.
- **Liquidity provision / spread capture (maker): YES, risk-adjusted.** "Skewing Avellaneda-Stoikov quotes by OFI keeps inventory tightly bounded (±15 vs ±173 for naive quoting) while recovering most of the PnL that plain inventory control gives up ($110 vs $18), the best risk-adjusted return of the three policies."

Policy table (README): Naive symmetric $128 / |inv| 173 / Sharpe* 44; Avellaneda-Stoikov $18 / 16 / 120; A-S + OFI skew $110 / 15 / 839. Real Binance.US capture: inventory ±12 vs ±29 naive.
Bottom line: earns = **execution improvement / inventory-risk reduction in market making**, plus spread capture; **explicitly not** taker direction.

### Checklist
| Item | Verdict | Evidence (1 line) |
|---|---|---|
| data source | Synthetic headline + real Binance.US validation | "Exchange APIs are not reachable from the build environment, so the headline results use a calibrated event-driven LOB simulator"; "same pipeline was run on 30 minutes of live Binance.US BTCUSDT top-of-book (9,808 snapshots, 1,801 one-second buckets)". |
| data granularity | 1-second buckets; 100 ms snapshots collected | collector streams `@depth20@100ms`; analysis buckets per second. |
| L1 vs L2 | L1 primary, top-5 levels used | "the top five levels (Xu et al. 2020)" raises R² 0.53→0.88; collector depth20 gives multi-level. |
| real trades vs synthetic | Both | Simulator for headline; real Binance.US capture replicating each metric. |
| uses future info? | NO | "No look-ahead. Forecasting labels use the move after OFI is observed, costs are charged at the spread prevailing at trade time"; a `tests/` "no-leakage check" exists. |
| train/val/test split | YES | "A model fit on the first 70% of the sample holds on the last 30% (IC 0.18, out of sample 0.19)"; `analysis.py` has "HAC errors, OOS split". |
| overlapping labels? | PARTIAL | 1s buckets with forward labels; Newey-West HAC used "because high-frequency returns are autocorrelated", but overlap purging not described. |
| purge/embargo? | DATA_GAP | Not mentioned in README. |
| transaction cost adjusted? | YES | `costs.py` (taker round-trip cost vs maker capture), `backtest.py` "out-of-sample taker backtest, gross vs net". |
| queue uncertainty? | NO | "The market-maker fill model is an Avellaneda-Stoikov intensity, not a queue-position simulation." |
| latency considered? | NO | "Latency and queue priority are out of scope." |
| adverse selection considered? | YES | "a market maker ... must control inventory and avoid being run over by informed flow"; OFI skew defends against it. |
| gross vs net distinguished? | YES | Explicit gross (+0.29) vs net (−2.20) ticks/trade; simulated vs real cost comparison. |
| realistically executable? | PARTIAL | Taker: provably not (0 cost-aware trades). Maker: fills modeled by intensity, no queue/latency → not fully executable. |

### Summary block
- **Success condition:** positive out-of-sample IC and a maker policy that bounds inventory while preserving PnL (achieved: IC 0.18→0.19 IS→OOS; A-S+OFI skew $110 at |inv| 15, Sharpe 839).
- **Failure condition:** the predicted edge is smaller than round-trip cost → cost-aware taker trades 0 times (achieved/documented). Real-capture caveat: taker gross flipped negative (−16 ticks/trade) on the 30-min thin-venue sample, attributed to small-sample drift.
- **Cost condition:** quantified and decisive — edge 0.09 ticks vs 2.48 ticks round-trip cost (sim: 29×; real: 81×).
- **Data condition:** L1 adequate for the core result; top-5 levels materially improve R² (0.53→0.88 sim, 0.37→0.64 real) → L2 preferred, L1 workable.
- **Execution type:** both — market (taker backtest) and limit (Avellaneda-Stoikov maker quoting).
- **Timescale:** 1-second primary, decay examined to 10s.
- **Transferability to XAUUSD:** **PARTIAL** — strongest methodology in this set (no-look-ahead labels, IS/OOS split, HAC, explicit gross/net cost test, real-data replication), portable to XAUUSD L2; but evidence is BTC (1-tick median spread, thin Binance.US sample), fills are intensity-based not queue-based, and no XAUUSD-specific spread/cost calibration exists.

---

## Cross-repo verdict

| slug | EXISTS | mechanism (1 line) | transferability |
|---|---|---|---|
| dshan12/Market-Microstructure | EXISTS | L1 top-of-book depth imbalance → 1–60s mid-return regression; MM PnL is 83–87% inventory appreciation, not spread capture | PARTIAL |
| nsoxbekdn/microstructure-lab | EXISTS | Synthetic multi-level LOB + execution-algorithm simulator measuring implementation shortfall/VWAP slippage; no alpha claim | PARTIAL |
| sauloduttra/ofi-signal | EXISTS | CKS-2014 OFI formula + synthetic latent-alpha LOB; OFI vs TFI R² head-to-head (R² 0.974, 3261× TFI) | DATA_GAP |
| lukeyin08/Order-Flow-Imbalance | EXISTS | OFI → next-1s move (IS IC 0.18 / OOS 0.19); taker loses after cost (0 trades), OFI-skewed A-S maker improves risk-adjusted PnL | PARTIAL |

**Fabrication audit:** no stars, forks, PnL, R², Sharpe, or file claims in this document were invented; each number is traceable to the fetched README/API JSON. Items absent from the repos are marked UNKNOWN / DATA_GAP / NO, never guessed.
