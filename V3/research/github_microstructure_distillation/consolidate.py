"""Consolidate the three distiller part files into the delivery artifacts.

READ-ONLY. Writes only under research/github_microstructure_distillation/.
No network, no MT5, no orders. Data below is transcribed from parts/group_{A,B,C}.md.
"""
from __future__ import annotations

import csv
import json
import os

H = os.path.dirname(os.path.abspath(__file__))
GEN = "2026-09-22T05:45:00Z"

# ---------------------------------------------------------------- repos
# slug, group, evidence, transferability, failure/negative type, one-line sharpest warning
REPOS = [
 ("RobertN1D/XAUUSD-GOLD-SCALPER-MT5-EA-FREE-SOURCE-CODE","A","E1","B","SYNTHETIC_DATA_DEPENDENCE",
  "11-generator ranker with NO backtest; its only order-flow term is a broker-synthetic DOM the author says to disable"),
 ("NadirAliOfficial/snipe-fx-ea","A","E4","B","COST_TYPE_FAILURE",
  "expected payoff a CONSTANT ~-0.31/trade across all 36 real-tick passes (PF<=0.23); entry is an execution defect"),
 ("NadirAliOfficial/trillex-10s-ea","A","E1","B","SYNTHETIC_TICK_FAILURE",
  "unevidenced signal tested on generated ticks + 10^n lot ladder (10,000-lot cap)"),
 ("n30dyn4m1c/gold-pro-scalper","A","E1","B","NO_PUBLISHED_EVIDENCE",
  "well-reasoned cost gate but no published results; predecessor's OHLC-profitable -> Every-Tick-losing is the trap"),
 ("Sandyyy123/xauusd-scalper-research","A","E1","D","FICTIONAL_FILL_MODEL",
  "bar-touch fills at exact SL/TP with ZERO spread on a 20-min gold scalp; proprietary licence"),
 ("mahmoud20138/OrderFlow-Scalper","A","E1","B","SYNTHETIC_DATA_DEPENDENCE",
  "unvalidated pipeline on a synthetic DOM with inferred aggressor flags; ships defaulted to BTCUSD"),
 ("Leotaby/Market-Making-Simulator","B","E2","C","TAUTOLOGICAL_ADVERSE_SELECTION",
  "AS is an injected post-fill drift; author states no real LOB/feed/queue/latency"),
 ("diegourda/Statistical-Arb-MM","B","E1","C","CLAIM_INFLATION",
  "'30% AS reduction' produced by an engine-free, non-markout toy on data that does not exist"),
 ("tfrmma/realistic-mm-backtester","B","E3","B","UNFALSIFIED_EDGE",
  "genuine FIFO queue/latency/fees/OOS framework but no published OOS result; cancel inference unidentifiable"),
 ("KlishevDA/Market-Microstructure-and-Latency-Effects-in-L2-Market-Making","B","E3","B","QUEUE_ASSUMPTION_FAILURE",
  "fills hinge on an uncalibrated 'rho' luck parameter; single 600s session; no fees"),
 ("xiaohany-cmu-S26/lob-fill-engine","B","E3","B","MODEL_DEPENDENT_LABEL",
  "rigorous purge/embargo/uniqueness fill-probability protocol, but stops at P(fill) - no economic closure"),
 ("siddhantsingh-1/execution-aware-alpha-backtester","C","E4","B","COST_ERASED_ALPHA",
  "OOS IC 0.473, gross +$1.48M, cost $13.11M, net -$11.64M; edge 9.11bps < 10.3bps round-trip"),
 ("snowkings/QIP_adverse_selection","C","E4","B","EXECUTION_FAILURE",
  "+0.29 tick midpoint move vs 1.08 tick spread; negative at every delay and horizon; no CI implied (clustered)"),
 ("himagna16/kalshi-microstructure","C","E4","B","COST_ERASED_ALPHA",
  "'inefficient at the mid, efficient at the touch'; naive taker momentum dies at 10.7c break-even; passive maker -$913"),
 ("aryansiwach/execution-market-microstructure","C","E3","B","REGIME_DEPENDENT_COST",
  "realised spread turns NEGATIVE for small caps under stress; IS never reaches zero for large orders"),
 ("gelatotrade/implementation-shortfall-hyperliquid","C","E3","B","DATA_INTEGRITY_FAILURE",
  "Perold 4-term IS incl. Opportunity on the UNFILLED fraction; namespace collision silently overwrote data"),
 ("Trumplus/AAPL-Limit-Order-Fill-Probability-Forecast","C","E3","C","MODEL_DEPENDENT_LABEL",
  "AUC ~0.72 ceiling for 5s fills; queue position dominates fill probability - which FXTM cannot observe"),
 ("AshJha0/electronic-trading","C","E4_ENGINEERING_E1_MARKET","B","CALIBRATION_GAP",
  "'calibration of eta,gamma_p,A,k to any real market is NOT verified'; AC omits the epsilon*X cost term"),
]

