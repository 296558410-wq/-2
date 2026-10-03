# GROUP C+D — Execution-aware alpha & failed-HFT research (negative evidence distillation)

- **Task:** V3-HFT-GITHUB-MICROSTRUCTURE-DISTILLATION-003 (READ-ONLY)
- **Scope:** Priority group C+D — execution cost pushed into the decision rule, and documented failure modes.
- **Method:** GitHub REST search (`/search/repositories`) → every slug re-verified via `https://api.github.com/repos/<slug>` (HTTP 200) → README fetched via `/repos/<slug>/readme` (base64) with raw.githubusercontent fallback → core code fetched from raw.githubusercontent at `HEAD`.
- **Date of audit:** 2026-09-22
- **Repos verified HTTP 200:** 19 distinct slugs. **Repos carded:** 8. **Repos verified-but-not-carded:** 11 (listed in §4).
- **No purchases, no signups, no MT5, no orders. All requests were unauthenticated GETs.**

## 0. Evidence scales used in this file

**EVIDENCE_LEVEL** (what actually backs the claim):

| Level | Meaning |
|---|---|
| E0 | Claim only; no code, no artifacts |
| E1 | README claim + code present, no committed results |
| E2 | Code + committed results, no validation/invariant tests |
| E3 | Code + committed results + some tests; single session/small sample or data not shippable |
| E4 | Code + committed results + reproducibility artifacts + explicitly documented limitations/self-audit |
| E5 | Independently reproducible end-to-end on public data with locked provenance (hashes/manifests) |

**TRANSFERABILITY to FXTM** (retail FX/CFD on MT5: spread + commission, NO order-level L2, queue position unobservable, latency real but unpriced, ~free short, no consolidated tape):

| Grade | Meaning |
|---|---|
| A | Directly usable — logic survives the absence of order-level data |
| B | Method/formula transfers; instrument or data specifics must be replaced |
| C | Concept transfers only; needs L2/event data FXTM does not expose → proxy required |
| D | Transfers only as a cautionary/accounting discipline |
| E | No transfer |

**NEGATIVE_EVIDENCE_TYPE:** COST_ERASED_ALPHA / REAL_TICK_FAILURE / SYNTHETIC_TICK_FAILURE / OVERLAP_FAILURE / OOS_FAILURE / TAIL_DEPENDENCE / EXECUTION_FAILURE / QUEUE_ASSUMPTION_FAILURE.

---

## 1. VERIFICATION LOG (every carded slug, live-API checked)

| # | slug | HTTP | stars | lang | pushed | pushed file evidence |
|---|---|---|---|---|---|---|
| 1 | `siddhantsingh-1/execution-aware-alpha-backtester` | 200 | 0 | Python | 2026-08-18 | README 10,216 B + `src/alpha/{labels,execution,backtest}.py` fetched |
| 2 | `snowkings/QIP_adverse_selection` | 200 | 0 | Python | 2026-09-18 | README 12,346 B |
| 3 | `himagna16/kalshi-microstructure` | 200 | 0 | Python | 2026-09-08 | README 15,956 B + `scripts/strategy_backtest.py` fetched |
| 4 | `KlishevDA/Market-Microstructure-and-Latency-Effects-in-L2-Market-Making` | 200 | 1 | Python | 2026-01-31 | README 8,892 B |
| 5 | `aryansiwach/execution-market-microstructure` | 200 | 0 | Python | 2026-09-09 | README 4,659 B |
| 6 | `gelatotrade/implementation-shortfall-hyperliquid` | 200 | 2 | Python | 2026-05-28 | README 16,094 B |
| 7 | `Trumplus/AAPL-Limit-Order-Fill-Probability-Forecast` | 200 | 2 | Python | 2026-08-03 | README 15,114 B |
| 8 | `AshJha0/electronic-trading` | 200 | 28 | Java | 2026-09-06 | README 14,691 B |

Every README above was retrieved as bytes from GitHub (not paraphrased from search snippets). Quoted numbers below are copied from those files.

---

## 2. REPOSITORY CARDS

### CARD 1 — `siddhantsingh-1/execution-aware-alpha-backtester`

**EVIDENCE_LEVEL: E4** — code + committed derived sample + 31 tests + reproduced result tables; raw licensed TAQ deliberately not shipped.
**TRANSFERABILITY: B** — the gross-vs-net *arithmetic* is exactly V3's problem and needs no order-level data; the queue simulator needs L1 NBBO FXTM does not publish.
**NEGATIVE_EVIDENCE_TYPE: COST_ERASED_ALPHA** (primary), secondary **QUEUE_ASSUMPTION_FAILURE**.

