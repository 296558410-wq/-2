# Search B — SPREAD AS A STATE VARIABLE vs spread as pure cost
## plus OPPORTUNITY COST of non-execution, and LIMIT/MAKER EXIT executability

**Task:** V3-HFT-GITHUB-CANDIDATE-MODEL-DISTILLATION-004
**Scope:** READ-ONLY GitHub search/audit. No purchases, no signups, no MT5, no orders, no training, no backtesting.
**Date:** 2026-09-22
**Method:** GitHub REST search API (`api.github.com/search/repositories`), then per-repo `raw.githubusercontent.com` retrieval of README + source. ~30 distinct search queries run.

---

## 0. Verification status — READ THIS FIRST

| Check | Result |
|---|---|
| GitHub HTML existence check (`https://github.com/<slug>`) | **HTTP 200 for all 18 candidate slugs reported below** |
| Raw content retrieval (README + specific `.py`/`.hpp` paths) | **Succeeded** for every repo whose content is quoted below |
| `https://api.github.com/repos/<slug>` (the endpoint named in the task) | **HTTP 403 for the entire run window** — unauthenticated core quota (60 req/hr) was drained by the search phase; `rate_limit` reported `core: 0/60 remaining, reset 1790058137` on three separate checks |

**Honest limitation:** the requested `/repos/<slug>` HTTP-200 check could not be completed because the unauthenticated core quota was exhausted (no token may be added — signups are out of scope). Existence is therefore established by (a) HTML 200 on `github.com/<slug>` and (b) successful `raw.githubusercontent.com` content fetches with real file bodies. Every slug below returned real README text (or a documented "README absent"), which a non-existent repo cannot do. **No slug is reported on inference.**

**EVIDENCE_LEVEL scale (declared by me, since the task did not define it):**
- **E0** claim only, no code
- **E1** README/spec only, no runnable model code inspected
- **E2** code exists, synthetic/simulated data, no validation
- **E3** code + real market-data path, but results not committed / not reproducible by me
- **E4** code + real data + committed evidence (tests, executed notebooks, stated numbers)
- **E5** E4 + out-of-sample / pre-registered gates **or** validated against an independent formula or published benchmark

**TRANSFERABILITY (declared by me):**
- **A** directly transferable to a V3 spread-state / cost-opportunity / maker-exit design
- **B** transferable with adaptation
- **C** one component transferable
- **D** conceptual analogy only
- **E** not transferable (different instrument / venue / notion of "spread")

---

## 1. THE SHARP ANSWER (up front)

