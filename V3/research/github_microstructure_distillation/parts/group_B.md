# GROUP B — Market Making / Adverse Selection / Markout / Passive Fill

Task: `V3-HFT-GITHUB-MICROSTRUCTURE-DISTILLATION-003`
Mode: READ-ONLY GitHub distillation (no purchases, no signups, no MT5, no orders).
Date: 2026-09-22
Verification method: `api.github.com/repos/<slug>` for existence; `raw.githubusercontent.com` for README + core source. Every statement below is anchored to a file that was actually read.

## Scales used

**EVIDENCE_LEVEL**
- **E0** — claim only; no code/data/artifact to check.
- **E1** — code exists but evidence is synthetic-only or self-referential; headline claims unverifiable from the repo.
- **E2** — code + tests, internally consistent, but synthetic/parametric data only.
- **E3** — uses real L2/L3 market data (or a real parsed feed) with a reproducible pipeline.
- **E4** — real data + realistic microstructure (queue/latency/costs) + out-of-sample validation.
- **E5** — E4 plus independent replication and demonstrated net-of-cost OOS edge.

**TRANSFERABILITY**
- **A** — directly reusable on FXTM as-is.
- **B** — reusable with clear adaptation to our data/venue.
- **C** — mechanism/idea transferable; implementation not.
- **D** — conceptual reference only.
- **E** — not transferable.

## Repo selection (GitHub API search)

Queries run via `search/repositories`: `market+making+adverse+selection` (94 hits), `markout+microstructure` (1 hit), `fill+probability+order+book` (3 hits). Two priority repos were given; three additional repos were found and verified as real:

| # | slug | stars | lang | verified |
|---|------|-------|------|----------|
| 1 | Leotaby/Market-Making-Simulator | 1 | Python/Jupyter | api.github.com → 200 |
| 2 | diegourda/Statistical-Arb-MM | 0 | C++20 | api.github.com → 200 |
| 3 | tfrmma/realistic-mm-backtester | 9 | Python/Rust | api.github.com → 200 |
| 4 | KlishevDA/Market-Microstructure-and-Latency-Effects-in-L2-Market-Making | 1 | Python | api.github.com → 200 |
| 5 | xiaohany-cmu-S26/lob-fill-engine | 0 | Python | api.github.com → 200 |

---

# Repo 1 — Leotaby/Market-Making-Simulator

**EXISTS** (MIT, `main`, id 1246100015, created 2026-05-21, pushed 2026-09-05).
Files read: `README.md`, `src/market_maker/simulation.py`, `src/market_maker/agents.py`, `src/market_maker/metrics.py`.

## REPOSITORY_CARD
1. **Claims** — Agent-based MM simulator on Avellaneda-Stoikov; compares naive fixed-spread vs A-S closed-form vs tabular Q-learning; reports PnL, inventory risk, and adverse-selection (markout) diagnostics. README table: A-S Sharpe 8.77 vs fixed 4.63 vs Q-learn 6.74.
2. **What code actually does** — `MarketMakingEnv`: mid = arithmetic Brownian motion `dS = sigma dW`; bid/ask fill by independent Bernoulli draws with `P(fill in dt)=1-exp(-A*exp(-k*δ)*dt)`; inventory capped at ±50, quotes pulled on the over-full side; terminal PnL = cash + inventory*mid. `AvellanedaStoikovAgent` implements `r = s - q·γ·σ²·τ` and `δ = γσ²τ + (2/γ)ln(1+γ/k)` exactly. `compute_markout` = mean signed per-fill PnL `horizon_steps=10` later.
3. **Data needed** — none. Fully parametric; no file ingestion, no feed, no LOB.
4. **Label** — none (no supervised target; RL uses wealth-change reward).
5. **Execution assumptions** — fill = stochastic intensity per side per step. No matching, no resting orders, no partial fills, no latency, no queue. Both sides can fill in the same step independently.
6. **Cost** — **none**. No fees, no slippage, no impact, no spread crossing cost. PnL is spread capture only.
7. **OOS evidence** — **none temporal**. 2,000 Monte-Carlo sessions with *paired seeds* across strategies (a variance-reduction device, not out-of-sample validation). No train/test split, no walk-forward.
8. **What failed** — README documents one real bug: the first inventory-skew test failed because `env.step()` advances the RNG, so "same paths" required fresh identically-seeded envs; fixed by re-seeding on construction.
9. **Synthetic** — everything. Mid price, fills, and adverse selection are all generated processes.
10. **Real** — the A-S closed-form arithmetic (reservation price, spread, markout sign convention) is correct and matches the literature.
11. **Transfers to FXTM** — (a) the markout diagnostic definition (`sell: p - m_{t+h}`, `buy: m_{t+h} - p`, mean per fill) is the exact desk metric V3 should compute on its own fills; (b) the reservation-price/skew S-shape as an intuition for inventory quoting; (c) the *paired-seed* comparison discipline for A/B of two strategies.
12. **Does not transfer** — the environment itself; the intensity fill law; the injected-drift AS; the Monte-Carlo PnL numbers.
13. **V3 should steal** — the markout implementation and the paired-seed A/B harness.
14. **V3 should reject** — any claim that this measures real adverse selection. AS here is a *post-fill injected drift* (`informed_impact`), so "markout moves when informed flow rises" is tautological: you moved the mid yourself. Also reject using its Sharpe/PnL as evidence of edge.