1. **Claims:** Short-horizon return prediction on NYSE TAQ microstructure; headline claim is that the strategy *loses money*. OOS IC 0.473 (LightGBM) / 0.442 (ridge); gross PnL **+$1,475,656**, total cost **$13,111,643**, net PnL **−$11,635,987** on $1M gross exposure; gross Sharpe +0.948, **net Sharpe −0.733**. Top-vs-bottom-decile realised edge **9.11 bps** vs median half-spread **5.14 bps**.
2. **What code does:** `src/alpha/labels.py` (forward mid log-return labels), `features.py` (OFI + Lee-Ready signed flow + microprice, backward as-of quote join), `cv.py` (purged walk-forward + 300-bar embargo), `execution.py` (`QueueSimulator` — queue-ahead state machine, pro-rata cancellation apportionment, `reprice_on_move`), `backtest.py` (cost-aware backtest + attribution).
3. **Data needed:** WRDS Daily TAQ millisecond (23 Dow components, one session 2024-11-19; 10.2M NBBO + 3.5M trades → 538,199 1-s bars). Licensed — not committed; derived 16,100-row feature sample is.
4. **Label:** `y_t = log(mid_{t+H}) − log(mid_t)`, H=10 bars. Explicit: **mid, not trade price** ("trade prices carry bid-ask bounce … would inflate measured predictability"). Labels overlap by construction → purging justified in-file.
5. **Execution assumptions:** passive post at touch; queue_ahead(0) = displayed size at level; queue drained by (a) trades at/through price, (b) size reductions unexplained by trades = cancellations, **apportioned pro-rata**; reprice loses queue position. Stated as **optimistic** vs reality (cancellations cluster at the back). Simulated passive fill rate **49.2%**, median wait 2 bars, **203/400 cancelled by market moving away**.
6. **Cost:** charged in `backtest.py` in size order — (1) half-spread per side, (2) square-root impact on participation × local vol, (3) maker rebate 0.10 bp / taker fee 0.25 bp, (4) **adverse selection measured from data** (mid move during the queue wait), not assumed. Cost per unit turnover **27.1 bps**.
7. **OOS:** purged walk-forward with embargo; test asserts `label_end[train].max() < test_start` per fold. Ridge baseline on identical folds. Time-of-day feature deliberately *excluded* because it was collinear with fold index (single-day) — removed changed IC by 0.0007.
8. **What failed:** The signal. "A signal that is highly statistically significant and completely untradeable is the normal outcome at this horizon." Mechanism: edge 9.11 bps < ~10.3 bps round-trip spread cost. **Ablation:** removing 5 reversion features drops IC 0.473 → **0.177** → almost all predictability is inside-spread short-horizon mean reversion = the market maker's edge, not a taker's.
9. **Synthetic:** `data/sample/features_sample.parquet` (derived from real TAQ); synthetic fixtures in tests only.
10. **Real:** Real TAQ, real NBBO, real tape; one session only (declared binding limitation: 5 folds = 5 slices of one regime; no annualisation performed because short-horizon PnL violates independence).
11. **Transfers to FXTM:** (a) the **spread-vs-edge inequality as a pre-trade gate** — compute realised edge per unit and compare to round-trip cost before believing any signal; (b) gross/net with attribution by cost type; (c) the reversion-ablation diagnostic (if removing reversion features kills the IC, the edge is the maker's, not a taker's) — directly applicable to V3's markout work; (d) purged CV + embargo for overlapping labels.
12. **Does NOT transfer:** the queue simulator (needs L1 aggregate sizes + trade tape FXTM does not expose per-venue); maker rebates (FXTM charges commission, gives no rebate); US-equity tick/spread regime; per-session single-regime Sharoe.
13. **V3 should steal:** (i) the *labelling discipline* — mid-based labels, drop (never pad) truncated labels, per-symbol shift; (ii) the cost ladder ordered by size with **adverse selection measured, not assumed**; (iii) non-overlapping rebalancing (stated reason: overlapping rebalancing counts the same price move H times and inflates both PnL and turnover); (iv) reporting `cost per unit turnover` alongside net Sharpe.
14. **V3 should reject:** the absolute numbers / one-session conclusion; treating 49.2% passive fill rate as an FXTM-valid constant (it is an L1-equity proxy); the pro-rata cancellation assumption as unbiased (author labels it optimistic).

---

### CARD 2 — `snowkings/QIP_adverse_selection`

**EVIDENCE_LEVEL: E4** — code (`tick_timing.py`, `evaluate.py`) + unit tests + committed `events_2026-07-10.parquet`, `summary` CSV, and a **hashed manifest** (grid-run provenance). Estimator itself withheld → not E5.
**TRANSFERABILITY: B** — markout/execution-state *measurement discipline* transfers; instrument (ES futures) and the private QIP grid do not.
**NEGATIVE_EVIDENCE_TYPE: EXECUTION_FAILURE** (directional information exists but is not capturable by crossing the spread).

1. **Claims:** A limit-order-book fair-price estimator (QIP, private) is evaluated as an **execution-state signal**, not an alpha. 4,701 trigger events, 2026-07-10 ES session. 3.7% adverse midpoint moves at 100 ms; **91.1%** of changed midpoints moved with the signal — yet average aggressive capture is **negative at every valid delay and horizon**.
2. **What code does:** `evaluate.py` (50 ms trigger + grid markout evaluator), `tick_timing.py` (tick-level timing + recorded-touch capture study), `test_tick_timing.py` (boundary/serialization/accounting tests), `render.py` (replay).
3. **Data needed:** external source tick data (5,760,236 valid RTH tick rows, ms-aligned) + the private QIP grid. Committed event file is sufficient to reproduce the replay and inspect grid markouts only.
4. **Label:** signed midpoint movement at 10/20/50/100/250/500/1,000 ms after signal availability; separate explicit fields for favorable/unchanged/adverse counts.
5. **Execution assumptions:** hypothetical infinitesimal long at ask / exit at bid (or short at bid / exit at ask); entry `t0+delay`, exit `t0+horizon`; delays 0/5/10/20/50/100 ms; **`remaining_hold_ms = horizon − delay`; nonpositive holds marked unavailable, never zero**. Lookups use last tick strictly before the observation time.
6. **Cost:** spread cost measured from the recorded touch — mean entry/exit spread cost **1.08 ticks** at 100 ms vs mean signed midpoint move **+0.29 ticks** → mean gross outcome **−0.79 tick**, **median −1.00 tick**. Stated identity: `Gross outcome = signed midpoint movement − ½ entry spread − ½ exit spread`. **No cost argument supplied ⇒ all net capture metrics are explicitly `null`** ("supplying zero costs is a different, explicit assumption"). Commissions/additional slippage not included.
7. **OOS:** Not a train/test study. Instead: single pre-selected session (chosen by recency *before* outcomes evaluated), one fixed pre-existing QIP parameterization, **no parameters tuned on the July 10 outcomes**, plus labeled clock-convention sensitivity cases (strict-before vs at-or-before: −0.197 vs −0.208 points, conclusion unchanged).
8. **What failed:** Crossing the spread. "+0.29 tick movement against 1.08 ticks of spread cost" — the signal is real and directional but smaller than the cost of acting on it aggressively. Also documented: **event overlap** — "triggers cluster and their outcome windows overlap, so the 4,701 events are not independent observations; **no event-independent confidence interval is reported or implied by the sample size**". And a stress sub-interval (10:31–10:37 ET) carrying 61 of 172 adverse outcomes (30.0% vs 2.5% elsewhere) — *retained*, not excised.
9. **Synthetic:** none for results; replay renderer only.
10. **Real:** Real ES tick data, real session, real spread.
11. **Transfers to FXTM:** the **execution-state vs alpha distinction** is the single most reusable idea — measure whether short-horizon information is worth more inside the execution decision than as a standalone crossing signal. Also: the gross-outcome identity; `remaining_hold = horizon − delay` accounting; null-not-zero for net metrics when costs are unknown; refusing to imply CIs from overlapping events.
12. **Does NOT transfer:** the QIP estimator is private and not in-repo; ES futures tick/spread structure ≠ FXTM; "recorded-touch" hypothetical fills are not actual fills (author states passive orders, queue position and successful cancellations were **not measured**).
13. **V3 should steal:** (i) the **favorable / unchanged / adverse midpoint** three-way classification instead of a binary win/loss markout; (ii) counting positive/zero/negative capture in explicit fields that reconcile to a valid denominator; (iii) the *retained* stress interval — do not silently drop the worst 6 minutes; (iv) "does not claim to have solved the execution policy" framing as the honest terminal statement for a measurement-layer deliverable.
14. **V3 should reject:** any attempt to lift "3.7% adverse" as a portable constant (one session, one instrument, overlapping windows); treating the 100 ms horizon as reachable on retail FXTM latency; using this as evidence QIP-style signals are untradeable in general — it evidences that *crossing* is uneconomic, not that the information is worthless.

