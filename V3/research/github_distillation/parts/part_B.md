# Part B — GitHub Microstructure Distillation (4 repos)

Task: V3-HFT-GITHUB-DISTILLATION-002
Mode: STRICT read-only audit. Evidence = live GitHub API + repo README (raw, `main` branch), fetched 2026-09-22 (Asia/Shanghai).
Rule applied: nothing below is inferred beyond what the fetched pages state; gaps are marked `DATA_GAP` / `UNKNOWN`.

Repo metadata (from `api.github.com/repos/<slug>`, exact):

| slug | exists | language | stars | forks | created | pushed | license (README) |
|---|---|---|---|---|---|---|---|
| twowaymind/orderflow-metrics | EXISTS | TypeScript | 11 | 3 | 2026-07-28 | 2026-09-21 | MIT (LICENSE file) |
| intrepidkarthi/orderbook | EXISTS | Go | 16 | 4 | 2025-01-08 | 2026-09-01 | MIT (LICENSE file) |
| Hellblazer704/nanolob | EXISTS | Jupyter Notebook (C++20 core) | 0 | 0 | 2026-07-16 | 2026-07-19 | UNKNOWN (no license file/statement seen) |
| tradingexpert/ordersim | EXISTS | Python | 2 | 0 | 2026-05-14 | 2026-08-30 | MIT (README "License" section) |

---

## 1. twowaymind/orderflow-metrics

**Existence:** EXISTS (`https://github.com/twowaymind/orderflow-metrics`, API 200, id 1314891891). Description: "Microstructure order-flow metrics — Order Flow Imbalance (OFI), depth and trade imbalance. Dependency-free TypeScript."

**Mechanism (one line):** a zero-dependency computation library of microstructure/TCA *metrics and estimators* (OFI, multi-level OFI, depth/trade imbalance, VPIN, information-driven bars, Kyle λ, markouts, Almgren–Chriss, implementation shortfall, TWAP/POV scheduling, volatility/VaR/risk stats), shipped as TS + a Python port — not a strategy and not a backtester.

### A. What it predicts
- No model, no strategy, no PnL path is shipped. It computes inputs/labels, it does not issue predictions.
- Only explicit predictive claim: `ofi` "implements the level-1 OFI of Cont, Kukanov & Stoikov (2014) … Empirically it is a strong linear predictor of short-horizon price changes." This is a cited literature claim, **not validated in-repo** (examples run on seeded synthetic data).
- `markoutProfile` / `adverseSelectionScore` are measurement lenses (post-fill drift, toxicity), not predictors.
- Verdict: **label = short-horizon mid move via OFI (literature claim only); otherwise N/A / UNKNOWN.**

### B. What it actually earns
- **Nothing measurable.** No order placement, no fills, no certification: it is a metrics library. `simulateMarketOrder` is explicitly read-only ("the book isn't touched"); `twap`/`pov` produce schedules, not outcomes.
- Category-wise: direction = N/A; spread capture = N/A; inventory appreciation = N/A; passive fill = N/A; liquidity provision = N/A; execution improvement = **analytics/tooling only** (cost, impact, markout, shortfall decompositions), no demonstrated P&L.

### Checklist
| item | verdict | 1-line evidence |
|---|---|---|
| data source | DATA_GAP | feed-agnostic API over caller-supplied quotes/trades/snapshots; examples use seeded synthetic data |
| data granularity | YES | accepts tick/quote/trade/level-update inputs (`ofiContribution`, `tickBars`, `ob.update(side,price,size)`) |
| L1 vs L2 | YES (both) | L1 OFI from best quotes; `multiLevelOFI(prev,curr,K)` / `OrderBook.depth()` over multi-level book snapshots |
| real trades vs synthetic | DATA_GAP | library ships no data; README examples explicitly "deterministic synthetic data" |
| uses future info? | NO (N/A) | no model/backtest; markouts consume later mids only as a post-trade analytic |
| train/val/test split | NO | no fitted model; regression helpers (`harForecast`, OLS) take data without a documented split |
| overlapping labels? | N/A | no label-construction pipeline |
| purge/embargo? | NO | nothing in README |
| transaction cost adjusted? | PARTIAL | supplies cost models (`squareRootImpact`, `almgrenChrissCost`, `implementationShortfall`, `effectiveSpread`) but no strategy that nets them |
| queue uncertainty? | NO | no queue-position model; `simulateMarketOrder` is a read-only sweep |
| latency considered? | NO | not addressed |
| adverse selection considered? | YES | `markoutProfile`, `adverseSelectionScore` (markout in half-spread units, ">1 = toxic") |
| gross vs net distinguished? | N/A | no P&L series |
| realistically executable? | N/A | no execution; library only |