- **EVIDENCE_LEVEL: E2** — clean reproducible code + 8 CI tests, but synthetic/parametric only, zero real data, zero costs.
- **TRANSFERABILITY: C** — mechanism (markout, A-S skew, paired A/B) is portable; nothing else.
- **FAILURE_MODE: tautological adverse selection / fabricated realism.** The "author's own limitation" is explicit and honest: *"Not an HFT/low-latency system. There is no real limit-order book with queue priority, no market-data feed, and no latency model. 'Fills' come from a stochastic intensity, not from matching against resting orders."* and *"Informed flow is a reduced-form model. Adverse selection is injected as a post-fill drift, which captures the effect... without modelling the informed trader's decision explicitly."* and *"this simulator is discrete and simplified, so I call it a benchmark rather than 'optimal'."* The danger is a downstream reader treating its AS/markout results as empirical.

---

# Repo 2 — diegourda/Statistical-Arb-MM

**EXISTS** (MIT, `main`, id 1126267103, created 2026-01-01, pushed 2026-04-09).
Files read: `README.md`, `PERFORMANCE.md`, `src/main.cpp`, `src/strategy/StatArbMM.hpp`, `src/execution/ExecutionSimulator.hpp`, `src/execution/TransactionCosts.hpp` (referenced), `src/backtest/Simulator.hpp`, `src/backtest/WalkForward.hpp`, `src/analytics/OFIValidation.hpp`, `docs/model_spec.md`, `docs/sensitivity.md`, `docs/failure_modes.md`, `docs/design_decisions.md`, `temp_lobster_test.csv`, `requirements`.

