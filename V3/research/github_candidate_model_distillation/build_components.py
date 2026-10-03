"""Build the model-component library + registries + matrices for task-004.

DISTILLATION_ONLY / READ_ONLY. Writes only under github_candidate_model_distillation/.
No training, no backtest, no MT5, no orders.
Evidence levels: E0 claim / E1 code / E2 backtest / E3 OOS / E4 execution-aware / E5 real execution.
Rule (§十九): a component or candidate needs E2+ to become a MODEL_SPEC_CANDIDATE; E0/E1 -> PARK.
"""
from __future__ import annotations

import csv
import json
import os

H = os.path.dirname(os.path.abspath(__file__))
GEN = "2026-09-22T05:55:00Z"

# component_id, dir, source_repos, evidence, mechanism, required_data, formula, assumption, failure_mode, fxtm
COMPONENTS = [
 ("CMP-01","01_state","KlishevDA/...L2-Market-Making; siddhantsingh-1/execution-aware-alpha-backtester","E3",
  "Point-in-time market state vector built ONLY from information available at t (as-of join, no future).",
  "bid, ask, mid, spread, spread percentile, rolling volatility, quote arrival, tick-rule proxy",
  "state(t) = [spread_bp, spread_pctile_n, rv_n, quote_rate, flow_proxy_n, displacement_1s, displacement_5s]",
  "all terms computed with as-of (backward) joins; anything needing a future window is FORBIDDEN here",
  "look-ahead via a centred/lagged window computed with a forward shift","COMPATIBLE (L1)"),
 ("CMP-02","02_signal","siddhantsingh-1/execution-aware-alpha-backtester (OFI+microprice); V3 L1 subset","E4",
  "Directional signal that maps the state to an expected signed move. MUST NOT use post-fill quantities.",
  "state vector only (no OFI/microprice on FXTM -> substitute L1 return/reversal terms)",
  "signal(t) = g(state(t)) ; on FXTM g may not use true OFI, microprice, queue or trade flow",
  "the strongest published L1 signals rely on OFI/microprice; on FXTM those are DATA_GAP, so the signal is degraded",
  "reusing a post-fill markout as a feature (leakage); renaming a proxy to the real quantity","PARTIAL (drop OFI/microprice terms)"),
 ("CMP-03","03_gross_edge","snowkings/QIP_adverse_selection; siddhantsingh-1/...","E4",
  "Expected GROSS markout per horizon, measured mid-to-mid, never mixed with cost.",
  "mid series + decision instants",
  "gross_edge(t,h) = E[ d * (mid(t+h) - mid(t)) ] ; signed midpoint movement, three-way (favourable/unchanged/adverse)",
  "mid-based labels avoid bid-ask bounce inflation; forward windows must be segment-guarded",
  "mid label used as if it were an executable price (ignores the spread you must cross)","COMPATIBLE (L1)"),
 ("CMP-04","04_cost","gelatotrade/implementation-shortfall-hyperliquid; AshJha0/electronic-trading","E3",
  "Explicit additive cost decomposition with declared signs; includes the opportunity term on the UNFILLED fraction.",
  "spread, commission, (impact), delivered fraction",
  "IS_total = Spread + Impact + Fee + Opportunity ; Opportunity = max(0, adverse post-window drift) * UNFILLED fraction",
  "each term separately visible; positive = cost; a term that is unknown is DATA_GAP, never 0",
  "silently booking unfilled size at the arrival price (opportunity cost = 0); netting costs invisibly","COMPATIBLE (0.914 bp measured)"),
 ("CMP-05","05_adverse_selection","Leotaby/Market-Making-Simulator (convention); snowkings/QIP_adverse_selection (measurement)","E4",
  "Post-fill adverse drift measured as a three-way classification; diagnostic only, never an entry feature.",
  "entry execution price + future mid",
  "AS_h = entry_exec_price - mid(t+h) for LONG ; mid(t+h) - entry_exec_price for SHORT ; AS>0 = adverse",
  "measured, never injected; at FXTM only L1 markout is available (queue-based AS is DATA_GAP)",
  "circularity (injecting the adverse move then measuring it); using realised AS inside the entry decision","PARTIAL (L1 diagnostic only)"),
 ("CMP-06","06_execution","tfrmma/realistic-mm-backtester; AshJha0/electronic-trading (latency accounting)","E3",
  "Execution model: taker crosses the spread at t+latency; exit cost is a SECOND spread crossing.",
  "bid, ask, measured latency (FXTM RTT ~279 ms)",
  "fill_price = ask(t+L) for market BUY ; bid(t+L) for market SELL ; exit adds one more spread + commission",
  "fill is ASSUMED for market orders (no fill model); passive fill is DATA_GAP on FXTM",
  "assuming mid fills; counting the spread once instead of twice","PARTIAL (taker only; passive PARKED)"),
 ("CMP-07","07_entry_gate","siddhantsingh-1 (cost hurdle, E4); n30dyn4m1c/gold-pro-scalper (cost-multiple gate, E1 corroboration)","E4",
  "Compare expected edge against the full cost BEFORE trading; abstain when the inequality fails.",
  "expected gross edge, full cost, uncertainty band",
  "TAKE iff E[net_edge] - uncertainty_margin > 0 ; cost-multiple variant: edge_fuel >= k1 * RT_cost and target >= k2 * RT_cost",
  "the gate is a comparison, not a fitted classifier; k1/k2 are NOT set here",
  "lowering the gate to increase fill rate (destroys the economics)","COMPATIBLE"),
 ("CMP-08","08_exit","AshJha0/electronic-trading (IS/opportunity); snowkings (remaining-hold accounting); KlishevDA (markout curves)","E4",
  "Exit when the expected REMAINING edge falls below the expected exit cost; four failure classes kept separate.",
  "current state, position, elapsed time, cost of a second crossing",
  "EXIT iff E[remaining_edge(t)] < E[exit_cost] ; E[t] functional form = TBD (see EDGE_DECAY_MODEL)",
  "exit cost must count the second spread crossing + commission; remaining_hold = horizon - elapsed (nonpositive -> unavailable)",
  "fixed TP/SL that ignores decay; exiting on realised PnL instead of expected remaining edge","COMPATIBLE (L1)"),
 ("CMP-09","09_uncertainty","snowkings (no CI on clustered events); himagna16 (cluster-robust); Trumplus (per-day AUC, eligibility)","E4",
  "Every edge estimate carries edge/execution/data uncertainty; overlapping events must not be treated as independent.",
  "bootstrap machinery, cluster labels, effective_N",
  "report edge_uncertainty (CI), execution_uncertainty (fill/cost band), data_uncertainty (DATA_GAP list); effective_N = n / max(1,rho)",
  "no CI is implied from the raw event count when events cluster; unobservable outcomes are excluded, never 0",
  "quoting a t-stat from overlapping events; reporting a mean without the median/tail","COMPATIBLE"),
 ("CMP-10","10_position","Leotaby/Market-Making-Simulator; diegourda/Statistical-Arb-MM (A-S skew)","E2",
  "Inventory-aware sizing/reservation price. Included for completeness; NOT usable without a fill model.",
  "current position, risk budget, (fill probability)",
  "reservation price r = s - q*gamma*sigma^2*tau ; optimal spread delta = gamma*sigma^2*tau + (2/gamma)*ln(1+gamma/k)",
  "the A-S form assumes continuous quoting and a calibrated intensity k; FXTM has neither",
  "importing A-S quoting without an intensity calibration; treating inventory skew as edge","PARKED (needs fills/intensity)"),
]

