"""Integrate the two task-004 gap-searches into the registries.

READ-ONLY. Writes only under github_candidate_model_distillation/.
No network here: it records what parts/search_*.md already verified.
"""
from __future__ import annotations

import json
import os

H = os.path.dirname(os.path.abspath(__file__))
GEN = "2026-09-22T06:05:00Z"

SEARCH_RESULTS = [
 {"slug": "r33bt/signal-decay-calculator", "E": "E1", "T": "B", "decay_form": "exponential, explicit formula",
  "formula": "IC(h) = IC0*exp(-lambda*h), lambda by log-linear OLS; half-life = ln2/lambda",
  "exit_trigger": "threshold on remaining edge (IC>=75% of IC0) -> rebalance cadence; NO intraday exit",
  "second_crossing": "not modelled", "taxonomy_4way": "no", "audit": "search_edge_decay"},
 {"slug": "quantskills/skill-factor-ic-decay", "E": "E2", "T": "B", "decay_form": "exponential via log-linear fit",
  "formula": "IC(h)=A*exp(-h/tau); t_half = tau*ln2; Newey-West t (lag=5); ICIR",
  "exit_trigger": "none (diagnostic only)", "second_crossing": "not modelled", "taxonomy_4way": "no",
  "audit": "search_edge_decay",
  "warning": "author states the half-life is a fitted shape parameter, NOT a promise that the signal works for N more days"},
 {"slug": "zj092912/wti-airline-stat-arb", "E": "E3", "T": "A", "decay_form": "structural: OU + finite-horizon optimal-stopping free boundary (tightens as time-to-close shrinks)",
  "formula": "no closed-form E(t); exit boundary from a free-boundary PDE on a 161-node grid",
  "exit_trigger": "optimal-stopping boundary vs z-score +-2sigma/+-0.5sigma",
  "second_crossing": "YES - the headline result: buys at ask, sells at bid, tracked in two books",
  "result": "mark-to-mid Sharpe 1.08, +$463,326  BUT realised -$24,931,458 over 10,907 trades -> the entire mid edge and more is inside the bid-ask spread",
  "taxonomy_4way": "partial (mid edge vs execution cost)", "audit": "search_edge_decay"},
 {"slug": "nirholas/markout-fee", "E": "E2", "T": "B", "decay_form": "EWMA toxicity weighting",
  "formula": "toxicity_t = (1-alpha)*toxicity_{t-1} + alpha*observation ; fee = baseFee + maxSurcharge*toxicity",
  "exit_trigger": "none (LP fee pricing)", "second_crossing": "no", "taxonomy_4way": "partial (informed vs noise, graded)",
  "audit": "search_edge_decay",
  "note": "uses a fixed minHorizon delay before grading, explicitly to avoid measuring the swap's own same-block impact"},
 {"slug": "punyamodi/Deep-Market-Maker", "E": "E2", "T": "B", "decay_form": "empirical IC/ICIR-vs-horizon curve (no fit)",
  "formula": "P(fill|q,V)=max(0,1-(q/V)^alpha); Hawkes kernel phi(tau)=alpha*exp(-beta*tau); A-S delta=gamma*sigma^2*(T-t)+(2/gamma)*ln(1+gamma/kappa)",
  "exit_trigger": "toxicity threshold quotes (toxicity>0.65 -> spread x2.5, size x0.5)", "second_crossing": "simulated exchange with queue fills + fees",
  "taxonomy_4way": "partial (spread / adverse selection / inventory carry)", "audit": "search_edge_decay"},
 {"slug": "tfrmma/realistic-mm-backtester", "E": "E3", "T": "C", "decay_form": "none; empirical adverse-selection score over lookback_ticks=10",
  "exit_trigger": "none", "second_crossing": "taker crossing + FIFO queue + lognormal latency + fees", "taxonomy_4way": "no",
  "audit": "search_edge_decay"},
 {"slug": "atiselsts/dex-markout-simulations", "E": "E1", "T": "D", "decay_form": "empirical markout curve at {0,1,3,10,30} min",
  "exit_trigger": "none", "second_crossing": "no", "taxonomy_4way": "no", "audit": "search_edge_decay"},
 {"slug": "Harmar88/mm-adverse-selection", "E": "E2", "T": "C", "decay_form": "exponential ARRIVAL-intensity decay lambda(delta)=A*exp(-k*delta) (NOT edge decay)",
  "exit_trigger": "none (quote width as defence)", "second_crossing": "no",
  "taxonomy_4way": "partial (exact identity spread + adverse_selection + inventory)", "audit": "search_edge_decay"},
 {"slug": "AshJha0/electronic-trading", "E": "E3", "T": "C", "decay_form": "exponential e-folding time of the AC trajectory theta=1/kappa (NOT ln2/kappa)",
  "exit_trigger": "none", "second_crossing": "no", "taxonomy_4way": "no", "audit": "search_edge_decay"},
 {"slug": "PrazwalR/Assay", "E": "E2", "T": "D", "decay_form": "none", "exit_trigger": "none", "second_crossing": "no",
  "taxonomy_4way": "adverse selection only", "audit": "search_edge_decay",
  "note": "honest negative: its own pre-declared gate FAILS (91 positives vs floor 100; weakest walk-forward fold 0.469 vs floor 0.60)"},
 {"slug": "aryansiwach/execution-market-microstructure", "E": "E4", "T": "A",
  "spread_role": "COST strictly; decomposed (quoted/effective/realised/impact) - a cost-ADEQUACY identity, not a predictor",
  "formula": "realised spread = 2*q*(price - mid_{t+h}); price impact = effective - realised; opp = side*(final_mid-arrival_mid)/arrival_mid*1e4 * unfilled/target; is_bps = (filled/target)*exec_cost + opp",
  "opportunity_cost": "YES - unfilled shares marked to final mid and weighted by fill ratio",
  "maker_exit": "EXECUTABLE & conservative: simulate_limit uses queue_ahead, cancel_on_through, deadline_ns, then sweeps the residual",
  "audit": "search_spread_state"},
 {"slug": "DaniyalMlk/slippage", "E": "E5", "T": "A", "spread_role": "COST (half-spread split into immediacy price and impact/timing)",
  "formula": "Perold IS decomposed: delay / trading / opportunity / commission / fees",
  "opportunity_cost": "YES - most rigorous in the corpus; 'opportunity is the move on shares that never traded'; order-basis vs executed-basis convention stated AND tested",
  "maker_exit": "NO queue model (consumes fills)", "audit": "search_spread_state"},
 {"slug": "K1ta141k/loblab", "E": "E3", "T": "B", "spread_role": "PURE COST - the repo is built around it",
  "formula": "obi=(bidD-askD)/(bidD+askD); fires at |obi|>0.30; maker r = mid - gamma*inventory + theta*OBI",
  "finding": "OBI is directionally right, but the move only clears the ~1-tick spread at extreme thresholds where n is tiny; 'that crux (signal < spread) is the whole game in taker alpha'",
  "maker_exit": "ABSENT - a maker/queue-position model is listed as future work", "audit": "search_spread_state"},
 {"slug": "AMIRMAHMOUDINIA/microstructure-signals-vs-executable-alpha", "E": "E5", "T": "A",
  "spread_role": "COST; spread crossed on both sides; non-overlapping positions; round-trip cost sensitivity 0..12 bps",
  "formula": "TFI = (2*taker_buy_volume - total_volume)/total_volume",
  "finding": "every cost scenario failed the economic gate; even at 0 additional bps the selected strategy averaged -0.343 bps/trade; gross break-even additional cost only 0.909 bps",
  "protocol": "pre-registered gates, locked test set, HAC, BH-FDR, block bootstrap",
  "audit": "search_spread_state"},
 {"slug": "SpencerOzgur/Optimal-High-Frequency-Market-Making-With-Robust-Backtesting", "E": "E3", "T": "A",
  "spread_role": "spread is an OUTPUT (quote width) driven by volatility and inventory; volatility is the state variable",
  "formula": "r = s - (q/lot)*gamma*sigma^2*(T-t); spread(t)=gamma_rv*sigma2_t*(T-t)+B",
  "maker_exit": "THE CLEANEST ANSWER: queue_model='front' (theoretical/optimistic) and 'back' (conservative/executable) are BOTH run and REPORTED SEPARATELY",
  "audit": "search_spread_state"},
 {"slug": "chinthakat/xauusd-rl-engine", "E": "E2", "T": "B", "spread_role": "PURE COST - a static hard gate",
  "formula": "if spread_points > MAX_SPREAD_POINTS(=50): refuse; MAX_SLIPPAGE=30 as MT5 deviation",
  "note": "XAUUSD on MT5 - the same venue family as Hermes; no regime, no dynamic threshold",
  "audit": "search_spread_state"},
 {"slug": "khintchine/rs-heston-mm", "E": "E2", "T": "B", "spread_role": "regime-INDEXED (the only genuine state use found)",
  "formula": "Lambda^a_i(delta)=A^a_i*exp(-eta^a_i*delta) indexed by volatility regime i; Wonham filter; Q = [[-lambda_HL, lambda_HL],[lambda_LH,-lambda_LH]]",
  "note": "the state is the VOLATILITY regime; spread is an argument, not the state -> causal direction is backwards for the gap",
  "audit": "search_spread_state"},
 {"slug": "andrewkni/bayesian-spike-detector", "E": "E1", "T": "D",
  "finding": "the only repo where a spread change is read as evidence about a future move - and it predicts REVERSAL ('widening spread on a big YES jump increases alpha = fake spike'), the OPPOSITE sign to the gap hypothesis",
  "audit": "search_spread_state"},
]