## REPOSITORY_CARD
1. **Claims** — "production-grade C++20 statistical arbitrage market-making system": A-S optimal quoting + cointegration pair selection + Kalman hedge ratio + order-flow toxicity. README claims **"reducing adverse selection by an estimated 30%"**, "zero-allocation pre-trade checks completing in under 100ns", and 16.41M add-order ops/sec. Description advertises "high-frequency limit order book (LOB) data".
2. **What code actually does** — `StatArbMM.hpp` is a faithful A-S implementation: reservation price, `optimalSpread` with the intensity term, terminal-time `tau` degradation, VPIN/Kyle spread modulation, z-score + OFI gating, inventory-scaled sizing, pre-trade risk checks. `ExecutionSimulator.hpp` *contains* queue logic (`queueAhead`, `fillProbability = volume/(volume+queueAhead)` with `exp(-decayRate*elapsed)` decay, partial fills, `adverseSelectionProb = max(0, ±ofi·0.5)`). But **the shipped demo (`main.cpp`) bypasses the executor entirely**: fills are `rng() % 100 < 8` (flat 8%), side chosen by `z < -1.0`, qty fixed at 100. Queue, latency and `fillProbability` are never exercised in the demo.
3. **Data needed** — LOBSTER L3 format is supported by `src/replay/LobsterParser.hpp`. **No data is shipped**: `data/raw/`, `data/samples/`, `data/processed/` contain only `.gitkeep`; `config/instruments.yaml` and `config/strategy_params.json` are 0 bytes. The only data file, `temp_lobster_test.csv`, is 2 rows of hand-made values (`34200.000000001,1,100,100,5000000,1`).
4. **Label** — none.
5. **Execution assumptions** — as coded: latency = base + uniform jitter; passive orders rest and get partial fills; marketable orders sweep one level. As *demoed*: none of the above (flat 8% fill).
6. **Cost** — Almgren-Chriss model exists in `TransactionCosts.hpp` and is called in both `Simulator::onFill` and `main.cpp` (`txCost.setDailyVolume(1e6)`), but impact/eta parameters are arbitrary, not calibrated.
7. **OOS evidence** — a real `WalkForward.hpp` framework exists (rolling train/test, `overfitRatio = OOS Sharpe / IS Sharpe`, thresholds 0.5/0.3). **No walk-forward output is shipped, and no real dataset exists to run it on.** The "30% AS reduction" is produced by `OFIValidator`, which runs a *standalone z-score-only toy simulation* (no engine, no queue, no book) and defines "adverse selection" as `sum |pnl| over losing trades`.
8. **What failed** — `docs/failure_modes.md` is candid and generic-but-real: cointegration breakdown, flash-crash "nickel problem", **adverse-selection spiral** ("being filled is NOT always good... high fill rates often indicate your quotes are too aggressive"), parameter drift, overfitting ("walk-forward is necessary but not sufficient"). Also: fixed-spread MM gave negative Sharpe; z-score-without-OFI produced 30% more trades and 40% more adverse selection; AR(1) OLS underestimated OU half-life by 20-30% vs MLE.
9. **Synthetic** — the entire demonstration: `main.cpp` generates a cointegrated pair via `mt19937_64` + normal noise. Performance numbers are micro-benchmarks of an order-book data structure, not market performance.
10. **Real** — the A-S math, the cointegration/Kalman/OFI/VPIN/Kyle classes, the risk-manager structure, and the walk-forward/overfit-ratio *design* are genuine engineering.
11. **Transfers to FXTM** — the A-S implementation with intensity calibration (`calibrateIntensity` does log-linear OLS of `log(fillRate) = logA - k*spread`) is directly useful; the `overfitRatio = OOS/IS` discipline; the failure-modes taxonomy as a checklist; the adverse-selection-spiral detector idea (rolling `AS/spread_capture > 1.5`).
12. **Does not transfer** — the headline numbers; the "production-grade" framing; the queue/latency code (present but unexercised and uncalibrated); the 30% figure.
13. **V3 should steal** — the intensity-calibration OLS; the `overfitRatio` diagnostic; the AS-spiral detection heuristic; the failure-modes doc as a pre-mortem template.
14. **V3 should reject** — **every headline performance/AS claim.** See the required disproof below.

### Required disproof — "adverse selection reduction ~30%": demonstrated vs claimed
- The claim appears only as an assertion in `README.md` ("...reducing adverse selection by an estimated 30%").
- The only quantification path is `analytics::OFIValidator::validate()`. That class:
  - takes bare `zScores`, `ofiValues`, `prices` vectors — **no order book, no queue, no spreads, no fills from an engine**;
  - simulates a *directional* z-score strategy (`position = ±1`), not passive market making;
  - defines adverse selection as `adverseSelection += |pnl|` for trades that turned out `pnl < 0` — i.e. *realized losses*, not markout against a future mid;
  - has no fee/impact/queue model.
- Therefore the "30% reduction" is a **self-referential metric computed on a synthetic, engine-free, direction-only toy**. It does not demonstrate that OFI gating reduces adverse selection in live or even realistic-simulation passive quoting.
- **Actually demonstrated:** OFI gating is a plausible filter; the *code to build* an A/B comparison exists; nothing about the size of the effect. **Claimed:** a 30% microstructure improvement. Gap: unbridgeable from the artifacts shipped.