> **No repository found in this audit shows a stable relationship between spread state and expected future move. In every repo that models spread quantitatively, spread is used purely as a COST — a threshold, a decomposition term, or a calibration input. It is never used as a predictor of the next move's size.**
>
> There are exactly three places where spread appears as a *state variable* rather than a cost, and none of them supports "wide spread ⇒ larger expected move":
> 1. `khintchine/rs-heston-mm` — spread/intensity parameters are indexed by a **volatility regime**, not a spread regime. Spread is a *function of* state, not a *predictor of* state. (Causal direction is backwards for the gap.)
> 2. `andrewkni/bayesian-spike-detector` — widening spread is used as evidence a price jump is **fake**, i.e. it predicts **reversal**, the *opposite* sign to "wide spread ⇒ bigger move coming". Heuristic, unvalidated, prediction-market venue.
> 3. `PentaMourya/...` and `emilianofrattolin/...` — *claim* a state→spread mapping and a "regime-dependent spread calibration", but cite no formula and commit no code.
>
> The one place where spread and future move are linked numerically is `aryansiwach/execution-market-microstructure`, where
> `realised spread = 2·q·(price − mid_{t+h})` and `price impact = effective spread − realised spread`.
> But the direction is **future move → spread adequacy** (was the dealer's spread wide enough to cover the move that followed?), **not** spread → future move. That is a *cost-adequacy* decomposition, and it is the single most useful artefact in this corpus for V3.
>
> The corpus also contains a hard **negative** measurement of the gap: `K1ta141k/loblab` sweeps a real signal against the spread and concludes `signal < spread` ("the move only clears the ~1-tick spread at extreme thresholds", "That crux (signal < spread) is the whole game in taker alpha").

---

## 2. REPO-BY-REPO FINDINGS

### 2.1 `aryansiwach/execution-market-microstructure` — EVIDENCE_LEVEL **E4**, TRANSFERABILITY **A**
Python, WRDS millisecond TAQ, 12 source modules, 59 tests, 8 executed notebooks, graduate report. **Best overall fit of the audit.**

**(a) Exact formulas quoted.** Opportunity cost of the *unfilled* part is modelled explicitly (`src/backtest.py`):
```python
unfilled = max(0.0, target_qty - filled_qty)
opp = (side * (final_mid - arrival_mid) / arrival_mid * 1e4
       * unfilled / target_qty) if target_qty > 0 else 0.0
w = filled_qty / target_qty if target_qty > 0 else 0.0
return {"is_bps": w * exec_cost + opp, "exec_cost_bps": exec_cost,
        "opportunity_bps": opp, "fill_ratio": w}
```
Spread decomposition (`src/liquidity.py`) — the cost-adequacy identity:
```
quoted spread        ask - bid  (and relative: / mid)
effective spread     2 * |price - mid|          (half-spread actually paid)
realised spread      2 * q * (price - mid_{t+h}) (dealer revenue net of the
                     permanent move over horizon h)
price impact         effective - realised        (the permanent component)
Roll implied spread  2 * sqrt(-cov(dp_t, dp_{t-1}))
```

**(b) Spread as cost or as market state?** **COST**, strictly. Spread is decomposed into a component that is *paid* (effective) and components attributed to adverse selection vs. processing. It is never a feature/state input.

**(c) Evidence linking HIGH SPREAD to expected FUTURE MOVE?** **No — and the arrow runs the other way.** The repo does link spread to a *realised* future move via `realised spread = 2·q·(price − mid_{t+h})`, but this quantifies whether the spread was wide enough to cover the move that happened. Reported evidence: *"MRR adverse-selection share (calm): 0.17 mega → 0.30 small — monotone in illiquidity, but flat-to-down under stress"*; *"Realised spread turns negative for small-caps in March 2020 (−2.6 bps): market making lost money."* That is a **cost-adequacy** statement (spread insufficient under stress), not a predictive one.

**(d) Opportunity cost of unfilled orders modelled?** **YES — the only repo besides `DaniyalMlk/slippage` that truly does.** Unfilled shares are marked to the final mid and weighted into IS by fill ratio.

**(e) Maker exits executable or theoretical?** **Modelled as executable, and conservatively.** `src/fills.py::simulate_limit`:
> *"a resting limit order at `price` joins the back of the displayed queue (`queue_ahead` shares in front); it fills as same-priced contra trades arrive and eat through the queue, and cancels if the NBBO trades through its price."*

with `queue_ahead = displayed_size * cfg["fills"]["queue_ahead_fraction"]`, `cancel_on_through`, and a `deadline_ns`. Residual is swept aggressively (`src/backtest.py`): *"the passive schedule posts at the touch, simulates a queue fill over the slice, and sweeps any residual with a marketable order at the slice close."* It also reports post-fill markout toxicity (`adverse_selection_bps`). Reported cost impact: *"Implementation shortfall (bps, 0.5% → 10% ADV): market 81 → 101, TWAP 24 → 35, passive-at-touch 17 → 31."*

---

### 2.2 `DaniyalMlk/slippage` — EVIDENCE_LEVEL **E5** (for the IS decomposition), TRANSFERABILITY **A** (gap B only)
Python, NumPy only, MIT, formal test suite.

**(a) Formula quoted.** Perold implementation shortfall, decomposed, with an explicit opportunity term:
> *"**Opportunity** is the move on shares that never traded. A trader who cuts an order short to save trading cost moves cost here rather than removing it."*

Components `delay / trading / opportunity / commission / fees`, worked example totals 67.50 bps (opportunity 1,200.00 = 24.00 bps). Validated independently:
> *"On every call the components are checked against the direct Perold formula computed by a separate route; a mismatch beyond rounding raises rather than returning a number."*

**(a-cont.) The convention question — directly relevant to V3's gap:**
> *"The default *order* basis charges delay on the whole target, since all of it sat idle; the *executed* basis charges it only on shares that traded. Both split the same total, which the test suite checks on randomly generated orders."*

**(b) Spread as cost or state?** **COST.** *"Given the half-spread it splits into the price of immediacy and the remainder, which is impact and timing."*

**(c) Spread → expected future move?** **No.** Spread appears only as the cost floor inside the trading-cost term.

**(d) Opportunity cost of unfilled modelled?** **YES — the most rigorous in the corpus**, with the two conventions stated and tested.

**(e) Maker exits modelled?** **NO.** It consumes fills as input; there is no limit-order fill/queue model at all. Executability of a maker exit is out of scope for this repo.

---

### 2.3 `K1ta141k/loblab` — EVIDENCE_LEVEL **E3**, TRANSFERABILITY **B**
C++17 LOB, lock-free SPSC ring, matching engine, OBI signal, spread-aware P&L backtest, A-S maker. Real Binance.US L2 replay for the book layers.

**(a) Formula quoted.** Imbalance `obi = (bidD - askD)/(bidD + askD)`, fires when `|obi| > 0.30`; maker reservation price `r = mid - gamma*inventory + theta*OBI`. The key table columns are literally `grossMid | spread | net/trade | ctrl/trade | edge`.

**(b) Spread as cost or state?** **PURE COST — and the repo is built around that fact.**
> *"Per signal it reports directional accuracy and the **taker P&L net of the spread crossed both ways**, against a random-direction control on the same triggers."*
> *"The honest read: OBI is **directionally right** ... but the move only clears the ~1-tick spread at extreme thresholds where the sample is tiny. So a pure **spread-crossing taker barely monetizes it** - the edge really belongs to a liquidity *provider* (post, don't cross) or as a filter/tilt. That crux (signal < spread) is the whole game in taker alpha."*

**(c) Spread → expected future move?** **Explicitly the opposite finding**: the expected move must clear the spread; usually it does not.

**(d) Opportunity cost of unfilled?** **No.**

**(e) Maker exits modelled?** **NO — and the author says so.** The roadmap lists as *not done*: *"Next: rdtsc/core-pinned timing on x86 Linux for clean tails; a maker/queue-position model; validate on recorded L2 data."* Then: *"a maker/queue-position model"* is explicitly future work. So maker exits are neither executable nor theoretical — **absent**.

---

### 2.4 `SpencerOzgur/Optimal-High-Frequency-Market-Making-With-Robust-Backtesting` — **E3**, **A**
A-S model, WRDS TAQ replay, queue-aware fills, realized-vol extension. Stanford 2018 paper reproduction.

**(a) Formulas quoted.**
```
r(s, t) = s - (q / lot_size) * gamma * sigma^2 * (T - t)
spread(t) = A * (T - t) + B      where A = gamma*sigma^2, B = (2/gamma)*ln(1+gamma/kappa)
Phi_bid = Phi_max * exp(-eta * q);  Phi_ask = Phi_max * exp( eta * q)
lambda(xi) = A * exp(-xi / b);      delta_lambda = lambda(xi_our) - lambda(xi_best)
```
Realized-vol extension: `spread(t) = gamma_rv * sigma2_t * (T - t) + B`, i.e. *"replaces the fixed `gamma * sigma^2` term ... with a rolling 10-minute realized variance computed from TAQ trade prices, updated every second"* and *"RV widens during volatile periods and tightens during calm periods."*

**(b) Spread as cost or state?** **Neither, strictly** — spread here is an **output** (the MM's quote width) driven by vol and inventory. It is **volatility** that plays the state role. This is the closest thing in the corpus to a state-conditional spread, but the conditioning variable is σ, not spread itself.

**(c) Spread → expected future move?** **No.** Volatility → spread. Spread never predicts a move.

**(d) Opportunity cost of unfilled?** **No.** Poisson uplift only adjusts fill *probability*; unfilled quantity carries no mark-to-future charge.

**(e) Maker exits executable or theoretical?** **BOTH — this is the only repo in the corpus that explicitly contrasts the two and reports them separately.** Two queue models:
> *"`queue_model='front'` — assumes the market maker is first in queue at the quoted price level. All addressable volume is available.*
> *`queue_model='back'` — assumes the market maker joins the back of the queue. The prevailing NBBO size is placed ahead; fill only occurs if total addressable volume exceeds that queue. Both models are run simultaneously in `run_with_wrds.py` and reported separately."*

`'front'` is the **theoretical/optimistic** maker fill; `'back'` is the **conservative/executable** one. The gap between them is exactly the quantity V3 needs to size.

---

### 2.5 `AMIRMAHMOUDINIA/microstructure-signals-vs-executable-alpha` — **E5** (methodology), **A**
BTCUSDT perp, pre-registered gates, locked test set, HAC, BH-FDR, block bootstrap.

**(a) Formulas quoted.** `TFI = (2 * taker_buy_volume - total_volume) / total_volume`; static L1 imbalance 10m beta `+0.5255` / `+0.6647` bps/unit (dev/validation).
**(b) Spread as cost or state?** **COST.** Execution protocol: *"signal from completed minute `t`; entry at reconstructed BBO at `t+1`; exit at original `t+10` endpoint; **spread crossed on both sides**; non-overlapping positions; additional round-trip cost sensitivity from 0 to 12 bps."*
**(c)/(d)/(e)** No spread predictor; no unfilled-quantity model; no limit-order fills.
**Killer numbers for the cost-to-move framing:**
> *"Every cost scenario failed the December economic gate. Even at **0 additional bps**, the selected December strategy averaged **-0.343 bps/trade**. The high-confidence threshold had gross break-even additional cost of only **0.909 bps**."*
> *"A feature can contain statistically reproducible information without establishing executable alpha."*

---

### 2.6 `chinthakat/xauusd-rl-engine` — **E2**, **B** (most venue-analogous to Hermes)
XAU/USD M1 RL sandbox on **MetaTrader 5**, cost-aware backtester, live loop. Directly same venue family as the Hermes V1/V2/V3 stack.

**(a) Formula quoted (the cost-aware entry gate, verbatim from `trade_executor.py`):**
```python
spread_points = round((tick.ask - tick.bid) / info.point)
if spread_points > config.MAX_SPREAD_POINTS:
    return False, f"Spread too wide: {spread_points} points (max: {config.MAX_SPREAD_POINTS})"
```
with `MAX_SPREAD_POINTS = 50  # Refuse to open if spread exceeds this` and `MAX_SLIPPAGE = 30  # Max price deviation, in points` passed as the MT5 order `deviation`.

**(b) Spread as cost or state?** **PURE COST — a static hard gate.** Widest-spread refusal is a binary filter; there is no regime, no dynamic threshold, no spread→move term.
**(c)** No. **(d) Opportunity cost of unfilled?** No (`--no-spread/--no-slippage/--no-latency/--no-commission` cost toggles exist, but no non-execution markout). **(e) Maker exits?** No — market orders with `deviation`, plus MT5 SL/TP. Note the backtester *does* model spread, slippage, latency, commission, swap and margin.

---

### 2.7 State-variable cases (gap A) — the three candidates that even approach it

**`khintchine/rs-heston-mm` — E2, B.** Optimal MM under regime-switching Heston with partial information (Wonham filter). Spread is **regime-indexed**, which is the only genuine "state" use in the corpus:
```
Lambda^a_i(delta) = A^a_i * exp(-eta^a_i * delta)      (delta = half-spread at execution)
Lambda^b_i(delta) = A^b_i * exp(-eta^b_i * delta)
Q = [[-lambda_HL, lambda_HL], [lambda_LH, -lambda_LH]]
dV_t = kappa_{X_t}(theta_{X_t} - V_t)dt + xi*sqrt(V_t) dW^V_t
```
`delta` is derived from trade price vs mid, and the **regime index `i`** makes both intensity parameters state-dependent. But the state is **volatility regime**, not spread regime — spread is an argument, not the state. Notebook-only, Korean README, no committed results.

**`andrewkni/bayesian-spike-detector` — E1, D.** The *only* repo where a spread change is read as evidence about a future move:
> *"Low/zero volume + widening spread on a big YES jump increases `alpha` (fake spike). High volume + tightening spread increases `beta` (real repricing)."*
> *"Enter when `mu > 0.7` and the spike stalls (`delta_price <= 0`)."*

This predicts **reversal** — the opposite direction to the gap hypothesis. Exit side is explicitly non-maker: *"Sell NO using a market order (reduce-only)"*. Kalshi prediction markets; no validation; `mu = alpha/(alpha+beta)`.

**`anwaro26/hmm-lstm-swap-spread` — E2, D.** Different object entirely: the "spread" is the **EUR 10Y swap spread** (swap rate − Bund yield), i.e. a credit/liquidity *rate* spread. HMM regimes + LSTM, regime-aware level and volatility forecasting. Useful only as an analogy: it treats a spread series as a **state-bearing** object with structural regimes. Its "spread" is never a transaction cost.

---

### 2.8 Remaining inspected repos (lower yield)

| slug | E | T | One-line finding |
|---|---|---|---|
| `ViswanathDas/market-making-execution-lab` | E2 | B | A-S lab. `optimal_spread = gamma*sigma^2*time_left + (2/gamma)*ln(1+gamma/k)`; `IS = (avg_price - arrival_price)*total_qty` — **no opportunity term**. Fills via `lambda = A*exp(-k*d)` = **theoretical** (no queue). |
| `thibault-charbonnier/market-making-engine` | E2 | C | C++ A-S engine; Poisson intensities *"increase as quotes move closer to the mid price"*; no opportunity cost; maker fills theoretical (Poisson). |
| `PentaMourya/High-Frequency-Market-Making-Desk-with-...` | E1 | C | Claims spread 1.8–4.2 bps driven by *"a rolling volatility estimate such as the 20-period standard deviation of returns"* and a 5-state condition score (Preferred/Good/Neutral/Poor/Worst). No formula, no code, unsupported PnL claims. |
| `GeetMalviya03/Equity-execution-and-market-making` | E1 | B | Best *design pattern* for the gap, README-only: *"identifies volatility and liquidity regimes using unsupervised learning, constructs a proxy for execution cost (slippage), and trains predictive models to estimate expected execution difficulty and the probability of high-cost trading conditions"*; *"regime and execution signals would directly inform quote width, order size, and inventory limits."* |
| `emilianofrattolin/Adaptive-Stochastic-Market-Making-...` | E0/E1 | D | 412-byte README. *"filtered volatility states ... and regime-dependent spread calibration"*; *"balancing expected short-term edge against inventory exposure and adverse execution risk."* Claim only. |
| `yodablocks/depth-map` | E2 | C | Cost-to-move in bps for $5k/$25k/$100k across 5 venues, `exh` when book runs out. Pure cost, cross-venue. |
| `Atheren009/Low-Latency-Order-Router-` | E2 | C | Fill rate 49.4%→66.7% across routers; slippage measured **on filled shares only**, so the unfilled half is never marked out. Spread/fees as cost. |
| `KBenBec/quant-microstructure-hft-` | E1 | C | One-line README: *"core features (spread/imbalance/microprice), cost-aware execution sims (TWAP/VWAP/POV)"*. No code retrieved. |
| `kexin-deng/High-Frequency-Execution-Strategy-...` | E1 | C | One-line README: *"score-based execution with momentum, order flow imbalance, **volatility-to-spread**, and time pressure."* The phrase `volatility-to-spread` is the nearest thing to a spread ratio in the corpus, but there is no code or formula. |
| `FrionicSaddly/perp-quant-bot` | E1 | D | *"cost-aware backtest"*, purged walk-forward CV. Off-gap. |
| `mega-Slaking/systematic_trading_model` | E3 | D | Large, tested engine — but its "regime" is **macro** (inflation/growth/curve), not spread. Off-gap. |
| `eldermorph/A-Microstructure-Playground-...` | — | — | HTML 200 but **no README** at `main`/`master`; no content to audit. |
| `sduprey/optimal_transaction_execution` | — | — | HTML 200 but **no README** at `main`/`master`. |
| `ayushshah37/Bootcamp_Ayush_Shah`, `chinthakat` (above) | — | — | Book-building; no spread-state content. |

---

## 3. EXPLICIT ANSWERS TO THE TASK'S FOUR QUESTIONS

| Question | Answer across all verified repos |
|---|---|
| Any repo that shows a **STABLE relationship between spread state and expected future move**? | **NO. Zero repos.** |
| Is spread used **purely as a cost filter**? | **YES — in every repo that quantifies it.** As a hard entry gate (`chinthakat`: `MAX_SPREAD_POINTS=50`), a P&L hurdle (`loblab`, `AMIRMAHMOUDINIA`), a decomposition term (`aryansiwach`, `DaniyalMlk`), or a quote-width calibration input (`SpencerOzgur`, `ViswanathDas`, `thibault-charbonnier`). |
| Is **opportunity cost of unfilled orders** modelled? | **Only 2 of 18**: `aryansiwach` (mark unfilled to final mid, weight by fill ratio) and `DaniyalMlk/slippage` (Perold opportunity component, with the order-vs-executed basis convention tested). Everything else that reports a fill rate does **not** charge unfilled quantity. |
| Are **maker exits** modelled as executable or theoretical? | **Executable & conservative: 2** — `aryansiwach` (`simulate_limit`: `queue_ahead`, `cancel_on_through`, `deadline_ns`, residual sweep) and `SpencerOzgur` (front-of-queue vs back-of-queue run **and reported separately**). **Theoretical: 3** — `ViswanathDas`/`thibault-charbonnier`/`SpencerOzgur`-synthetic use Poisson/intensity fills with no queue. **Absent: the rest**, including `loblab`, which lists "a maker/queue-position model" as explicit future work. |

### The single most transferable idea in the corpus
`SpencerOzgur`'s **front-of-queue vs back-of-queue as two reported scenarios** is the cleanest existing answer to *"theoretical maker exit vs actually executable maker exit"*. `aryansiwach`'s `simulate_limit` is the concrete executable implementation of that idea, and `DaniyalMlk/slippage`'s order-basis/executed-basis split is the cleanest treatment of *where the cost of not trading belongs*.

### The single most useful warning
`K1ta141k/loblab` and `AMIRMAHMOUDINIA/...` independently show that **the expected move must clear the spread**, and that it usually does not (`edge` only positive where n is tiny; every cost scenario failed the gate; gross break-even cost 0.909 bps). Any V3 design that treats spread as a state variable rather than a hurdle is unsupported by anything found here.

---

## 4. NEGATIVE-RESULT REGISTER (valid outcomes, recorded so this search is not repeated)

Searches returning **0 repositories**: `passive execution simulator`, `market maker backtest limit order fill`, `opportunity cost unfilled order`, `limit order exit strategy backtest`, `cost aware entry filter trading`, `spread predictor future returns`, `take profit limit order queue simulation`, `bid ask spread volatility relationship`, `spread cost filter strategy signal`, `maker exit limit order profit`, `expected move versus cost trade`.

Search terms that returned only noise/unrelated repos (highest-star results were unrelated documents or games): `spread spike`, `dynamic execution threshold`, `cost to move trading`, `touch exit limit order`, `cost of not trading`, `non execution risk trading`, `spread regime filter`.

**Conclusion for gap (A):** the GitHub OSS population implements spread as **cost**, and does not implement spread regime / spread spike / volatility×spread / spread-to-expected-move / cost-to-move *as a state variable*. The phrase "cost-to-move" appears in public code (`yodablocks/depth-map`) but only as a **slippage metric**, never as a decision variable. **Gap (A) remains genuinely open in public repos.**