REPOS = [
 ("siddhantsingh-1/execution-aware-alpha-backtester","E4","B","COST_ERASED_ALPHA",
  "gross +$1.48M, cost $13.11M, net -$11.64M; reversion-ablation IC 0.473->0.177"),
 ("snowkings/QIP_adverse_selection","E4","B","EXECUTION_FAILURE",
  "+0.29 tick move vs 1.08 tick spread; clustered events, no CI implied"),
 ("himagna16/kalshi-microstructure","E4","B","COST_ERASED_ALPHA",
  "inefficient at the mid, efficient at the touch; 10.7c break-even"),
 ("gelatotrade/implementation-shortfall-hyperliquid","E3","B","DATA_INTEGRITY_FAILURE",
  "Perold 4-term IS incl. Opportunity on the unfilled fraction"),
 ("aryansiwach/execution-market-microstructure","E3","B","REGIME_DEPENDENT_COST",
  "realised spread turns negative under stress; IS never zero for large orders"),
 ("tfrmma/realistic-mm-backtester","E3","B","UNFALSIFIED_EDGE",
  "FIFO qty_in_front + cancel model + latency + fees + OOS framework, no published OOS result"),
 ("KlishevDA/...L2-Market-Making","E3","B","QUEUE_ASSUMPTION_FAILURE",
  "markout curves + rho luck parameter; single 600s session; no fees"),
 ("xiaohany-cmu-S26/lob-fill-engine","E3","B","MODEL_DEPENDENT_LABEL",
  "rigorous fill-probability protocol; no economic closure"),
 ("Trumplus/AAPL-Limit-Order-Fill-Probability-Forecast","E3","C","MODEL_DEPENDENT_LABEL",
  "AUC~0.72 ceiling; queue position dominates; eligibility censoring"),
 ("AshJha0/electronic-trading","E4_ENGINEERING_E1_MARKET","B","CALIBRATION_GAP",
  "IS decomposition + price-shift invariance; calibration explicitly NOT verified"),
 ("NadirAliOfficial/snipe-fx-ea","E4","B","COST_TYPE_FAILURE",
  "flat ~-0.31/trade across 36 real-tick passes (PF<=0.23)"),
 ("n30dyn4m1c/gold-pro-scalper","E1","B","NO_PUBLISHED_EVIDENCE",
  "cost-multiple gate (corroboration only; E1 so PARK as a primary basis)"),
]