- **EVIDENCE_LEVEL: E1** — substantial code and tests exist, but the headline claims are supported only by synthetic/self-referential evidence; no real data, empty config/data dirs, demo bypasses the realistic executor.
- **TRANSFERABILITY: C** — A-S + intensity calibration + overfit-ratio discipline are portable ideas; no real data path is exercised.
- **FAILURE_MODE: claim inflation.** A zero-star repo labelled "production-grade" with a 30% AS figure produced by a metric that isn't markout, on data that doesn't exist, through an executor the demo doesn't call. Its own `failure_modes.md` warns about exactly this class of overfitting, yet the README's numbers are produced outside any walk-forward.

---

# Repo 3 — tfrmma/realistic-mm-backtester

**EXISTS** (`main`, id verified via API, 9 stars, Python + Rust/PyO3, pushed 2026-07-17).
Files read: `README.md`, `mmbt/queue/fifo.py`.

## REPOSITORY_CARD
1. **Claims** — "FIFO queue simulation for market making"; tick-by-tick L2/L3 replay, iceberg detection + cancel inference, lognormal latency modeling, maker/taker execution, multi-asset, adverse-selection metrics.
2. **What code actually does** — This is the real thing at the queue level. `FIFOQueueState.process_trade` maintains `qty_in_front`; a trade consumes `trade.size*(1+frac)` where `frac` comes from a `CancelModel`; overshoot fills the order; `fill.qty_in_front` is reported. `FIFOQueueSimulator` registers every resting order, honours cancels, has a Rust-accelerated inner loop (`mmbt._core.FIFOQueueCore`) with pure-Python fallback and parity tests. `ProBacktestEngine` applies latency and evaluates taker/post-only against the *true* book after `order_us` delay.
3. **Data needed** — user-supplied L2/L3 ticks via `TickLoader.from_csv` / `from_parquet`, multi-level book columns supported; `CSVExchange`/`Exchange` adapters; `BitfinexL3Exchange` referenced for ground-truth cancels. No dataset shipped.
4. **Label** — none.
5. **Execution assumptions** — FIFO queue, per-order `qty_in_front`, cancel models (`ReduceRatioCancelModel`, `ProbQueueCancelModel`), lognormal per-event latency (feed/order/cancel), taker sweep across levels with IOC semantics, post-only rejection.
6. **Cost** — `fee_rate_maker` / `fee_rate_taker` (negative maker fees = rebates supported).
7. **OOS evidence** — real framework: `out_of_sample_validate` (chronological split, no shuffle), `walk_forward_validate` (n_folds, expanding/rolling), `walk_forward_summary` reporting `oos_profitable_frac`, avg/std OOS PnL, and `param_consistency`. **No OOS result is published in the repo.**
8. **What failed** — code comment documents a real silent bug: `_build_rust_core` used `getattr(cancel_model,'cancel_ratio',0.20)`, so a `ProbQueueCancelModel` silently ran a *fixed 0.20* ratio in Rust — "same object, wrong model, no warning." Fixed by concrete-type checking. Also: `known_cancels` (ground-truth cancels) is honoured only on the pure-Python path, not in Rust.
9. **Synthetic** — `data/synthetic.py` (random walk) exists for smoke tests; engines accept it.
10. **Real** — real-data-capable by design (CSV/Parquet L2/L3), real FIFO queue, real latency, real fees, real OOS framework, 80 tests, CI incl. Rust/Python parity.
11. **Transfers to FXTM** — the FIFO `qty_in_front` model and cancel-inference from visible size deltas is exactly the mechanism V3 needs for passive fill realism; the latency-cost accounting (`queue_displacement_us`); the fee model; the walk-forward/param-consistency reporting. The queue model is venue-agnostic Python.
12. **Does not transfer** — specifics of crypto/equity tick schemas; the book-depth assumption (depth capped by what your data provides — a problem for thin FXTM DOM).
13. **V3 should steal** — per-order FIFO `qty_in_front` + cancel model; `queue_displacement_us` (latency cost of a late cancel); `walk_forward_summary.param_consistency` as a stability gate.
14. **V3 should reject** — the assumption that cancel inference from visible size deltas is identifiable (it cannot separate cancels from hidden/iceberg fills without ground truth); and treating the framework's existence as evidence of edge.