- **Success condition:** DATA_GAP (no strategy to succeed). **Failure condition:** DATA_GAP.
- **Cost condition:** DATA_GAP for earnings; cost *estimators* provided.
- **Data condition:** works on L1 quotes and multi-level (L2-depth) snapshots; DATA_GAP on which is required for the OFI claim to hold.
- **Execution type:** N/A (no execution); scheduling helpers model TWAP/POV.
- **Timescale:** OFI/trade metrics = tick→seconds; risk/VaR/HAR = daily+.
- **Transferability to XAUUSD: PARTIAL** — metric definitions are asset-agnostic and computable on XAUUSD L1/L2 + prints, but the repo supplies no evidence of predictive or economic value on XAUUSD (or any asset).

---

## 2. intrepidkarthi/orderbook

**Existence:** EXISTS (`https://github.com/intrepidkarthi/orderbook`, API 200, id 913993414). Description: "A fast, embeddable limit-order-book & matching engine in Go — plus a microstructure research harness and a WASM-powered animated explainer. MIT."

**Mechanism (one line):** integer-exact matching engine (0 B/op match path, L1/L2/L3 snapshots) plus a research harness (OFI, price-impact/Kyle λ, delta-CVD signals, deterministic simulator, Avellaneda–Stoikov maker backtest) whose studies mostly **refute** the popular claims against ground truth.

### A. What it predicts
- Signals only: OFI, price-impact, delta/CVD. The headline study answers the predictive question directly: **"Does order-flow imbalance predict the next move? Contemporaneous R² ≈ 0.24, predictive R² ≈ 0.0004 — a ~577× gap, and the little that remains points the other way."** → the repo's own finding is that OFI is essentially **not** predictive out-of-sample in its harness.
- `cmd/flowstudy` is framed as "what survives a control". No ML/classifier model.
- Verdict: **label = next-move prediction tested and largely NOT supported (R² ≈ 0.0004 predictive).**

### B. What it actually earns
- **Nothing live.** README: "It has never run a live market"; "Nobody runs this in production today."
- Simulated market-making exists (`examples/marketmaker`, A–S maker backtest) but no P&L figures are quoted in the README.
- Category-wise: direction = studied/refuted; spread capture = simulated (A–S backtest, no numbers in README); inventory appreciation = N/A; passive fill = simulated; liquidity provision = engine capability only; execution improvement = N/A.

### Checklist
| item | verdict | 1-line evidence |
|---|---|---|
| data source | YES (mixed) | primary = engine's own simulator ("The engine is its own data source — per-order (L3) event streams plus simulator ground truth"); also `cmd/l2capture` live Coinbase L2 |
| data granularity | YES | per-order (market-by-order) events in sim; L2 incrementals live |
| L1 vs L2 | YES (all) | "L1 / L2 / L3 (market-by-order) snapshots with sequence numbers" + `marketdata.L2Feed` |
| real trades vs synthetic | PARTIAL | core studies run on simulator ground truth; a live L2 capture path (Coinbase) is provided for OFI display |
| uses future info? | NO | contemporaneous-vs-predictive split is the explicit design (R² gap measured) |
| train/val/test split | DATA_GAP | not stated in README (may exist in docs/research, not verified) |
| overlapping labels? | DATA_GAP | not stated |
| purge/embargo? | DATA_GAP | not stated |
| transaction cost adjusted? | DATA_GAP | no fee/cost statement for the A–S backtest in README |
| queue uncertainty? | NO | queue-position model is listed as *future* work ("More signals — … a queue-position model") |
| latency considered? | NO | end-to-end latency measurements listed as roadmap, not done |
| adverse selection considered? | PARTIAL | price-impact study via Kyle's λ (`cmd/lambdastudy`, "cost of a block order"); no explicit markout/adverse-selection metric |
| gross vs net distinguished? | DATA_GAP | no P&L table in README |
| realistically executable? | NO | author states it is an experiment, never run live, API/protocol broken repeatedly, no independent review |