---

### CARD 3 — `himagna16/kalshi-microstructure`

**EVIDENCE_LEVEL: E4** — collectors + strategy backtest + `FINDINGS_FROZEN.md` pre-registration + cluster-robust stats; OOS half still pending at audit time.
**TRANSFERABILITY: B** — the cost-hurdle arithmetic and pre-registration discipline are directly portable; prediction-market mechanics are not.
**NEGATIVE_EVIDENCE_TYPE: COST_ERASED_ALPHA + EXECUTION_FAILURE**.

1. **Claims:** 19 days / 8.06M orderbook snapshots / 54,380 contracts / 427,017 settlements. Market **well calibrated** (Brier 0.009 at close vs 0.244 base rate) with textbook favorite–longshot bias; but a round trip costs **~9–11¢** on a 40–50¢ contract (must move **10.7¢** to break even). "This is why naive taker momentum strategies die here."
2. **What code does:** `collect.py` (public-API orderbook collector, no credentials), `collect_trades.py` (trade tape), `strategy_backtest.py` (settlement-hold takers + maker sim), `robust_stats.py` (cluster-robust t-stats), `check_droplet_sync.py` (hash-based drift guard), `aggregate_droplet.py`.
3. **Data needed:** Kalshi **public** market-data endpoints, no account/key; ~150 MB/day books. Raw multi-GB DB stays on the collector droplet; committed CSVs are aggregates.
4. **Label:** binary settlement outcome (`result = 'yes'`) joined to the last two-sided quote in the window `[close − 6h, close − 15min]`; calibration uses implied mid at horizon vs realised.
5. **Execution assumptions:** takers enter at the **displayed touch + taker fee**, 1 contract (top-of-book depth is hundreds of dollars, so realistic for small size); makers quote both sides at touch and fill **only when a later snapshot trades strictly THROUGH the price** — explicitly the pessimistic bound ("every fill is by definition adversely selected and benign at-price fills are missed").
6. **Cost:** `fee(p) = 0.07 · P · (1 − P)` per contract per side, charged in-code in `strategy_backtest.py`. Fee is maximised exactly where event trading is interesting (uncertain prices) and stacks on the widest spread.
7. **OOS:** **Pre-registered.** `FINDINGS_FROZEN.md` fixes pass/fail in advance; everything with `close_ms >= 1787011200000` reserved and unlooked-at; OOS half due 2026-09-17.
8. **What failed:** (a) **Buying longshots at the ask loses 3.1¢/contract (t = −8.9)** — a real bias at the mid that is destroyed at the touch; (b) **fading them earns nothing (+0.2¢, t = 0.6)** — "the market is inefficient at the mid and **efficient at the touch**"; (c) **the passive maker gets run over**: BTC-hourly through-price fills, buys −4.1¢/fill, sells −8.2¢/fill, **−$913 over 14,690 fills** vs only 1–3¢ spread capture; (d) infrastructure failure — disk-full cascade, a health line that printed `252 rows in 41.3s (0 errors)` **while persisting nothing**, and ~4h of unrecoverable snapshots (no historical API).
9. **Synthetic:** none in the carded results.
10. **Real:** Real live-collected quotes, real settlements.
11. **Transfers to FXTM:** (i) **compute the break-even adverse move per instrument before testing any signal** — V3 should publish "how far must price move to clear spread+commission" for each FXTM symbol and use it as an alpha screen; (ii) the mid-vs-touch asymmetry test: a bias measured on mids can vanish entirely once you pay the touch — V3 must measure both; (iii) pre-registration + frozen-findings with a hash drift-guard; (iv) cluster-robust errors when observations share an hour/underlying.
12. **Does NOT transfer:** Kalshi's `0.07·P·(1−P)` fee shape (maximised mid-range, zero at extremes) has **no FXTM analogue** — FXTM cost is spread-dominated and roughly proportional to volatility; settlement-hold strategies have no FX equivalent; six crypto series ≠ politics/weather markets.
13. **V3 should steal:** (i) the **"inefficient at the mid, efficient at the touch"** framing as an explicit V3 audit question for every signal; (ii) the honest residual-risk statement — selection (best of three strategies) + single regime ⇒ pre-register the OOS; (iii) the drift-guard idea: a run that "exits 0 and reports a plausible number computed over in-sample and out-of-sample data pooled together" — **check the hash, not the filename**.
14. **V3 should reject:** the fee model's shape as a cost proxy; treating the favorites edge (+1.5¢, t = 2.14) as established before the OOS run completes; the top-of-book-only cost stats as sufficient for size.