# ---------------------------------------------------------------- mechanisms
MECH = [
 ("MECH-001","Cost-multiple entry gate","A4",
  "Take a trade only if StdDev(fuel) >= k1 * roundTripCost AND distanceToTarget >= k2 * roundTripCost (k1=3,k2=4).",
  "makes marginal trades unprofitable by construction","B","AVAILABLE (spread+commission known)","READY"),
 ("MECH-002","Adaptive tick-window lookback","A1",
  "Start at 30 ticks and EXPAND the window until it spans >= 1 second (cap 250) before computing velocity/acceleration.",
  "fixes velocity maths that collapse when gold prints 100+ ticks/s at the NY open","B","AVAILABLE","READY"),
 ("MECH-003","Rolling p90 spread + spike gate + spread/target ratio in the ranker","A1/A4",
  "Use a rolling p90 spread, block entries on a spread SPIKE multiple, and carry spread/target cost as a scoring term.",
  "cost becomes a first-class ranking feature, not a binary filter","B","AVAILABLE","READY"),
 ("MECH-004","Cost-type-failure test (flat-payoff invariance)","A2",
  "If per-trade expected payoff is flat across the whole parameter surface, the failure is cost, not alpha: stop.",
  "cheapest possible kill-test for a promising-looking sweep","B","AVAILABLE","READY"),
 ("MECH-005","Perold 4-term implementation shortfall incl. Opportunity on the UNFILLED fraction","C6/C8",
  "IS = Spread + Impact + Fee + Opportunity, where Opportunity = max(0, adverse post-window drift) * UNFILLED fraction.",
  "retail backtests silently book unfilled size at par (opportunity cost = 0)","B","PARTIAL (fills!)","READY"),
 ("MECH-006","Spread-vs-edge pre-trade hurdle + mid-vs-touch asymmetry","C1/C3",
  "Publish a per-symbol break-even move (cost hurdle); evaluate every signal at the TOUCH, never only at mid.",
  "'inefficient at the mid, efficient at the touch' is a general law","B","AVAILABLE","READY"),
 ("MECH-007","Reversion-ablation maker/taker classifier","C1",
  "Drop the mean-reversion features; if IC collapses (0.473 -> 0.177), the edge belongs to the quoter, not the taker.",
  "classifies whether your signal is a taker edge at all","B","AVAILABLE","READY"),
 ("MECH-008","Purge + embargo + uniqueness + eligibility censoring + day-level AUC","C7/C1/B5",
  "Chronological splits, purge/embargo by label window, sample-uniqueness weights, exclude unobservable outcomes, report per-day variability.",
  "the standard anti-leakage/anti-inflation protocol","B","AVAILABLE","READY"),
 ("MECH-009","Markout methodology (signed, multi-horizon, with equity)","B1/B4",
  "Per fill: sell -> p - m(t+h); buy -> m(t+h) - p; report markout alongside equity and inventory, never instead.",
  "equity can look fine while markout is negative (hidden toxicity)","B","PARTIAL (L1-based)","READY"),
 ("MECH-010","FIFO qty_in_front + cancel model + size-aware fill label","B3/B5",
  "queue_ahead tracked per order; label 'filled' iff cumulative volume at/through price >= queue_ahead + order_size.",
  "the correct passive-fill formulation","C","DATA_GAP (no real queue on FXTM)","PARKED"),
 ("MECH-011","Intensity calibration + overfit ratio","B2",
  "Fit log(fillRate) = logA - k*spread by OLS; gate every parameter set on OOS_Sharpe / IS_Sharpe.",
  "turns a free parameter into a measured one; flags overfitting","C","DATA_GAP (needs fills)","PARKED"),
 ("MECH-012","Sensitivity parameter published as a first-class result","B3/B4",
  "Publish the fill-model luck parameter (rho) sweep as an output, not as a hidden constant.",
  "queue assumptions are the dominant unmodelled risk","B","AVAILABLE (as a discipline)","READY"),
 ("MECH-013","Detect whether your microstructure input is real before using it","A6/A1",
  "Record has_trade_flags; validate DOM non-degeneracy (constant 50/50 or +-90 jitter = unusable) before it earns weight.",
  "same conclusion reached from both the DOM and the tick side","B","AVAILABLE","READY"),
 ("MECH-014","Real-tick-only acceptance + generated-vs-real honesty table","A2/A3",
  "No tick-scale result is admissible unless it declares 100% real ticks; publish the generated-vs-real delta.",
  "same build: generated PF 1.97 vs real 0.34 (5.8x overstatement)","B","AVAILABLE","READY"),
 ("MECH-015","Init-time invariants, slippage abort, virtual-stop persistence, magic isolation","A2",
  "Refuse to load on illegal parameter combinations; abort a fill worse than N pips; persist virtual SL/TP; scope every position scan by magic+symbol.",
  "cheap, machine-checkable safety that killed a whole EA generation","B","AVAILABLE","READY"),
 ("MECH-016","Avoid paying the spread twice: limit exit at the statistical mean","A4",
  "Enter on the closed bar, exit with a server-side limit at the target so the exit does not cross the spread.",
  "market-order exits pay the spread on both legs","B","AVAILABLE","READY"),
]

