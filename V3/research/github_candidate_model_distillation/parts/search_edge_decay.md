# Search A — Edge Decay / Alpha Decay / Markout Decay / Dynamic Exit

**Task:** V3-HFT-GITHUB-CANDIDATE-MODEL-DISTILLATION-004
**Mode:** READ-ONLY GitHub search/audit (no purchases, no signups, no MT5, no orders, no training, no backtesting)
**Date:** 2026-09-22
**Scope:** find real repos implementing EDGE DECAY / ALPHA DECAY / MARKOUT DECAY / DYNAMIC EXIT / SURVIVAL-HAZARD EXIT; extract decay form, data reality, exit trigger, second-spread-crossing handling, and whether the repos distinguish ENTRY_WRONG vs EDGE_DECAY vs ADVERSE_SELECTION vs COST_EROSION.

---

## 1. Method & verification

**Search:** GitHub Search API (`https://api.github.com/search/repositories?q=...`) over queries:
`alpha+decay`, `markout+decay`, `signal+decay+half+life`, `hazard+model+trading`, `survival+analysis+order`,
`dynamic+exit+trading`, `execution+markout+curve`, `adverse+selection`, `market+making+adverse+selection`,
`optimal+stopping+exit`, `time+stop+exit`, `order+flow+toxicity`, `half+life+decay`, `market+impact+decay`,
`execution+cost+model`, `hazard+rate`, `survival+analysis`.

**Verification (per repo, before reporting):**
1. `api.github.com/repos/<slug>` returned **HTTP 403 / core-quota exhausted (0/60)** for the shared egress IP during the whole run (60/min→60/hr unauthenticated core pool was already spent by other traffic; reset window ~39 min out). So an equivalent **api.github.com** existence proof was used: repository-search across `api.github.com` scoped with `q=<name> in:name user:<owner>`, asserting the returned `full_name` **exactly equals** the slug. Result: **matched=15, unmatched=0** (every slug returned HTTP 200 with an exact identity match).
2. Cross-checked with `https://github.com/<slug>` → **HTTP 200** for all 15.
3. Cross-checked with `https://raw.githubusercontent.com/<slug>/HEAD/README.md` → **HTTP 200** for all 15 (404 otherwise), and READMEs + core source files were read via `raw.githubusercontent.com`.

**Caveat recorded honestly:** the literal `/repos/<slug>` endpoint was not reachable (quota), but identity was confirmed three independent ways, all HTTP 200. No repo, file, formula or number below is invented; every quoted formula is copied from the actual file.

---

## 2. Verified repos (15) — extraction

Legend: **EVIDENCE_LEVEL** E0 (claim only) → E5 (production + replicated). **TRANSFERABILITY** A (directly usable in an HFT exit engine) → E (not transferable).

### 2.1 `r33bt/signal-decay-calculator` — ★0, MIT, pushed 2026-07-24
- **DECAY FORM:** **exponential, functional form given explicitly.** `IC(h) = IC₀ · e^(−λ·h)`, fitted by log-linear OLS `ln IC = a + b·h`, `λ = −b`.
- **REAL vs SYNTHETIC:** neither — a pure calculator; IC inputs are user-entered and the shipped defaults are **illustrative (synthetic)**.
- **EXIT TRIGGER:** threshold-on-remaining-edge → rebalancing cadence: `rebalanceDays = ceil(−ln(0.75)/λ)` (rebalance when IC(h)/IC₀ ≥ 0.75). Not an intraday exit.
- **SECOND SPREAD CROSSING:** **not modelled.**
- **4-way taxonomy:** **no.**
- **EVIDENCE:** **E1.** **TRANSFERABILITY:** **B.**
- **CODE (quoted, `index.html`):**
  ```js
  var fit = linReg(xs, ys);          // ys = Math.log(parseFloat(r.ic))
  var ic0 = Math.exp(fit.a);
  var lambda = -fit.b;
  if (lambda <= 0) return null;
  var halfLife = Math.log(2) / lambda;
  var rebalanceDays = Math.ceil(-Math.log(0.75) / lambda);
  ```