NEGATIVE_SEARCHES = [
 "passive execution simulator", "market maker backtest limit order fill", "opportunity cost unfilled order",
 "limit order exit strategy backtest", "cost aware entry filter trading", "spread predictor future returns",
 "take profit limit order queue simulation", "bid ask spread volatility relationship",
 "spread cost filter strategy signal", "maker exit limit order profit", "expected move versus cost trade",
]
NOISE_SEARCHES = ["spread spike", "dynamic execution threshold", "cost to move trading", "touch exit limit order",
                  "cost of not trading", "non execution risk trading", "spread regime filter"]

# component patches driven by the two searches
PATCH = {
 "CMP-04": {"evidence_level": "E5",
   "source_repo": "DaniyalMlk/slippage (E5 Perold, order-vs-executed basis); aryansiwach/execution-market-microstructure (E4 opportunity on unfilled); gelatotrade (E3); AshJha0 (E4-eng)",
   "formula": "IS_total = Spread + Impact + Fee + Opportunity ; Opportunity = max(0, adverse post-window drift) * UNFILLED fraction  "
              "|| aryansiwach: opp = side*(final_mid-arrival_mid)/arrival_mid*1e4 * unfilled/target ; is_bps = (filled/target)*exec_cost + opp",
   "assumption": "each term separately visible; positive = cost; unknown = DATA_GAP never 0; the DELAY term has two conventions "
                 "(order-basis charges all target shares, executed-basis charges only traded shares) and both must be declared"},
 "CMP-06": {"source_repo": "SpencerOzgur (E3: front-of-queue vs back-of-queue run AND reported separately); aryansiwach (E4 simulate_limit: queue_ahead/cancel_on_through/deadline_ns + residual sweep); tfrmma (E3)",
   "formula": "fill_price = ask(t+L) BUY / bid(t+L) SELL ; exit adds a SECOND spread + commission. "
              "Maker fills must be reported as a front/back QUEUE PAIR (theoretical vs executable), never as a single number."},
 "CMP-08": {"source_repo": "r33bt (E1) + quantskills (E2) for the exponential fit; zj092912 (E3, REAL data) for the exit-cost annihilation; AshJha0 (E4-eng) price-shift invariance; KlishevDA (markout curves)",
   "formula": "E(t) = E0 * exp(-lambda*t), t_half = ln2/lambda, lambda by log-linear OLS on ln E vs h  ||  "
              "EXIT iff E[remaining_edge] - exit_cost < 0, exit_cost = one more spread + commission",
   "assumption": "NO repo derives E(t) from microstructural primitives; the exponential form is a FIT, not a law. "
                 "zj092912 shows the exit spread can annihilate the entire mid edge (mark-to-mid Sharpe 1.08 -> realised -$24.9M), "
                 "so lambda is irrelevant if exit_cost >= residual edge at every horizon.",
   "failure_mode": "fixed TP/SL ignoring decay; exiting on realised PnL instead of expected remaining edge; "
                   "fitting the decay on the same trades it times"},
 "CMP-09": {"evidence_level": "E5",
   "source_repo": "AMIRMAHMOUDINIA (E5: pre-registered gates, locked test, HAC, BH-FDR, block bootstrap); snowkings; himagna16; Trumplus",
   "formula": "report edge_uncertainty (CI), execution_uncertainty (fill/cost band), data_uncertainty (DATA_GAP list); "
              "effective_N = n/max(1,rho); cost sensitivity across 0..12 bps as in AMIRMAHMOUDINIA"},
}

