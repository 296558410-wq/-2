# Part C — GitHub Distillation (3 repos)

Task: V3-HFT-GITHUB-DISTILLATION-002 (STRICT read-only audit).
Method: existence via `github.com/<slug>` + `api.github.com/repos/<slug>`; content from actual README / source files fetched 2026-09-21. Nothing invented. Items not stated in the repo are marked UNKNOWN / DATA_GAP.

Verification snapshot (from GitHub API, 2026-09-21):

| slug | exists | created | last push | size | stars | license | primary lang |
|---|---|---|---|---|---|---|---|
| jaefit/deep-ofi | EXISTS | 2026-06-08 | 2026-06-08 | 147 KB | 1 | none | Python |
| MaharshKhatri/lob-simulator | EXISTS | 2026-04-23 | 2026-04-23 | 356 KB | 0 | none (README says MIT) | Python (+C++) |
| 1816x/Trading-Microstructure-Engine | EXISTS | 2026-07-13 | 2026-07-23 | 819 KB | 1 | MIT | TypeScript (+Rust/Python) |

---

## Repo 1 — jaefit/deep-ofi

**exists = EXISTS** (public, Python, default branch `main`).

Files read as evidence: `README.md`, `REPORT.md`, `src/features.py`, git tree.

### A. What does it predict?
**Short-horizon mid-price direction, 3-class.** `README.md`: "Predict the short-horizon direction of the mid-price from the limit order book." `features.py`/`REPORT.md`: label = sign of `(mean(mid[t+1..t+k]) − mid[t]) / mid[t]`, 3 classes (down/flat/up) with a **fixed ±0.3 bp flat band**; horizons k ∈ {10,20,50,100} snapshots at 100 ms = **1–10 s**. This is a **mid-return direction** target, not next-tick, not fill probability.

### B. What does it actually earn?
**Nothing — no economic claim.** It is a pre-registered hypothesis test ("is OFI a sufficient statistic for the raw book?"). No PnL, no spread capture, no inventory appreciation, no passive fill, no execution improvement. Metric is macro-F1 only. Direction/earnings are **not merged** because there is no earnings component at all: it is a *statistical prediction* study.

Decomposed earnings channels (all explicit):
- direction (prediction of mid direction): **YES** (target is direction)
- spread capture: NO — not claimed
- inventory appreciation: NO
- passive fill: NO
- liquidity provision: NO
- execution improvement: NO

### Checklist
| Item | Verdict | Evidence (1 line) |
|---|---|---|
| data source | YES | Self-collected live Binance WebSocket `depth20@100ms` (BTCUSDT, ETHUSDT), `src/collect.py` |
| data granularity | YES | 100 ms partial-book snapshots, 20 levels; ~54,000 snapshots, ~45 min |
| L1 vs L2 | **L2** | 20-level bid/ask (price, qty) per snapshot |
| real trades vs synthetic | REAL (book), no trades | Live book snapshots; no trade/tape data (snapshot-based OFI approximation, stated as a limitation) |
| uses future info? | NO | `features.py` leakage guard: features ≤ t; label uses future mids; single temporal cut |
| train/val/test split | YES (train/test) | 70/30 single temporal cut, no shuffling, scaler fit on train only; separate val set not mentioned → DATA_GAP |
| overlapping labels? | DATA_GAP | Label averages mids t+1..t+k; overlap between consecutive t is not discussed |
| purge/embargo? | NO / DATA_GAP | No purge/embargo mentioned anywhere |
| transaction cost adjusted? | NO | Metric is macro-F1; no cost model |
| queue uncertainty? | NO | Uses book qty; no queue-position/fill model |
| latency considered? | NO | 100 ms snapshot clock; no latency modeling (event-time listed as future work) |
| adverse selection considered? | NO | Not discussed |
| gross vs net distinguished? | N/A | No PnL, so nothing to gross/net |
| realistically executable? | NO | No execution model, no order placement |