### 2.2 `quantskills/skill-factor-ic-decay` — ★1, GPL-3.0, pushed 2026-08-07
- **DECAY FORM:** **exponential via log-linear fit:** `log IC(h) = log A − h/τ  ⇒  IC(h) = A·e^(−h/τ)`; half-life `t½ = τ·ln2`. Computes daily cross-sectional Spearman IC, ICIR (raw + annualized), Newey–West t (lag=5), rolling-window stability.
- **REAL vs SYNTHETIC:** user-supplied panel `date,symbol,factor,fwd_ret`; ships a **synthetic demo panel**. Framework-neutral, no data source included.
- **EXIT TRIGGER:** **none** — explicitly a diagnostic ("no trading signals"). It warns against treating half-life as a shelf-life: *"t½ 是历史衰减形状的拟合参数, 不是'还能用 N 天'的承诺"*.
- **SECOND SPREAD CROSSING:** **not modelled.**
- **4-way taxonomy:** **no.**
- **EVIDENCE:** **E2** (sample guards: IC obs <60 → hard reject; <252 → low-sample warning; `validate.py` 9/9 self-checks). **TRANSFERABILITY:** **B.**
- **CODE (quoted, `references/ic-methods.md`):** `IC(h)=A\,e^{-h/\tau}`, `t_{1/2} = \tau \ln 2`, plus Newey–West: `t_NW = mean(IC)/sqrt(σ²_NW/n)`.

### 2.3 `zj092912/wti-airline-stat-arb` — ★0, pushed 2026-08-12  ← **most relevant for exit cost**
- **DECAY FORM:** **none (structural).** OU mean-reversion (κ, θ, σ). Exit boundary is solved as a **finite-horizon optimal-stopping free-boundary PDE** — the boundary is **time-varying and tightens as the close approaches** (continuation value decays with time-to-close). That is an implicit time-dependent exit threshold, not a modelled E(t).
- **REAL vs SYNTHETIC:** **REAL** — 4 years of 15-minute real bid/ask data (WTI vs DAL/UAL/AAL), walk-forward (60-day warm-up → 20-day OOS → roll).
- **EXIT TRIGGER:** optimal-stopping boundary (free-boundary PDE, 161-node grid); compare ad-hoc z-score ±2σ/±0.5σ.
- **SECOND SPREAD CROSSING:** **YES — and it is the headline result.** Every fill crosses the actual quoted spread (buys at ask, sells at bid), tracked in two books (mark-to-mid vs realized-with-execution). PDE-optimal bands: **mark-to-mid Sharpe 1.08, +$463,326, but realized P&L −$24,931,458** on $1M capital over 10,907 trades (avg hold 31 min). *"The entire edge — and then some — is inside the bid–ask spread."*
- **4-way taxonomy:** **partial** — separates mid-price edge from execution cost (≈ EDGE vs COST_EROSION), but not all four.
- **EVIDENCE:** **E3** (real data, strict OOS, honest negative result). **TRANSFERABILITY:** **A.**
- **No closed-form decay formula**; the finding is the exit-cost annihilation of a mid-price edge.

### 2.4 `nirholas/markout-fee` — ★3, Apache-2.0, pushed 2026-09-15 (Uniswap v4 hook)
- **DECAY FORM:** **exponential weighting (EWMA)** over toxic/informed verdicts: `toxicity_t = (1−α)·toxicity_{t−1} + α·observation`, `α = alphaWad` (default 0.1).
- **REAL vs SYNTHETIC:** **on-chain real tick history** (grades actual past swaps).
- **EXIT TRIGGER:** none (LP fee pricing); the *measurement rule* is a fixed **`minHorizon` (seconds) delay** before a verdict is recorded — **explicitly to avoid measuring the swap's own same-block price impact** rather than what happened next.
- **SECOND SPREAD CROSSING:** no (hook-side fee, not a taker).
- **4-way taxonomy:** **partial** — informed (adverse selection) vs noise, graded **by magnitude** (scaled `continuationTicks / saturationTicks`, then clamped), not as a coin flip.
- **EVIDENCE:** **E2** (production hook, fixed immutable params, no privileged role; unaudited). **TRANSFERABILITY:** **B.**
- **CODE (quoted, `src/hooks/MarkoutFeeHook.sol`):** `fee = baseFee + maxSurcharge * toxicity`; `FeeMath.addClamped(cfg.baseFee, FeeMath.mulDiv(cfg.maxSurcharge, bounded, WAD))`.