---

### CARD 4 — `KlishevDA/Market-Microstructure-and-Latency-Effects-in-L2-Market-Making`

**EVIDENCE_LEVEL: E3** — pipeline + queue/latency engine + committed plots and markout reports; raw stream and processed CSVs not shipped; single 600 s session.
**TRANSFERABILITY: C** — the *question* (does latency change fills and markout?) is exactly V3's; every mechanism needs a top-N L2 event stream FXTM does not expose.
**NEGATIVE_EVIDENCE_TYPE: QUEUE_ASSUMPTION_FAILURE** (explicitly parameterised and flagged as an assumption, not a measurement).

1. **Claims:** Binance L2 (top-N) replay → book features → passive quoting + fill simulation → PnL/inventory/markout **as a function of latency**. Studies how `place_delay_ms` / `cancel_delay_ms` change fills, and how toxic the resulting fills are.
2. **What code does:** `data/get_data.py` (depth websocket + snapshot/diff capture), `data/replay.py` (strict `U == last_u + 1` continuity rebuild), `data/features.py` (imbalance, microprice, log-returns, volume heat-vector), `engine/order_book.py` (L2 map), `engine/queue_model.py` (**the key approximation**), `engine/execution.py` (latency wrapper), `strategy/quoting.py` (touch quoting + inventory skew), `reports/markout.py`.
3. **Data needed:** Binance `@depth` stream @100 ms + HTTP snapshot + diffs; committed as figures/notebooks only.
4. **Label:** none — diagnostic features (`imb1`, `depth_imb`, microprice, log-returns) and markout curves; no supervised target.
5. **Execution assumptions:** join the **back** of the queue (`q_ahead = level_qty`); on each level decrease `dec`, assume a fraction **`rho · dec`** was ahead of you. "Parameter `rho ∈ [0..1]` controls how 'lucky' you are." `place_delay_ms` and effective-after-`cancel_delay_ms` cancellation are modelled. Markout sign convention **positive = good for maker**.
6. **Cost:** expressed as fill realism + markout, **not** as a bps charge. The recommendation is to read equity and markout *together*, because "PnL can look okay while markout is negative → hidden toxicity".
7. **OOS:** none — parameter sweeps (`rho`, offsets, inventory skew, latency) stand in for robustness; explicitly framed as a "research loop" of tuned experiments.
8. **What failed:** no headline loss claimed. The documented failure mode is **assumptive**: `rho` is a free luck parameter with no calibration to observed cancellation behaviour; fills therefore depend on an unvalidated constant. It also flags the FAT FALSIFIER for touch quoting — "if spread is often at the tick minimum, passive quotes at touch will be frequently picked off" — with fat log-return tails implying jumps ⇒ **wider offsets or inventory controls** needed.
9. **Synthetic:** none for results.
10. **Real:** real Binance L2 stream, single 600 s session.
11. **Transfers to FXTM:** (i) the *latency sweep as a first-class output* — measure PnL and markout across `place_delay_ms`/`cancel_delay_ms` rather than assuming instant reaction; (ii) markout sign convention and the "equity positive but markout negative" toxicity warning; (iii) **read inventory, equity and markout together** — a PnL-only report hides adverse selection.
12. **Does NOT transfer:** the queue model itself (needs per-level quantities and update deltas); `rho` is crypto-Binance-specific and uncalibrated; 600 s single session; no fee/commission model at all.
13. **V3 should steal:** (i) the **`rho` sensitivity sweep reported as a first-class result** rather than a hidden constant — V3 must publish its fill-model parameter sensitivity; (ii) markout as a *diagnostic alongside* PnL, never instead of it; (iii) the three-way joint read (equity, inventory, markout).
14. **V3 should reject:** `rho = 1`-style optimistic queue assumptions; the touch-quoting strategy's implied profitability given FXTM spread regime; any absolute markout numbers from one 10-minute window.

---

### CARD 5 — `aryansiwach/execution-market-microstructure`

**EVIDENCE_LEVEL: E3** — 12 source modules, 59 tests, 8 executed notebooks, report + defence + audit docs; WRDS licensed data not committed.
**TRANSFERABILITY: B** — IS decomposition, schedule comparison and stress-regime cost scaling transfer as *method*; TAQ/NBBO specifics do not.
**NEGATIVE_EVIDENCE_TYPE: none explicit** — but it evidences **regime dependence of market-making revenue** (realised spread goes negative in stress) and is the strongest cost-decomposition template in this group.