- **Success condition:** a popular claim survives the harness's ground-truth control (study aims to show what survives a control); the OFI predictive claim fails it.
- **Failure condition:** predictive R² ≈ 0.0004 with residual sign pointing the wrong way → OFI-directional hypothesis not supported.
- **Cost condition:** Kyle λ price-impact / block-order cost studied; fees not modelled.
- **Data condition:** simulated L3 (MBO) ground truth by default; optional live L2 (Coinbase); not a real-trade backtest by default.
- **Execution type:** engine supports limit GTC/IOC + market (both); maker backtest quotes limits.
- **Timescale:** engine µs-class match path; signals/studies at event→seconds scale.
- **Transferability to XAUUSD: PARTIAL** — the engine/harness is asset-agnostic infrastructure (integer tick/lot domain, external decimals at boundary) and could host XAUUSD data, but all evidence is simulator + Coinbase crypto, with zero XAUUSD result and no fees/latency model.

---

## 3. Hellblazer704/nanolob

**Existence:** EXISTS (`https://github.com/Hellblazer704/nanolob`, API 200, id 1302889811). Description: "Low-latency C++20 limit order book & matching engine with Binance L2 replay and an Avellaneda-Stoikov market-making simulator". Stars 0, forks 0 (as fetched).

**Mechanism (one line):** a C++20 LOB/matching engine (33 ns median add, lock-free SPSC ingest) that replays **real Binance BTCUSDT L2** (100 ms depth diffs + trades, validated 17/17 exact vs exchange snapshots) and runs an **Avellaneda–Stoikov** market-maker vs a naive fixed-spread control with a FIFO queue-position fill model.

### A. What it predicts
- Not a predictor repo; the strategy is **Avellaneda–Stoikov quoting**: reservation price `r = m − q·γ·σ²·τ`, half-spread `½·γ·σ²·τ + (1/γ)·ln(1 + γ/k)` — i.e. it *reacts to inventory and volatility*, it does not forecast returns.
- Fill probability is modelled implicitly via **FIFO queue position** and trade-through logic (queue-ahead consumed first; through-price ⇒ full fill; cancellation proration; opposite-best crossing ⇒ run over).
- Verdict: **label = fill occurrence/queue position (implicit), inventory-aware quoting; NO directional return forecast.**

### B. What it actually earns
- Documented, decomposed P&L over **25 min live BTCUSDT** (gross, no fees): **A–S total −23.59 USDT** (= spread capture −0.01 + inventory PnL −23.57); naive control **−23.51 USDT** (+0.05 + −23.56). Session rallied ~104 USDT; both were lifted on offers → short into the rise.
- Category-wise: direction = none; **spread capture** = yes, quantified (−0.01 / +0.05 USDT — "pennies"); **inventory appreciation** = yes, dominant (−23.57 / −23.56 USDT — "dollars"); passive fill = yes, via queue model (529 vs 183 fills); liquidity provision = yes (both quote passively); execution improvement = N/A (not an execution-optimisation study).
- Key self-stated lesson: "Spread capture is pennies; inventory is dollars. A passive quoting policy's real job is inventory control."