### Required conditions
- **Success condition:** OFI (flow) matches or beats the raw book ⇒ OFI is a sufficient statistic. **Result: refuted** (raw book wins 8/8 static cells; best single-snapshot raw model 0.40–0.45 > every LSTM 0.33–0.40).
- **Failure condition:** raw book wins / OFI adds ~nothing ⇒ hypothesis refuted. This is what the REPORT reports.
- **Cost condition:** none (no transaction cost modelled).
- **Data condition (L1/L2):** L2 (top-20 levels).
- **Execution type:** N/A — no market/limit orders.
- **Timescale:** sub-second features (100 ms) predicting 1–10 s horizons.
- **Transferability to XAUUSD:** **PARTIAL** — the OFI / queue-imbalance *method* is venue-agnostic and could be applied to FX/metals L2, but the evidence is crypto-only (2 symbols, one 45-min window), with **no costs, no execution, and no XAUUSD data**. Method transferable; empirical result not.

---

## Repo 2 — MaharshKhatri/lob-simulator

**exists = EXISTS** (public, Python + C++ engine, default branch `main`; README self-labels "High School Senior Project, Summer 2025").

Files read as evidence: `README.md`, `config.yaml`, `src/models/fill_prob.py`, git tree.

### A. What does it predict?
**Fill probability and optimal quotes — not price direction.** `README.md`: Monte Carlo model `P(fill | queue rank k, spread s)` (10,000 paths) and **expected fill time**; the strategy layer computes **Avellaneda–Stoikov reservation price and optimal spread**. `fill_prob.py` confirms `estimate_fill_prob(...)` and `expected_fill_time(...)`. So: **passive fill probability + inventory-aware optimal quoting**, not next-tick / mid-return / trade-direction.

### B. What does it actually earn?
**Liquidity provision / spread capture on synthetic flow** (a market-making PnL), explicitly **synthetic and not live**. README "Key Results (Synthetic Data)": annualised Sharpe **3.4**, max drawdown **1.2%**, mean passive fill rate **61%**, adverse-selection cost **0.3 bps/fill**, 10,000 Monte Carlo paths — with the explicit caveat "Results are on synthetic order flow. Do not treat as live-trading performance."

Decomposed earnings channels:
- direction: NO — no directional forecast
- spread capture: **YES (claimed, synthetic)** — passive market making
- inventory appreciation: NO (inventory is *risked/penalised*, not an earnings claim)
- passive fill: **YES** — fill-probability model is central
- liquidity provision: **YES** — quotes both sides
- execution improvement: NO — not an execution algo

### Checklist
| Item | Verdict | Evidence (1 line) |
|---|---|---|
| data source | SYNTHETIC | Poisson order-flow generator (`flow_generator.py`); `config.yaml` arrival_rate 10.0/s, cancel 0.3, seed 42 |
| data granularity | YES (event/step) | Event-driven replay; MC time-step `dt=0.1 s` in `fill_prob.py` |
| L1 vs L2 | Full book (L2+) | Matching engine holds multi-level depth (bid/ask levels) |
| real trades vs synthetic | SYNTHETIC | README: "Results are on synthetic order flow" |
| uses future info? | DATA_GAP | Simulation; no look-ahead discussion (also N/A since no ML fit on real data) |
| train/val/test split | N/A / DATA_GAP | No ML train/test; calibration notebooks only |
| overlapping labels? | N/A | No labels |
| purge/embargo? | NO | Not applicable / not mentioned |
| transaction cost adjusted? | PARTIAL | Adverse-selection cost 0.3 bps/fill is modelled; exchange fees/rebates not stated → UNKNOWN |
| queue uncertainty? | **YES** | Fill probability stratified by queue position rank `k` via MC paths |
| latency considered? | NO / UNKNOWN | No latency/network delay modelling mentioned |
| adverse selection considered? | **YES** | "Adverse Selection Cost 0.3 bps / fill" reported |
| gross vs net distinguished? | UNKNOWN | README shows Sharpe/DD after adverse selection; fee treatment unspecified |
| realistically executable? | NO | Synthetic flow, self-reported numbers, no market validation |