1. **Claims:** Measures the cost of demanding liquidity across 20 names in 5 liquidity tiers, calm (Jul-2019, VIX ~13) vs stressed (Mar-2020, VIX 82); decomposes spread into adverse selection vs processing; fits an impact model; backtests optimal-execution schedules against the real tape with a queue-aware fill simulator.
2. **What code does:** `clean.py` (filters, NBBO series, as-of match), `classify.py` (Lee-Ready / EMO / tick-test signing), `liquidity.py` (quoted/effective/realised spread, Roll, Amihud), `decomposition.py` (Glosten-Harris 1988; MRR 1997), `impact.py` (Kyle λ, metaorder reconstruction, sqrt-impact), `execution.py` (Almgren-Chriss trajectory, TWAP, VWAP), `fills.py` (queue-position-aware fill simulator), `backtest.py` (schedule × size × tape → implementation shortfall), `evaluation.py` (bootstrap, hypothesis verdicts).
3. **Data needed:** WRDS Daily TAQ millisecond, RTH only; licensed, nothing under `data/` committed. Universe 20 names × 2 periods. Time carried as **integer ns since 09:30 ET** (no timezone handling in the hot path).
4. **Label:** none — outcomes are spread decompositions and implementation-shortfall bps.
5. **Execution assumptions:** queue-position-aware fill simulator; schedule comparison across `NAIVE_MARKET` / `TWAP` / `VWAP` / Almgren-Chriss; order sizes 0.5% → 10% ADV.
6. **Cost:** decomposed instrument-level: effective spread (value-weighted) mega 1.1 → 3.1 bps calm→stress, small-cap 9.8 → **21.5 bps**; MRR adverse-selection share 0.17 (mega) → 0.30 (small), calm, flat-to-down under stress; **realised spread turns NEGATIVE for small-caps in Mar-2020 (−2.6 bps) → market making lost money**. Impact concavity exponent fitted 0.11–0.23, every fit t > 6.
7. **OOS:** calm/stress cross-period contrast + paired bootstrap on schedule differences (TWAP beats market order by −65 bps, p < 0.001); cross-sectional regressions with bootstrap; report carries 22 defence questions + a 15-category self-audit.
8. **What failed / limiting finding:** Implementation shortfall does **not** go to zero for large orders under any schedule — market 81 → 101 bps, TWAP 24 → 35, passive-at-touch 17 → 31 (0.5% → 10% ADV). Stress inflates the shortfall by ~+39 bps and small-cap by ~+26 bps cross-sectionally — "cost is first-order about *what* you trade". And market-making revenue inverts (negative realised spread) precisely when it is most needed.
9. **Synthetic:** tests use synthetic fixtures, no network.
10. **Real:** real TAQ, two regimes, 20 names.
11. **Transfers to FXTM:** (i) the **schedule comparison as a control** — always include naive market order / TWAP as the baseline before attributing edge to a clever schedule; (ii) **spread decomposition into adverse selection vs processing** to see how much of FXTM's spread is informational rather than mechanical; (iii) cost scaling by size tier; (iv) the stress-regime contrast — reproduce the same measurement in calm vs high-vol weeks.
12. **Does NOT transfer:** WRDS/TAQ pipeline, ns-precision NBBO, equity tick regimes, metaorder reconstruction from exchange-level prints, per-venue queue simulation.
13. **V3 should steal:** (i) the habit of reporting **quoted vs effective vs realised spread** and the adverse-selection share as separate numbers; (ii) the explicit "calm vs stressed" repetition of the whole measurement; (iii) Almgren-Chriss/TWAP/VWAP as *baselines to be beaten*, not as strategies; (iv) the two-environment split (online pull isolated, offline pipeline reproducible) as a data-hygiene pattern.
14. **V3 should reject:** absolute bps levels (US equities 2019/2020); the assumption that a queue-position-aware simulator is available for FXTM; any schedule optimisation built on licensed data that cannot be re-run.

---

### CARD 6 — `gelatotrade/implementation-shortfall-hyperliquid`

**EVIDENCE_LEVEL: E3** — full 6-module pipeline + committed `summary_stats.csv` (5,050 rows) + LaTeX tables + fee schedule CSV + data-integrity doc; raw ~15 GB not committed (S3, requester-pays).
**TRANSFERABILITY: B** — the **Perold 4-way decomposition is directly reusable**; perp/exchange-fee mechanics are not.
**NEGATIVE_EVIDENCE_TYPE: none explicit** — documents a real **data-integrity failure** (cross-deployer namespace collision that silently overwrote data) and is the cleanest cost-attribution template in this group.