### Checklist
| item | verdict | 1-line evidence |
|---|---|---|
| data source | YES (real) | Binance websocket `@depth@100ms` + trade stream + REST snapshots via `binance.vision`, no API key (`scripts/download_binance.py`) |
| data granularity | YES | 100 ms L2 depth diffs + individual trades (2 live captures: 6 min + 25 min) |
| L1 vs L2 | L2 | aggregated price-level depth (one synthetic order per level); not MBO |
| real trades vs synthetic | YES (real) | live BTCUSDT capture; reconstruction validated: "17/17 snapshot validations exact", "490k level updates, 0 sequence gaps, 0 phantom matches" |
| uses future info? | NO | queue sim uses only observable flow; book mirror is removals-before-additions, regression-tested for phantom matches |
| train/val/test split | NO | no ML; parameters explicitly **not** calibrated ("A–S parameters are demo-scaled") |
| overlapping labels? | N/A | no label pipeline |
| purge/embargo? | N/A | no label pipeline |
| transaction cost adjusted? | **NO** | "**No fees or rebates.** Maker rebates and taker fees dwarf 1–2 tick edges in practice; every PnL number here would move materially." |
| queue uncertainty? | YES (disclosed) | queue-ahead estimated; cancellation proration is "a neutral guess — cancel positions are unobservable from L2" |
| latency considered? | **NO** | "**No latency model.** Quotes update on the next 100 ms diff" |
| adverse selection considered? | YES (core) | Phase 5, executed notebook: markouts −417/−676/−888 ticks (1s/5s/30s); fill vs no-fill gap −551 ticks |
| gross vs net distinguished? | NO | only gross is reported; fees/rebates explicitly excluded |
| realistically executable? | NO (as-is) | no fees, no latency, no self-impact, demo-scaled params, "Single sessions, one symbol … one sample" |

- **Success condition:** DATA_GAP — neither strategy wins in the one session; the study's success is the honest decomposition itself.
- **Failure condition:** a trending session → both quoters picked off; realized edge @30 s = −887 (A–S) / −759 (naive) ticks; total PnL negative.
- **Cost condition:** NO fee/rebate model → gross-only; acknowledged as materially distorting.
- **Data condition:** L2 (Binance 100 ms diffs) + trade stream; needs periodic REST snapshots for seeding/validation.
- **Execution type:** passive **limit** quotes only (both strategies quote; no market-order strategy).
- **Timescale:** 100 ms update cadence; markout horizons 1 s / 5 s / 30 s; 25-minute session.
- **Transferability to XAUUSD: PARTIAL** — the A–S + queue-position + PnL-decomposition + markout methodology ports directly to XAUUSD L2, but evidence is BTCUSDT-only, gross-only (no spread/fee realism) and latency-free.

---

## 4. tradingexpert/ordersim

**Existence:** EXISTS (`https://github.com/tradingexpert/ordersim`, API 200, id 1238640897). Description: "Inspectable execution simulator for order-book replay and latency-aware fill simulation". Stars 2, forks 0.

**Mechanism (one line):** a deterministic, inspectable **execution simulator** (Python reference engine + equivalent C++ engine) that replays observed MBO (Databento) or L2→reconstructed "virtual MBO" (Binance USD-M) and simulates place/cancel/fill/passive-fill with visible queue-ahead and latency models.

### A. What it predicts
- Explicitly "**not** a signal library" — it predicts **execution outcomes**, i.e. fill occurrence, filled quantity, and time-to-fill under stated queue and latency assumptions (the stated benchmark target).
- Verdict: **label = passive fill probability / fill quantity / time-to-fill (execution realism).**

### B. What it actually earns
- **Nothing itself** — no strategy, no P&L claim: "It is not a general backtesting framework. You own the strategy loop." Outputs are fill ledger, equity curve, execution summary (e.g. synthetic example prints `result.fills`, `result.execution_summary`).
- Category-wise: direction = N/A; spread capture = N/A; inventory appreciation = N/A; **passive fill = YES (primary modelling target)**; liquidity provision = modelled (own resting orders with queue-ahead); **execution improvement = the deliverable** (audit + latency-aware execution replay, not realised alpha).