SYNTHESIS = [
 "SPREAD_IS_COST_NOT_PREDICTOR: across all verified repos, NO repo shows a stable spread-state -> expected-future-move relationship. "
 "Gap (A) remains genuinely open in public repos; spread is a cost / a hurdle / a quote-width output.",
 "INDEPENDENT_CONFIRMATION: K1ta141k/loblab ('signal < spread is the whole game in taker alpha') and "
 "AMIRMAHMOUDINIA ('even at 0 additional bps, -0.343 bps/trade; gross break-even additional cost 0.909 bps') "
 "independently reproduce V3's own central finding (0.914 bp cost vs sub-cost edge).",
 "EXIT_COST_ANNIHILATION: zj092912 - mark-to-mid Sharpe 1.08 / +$463,326 became realised -$24,931,458. "
 "The second spread crossing is not a detail; it is the result.",
 "THEORETICAL_VS_EXECUTABLE_MAKER_EXIT: SpencerOzgur is the only repo that runs front-of-queue and back-of-queue "
 "AND reports them separately - the cleanest way to publish maker-exit uncertainty.",
 "OPPORTUNITY_COST_IS_RARE: only 2 of 18 repos charge unfilled quantity (aryansiwach, DaniyalMlk). "
 "Retail backtests silently set opportunity cost to zero.",
 "NO_REPO_DERIVES_E(t): the exponential E(t)=E0*exp(-lambda t) is the only reusable form, and it is a fit. "
 "The 4-way taxonomy (ENTRY_WRONG / EDGE_DECAY / ADVERSE_SELECTION / COST_EROSION) is implemented by NO repo "
 "- CAND-003 must supply it itself.",
]