1. **Claims:** Empirical TCA of 101 perpetual-futures markets across 7 deployers, 149 days, ~1.1M book snapshots, ~1.5B trades, **55,069,575 IS simulation runs**, 5 strategies × 5 size tiers × 2 sides.
2. **What code does:** `discover_hip3.py` → `fetch_hip3.py` / `fetch_native_hl.py` (memory-bounded two-pass streaming extract via `numpy.searchsorted`) → `build_fee_schedule.py` (live fee params + scaling formula) → `simulator.py` (order-book walker, 55M runs) → `is_decomp.py` (Perold decomposition, DuckDB) → `aggregator.py` (tables/figures).
3. **Data needed:** Hyperliquid mainnet JSON-RPC + requester-pays S3 Reservoir (book snapshots 1-min cadence, fills windowed [−5 min, +30 min]); ~20 GB disk, ~6 h compute.
4. **Label:** none — outcome is per-(market, strategy, size, side) IS in bps.
5. **Execution assumptions:** strategies `NAIVE_MARKET` (single sweep), `MARKET_CAP5` (cap at 5% of each level's depth), `TWAP_5MIN`, `TWAP_30MIN`, `VWAP_30MIN`; size grids calibrated per liquidity tier (crypto major $10k–$10M, pre-IPO $1k–$50k).
6. **Cost:** **`IS_total = Spread + Impact + Fee + Opportunity`** (Perold 1988), all in bps, signed positive = cost, where Spread = ½spread × fill fraction; Impact = (VWAP − arrival mid) × fill fraction; Fee = effective taker rate × fill fraction; **Opportunity = max(0, adverse post-window mid drift) × UNFILLED fraction**. Per-(deployer, coin) taker fees computed from the published formula `takerRate × scaleIfHip3 × growthModeScale × (1 − referralDiscount)` — **not hardcoded** (a committed 196-row fee-schedule CSV is loaded at runtime).
7. **OOS:** **Cross-listings as identification** — 6 four-way cross-listings (TSLA, NVDA, GOLD, SILVER, OIL, SP500 across 4 deployers) + 9 native-vs-HyENA pairs + 1 three-way XMR, enabling fee-delta and venue-effect identification; tier robustness sweeps (Tier 0–3 ± staking).
8. **What failed:** a **data-integrity bug** — missing cross-deployer disambiguation (`dex__COIN`) caused "cross-deployer data to overwrite each other", documented in `docs/DATA_INTEGRITY.md`. Also: the **opportunity-cost term only exists because unfilled orders are real** — a naive "fill everything at VWAP" simulation would report zero opportunity cost and understate the shortfall by the whole unfilled-size component.
9. **Synthetic:** none for results.
10. **Real:** real on-chain books, real fills, real fee schedule fetched live.
11. **Transfers to FXTM:** (i) the **4-term Perold decomposition with a separate opportunity term on the UNFILLED fraction** — this is the single most portable accounting object in the whole distillation (FXTM orders do genuinely fail to fill; V3 must not book unfilled size at the arrival price); (ii) loading fees from a data file rather than hardcoding; (iii) the composite-key discipline (`dex__COIN`) — V3 must namespace lock its instrument×venue×account keys before any join; (iv) DuckDB for the heavy joins.
12. **Does NOT transfer:** Hyperliquid HIP-3 fee formula and growth-mode scaling; perp funding; $10M size tiers; the S3 requester-pays reproducible-data assumption (FXTM tick history is not free/complete).
13. **V3 should steal:** (i) the IS decomposition *as the V3 cost-report format*; (ii) `Opportunity` as a first-class component — it is the term most retail backtests silently set to zero; (iii) fee schedule as data, not code; (iv) the namespace-collision post-mortem as a schema-review checklist item.
14. **V3 should reject:** the strategy set (they are *schedules*, not alphas); perp-specific cost components; assuming 55M-run scale is necessary — V3's binding constraint is tick-history coverage, not compute.

---

### CARD 7 — `Trumplus/AAPL-Limit-Order-Fill-Probability-Forecast`

**EVIDENCE_LEVEL: E3** — dataset (~45 MB, 10k orders + LOB history) **committed in-repo**, 8 self-contained scripts, metrics CSV, confusion matrices, ablations. Limited by single symbol / single period / a summer-school group project.
**TRANSFERABILITY: C** — the leakage-free protocol and queue-position finding transfer; the model needs order-level LOB + queue data FXTM does not expose.
**NEGATIVE_EVIDENCE_TYPE: none explicit** — but it is the reference for **how to build a fill-probability label honestly**, and shows the achievable ceiling (AUC ~0.72–0.73) for a 5–60 s fill question.

1. **Claims:** Binary prediction of whether an AAPL limit order fills within 5 / 30 / 60 s, from order attributes + queue position + top-5 LOB + 50×25 LOB history. ROC-AUC ~0.72 (5 s) → ~0.73 (60 s); **queue position (`normalized_queue_ahead`) is the strongest negative driver at every horizon**.
2. **What code does:** `main_deep_models.py` (LSTM/GRU/TCN/Transformer/CNN-LSTM/CatBoost/RF), `main_classical_ml.py` (LPM/LogReg/DT/SVM/XGBoost), `logistic_regression_analysis.py`, `survival_analysis.py` (discrete-time hazard, censoring-aware, td-AUC/Brier, IAUC/IBS), `kanformer_comparison.py`, `confusion_matrix.py`, `history_length_ablation.py` (L = 0…50), `make_results_tables.py`.
3. **Data needed:** `AI_Order_Execution.xlsx` (10,000 orders) + `Single_Symbol_LOB_History.json.gz` (50 snapshots × 25 channels pre-`t0`). Committed.
4. **Label:** `target_fill_{5,30,60}s` with companion **`eligible_{5,30,60}s`** (whether the outcome is even observable) + survival fields (`observed_duration_s`, `fill_event`, `cancellation_or_expiry`). The eligibility field is the key discipline: **unobservable outcomes are excluded, not labelled 0**.
5. **Execution assumptions:** none — the fills are observed/derived, not simulated. All execution realism lives in the feature set (queue ahead, same-price total qty, normalized queue position, 10-s event counters).
6. **Cost:** **none.** No spread/fee/PnL in the repo. This is a pure *fill-probability* classifier — cost is left to the consumer, which is a real gap for V3 use.
7. **OOS:** **chronological** train/val/test split; **threshold selected on validation only** and then applied to test; all scalers normalised on train only; mutual-information feature selection (top 60) **on train only**; per-test-day AUC variability reported.
8. **What failed / key limitation:** the ceiling itself — AUC ~0.72 means a 5-second fill question is only weakly predictable from static + short-history book state, and "longer horizons are markedly easier" (because class balance improves) — i.e. part of the apparent skill at 60 s is the changing base rate, not added information. Baseline drift risk is flagged by the per-day AUC variability panel.
9. **Synthetic:** none — real AAPL order/LOB data committed.
10. **Real:** real order-level data; single symbol, and the sample is 10,000 orders (small for the deep models).
11. **Transfers to FXTM:** (i) the **label-with-eligibility pattern** — V3 must mark outcomes that are censored/unknowable as *excluded*, never as negatives; (ii) **threshold chosen on validation only** and applied to test — a cheap, high-value discipline for V3's own classifiers; (iii) the finding that **queue position dominates fill probability** means for FXTM (no queue visibility) any fill model is structurally weaker — this is itself an argument for V3 to treat fill as an assumption band, not a point estimate; (iv) MI feature selection restricted to train.
12. **Does NOT transfer:** all 302 features (require order-level LOB + per-order queue position); the models' absolute AUCs (single symbol, small sample); anything about PnL (no cost layer at all).
13. **V3 should steal:** (i) `eligible_*`-style censoring flags; (ii) train-only threshold/scaler/MI-selection discipline; (iii) per-day (per-regime) AUC variability as a standard robustness panel; (iv) survival analysis (hazard + censoring) as the *correct* formulation of "will it fill" instead of independent binary classifiers per horizon.
14. **V3 should reject:** treating AUC ~0.72 as an edge (it is fill *timing* skill, not PnL skill); porting deep sequence models to a setting with no queue data; using this repo for cost assumptions — it has none.

---

### CARD 8 — `AshJha0/electronic-trading`

**EVIDENCE_LEVEL: E4 for engineering rigor** (4 language ports pinned to 19 shared golden cases, 300 tests, 1e-10…1e-12 tolerances, literature closed-form checks at 1e-12) — **but E1 for market validity** (all parameters synthetic; author states calibration to any real market is *not* verified).
**TRANSFERABILITY: B** for the formulas/decomposition, **D** for anything requiring real calibration.
**NEGATIVE_EVIDENCE_TYPE: none of the listed types**, but it documents an explicit **model-vs-paper discrepancy** and a **calibration gap** (see item 8).

1. **Claims:** Four independent implementations (Python reference, C++17, Rust, Java 21) of Almgren-Chriss (2000) discrete optimal execution, Avellaneda-Stoikov (2008) finite-horizon market making, and execution analytics (Perold implementation-shortfall decomposition, participation rate, native OLS impact fit) — all mirroring a pinned `API_SPEC.md`.
2. **What code does:** `almgren_chriss` (closed-form κ, trajectory x_j, n_j, exact discrete E[IS]/Var[IS], efficient frontier, λ=0 → TWAP limit branch), `avellaneda_stoikov` (reservation price, optimal spread, `A·exp(−k·δ)` thinned-Poisson fills, inventory cap, stress-vol sim), `analytics` (IS decomposition delay/trading/opportunity, participation rate, OLS impact), plus Monte-Carlo IS cross-checks and a fixed-spread comparison agent on the same RNG stream.
3. **Data needed:** none market-based — pinned synthetic parameter sets: `params_liquid.json`, `params_illiquid.json`, **`params_fx.json`** (tight spread, high k), `parent_order.json`.
4. **Label:** none — analytic/target-cost study; the "label" is E[IS] and its variance.
5. **Execution assumptions:** linear temporary + permanent impact, arithmetic random walk, **fractional shares (no lot rounding)**, abstract time unit (1 = one trading day, no calendar), arithmetic σ, prices may go negative, A-S fills one unit each, sell programs only in AC.
6. **Cost:** all costs in currency, **positive = loss**. IS decomposition printed as `delay / trading / opportunity / TOTAL` in the demo. Critically documented caveat: **the paper's fixed cost `epsilon·sum|n_j|` (half-spread, fees) is OMITTED** from AC — "it equals `epsilon·X` for any one-sided schedule and does not change the trajectory; **add it to `E[IS]` if you report total cost**."
7. **OOS:** Not applicable. Substitutes: 19 golden cases cross-validated across 4 languages; paper closed forms vs discrete sums at 1e-12; Monte-Carlo vs closed form within 4 SE (20k paths); determinism-by-seed; property invariants (trajectory monotonicity, inventory cap, IS decomposition identity and **price-shift invariance**, frontier monotonicity); overflow safety at `κ·T > 2500`.
8. **What failed / documented gaps:** (a) **Model-vs-paper discrepancy** — the A-S fill probability is implemented as the *exact* thinned `1 − exp(−λ·dt)` rather than the paper's first-order `λ·dt`, so **mean PnL is ~12% below the paper's Table 1** while std PnL agrees; (b) **calibration is explicitly not verified** — "What is *not* verified: calibration of `eta`, `gamma_p`, `A`, `k` to any real market"; (c) scope exclusions are enumerated: no square-root impact, no adaptive re-optimisation, **no adverse selection**, no order types, venues, ticks, lots, or latency.
9. **Synthetic:** entirely synthetic (seeded generator `data/generate_data.py`); `params_fx.json` is an FX-like *parameter set*, not FX data.
10. **Real:** none. No market data whatsoever.
11. **Transfers to FXTM:** (i) the **IS delay/trading/opportunity decomposition** as a report format (pairs with CARD 6's 4-term Perold version); (ii) `params_fx.json` — an FX-like regime (tight spread, high k) already parameterised, useful as a **sensitivity bracket** rather than a calibration; (iii) the explicit "add epsilon·X if you report total cost" warning — V3 must decide whether its reports are *pre-cost* or *post-cost* and say so; (iv) the golden-value + property-invariant test pattern (IS decomposition identity, **price-shift invariance**) for V3's own cost code.
12. **Does NOT transfer:** all parameter values (uncalibrated, synthetic); the A-S first-order vs exact fill-probability choice; lack of adverse selection in the model — which is precisely V3's measured problem; arbitrage-free arithmetic-walk assumptions.
13. **V3 should steal:** (i) **`price-shift invariance` as a unit test on any cost/PnL decomposition** — a decomposition that changes when you shift all prices is wrong; (ii) the closed-form ↔ discrete-sum ↔ Monte-Carlo triangle as three independent checks of one number; (iii) the "what is NOT verified" section as a mandatory deliverable block; (iv) cross-language golden values as the template for cross-*module* golden values in V3's pipeline.
14. **V3 should reject:** using AC/AS outputs as forecasts (uncalibrated); any E[IS] figure that silently excludes the epsilon·X spread/fee term; assuming no adverse selection (contradicted by CARDs 1–3).

---

## 3. CROSS-CUTTING LESSONS FOR V3

1. **The gross/net gap is the normal case, not the anomaly.** Four independent repos (CARDs 1, 2, 3, 5) show a signal that is statistically real and economically dead: 9.11 bps edge vs 10.3 bps round trip (C1); +0.29 tick movement vs 1.08 tick spread (C2); a real longshot bias that flips to −3.1¢ at the touch (C3); realised spread negative for small caps under stress (C5). **V3 must publish a per-symbol cost hurdle (spread + commission + expected slippage) and screen every candidate alpha against it before any backtest.**
2. **Measure at the touch, not the mid.** C3's sharpest sentence — "the market is inefficient at the mid and efficient at the touch" — is a general law. C1 independently confirms it by refusing mid-price fills. **Any V3 signal evaluated at mid is unverified.**
3. **The reversion-ablation is a maker/taker classifier.** C1: drop reversion features and IC collapses 0.473 → 0.177. If a V3 signal's edge is mostly inside-spread reversion, it belongs to whoever is *quoting*, not to whoever is *taking* — V3 must run this ablation and state the verdict.
4. **Unfilled size is a real cost term.** C6's `Opportunity` = adverse drift × **unfilled fraction**, and C7's `eligible_*` censoring flags, are two views of the same discipline: **never book unfilled or unobservable outcomes at par, and never label them as losses.** Retail backtests silently set opportunity cost to zero.
5. **Fill/queue assumptions are the dominant unmodelled risk.** C4 (an uncalibrated `rho` luck parameter), C1 (pro-rata cancellation explicitly labelled optimistic), C2 (recorded-touch hypothetical, queue position *not measured*), C7 (queue position is the strongest fill driver, and FXTM cannot observe it). **V3 must treat fills as a sensitivity band (`rho`-style sweep published as a result), not a point estimate.**
6. **Costs must be additive-explicit, never netted silently.** C6's four orthogonal terms, C8's delay/trading/opportunity trio + the epsilon·X warning. **V3's report format should be a decomposition where every component is separately visible and signs are declared (positive = cost).**
7. **Overlap and independence are accounting hazards.** C1 (purged walk-forward + embargo; non-overlapping rebalancing or the same move is counted H times), C2 (4,701 clustered events ⇒ **no CI implied**), C3 (cluster-robust t-stats by hour × underlying). **V3 must purge, embargo, de-overlap, and cluster its errors before quoting any t-stat.**
8. **Provenance beats narrative — check the hash, not the filename.** C3's drift incident: a stale script "exits 0 and reports a plausible number computed over in-sample and out-of-sample data pooled together. There is no error to catch." C6's namespace collision silently overwrote cross-deployer data. C3's collector printed `0 errors` while persisting nothing. **V3 must hash-lock its in-sample/OOS split boundary and its cost schedule, and assert the guard in CI.**
9. **The terminal honest statement is a deliverable.** C2: "This study measures that problem; it does not claim to have solved the execution policy." C3 and C6 pre-register OOS pass/fail in advance and commit to publishing a refutation. **V3 should require an explicit "what this does NOT verify" block (C8's format) and a pre-registered OOS criterion on every research stage.**
10. **Report the ceiling, not just the best model.** C7's AUC ~0.72 for 5-second fills, and C2's "negative at every valid delay and horizon", are more useful to V3 than any positive result in this group — they set the bound on what short-horizon signals can buy once execution is charged.

---

## 4. VERIFIED-BUT-NOT-CARDED (HTTP 200, kept for completeness)

The following slugs were verified live (HTTP 200) but not carded: 4 had no README retrieved within the audit window, and 7 were lower-priority than the 8 cards above (no direct execution-cost / failure evidence surface in the search snippet).

**Verified 200, README not retrieved (not carded):** `Weichong515/Algo-Trading-14` (16★, momentum + implementation-shortfall algorithm, 2019), `KBenBec/quant-microstructure-hft-` (3 KB, synthetic-data toolkit), `furlong-cp/QueueEdge` (1 KB, queue simulator — essentially no content), `FrionicSaddly/perp-quant-bot`.

**Verified 200, intentionally de-prioritised:** `ishabh-24/markout`, `Leotaby/Market-Making-Simulator`, `ferflorespr/quant-backtest-execution-engine`, `FETKlOkAn2/crypto-quant-platform`, `xuxingjiankr-cpu/perception-xalpha-lite`, `FatihHekim0glu/algo-system`, `srgangaram-swe/AlphaForge`. Several of these may be worth carding in a later batch (notably `FatihHekim0glu/algo-system`'s "backtest-vs-live parity oracle" and `FETKlOkAn2/crypto-quant-platform`'s "built to tell you when a strategy doesn't work"), but the Group C+D failure-evidence quota is already exceeded by the 8 cards.

## 5. SEARCHES THAT RETURNED NOTHING USABLE (valid findings)

Recorded as explicit negative results — no qualifying repo was found, and none was invented:

| Query | Result |
|---|---|
| `latency+discount+backtest` | total_count 0 |
| `backtest+profit+real+tick+failure` | total_count 0 |
| `cost+aware+loss+trading` | 2 hits, both **spam** (reposted Terms-of-Service documents), no code |
| `HFT+failed` | 1 hit, irrelevant (a live lead-lag bot) |
| `predictive+R2+contemporaneous+R2+trading` | total_count 0 |
| `tail+risk+dominated+PnL+strategy` | total_count 0 |
| `expected+net+return+label+trading` | total_count 0 |
| `gross+net+pnl+attribution+trading` | total_count 0 |
| `microstructure+forex+execution+cost` | total_count 0 |

**Consequence for the requested audit questions:** **no repo was found that explicitly separates PREDICTIVE R² from CONTEMPORANEOUS R²** (0 hits; the nearest analogue is CARD 1's out-of-sample **IC** vs its reversion ablation, and CARD 7's chronological-split AUC). **No repo was found that documents "parameter change does not affect per-trade loss" as a cost-type failure.** **No repo was found whose stated failure is tail-dominated PnL** (CARD 5's stress-regime realised-spread inversion is the closest analogue). These three remain **open negative results** for the distillation: if V3 needs them, they must be produced internally rather than sourced from GitHub.

## 6. AUDIT LIMITATIONS

- All slugs verified HTTP 200 on 2026-09-22; star counts and `pushed_at` are as of that date.
- README content was read as fetched bytes; numbers are quoted from the repository, **not independently reproduced** (reproduction was out of scope for a read-only audit: it would require WRDS, S3 requester-pays, private QIP grids, or live collectors).
- Star counts are near-zero for 6 of 8 cards — these are recent, small, single-author research repos, not established libraries. Evidence quality was therefore graded on **artifacts and internal rigor** (E0–E5), not popularity. CARD 8 (`AshJha0/electronic-trading`, 28★) is the only broadly-adopted repo in the set and is explicitly synthetic.
- `EVIDENCE_LEVEL` for CARD 7 is capped at E3 by single-symbol/small-sample scope; CARD 8 is split-graded (E4 engineering / E1 market validity) and marked as such rather than averaged.