### 2.5 `punyamodi/Deep-Market-Maker` — ★7, pushed 2026-02-28
- **DECAY FORM:** **empirical only** — `compute_ic_decay()` builds an IC/ICIR-vs-horizon **curve** (Spearman/Pearson); `compute_rolling_ic()` for decay detection. **No functional fit, no half-life.**
- **REAL vs SYNTHETIC:** **real** LOBSTER L3 pipeline (plus `generate_synthetic_lobster_data` for tests); headline quickstart uses synthetic.
- **EXIT TRIGGER:** **threshold on toxicity signal** — `toxicity > 0.65 → spread ×2.5, size ×0.5`; `toxicity < 0.35 → tighten 10%`. A quote-tilt rule, not a position exit.
- **SECOND SPREAD CROSSING:** simulated exchange with queue fills, latency jitter, maker/taker fees; PnL attribution **spread capture / adverse selection / inventory carry**.
- **4-way taxonomy:** **partial** (spread vs adverse-selection vs inventory), not the four requested.
- **EVIDENCE:** **E2** (28 tests, FDR/SPA/Deflated-Sharpe guards; real pipeline exists but results shown are synthetic). **TRANSFERABILITY:** **B.**
- **CODE (quoted):** fill `P(fill | q, V) = max(0, 1 − (q/V)^alpha)` (Cont–Stoikov–Talreja); Hawkes kernel `φ(τ) = α·exp(−β·τ)`; A–S `δ = γσ²(T−t) + (2/γ)·ln(1+γ/κ)`, `r = s − q·γ·σ²·(T−t)`; `ICIR = mean(rolling IC)/std(rolling IC)`.

### 2.6 `tfrmma/realistic-mm-backtester` — ★9, pushed 2026-07-17
- **DECAY FORM:** **none.** Empirical **adverse-selection score** = mean over fills of post-fill mid move (`lookback_ticks=10`).
- **REAL vs SYNTHETIC:** supports **real** CSV/Parquet L2/L3 tick replay; `synthetic.py` random-walk for smoke tests.
- **EXIT TRIGGER:** none (market making); reporting flags *"edge decay"* only qualitatively (`equity_curves_overlay`).
- **SECOND SPREAD CROSSING:** models taker crossing, FIFO queue, lognormal latency, maker/taker fees — exit cost only via fees.
- **4-way taxonomy:** **no** (adverse-selection score only).
- **EVIDENCE:** **E3** (CI, 80 tests, Rust-accelerated queue path). **TRANSFERABILITY:** **C.**
- **CODE (quoted, `mmbt/reporting/metrics.py`):** `scores.append((fr.mid_at_fill - mid_list[fi]) * side_sign)` (positive = adversely selected); `equity = realized_pnl + unrealized_pnl - fees_paid`.

### 2.7 `atiselsts/dex-markout-simulations` — ★5, pushed 2024-07-30
- **DECAY FORM:** **empirical markout curve** across horizons `{0,1,3,10,30}` minutes (`self.markouts = {0:[],1:[],3:[],10:[],30:[]}`).
- **REAL vs SYNTHETIC:** **SYNTHETIC** — markout measured on simulated price trajectories (LVR model).
- **EXIT TRIGGER:** none. **SECOND SPREAD CROSSING:** no. **4-way taxonomy:** no.
- **EVIDENCE:** **E1.** **TRANSFERABILITY:** **D.**