def main():
    p = os.path.join(H, "github_search_registry.json")
    reg = json.load(open(p, encoding="utf-8"))
    reg["generated_utc"] = GEN
    reg["results"] = SEARCH_RESULTS
    reg["result_count"] = len(SEARCH_RESULTS)
    reg["negative_searches_zero_repos"] = NEGATIVE_SEARCHES
    reg["noise_only_searches"] = NOISE_SEARCHES
    reg["verification_caveat"] = ("the literal /repos/<slug> endpoint was HTTP 403 for both searches "
                                   "(unauthenticated core quota 0/60 drained by the search phase). Existence was proven instead by "
                                   "(a) api.github.com scoped search returning an EXACT full_name match (search A: 15/15), and "
                                   "(b) github.com/<slug> HTTP 200 + successful raw.githubusercontent.com README/source fetches "
                                   "(search B: 18/18). No slug is reported on inference.")
    reg["synthesis"] = SYNTHESIS
    json.dump(reg, open(p, "w", encoding="utf-8", newline="\n"), indent=1)
    print("updated github_search_registry.json (results:", len(SEARCH_RESULTS), ")")

    cp = os.path.join(H, "model_component_registry.json")
    comp = json.load(open(cp, encoding="utf-8"))
    for c in comp["components"]:
        patch = PATCH.get(c["component_id"])
        if patch:
            c.update(patch)
            c["patched_utc"] = GEN
    comp["generated_utc"] = GEN
    comp["search_integration"] = "task-004 gap-searches (search_edge_decay, search_spread_state) integrated; see github_search_registry.json"
    json.dump(comp, open(cp, "w", encoding="utf-8", newline="\n"), indent=1)
    print("patched components:", list(PATCH.keys()))


if __name__ == "__main__":
    main()