- **EVIDENCE_LEVEL: E3** — genuine L2/L3 replay, FIFO queue, latency, fees, and an OOS framework; no shipped dataset and no published OOS PnL, so not E4.
- **TRANSFERABILITY: B** — queue/cancel/latency/fee machinery is directly adaptable to our tick data; needs re-wiring to the FXTM feed.
- **FAILURE_MODE: unfalsified edge + unidentifiable cancels.** A realistic harness with no demonstrated profitable OOS result; and the core inference (how much of a level-size drop was ahead of you) is fundamentally unidentifiable without hidden-order ground truth. The author is honest: *"`overfit_flag` is a cheap heuristic... not a rigorous test"*; *"`MultiAssetEngine` has no FIFO/latency-aware counterpart yet"*; *"CSV/Parquet book depth is capped by whatever your data provides."*

---

# Repo 4 — KlishevDA/Market-Microstructure-and-Latency-Effects-in-L2-Market-Making

**EXISTS** (`main`, 1 star, Python, size ~4.8MB, created 2026-01-31, pushed 2026-01-31 — single-commit research drop).
Files read: `README.md`, `engine/queue_model.py`, `engine/execution.py`.

## REPOSITORY_CARD
1. **Claims** — Binance L2 (top-N) microstructure research: collect snapshot + depth diffs, rebuild a *coherent* L2 stream, compute book features, run a simple passive quoting + fill simulation, and evaluate PnL / inventory / **markout** vs latency.
2. **What code actually does** — `QueueModel`: on `place()` you join the back of the visible queue (`q_ahead = level_qty`); on each book update, if the level size *decreases* by `dec`, a fraction `rho*dec` is assumed to have been ahead of you; when `q_ahead` hits 0 the residual decrease fills you. `simulate_maker()` in `execution.py` replays a JSONL book stream with `place_delay_ms` and effective `cancel_delay_ms` (late cancels), producing a fill list. `reports/markout.py` (referenced) computes markout at horizons `h` ms: `bid: mid_future - fill_px`, `ask: fill_px - mid_future`, and plots mean markout curve + per-fill scatter.
3. **Data needed** — **real Binance L2**: `@depth` websocket at 100ms + HTTP snapshot, replayed with strict sequence continuity (`U..u`, bridging event, `next U == last_u+1`). Output `*_replay_<s>s_L<levels>.jsonl`.
4. **Label** — none; markout is a diagnostic.
5. **Execution assumptions** — deterministic queue model parameterised by `rho ∈ [0,1]`; latency modelled as place/cancel delays; **no fees** modelled in the code read.
6. **Cost** — none visible (no fee/impact in `queue_model.py` / `execution.py`).
7. **OOS evidence** — **none**. This is a single 600s-per-symbol research run with a tuning loop ("what to tune next"), not a walk-forward. No train/test split.
8. **What failed** — the README does not report failures; it frames `rho` as a sensitivity knob. The honest part is the explicit admission that the queue model *is* an assumption.
9. **Synthetic** — none in the fill path; the whole point is real Binance L2. (Features/plots come from real replay data.)
10. **Real** — real L2 collection + sequence-consistent replay + real markout computation + real inventory-skew quoting + real latency simulation.
11. **Transfers to FXTM** — (a) the **markout script** is directly portable and is exactly the toxicity diagnostic V3 needs; (b) the sequence-consistency replay discipline (drop stale, bridge, enforce contiguity) is the correct pattern for any incremental DOM feed; (c) inventory-skew quoting in ticks; (d) the "look at equity *and* markout together — PnL can look fine while markout is negative" research rule.
12. **Does not transfer** — Binance-specific schema; the assumption that `rho*dec` of a level decrease was ahead of you (same identifiability problem as Repo 3, and worse on thin books).
13. **V3 should steal** — the markout-at-horizons methodology and plots; the L2 replay bridge/contiguity check; the "equity + markout together" acceptance gate.
14. **V3 should reject** — treating `rho`-based queue fills as calibrated truth; and any PnL number without fees.