### Required conditions
- **Success condition:** positive risk-adjusted PnL (Sharpe) under the A–S strategy on the synthetic book.
- **Failure condition:** negative PnL / unfavourable spread-vs-adverse-selection tradeoff (not explicitly defined in README).
- **Cost condition:** adverse-selection cost per fill (0.3 bps); fee model UNKNOWN.
- **Data condition (L1/L2):** full LOB depth (L2-equivalent) but **synthetic**.
- **Execution type:** **LIMIT** (passive two-sided market making).
- **Timescale:** seconds–minutes (1-hour simulated session; MC horizon in `fill_prob.py` default up to 3600 s).
- **Transferability to XAUUSD:** **PARTIAL** — Avellaneda–Stoikov market making, queue-position fill probability and adverse-selection accounting are standard and *directly relevant* to XAUUSD liquidity provision; but all results are synthetic, tick size is 0.01 at price 100 (not XAUUSD-realistic), and no XAUUSD data or cost calibration is present.

---

## Repo 3 — 1816x/Trading-Microstructure-Engine

**exists = EXISTS** (public, MIT, default branch `main`; monorepo Rust + Python + Next.js).

Files read as evidence: `README.md`, `engine/src/metrics.rs`, `backtest/src/backtest/` listing, git tree.

### A. What does it predict?
**Nothing — explicitly no prediction.** README disclaimer: "this is **not** financial advice and it does not predict prices. It is a tool for analyzing your *own* trading behavior against microstructure context." The engine computes descriptive metrics per window: **OFI `(buy − sell)/(buy + sell)`**, realized volatility `sqrt(Σ r²)`, buy/sell/total volume, VWAP (`metrics.rs` verified). Plus a Claude-powered **behavioral** coach on a trade journal.

### B. What does it actually earn?
**Nothing — no PnL and no trading logic.** Despite a `backtest/` folder, its contents are `api.py`, `coach.py`, `journal.py` (FastAPI + journal + LLM coach) — there is **no strategy, no order placement, no PnL accounting**. Earnings channels are all NO:
- direction: NO (no forecast)
- spread capture: NO
- inventory appreciation: NO
- passive fill: NO
- liquidity provision: NO
- execution improvement: NO (the agent gives behavioral observations, "not trading advice")

### Checklist
| Item | Verdict | Evidence (1 line) |
|---|---|---|
| data source | SYNTHETIC | Bundled `data/sample_mnq_ticks.csv`, `data/generate_ticks.py` "deterministic, seeded"; README "All bundled data is synthetic" |
| data granularity | YES | Tick-by-tick, aggregated into 1 s windows (`--window 1s`) |
| L1 vs L2 | **L1 (trades only)** | Inputs are aggressor-tagged trades (price, size, side); **no book depth** |
| real trades vs synthetic | SYNTHETIC | Synthetic tape with a drifting buy-pressure regime; synthetic journal |
| uses future info? | NO | One-pass windowing over time-sorted tape; no forward-looking labels |
| train/val/test split | N/A | No ML training (only a mocked-LLM test) |
| overlapping labels? | N/A | No labels |
| purge/embargo? | N/A | No ML |
| transaction cost adjusted? | NO | No PnL / no cost model |
| queue uncertainty? | NO | Trades-only, no queue/fill model |
| latency considered? | PARTIAL (rationale only) | Rust chosen "for low-latency processing"; **no latency measurement or budget** |
| adverse selection considered? | NO | Not modelled |
| gross vs net distinguished? | N/A | No PnL |
| realistically executable? | N/A | No execution layer; engine is analytics-only |