def w(name, text):
    p = os.path.join(H, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", name)


def main():
    reg = {"schema": "v3_model_component_registry/1",
           "task": "V3-HFT-GITHUB-CANDIDATE-MODEL-DISTILLATION-004", "generated_utc": GEN,
           "rule": "E2+ required to be a MODEL_SPEC_CANDIDATE component; E0/E1 -> PARK",
           "components": []}
    for cid, d, src, ev, mech, data, formula, assum, fail, fxtm in COMPONENTS:
        rec = {"component_id": cid, "source_repo": src, "source_commit": "HEAD_AT_AUDIT_2026-09-22",
               "evidence_level": ev, "mechanism": mech, "required_data": data, "formula": formula,
               "assumption": assum, "failure_mode": fail, "FXTM_compatibility": fxtm,
               "parameters": "TBD_IN_PRE_REGISTERED_EXPERIMENT"}
        reg["components"].append(rec)
        md = [f"# {cid} — {d.split('_',1)[1]}", "",
              f"- source_repo: {src}", f"- source_commit: HEAD_AT_AUDIT_2026-09-22",
              f"- evidence_level: **{ev}**", f"- FXTM_compatibility: {fxtm}",
              f"- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT", "",
              "## mechanism", "", mech, "", "## required_data", "", data, "",
              "## formula", "", "```", formula, "```", "", "## assumption", "", assum, "",
              "## failure_mode", "", fail, "",
              "## FXTM note", "",
              ("Usable on the current FXTM L1 feed." if fxtm.startswith("COMPATIBLE") else
               ("Usable only in degraded form; the published inputs include DATA_GAP quantities on FXTM."
                if fxtm.startswith("PARTIAL") else
                "PARKED: the required input (real queue / fill probability / intensity) is DATA_GAP on FXTM.")),
              ""]
        w(f"model_components/{d}/{cid}.md", "\n".join(md))
    w("model_component_registry.json", json.dumps(reg, indent=1))

    cand = {
      "schema": "v3_candidate_model_registry/1",
      "task": "V3-HFT-GITHUB-CANDIDATE-MODEL-DISTILLATION-004",
      "generated_utc": GEN,
      "status_note": "CANDIDATE_MODEL = UNTESTED. READY_FOR_PRE_REGISTRATION is a documentation state, not a result.",
      "candidates": [
        {"CANDIDATE_ID": "V3-HFT-CAND-001", "NAME": "Execution-Aware L1 Markout Gate",
         "ROLE": "PRIMARY_CANDIDATE",
         "ROLE_JUSTIFICATION": "general form: hosts the state/edge/cost/gate/exit components behind one interface",
         "components": ["CMP-01","CMP-02","CMP-03","CMP-04","CMP-05","CMP-06","CMP-07","CMP-08","CMP-09"],
         "anchor_evidence": "E4 (snowkings, siddhantsingh)", "FXTM_DATA": "L1 only",
         "DECISION": ["TAKE","WAIT","EXIT"], "STATUS": "UNTESTED",
         "PRE_REGISTRATION_READINESS": "READY_FOR_PRE_REGISTRATION"},
        {"CANDIDATE_ID": "V3-HFT-CAND-002", "NAME": "Spread-State Execution",
         "ROLE": "SECONDARY_CANDIDATE",
         "ROLE_JUSTIFICATION": "the policy/filter view of the same machinery; answers 'can any action be economic now?'",
         "components": ["CMP-01","CMP-04","CMP-06","CMP-07","CMP-09"],
         "anchor_evidence": "E3-E4 (himagna16, aryansiwach, siddhantsingh)", "FXTM_DATA": "L1 only",
         "DECISION": ["TRADEABLE","NOT_TRADEABLE","UNKNOWN"], "STATUS": "UNTESTED",
         "PRE_REGISTRATION_READINESS": "READY_FOR_PRE_REGISTRATION"},
        {"CANDIDATE_ID": "V3-HFT-CAND-003", "NAME": "Adverse-Selection Conditional Exit",
         "ROLE": "EXPLORATORY_CANDIDATE",
         "ROLE_JUSTIFICATION": "depends on the least-established piece (the functional form of edge decay)",
         "components": ["CMP-01","CMP-03","CMP-05","CMP-06","CMP-08","CMP-09"],
         "anchor_evidence": "E3-E4 (AshJha0, snowkings, KlishevDA)", "FXTM_DATA": "L1 only",
         "DECISION": ["HOLD","EXIT"], "STATUS": "UNTESTED",
         "PRE_REGISTRATION_READINESS": "READY_FOR_PRE_REGISTRATION"},
        {"CANDIDATE_ID": "V3-HFT-CAND-004", "NAME": "Passive / Queue Market Making",
         "ROLE": "PARKED", "components": ["CMP-10","CMP-06"],
         "blocking": "fill probability / queue position / real depth = DATA_GAP on FXTM",
         "STATUS": "PARKED"},
        {"CANDIDATE_ID": "V3-HFT-CAND-005", "NAME": "Cross-Venue Context",
         "ROLE": "PARKED", "components": ["CMP-01"],
         "blocking": "another venue's data is not FXTM's execution pool",
         "STATUS": "PARKED"},
      ],
      "interface": {"ModelState": "CMP-01 -> GrossEdge: CMP-03 -> ExecutionCost: CMP-04/06 -> "
                                 "AdverseSelectionRisk: CMP-05 -> NetEdge -> Decision(TAKE|WAIT|EXIT)"},
      "forbidden_language": ["best", "winner", "most profitable"],
    }
    w("candidate_model_registry.json", json.dumps(cand, indent=1))

    # evidence matrix + failure matrix
    with open(os.path.join(H, "evidence_matrix.csv"), "w", encoding="utf-8", newline="\n") as f:
        csv.writer(f).writerows([["repo","evidence_level","transferability","negative_type","key_finding"]] + [list(r) for r in REPOS])
    print("wrote evidence_matrix.csv")
    fails = [
      ["failure_id","class","where_it_appears","description","mitigation_in_spec"],
      ["F-01","COST_ERASED_ALPHA","siddhantsingh, himagna16, V3 internal","edge smaller than round-trip cost","CMP-07 gate: compare edge to full cost before trading"],
      ["F-02","EXECUTION_FAILURE","snowkings, V3 internal","real directional info, negative at every delay/horizon","CMP-06 counts the spread twice; CAND-003 exit rule"],
      ["F-03","LOOK_AHEAD","general risk","future outcome leaking into the decision","timelines/ mark every field AVAILABLE / LABEL_ONLY / DIAGNOSTIC_ONLY"],
      ["F-04","POST_FILL_LEAKAGE","AS-based ideas","realised markout used as an entry feature","CMP-05 is DIAGNOSTIC_ONLY; AS may enter only as a lagged PIT estimate"],
      ["F-05","SELECTION_BIAS","any multi-variant search","choosing on VAL/TEST or re-selecting after stress","OOS discipline: VAL-only selection, single TEST evaluation, FDR"],
      ["F-06","OVERLAP_INFLATION","snowkings, siddhantsingh","clustered events treated as independent","CMP-09 effective_N + cluster-robust/bootstrap; no CI from raw counts"],
      ["F-07","TAIL_DEPENDENCE","V3 internal","mean driven by a few extreme outcomes","report mean AND median AND top1/5/10% shares"],
      ["F-08","OPPORTUNITY_COST_OMITTED","gelatotrade, AshJha0","unfilled size booked at arrival price","CMP-04 Opportunity term on the UNFILLED fraction"],
      ["F-09","QUEUE_ASSUMPTION","tfrmma, KlishevDA, xiaohany","uncalibrated fill/luck parameters","CAND-004 PARKED; sensitivity parameter must be published (CMP-09)"],
      ["F-10","DATA_INTEGRITY","himagna16, gelatotrade","silent provenance failure producing plausible numbers","hash-locked split boundary + cost schedule asserted in CI"],
    ]
    with open(os.path.join(H, "failure_matrix.csv"), "w", encoding="utf-8", newline="\n") as f:
        csv.writer(f).writerows(fails)
    print("wrote failure_matrix.csv")

    # search registry (this task)
    sr = {"schema": "v3_candidate_search_registry/1", "task": "V3-HFT-GITHUB-CANDIDATE-MODEL-DISTILLATION-004",
          "generated_utc": GEN, "method": "GitHub public API only; repo reported only if /repos/<slug> returned 200",
          "queries_dispatched": ["alpha+decay", "markout+decay", "signal+decay+half+life", "hazard+model+trading",
                                  "survival+analysis+order", "dynamic+exit+trading", "execution+markout+curve",
                                  "adverse+selection+exit", "profit+protection+limit+exit", "toxic+flow+exit",
                                  "touch+exit+spread+aware", "spread+regime", "spread+spike",
                                  "dynamic+execution+threshold", "cost+to+move", "spread+to+volatility",
                                  "implementation+shortfall+opportunity", "opportunity+cost+execution",
                                  "non+execution+risk", "maker+exit", "limit+exit+backtest", "passive+execution+simulator"],
          "delegation": {"search_A": "edge decay / dynamic exit (parts/search_edge_decay.md)",
                          "search_B": "spread state vs cost / opportunity cost / maker exit (parts/search_spread_state.md)"},
          "carried_forward_from_003": ["siddhantsingh-1/execution-aware-alpha-backtester", "snowkings/QIP_adverse_selection",
                                        "himagna16/kalshi-microstructure", "gelatotrade/implementation-shortfall-hyperliquid",
                                        "aryansiwach/execution-market-microstructure", "tfrmma/realistic-mm-backtester",
                                        "KlishevDA/...L2-Market-Making", "xiaohany-cmu-S26/lob-fill-engine",
                                        "Trumplus/AAPL-Limit-Order-Fill-Probability-Forecast", "AshJha0/electronic-trading",
                                        "NadirAliOfficial/snipe-fx-ea", "n30dyn4m1c/gold-pro-scalper"],
          "results": []}
    w("github_search_registry.json", json.dumps(sr, indent=1))

    # repository card index (carried forward)
    lines = ["# Repository Cards (carried forward from task-003, re-used as component sources)", "",
             "Full 14-item cards: `../../github_microstructure_distillation/parts/group_{A,B,C}.md`.", "",
             "| repo | EVIDENCE | TRANSFERABILITY | negative type | key finding |", "|---|---|---|---|---|"]
    for slug, ev, tr, nt, kf in REPOS:
        lines.append(f"| `{slug}` | {ev} | {tr} | {nt} | {kf} |")
    lines += ["", "**New this task:** see `parts/search_edge_decay.md` and `parts/search_spread_state.md`.", ""]
    w("repository_cards/index.md", "\n".join(lines))
    print("components:", len(COMPONENTS))


if __name__ == "__main__":
    main()