- **EVIDENCE_LEVEL: E3** — real L2 data, replay, queue model, markout; but short runs, no OOS, no fees.
- **TRANSFERABILITY: B** — markout + replay discipline + inventory skew transfer cleanly; the queue fidelity depends on our (likely thinner) FXTM DOM.
- **FAILURE_MODE: uncalibrated queue luck.** Fills hinge entirely on `rho` ("how much of the reduction is assumed ahead of you" / "how 'lucky' you are"), which is a free parameter never calibrated to ground truth. The author is explicit: *"This is the key approximation: we are a passive maker sitting in the queue at a given price level."*

---

# Repo 5 — xiaohany-cmu-S26/lob-fill-engine

**EXISTS** (`main`, 0 stars, Python, size ~13.5MB, created 2026-04-27, pushed 2026-04-28).
Files read: `README.md`, `fill_estimator.py`.

## REPOSITORY_CARD
1. **Claims** — Fill-probability estimator trained on LOBSTER tick data: predicts `P(passive order at best bid/ask fully fills within 1s)` from book microstructure, order size, and intraday seasonality, with walk-forward validation and López de Prado-style purging/embargoing/uniqueness weighting. Phase 3 of a larger LOB + MM simulator (Phase 4 = EV-based quoting using fill probability).
2. **What code actually does** — Label construction: a synthetic passive order is placed at the **back of the queue** at best bid/ask at each `event_type==1` (new limit) message, size matching the original order; **filled iff cumulative execution volume at-or-through that price within 1s ≥ `queue_ahead + order_size`** (size-aware, via `numpy.searchsorted`). Features (all backward-looking): `imbalance`, `depth_imbalance`, `queue_ahead`, `spread_norm`, `local_vol`, `aggressive_flow`, `direction`, `order_size`, `time_sin/cos`, `time_bucket`, `vol_regime`, `day_of_week`. Models: LogReg / RandomForest / HistGradientBoosting. `fill_estimator.py` ships `FillEstimator` with `predict_proba`/`estimate` and a `TemperatureScaler` post-hoc calibrator.
3. **Data needed** — **real LOBSTER** NASDAQ L3/L2: `<sym>_message_10.csv` (event_type 1/2/3/4/5/7) + `<sym>_orderbook_10.csv` (10 levels); AAPL July 2023; also CSCO for cross-stock test. Data is licensed by LOBSTER — **not shipped**.
4. **Label** — binary `filled within 1s`, defined by `cum_volume ≥ queue_ahead + order_size`.
5. **Execution assumptions** — you are at the **back of the visible best-level queue**; no hidden order modelling; fill is a volume-threshold event within a fixed 1s horizon.
6. **Cost** — none (it is an estimator, not a backtester). EV is framed as `prob*spread_capture - (1-prob)*inventory_cost`.
7. **OOS evidence** — **strong and disciplined**: chronological 70/15/15; no shuffling anywhere; feature selection (MI, RFECV, GA) on the training set only; `vol_regime` threshold fitted on train only; purging (drop train rows whose 1s label window enters val); embargo (first 30s of val/test dropped); `TimeSeriesSplit(n_splits=5, gap=500)`; **sample-uniqueness weights** (AFML Ch.4); day-level AUC ± std (not tick-level, to avoid autocorrelation-inflated CIs); Brier + calibration curves; **cross-stock generalization AAPL↔CSCO** as a robustness substitute for macro-regime variation.
8. **What failed** — the author is candid: *"The one-month data scope is insufficient for monthly/macro regime variation; cross-stock generalization is the substitute robustness test."* Experiment 2 expects (and reportedly finds) macro/regime variables add <1% AUC — i.e. `vol_regime`/`day_of_week` add nothing at the 1s horizon.
9. **Synthetic** — the labellable orders are *synthetic* (injected at each new-limit message); the *data and fills* are real LOBSTER.
10. **Real** — real LOBSTER L3 messages + real order-book states; real queue-ahead; real size-aware fill outcomes; real out-of-sample discipline.
11. **Transfers to FXTM** — this is the strongest **methodology** transfer for V3's passive-fill model: (a) the size-aware queue-based label (`cum_vol ≥ queue_ahead + size`); (b) the purge/embargo/uniqueness + day-level-AUC evaluation protocol; (c) the feature set and its stationarity justifications; (d) the explicit "don't use raw price levels/timestamps" stationarity rule; (e) temperature-scaling calibration.
12. **Does not transfer** — LOBSTER schema; the assumption of a deep, visible NASDAQ book (FXTM DOM is thinner and possibly unreliable); the 1s horizon is equity-specific.
13. **V3 should steal** — the fill-label definition, the purge/embargo/uniqueness CV protocol, day-level (not tick-level) uncertainty reporting, and the cross-instrument generalization test.
14. **V3 should reject** — importing the model itself (features/horizon are LOBSTER/AAPL-specific); and treating the estimator as validated for strategy PnL — it never computes net PnL.