### 2.8 `Harmar88/mm-adverse-selection` — ★1, pushed 2026-07-26
- **DECAY FORM:** exponential **arrival-intensity** decay: `λ(δ) = A·e^(−kδ)` (fill-rate decay in quote distance δ) — *not* edge decay.
- **REAL vs SYNTHETIC:** **SYNTHETIC** simulator.
- **EXIT TRIGGER:** none (quote width as defence).
- **SECOND SPREAD CROSSING:** no. **4-way taxonomy:** **partial** — exact P&L identity `spread + adverse_selection + inventory` (inventory = residual); markout inferred, cross-checked vs ground-truth informed flags.
- **EVIDENCE:** **E2** (assertions every run; zero-toxicity case checked vs Avellaneda–Stoikov 2008 Table 1). **TRANSFERABILITY:** **C.**
- **CODE (quoted, README):** `dS = σ dW + J dN`; `λ(δ) = A e^{-kδ}`.

### 2.9 `AshJha0/electronic-trading` — ★28, pushed 2026-09-06
- **DECAY FORM:** exponential **e-folding time of the AC liquidation trajectory**, `θ = 1/κ`; the docstring explicitly states it is the e-folding time **not** `ln2/κ`.
- **REAL vs SYNTHETIC:** **synthetic** (parameter sets + 19 golden cases).
- **EXIT TRIGGER:** none (schedule; TWAP/POV baselines).
- **SECOND SPREAD CROSSING:** no (Almgren–Chriss impact only). **4-way taxonomy:** no.
- **EVIDENCE:** **E3** (4-language golden-value suite, literature closed-form = discrete sums to 1e-12). **TRANSFERABILITY:** **C.**
- **CODE (quoted, `python/src/etrade/almgren_chriss.py`):** `half_life(params) -> theta = 1/kappa`; `kappa = log1p(x + sqrt(x*(2.0+x)))/tau`.

### 2.10 `KlishevDA/Market-Microstructure-and-Latency-Effects-in-L2-Market-Making` — ★1, pushed 2026-01-31
- **DECAY FORM:** **empirical markout curve** over horizons (ms) — `reports/markout.py`, mean-markout plot.
- **REAL vs SYNTHETIC:** run JSONL from **BTC** book replay.
- **EXIT TRIGGER:** none. **SECOND SPREAD CROSSING:** no. **4-way taxonomy:** no.
- **EVIDENCE:** **E1.** **TRANSFERABILITY:** **D.**
- **CODE (quoted):** bid fill markout `= mid_future − fill_px`; ask fill `= fill_px − mid_future` (positive = good for maker).

### 2.11 `PrazwalR/Assay` — ★4, pushed 2026-09-11
- **DECAY FORM:** **none.** Per-swap adverse-selection tariff from the price gap the *specific* swap closes.
- **REAL vs SYNTHETIC:** classifier trained on **real** swap data — but the **pre-declared gate FAILS** (91 positives vs floor 100; weakest walk-forward fold 0.469 vs floor 0.60; AUC 0.7485 clears its 0.65 floor). Honest negative result.
- **EXIT TRIGGER:** none. **SECOND SPREAD CROSSING:** no. **4-way taxonomy:** adverse selection only.
- **EVIDENCE:** **E2** (source-verified, fork-tested on Base Sepolia; never held real value). **TRANSFERABILITY:** **D.**
- **CODE (quoted, README):** `fee = clamp(500 + drift-adjustment, 100, 10,000)` (pips).