### Checklist
| item | verdict | 1-line evidence |
|---|---|---|
| data source | YES | Databento MBO (observed); Binance USD-M L2+trades (reconstructed); normalized CSV/Parquet; synthetic fixtures |
| data granularity | YES | canonical `MBOEvent` (order-level add/cancel/modify/trade rows); ns timestamps |
| L1 vs L2 | YES (both) | observed MBO (L3-equivalent) + reconstructed virtual MBO from sequence-validated L2 depth |
| real trades vs synthetic | YES (both) | real Databento/Binance integrations + `fixtures.synthetic` for tests/examples |
| uses future info? | NO | deterministic replay; ordering is explicit (`gateway.advance_to(...)`), latency applied as a delay instead of peeking |
| train/val/test split | NO | no fitted model; validation challenge requests **held-out** observations (implies none shipped) |
| overlapping labels? | N/A | no label pipeline |
| purge/embargo? | N/A | no label pipeline |
| transaction cost adjusted? | YES (partial) | `InstrumentSpec` carries `commission_per_contract`; `docs/economics.md` documents execution economics |
| queue uncertainty? | YES (disclosed) | visible queue-ahead exposed; "recommended conservative policy and an optimistic sensitivity policy expose that uncertainty instead of burying it" |
| latency considered? | YES | `ConstantLatency(entry_ns=25_000_000)`; `examples/latency_demo.py` |
| adverse selection considered? | YES | demo `passive_orders_and_adverse_selection.py` — "fills are not automatically good news" |
| gross vs net distinguished? | YES | commission in `InstrumentSpec` + economics doc alongside fill/gross metrics |
| realistically executable? | PARTIAL | replays real data with documented assumptions, but is explicitly "not a live trading system"; hidden exchange FIFO remains unknowable |

- **Success condition:** measured book/trade alignment — first Binance study: **7,345,447 / 7,347,590 trades (99.9708%)**, all 3,328,132 L2 endpoints, **116,381 / 116,381** joinable top-of-book states; stated benchmark rewards "predictive execution realism … on held-out observations", not mere endpoint reproduction.
- **Failure condition:** trades that occur at snapshot/capture boundaries the evidence "could not place … safely"; queue assumptions that the repo concedes cannot be verified against Binance's hidden FIFO.
- **Cost condition:** commission per contract in `InstrumentSpec`; execution economics documented.
- **Data condition:** observed MBO (best fidelity) or L2 depth + trades reconstructed to virtual MBO.
- **Execution type:** both — `place_limit` (passive resting) and `place_market`.
- **Timescale:** event-level, nanosecond timestamps; latency example 25 ms; replay of full sessions.
- **Transferability to XAUUSD: PARTIAL** — the replay core is "independent of asset class, venue, and data vendor", so methodology transfers; but current integrations are only Databento (futures/equities) and Binance crypto, so an XAUUSD feed would need a new connector (`DataSource`) — no XAUUSD evidence.

---

## Cross-repo summary

| slug | exists | type | predicts | earns | XAUUSD transferability |
|---|---|---|---|---|---|
| twowaymind/orderflow-metrics | EXISTS | metrics library (TS/Py) | OFI→short-horizon move (lit. claim, unvalidated) | nothing (tooling only) | PARTIAL |
| intrepidkarthi/orderbook | EXISTS | engine + research harness (Go) | next move via OFI — **largely refuted** (R² ≈ 0.0004) | nothing live; sim only | PARTIAL |
| Hellblazer704/nanolob | EXISTS | C++20 engine + A–S MM sim | fill/queue (implicit), no return forecast | spread capture (pennies) + inventory PnL (dollars), **negative net-of-nothing session** | PARTIAL |
| tradingexpert/ordersim | EXISTS | execution simulator (Py/C++) | passive fill probability / fill quantity / time-to-fill | execution-realism audit, no alpha claim | PARTIAL |

**Common DATA_GAPs across all four:** none reports a train/validation/test split, purge/embargo, or an ML label pipeline (only ordersim references held-out validation as a *request* to third parties).