- **EVIDENCE_LEVEL: E3** — real LOBSTER data with rigorous OOS discipline on the *fill-probability* task, but it is an estimator: no strategy PnL, no costs, no execution path.
- **TRANSFERABILITY: B** — the labeling + CV methodology is directly reusable on our data; the fitted model is not.
- **FAILURE_MODE: model-dependent label + no economic closure.** "Filled within 1s" assumes the order sits at the back of the *visible* best-level queue with no hidden liquidity — if FXTM matching differs (or the DOM hides size), the label is systematically wrong, and a well-calibrated probability on a wrong label is still wrong. Also: a probability is not an edge — the repo stops at Phase 3 and never demonstrates EV-positive quoting.

---

## Cross-repo synthesis

| slug | EVIDENCE | TRANSFERABILITY | real L2/L3? | queue pos? | fill prob | adverse selection | inventory/A-S | OOS | costs |
|------|----------|-----------------|-------------|------------|-----------|-------------------|---------------|-----|-------|
| Leotaby/Market-Making-Simulator | E2 | C | **no** | no | stochastic intensity A·exp(−kδ) | **injected post-fill drift (off by default)** | yes (full A-S) | no (MC paired seeds) | **none** |
| diegourda/Statistical-Arb-MM | E1 | C | parser only, **no data** | code exists, **demo bypasses** | `vol/(vol+queue)` (unexercised) | `±ofi·0.5` heuristic, **no markout** | yes (full A-S + signals) | framework only, no run | A-C model, uncalibrated |
| tfrmma/realistic-mm-backtester | E3 | B | **capable (CSV/Parquet)** | **yes, per-order FIFO** | implicit via queue + cancel model | reporting/plots + displacement cost | inventory risk mgr + skew strat | **yes (OOS + walk-forward)** | maker/taker fees |
| KlishevDA/…L2-Market-Making | E3 | B | **yes (Binance L2)** | **yes (rho-based)** | deterministic via rho | **real markout at horizons** | inventory skew | no | none |
| xiaohany-cmu-S26/lob-fill-engine | E3 | B | **yes (LOBSTER L3)** | **yes (queue_ahead)** | **ML P(fill within 1s)** | not modelled | EV framing only | **yes, rigorous (purge/embargo)** | none |

**Three things V3 can actually reuse**
1. **Markout methodology** (Repos 1 + 4): signed per-fill PnL vs future mid at multiple horizons; use *equity + markout together*; never accept a PnL number whose markout is negative.
2. **Passive-fill modelling stack** (Repos 3 + 5): per-order `qty_in_front` FIFO with a cancel model, plus a size-aware fill label `cum_vol ≥ queue_ahead + order_size`, evaluated with purge/embargo/uniqueness CV and day-level uncertainty.
3. **A-S + intensity calibration + overfit ratio** (Repos 1 + 2): estimate `k` by log-linear OLS on `(spread, fillRate)`, and gate every parameter set on `OOS Sharpe / IS Sharpe`.

**Three traps to avoid**
1. **Injected-vs-measured adverse selection** (Repo 1): if you generate the adverse move, you have not measured toxicity.
2. **Claim inflation** (Repo 2): a "30% AS reduction" produced by a non-markout, non-executed, synthetic toy — verify every headline against the code that produced it.
3. **Uncalibrated queue luck** (Repos 3 + 4): the fraction of a level-size drop that was ahead of you is unidentifiable without ground truth; treat it as a sensitivity parameter, never as truth.