### 2.12 `Leotaby/Market-Making-Simulator` — ★1, pushed 2026-09-05
- **DECAY FORM:** exponential **fill-probability** decay vs distance: `A·e^(−kδ)` (A=liquidity, k=decay).
- **REAL vs SYNTHETIC:** **SYNTHETIC** Monte Carlo; adverse selection injected as post-fill drift.
- **EXIT TRIGGER:** none. **SECOND SPREAD CROSSING:** no. **4-way taxonomy:** no (markout metric; markout crosses zero as informed impact ≈ captured spread).
- **EVIDENCE:** **E2** (8 CI tests, paired seeds). **TRANSFERABILITY:** **D.**

### 2.13 `369geofreeman/Ornstein_Uhlenbeck_Model` — ★14, pushed 2022-06-15
- OU parameter MLE (log-likelihood) + optimal-stopping problem for entry/exit. **No decay form, synthetic/unknown data, no spread-crossing, no taxonomy.** **EVIDENCE E1, TRANSFERABILITY D.**

### 2.14 `jaikaushik-prog/optimal-stopping-regime-uncertainty` — ★0, pushed 2025-12-25
- Optimal stopping under hidden regimes; belief over trend vs mean-reversion drives entry/exit/sizing. README is 3 lines; no data/formula evidence. **EVIDENCE E1, TRANSFERABILITY D.**

### 2.15 `poojitha376sp/adverse-selection-market-making` — ★0, pushed 2026-07-23
- Avellaneda–Stoikov extension, adverse-selection-aware quoting (QuantFest microstructure suite). No decay form, no exit-cost model. **EVIDENCE E1, TRANSFERABILITY D.**

---

## 3. Cross-cutting findings

**Does ANY repo derive a FUNCTIONAL FORM for E(t) — remaining edge over time?**
**NO.** No repo in this sweep derives E(t) from microstructural primitives.
- Repos with an **explicit parametric decay function** (fits, not derivations): `r33bt` (`IC(h)=IC₀e^(−λh)`), `quantskills` (`IC(h)=A e^(−h/τ)`), `Leotaby`/`Harmar88` (fill intensity `A e^(−kδ)`), `AshJha0` (`θ=1/κ` trajectory e-folding), `nirholas` (EWMA).
- Repos that only **report an empirical curve**: `atiselsts`, `KlishevDA`, `punyamodi`, `tfrmma` (markout/IC curves over horizons, no fitted law).
- The closest thing to a *derived* time-dependent exit is `zj092912`'s finite-horizon optimal-stopping free boundary (the boundary tightens as time-to-close shrinks) — structural, not a closed-form E(t).

**Second spread crossing (exit cost) modelled explicitly:** only `zj092912` (crosses the real quoted spread on entry *and* exit; the entire mid-price edge is erased by it). Everyone else models fees/impact at best; most ignore it.

**4-way taxonomy (ENTRY_WRONG vs EDGE_DECAY vs ADVERSE_SELECTION vs COST_EROSION):** **no repo implements it.** Best partials: `Harmar88` (`spread + adverse_selection + inventory` identity), `punyamodi` (spread / adverse selection / inventory carry), `zj092912` (mid edge vs execution cost). This decomposition is a **genuine gap** the candidate model must supply itself.

**Valid negative results:** no repo with a trading **survival/hazard exit** (Cox, hazard-rate) was found — GitHub "survival analysis" hits are biomedical/churn, and "hazard model" hits are seismic/CDS/churn, not trade-exit. No repo implements a **markout-rule exit** (exit when realised markout crosses a threshold) — markout is used only as *diagnostics*.

## 4. Single most reusable formula / finding

**`E(t) = E₀ · e^(−λ·t)`, with half-life `t½ = ln2/λ`, estimated by log-linear OLS on positive-edge horizons (`ln E = a − λ·h`).**
Two independent repos (`r33bt/signal-decay-calculator`, `quantskills/skill-factor-ic-decay`) implement exactly this, and it is the only *reusable functional form* found. Combine it with `zj092912`'s hard constraint: **before trusting any E(t), subtract the second spread crossing** — a 1.08 mid Sharpe became −$24.9M net, i.e. the fitted decay rate λ is irrelevant if the exit cost exceeds the residual edge at every horizon.