### Required conditions
- **Success condition:** the end-to-end pipeline runs (tape → Rust metrics → SQLite → API → dashboard; `make demo` / `scripts/verify_pipeline.sh`, CI green).
- **Failure condition:** CI/test/lint failure, or pipeline verification fails.
- **Cost condition:** none (no trading, no costs).
- **Data condition (L1/L2):** L1 trade ticks with aggressor side (no book depth).
- **Execution type:** NONE (no orders).
- **Timescale:** 1 s aggregation windows over a tick tape.
- **Transferability to XAUUSD:** **NOT_SUPPORTED** as an alpha/execution source — it makes no trading claim and has no execution layer or PnL. (Its OFI/realized-vol metric definitions are generic and could *describe* XAUUSD tick data, but there is no method, cost, or evidence transferable to XAUUSD trading.)

---

## Canonical literature-level methods (cross-repo / field level)

Marked UNKNOWN where not verifiable from the repos/literature actually cited in them. Cites referenced by these repos: Cont–Kukanov–Stoikov 2014; Kolm–Turiel–Westray 2023; Zhang–Zohren–Roberts (DeepLOB) 2019; Cont–Cucuringu–Zhang 2023; Avellaneda–Stoikov 2008; Guéant 2017; Cont–Stoikov–Talreja 2010. Formulas below are stated as field-canonical; **I did not independently verify each published derivation this run** — treat as UNKNOWN where unstated.

**Microprice.** Weighted mid that crosses the quote proportionally to opposite-side (queue) sizes: `microprice = (Q_bid·P_ask + Q_ask·P_bid) / (Q_bid + Q_ask)`, a size-weighted imbalance anchor that leads the raw mid. `deep-ofi` is consistent with this in *result* (its raw book carries the L1 queue-imbalance state as the strongest predictor) but the repo does **not** implement an explicit microprice formula → UNKNOWN there. General "microprice better predicts the next mid move than mid" claim: field-canonical, not re-verified here.

**OFI (Order-Flow Imbalance).** Cont–Kukanov–Stoikov (2014): per-event book change — bid flow `+q_n` if bid improves, `q_n − q_{n−1}` if unchanged, `−q_{n−1}` if bid worsens; ask flow symmetric; `OFI = OF_bid − OF_ask`; **price change is approximately linear in windowed OFI**. `deep-ofi` implements exactly this per level, extended multi-level, summed over a trailing 100 ms window (`features.py`) — **VERIFIED in source**. Note: repo 3 uses a *different, trade-based* definition `(buy − sell)/(buy + sell)` — a normalized volume imbalance, **not** CKS OFI (verified in `metrics.rs`); same acronym, different quantity.

**Markout.** Post-fill mark-to-market at a fixed horizon (e.g. +1 s / +5 s) versus fill price, used to measure the true cost/value of a passive fill and to detect toxic flow. **Not implemented in any of the three repos** — `lob-simulator` reports a related but coarser "adverse selection cost 0.3 bps/fill". Markout formulas/horizons: UNKNOWN here.

**Adverse selection.** The loss to a liquidity provider when a resting quote fills precisely because informed flow moves the price against it; typically decomposed from the effective spread (realized spread + price impact). `lob-simulator` names and quantifies it (0.3 bps/fill, synthetic) but the derivation is UNKNOWN from the README. `deep-ofi` / repo 3 do not model it.

**Implementation shortfall (IS).** Perold-style execution metric: difference between the decision price and the actual execution price × size (plus opportunity cost of unfilled size), used to grade execution quality against a benchmark (e.g. arrival price / VWAP). **Repo 3 computes VWAP but only as a descriptive chart metric — no IS, no execution benchmark** (verified: `metrics.rs` has `vwap` only). `deep-ofi` names "execution improvement" as motivation but implements no IS measure. IS definitions/allocations: UNKNOWN here.

### Cross-repo verdict
None of the three implements an executable, cost-adjusted strategy on real XAUUSD (or FX) data. Repo 1 is a rigorous-but-negative prediction study on crypto L2; Repo 2 is a synthetic A–S market-making sandbox with the most *transferable method* (queue-aware fill probability + adverse-selection accounting); Repo 3 is an analytics/behavioral tool with **no trading claim at all**.