# ---------------------------------------------------------------- negative evidence (repo-sourced)
NEG = [
 ("NEG-101","COST_ERASED_ALPHA","siddhantsingh-1/execution-aware-alpha-backtester",
  "OOS IC 0.473; gross +$1,475,656; cost $13,111,643; net -$11,635,987; net Sharpe -0.733; edge 9.11bps vs 10.3bps round trip.",
  "the signal is inside-spread reversion: dropping reversion features collapses IC 0.473 -> 0.177 (maker's edge, not a taker's).",
  "V3: publish a per-symbol cost hurdle and screen every candidate against it BEFORE any backtest."),
 ("NEG-102","EXECUTION_FAILURE","snowkings/QIP_adverse_selection",
  "+0.29 tick mean signed midpoint move vs 1.08 tick entry+exit spread cost: negative at every valid delay and horizon (median -1.00 tick).",
  "the directional information is real but smaller than the cost of crossing to act on it.",
  "V3: measure execution-state value inside the decision, not as a standalone crossing signal."),
 ("NEG-103","COST_ERASED_ALPHA","himagna16/kalshi-microstructure",
  "round trip ~9-11c on a 40-50c contract (10.7c break-even); longshots bought at the ask lose 3.1c (t=-8.9); passive maker -$913 over 14,690 fills.",
  "inefficient at the mid, efficient at the touch.",
  "V3: compute the break-even adverse move per symbol; test mid AND touch."),
 ("NEG-104","QUEUE_ASSUMPTION_FAILURE","KlishevDA/...+tfrmma/realistic-mm-backtester+xiaohany-cmu-S26/lob-fill-engine",
  "passive fills depend on uncalibrated parameters: rho (fraction of a level drop assumed ahead of you), pro-rata cancel apportionment, queue_ahead estimand.",
  "the fraction of a level-size drop that was ahead of you is unidentifiable without ground-truth cancels/hidden orders.",
  "V3: treat fills as a SENSITIVITY BAND and publish the sweep; never a point estimate."),
 ("NEG-105","COST_TYPE_FAILURE","NadirAliOfficial/snipe-fx-ea",
  "36 real-tick parameter passes on XAUUSD M1 all land at expected payoff ~-0.31/trade (range -0.307462..-0.316822), PF 0.209-0.230, trades 1,049->5,073.",
  "filters change HOW MANY trades you take, never WHAT A TRADE IS WORTH => pure cost, no alpha to tune.",
  "V3: adopt this as a mandatory acceptance test."),
 ("NEG-106","SYNTHETIC_TICK_FAILURE","NadirAliOfficial/snipe-fx-ea + trillex-10s-ea",
  "same build/settings: generated ticks PF 1.97 / +252 vs real ticks PF 0.34 / -5,258; DD 0.13% vs 52.58% (5.8x).",
  "generated-tick backtests systematically overstate XAUUSD tick strategies.",
  "V3: real-tick-only acceptance; publish the generated-vs-real delta."),
 ("NEG-107","CLAIM_INFLATION","diegourda/Statistical-Arb-MM",
  "'reducing adverse selection by an estimated 30%' comes from OFIValidator: a z-score-only, engine-free, direction-only toy that defines AS as |realized loss| on synthetic data.",
  "the headline number is not markout, not passive, and not executed.",
  "V3: verify every headline against the code that produced it; require a mechanism-matched metric."),
 ("NEG-108","TAUTOLOGICAL_ADVERSE_SELECTION","Leotaby/Market-Making-Simulator",
  "AS is injected as a post-fill drift (informed_impact); the README states there is no real LOB, feed, queue or latency.",
  "if you generate the adverse move you have not measured toxicity.",
  "V3: never accept an AS result from a simulator that injects the AS."),
 ("NEG-109","FICTIONAL_FILL_MODEL","Sandyyy123/xauusd-scalper-research",
  "bar-touch fills at exact SL/TP, SL checked before TP, commission 0.0003 relative, slippage 0.0001 - and NO spread cost at all, on ~18-minute gold scalps.",
  "win rate is set by barrier geometry, not edge; the reported 77.3% / 4.43x return-DD is a simulator artifact.",
  "V3: bar-level results must be re-run on ticks before any gold scalp claim."),
 ("NEG-110","SYNTHETIC_DATA_DEPENDENCE","RobertN1D/... + mahmoud20138/OrderFlow-Scalper",
  "A1's own source: 'Most retail brokers serve a synthetic DOM derived from their B-book pool ... DISABLE on retail accounts.' A6 records has_trade_flags because MT5 forex usually lacks aggressor flags.",
  "retail MT5 gold order-flow inputs are inferred or synthetic.",
  "V3: validate DOM non-degeneracy and flag availability before any microstructure feature earns weight."),
 ("NEG-111","DATA_INTEGRITY_FAILURE","gelatotrade/implementation-shortfall-hyperliquid + himagna16/kalshi-microstructure",
  "cross-deployer namespace collision silently overwrote data; a collector printed '0 errors' while persisting nothing; a stale script 'reports a plausible number computed over in-sample and out-of-sample data pooled together'.",
  "provenance failures are silent and produce plausible numbers.",
  "V3: hash-lock the IS/OOS split boundary and the cost schedule; assert the guard in CI."),
 ("NEG-112","OVERLAP_FAILURE","snowkings/QIP_adverse_selection + siddhantsingh-1/execution-aware-alpha-backtester",
  "4,701 clustered trigger events with overlapping windows => no CI implied; overlapping labels require purging; overlapping rebalancing counts the same move H times.",
  "overlap inflates both PnL and turnover and invalidates naive t-stats.",
  "V3: purge, embargo, de-overlap, cluster errors before quoting any statistic."),
 ("NEG-113","NO_ALPHA_FOUND_IN_GROUP_A","Group A (6 XAUUSD/MT5 repos)",
  "No Group-A repo demonstrates net-of-cost, out-of-sample, tick-level edge on XAUUSD.",
  "the only execution-aware honest work concludes the scalping entry is an execution defect; profitability requires NOT scalping.",
  "V3: treat the XAUUSD tick-scalping route as evidence-backed unproductive."),
 ("NEG-114","CALIBRATION_GAP","AshJha0/electronic-trading",
  "author: 'What is not verified: calibration of eta, gamma_p, A, k to any real market'; the AC model also omits the epsilon*X spread/fee term.",
  "engineering rigor does not imply market validity.",
  "V3: require an explicit 'what is NOT verified' block and refuse uncalibrated parameters as forecasts."),
]

OPEN_NEG = [
 "predictive_R2_vs_contemporaneous_R2_separation: 0 GitHub hits (must be produced internally)",
 "parameter_change_does_not_affect_per_trade_loss: 0 GitHub hits as a documented cost-type failure (A2 is the nearest, internally produced analogue)",
 "tail_dominated_PnL_as_a_stated_failure: 0 GitHub hits (C5's stress-regime realised-spread inversion is the closest analogue)",
]


def w(name, text):
    p = os.path.join(H, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", name)


def main():
    # ---- repository card index
    lines = ["# Repository Cards — Index (18 carded)", "",
             "Full 14-item cards live in `../parts/group_{A,B,C}.md`. This index is the machine-checkable summary.", "",
             "| slug | group | EVIDENCE_LEVEL | TRANSFERABILITY | negative type | sharpest warning |",
             "|---|---|---|---|---|---|"]
    for slug, g, e, t, n, warn in REPOS:
        lines.append(f"| `{slug}` | {g} | {e} | {t} | {n} | {warn} |")
    lines += ["", "## Verified but not carded (HTTP 200, kept for completeness)", "",
              "Group C reported 19 slugs verified / 8 carded; the 11 not carded are listed in `../parts/group_C.md` §4",
              "(`Weichong515/Algo-Trading-14`, `KBenBec/quant-microstructure-hft-`, `furlong-cp/QueueEdge`,",
              "`FrionicSaddly/perp-quant-bot`, `ishabh-24/markout`, `ferflorespr/quant-backtest-execution-engine`,",
              "`FETKlOkAn2/crypto-quant-platform`, `xuxingjiankr-cpu/perception-xalpha-lite`, `FatihHekim0glu/algo-system`,",
              "`srgangaram-swe/AlphaForge`).", "",
              "**Searches returning nothing usable (valid negative results):** `latency+discount+backtest` (0),",
              "`backtest+profit+real+tick+failure` (0), `predictive+R2+contemporaneous+R2+trading` (0),",
              "`tail+risk+dominated+PnL+strategy` (0), `expected+net+return+label+trading` (0),",
              "`gross+net+pnl+attribution+trading` (0), `microstructure+forex+execution+cost` (0);",
              "`cost+aware+loss+trading` returned 2 spam hits; `HFT+failed` 1 irrelevant hit.", ""]
    w("repository_cards/index.md", "\n".join(lines))

    # ---- evidence matrix
    rows = [["repo","group","evidence_level","transferability","negative_type","sharpest_warning"]]
    for r in REPOS:
        rows.append(list(r))
    with open(os.path.join(H, "evidence_matrix.csv"), "w", encoding="utf-8", newline="\n") as f:
        csv.writer(f).writerows(rows)
    print("wrote evidence_matrix.csv")

    # ---- mechanism registry + cards
    reg = {"schema": "v3_github_distillation_registry/1", "task": "V3-HFT-GITHUB-MICROSTRUCTURE-DISTILLATION-003",
           "generated_utc": GEN, "mechanisms": [], "counts": {}}
    for mid, name, src, mech, why, trans, data, status in MECH:
        reg["mechanisms"].append({"MECHANISM_ID": mid, "NAME": name, "SOURCE_REPOS": src,
                                  "MECHANISM": mech, "WHY_IT_MATTERS": why,
                                  "TRANSFERABILITY": trans, "FXTM_DATA_STATUS": data,
                                  "STATUS": status})
    reg["counts"] = {"total": len(MECH),
                     "READY": sum(1 for m in MECH if m[7] == "READY"),
                     "PARKED": sum(1 for m in MECH if m[7] == "PARKED")}
    reg["note"] = "no 'best'/'winner' ranking; mechanisms only"
    w("github_distillation_registry.json", json.dumps(reg, indent=1))

    for mid, name, src, mech, why, trans, data, status in MECH:
        card = (f"# {mid} — {name}\n\n"
                f"- SOURCE_REPOS: {src}\n- TRANSFERABILITY: {trans}\n- FXTM_DATA_STATUS: {data}\n"
                f"- STATUS: **{status}**\n\n## Mechanism\n\n{mech}\n\n## Why it matters\n\n{why}\n\n"
                f"## V3 use\n\n"
                f"{'Applicable on the current FXTM L1 feed.' if status == 'READY' else 'PARKED: the required input is DATA_GAP on FXTM (no real L2 queue / no fills), so the mechanism cannot be tested here.'}\n")
        w(f"mechanism_cards/{mid}.md", card)

    # ---- negative evidence registry (V3 internal + repo-sourced)
    neg = {
      "schema": "v3_negative_evidence_registry/1",
      "task": "V3-HFT-GITHUB-MICROSTRUCTURE-DISTILLATION-003",
      "generated_utc": GEN,
      "purpose": "failure mechanisms are the highest-value distillation output; each entry states WHAT failed and WHY",
      "sources": {"internal": 6, "github": len(NEG)},
      "internal": ["V3-NEG-001 COST_ERASED_ALPHA", "V3-NEG-002 TAIL_DEPENDENCE",
                    "V3-NEG-003 MECHANICAL_SIGNAL_ARTIFACT", "V3-NEG-004 LABEL_IMPLEMENTATION_BUG",
                    "V3-NEG-005 SYNTHETIC_DATA_DEPENDENCE", "V3-NEG-006 POWER_LIMITATION"],
      "github": [{"id": i, "type": t, "source": s, "finding": fi, "why": wy, "v3_action": va}
                  for i, t, s, fi, wy, va in NEG],
      "open_negative_results": OPEN_NEG,
    }
    w("negative_evidence_registry.json", json.dumps(neg, indent=1))
    print("mechanisms:", reg["counts"])


if __name__ == "__main__":
    main()
