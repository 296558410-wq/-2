# -*- coding: utf-8 -*-
"""analyze.py — cross-system comparison, PIT/lookahead audit, replay results, restart facts (READ-ONLY).
Emits CROSS_SYSTEM_COMPARISON.csv, PIT_AUDIT.json, REPLAY_RESULTS.jsonl, RESTART_FACTS.json.
Instrument notes (verified before use):
  - evidence_registry 'version' is a GLOBAL fetch sequence (not per-item revision); real revisions are rows
    with previous_content_sha256 != null (31 evidence_ids).
  - V1_NEW ledger DECISION 'replay_match' is always null (never populated) -> cannot cite it as replay evidence.
"""
from __future__ import annotations
import csv, json, os, collections, datetime as dt
from email.utils import parsedate_to_datetime

REPO = r"C:\AIQuant"; BASE = os.path.join(REPO, "research", "hermes")
OUT = os.path.join(BASE, "audit", "hermes_alpha_drift_pit")
def jl(p): return [json.loads(l) for l in open(p, encoding="utf-8", errors="replace") if l.strip()]
def to_epoch(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip()
    if s.replace(".", "", 1).replace("-", "", 1).isdigit(): return float(s)
    try: return parsedate_to_datetime(s).timestamp()
    except Exception: pass
    try: return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception: return None

# ---------- 1. cross-system ----------
v1 = jl(os.path.join(OUT, "V1_HERMES_TRADE_DATABASE.jsonl"))
def stats(rows, cut):
    closed = [r for r in rows if r["closed"]]
    def s(rs):
        n = len(rs)
        return {"n": n, "price": round(sum(r["profit_price"] for r in rs), 2) if n else 0.0,
                "net": round(sum(r["net"] for r in rs), 2) if n else 0.0,
                "wr": round(sum(1 for r in rs if r["outcome"] == "WIN") / n, 3) if n else None}
    return s([r for r in closed if r["exit_ts"][:10] < cut]), s([r for r in closed if r["exit_ts"][:10] >= cut]), s(closed)
old = [r for r in v1 if r["system"] == "V1_OLD"]; new = [r for r in v1 if r["system"] == "V1_NEW"]
o_e, o_l, o_t = stats(old, "2026-09-15"); n_e, n_l, n_t = stats(new, "2026-09-30")
rows = [
 {"system":"V1_OLD","engine_or_layer":"Hermes LLM plan engine (decisions carry model/confidence/answers_14)","magic":90002,"market":"DEMO(MT5)","live_or_paper":"DEMO","window":"2026-09-07..2026-09-28","n_closed":o_t["n"],"early_phase":"09-08..09-14","early_net_price":o_e["price"],"early_net_incl_cost":o_e["net"],"late_phase":"09-15..09-28","late_net_price":o_l["price"],"late_net_incl_cost":o_l["net"],"total_net_price":o_t["price"],"total_net_incl_cost":o_t["net"],"win_rate":o_t["wr"],"early_profit_late_decay":"CONFIRMED(day-level,both bases)","hermes_alpha_executed":"CANDIDATE(LLM plan engine) but PIT-unverifiable early inputs","pit_status":"PARTIAL/DATA_GAP","replay_status":"NOT_POSSIBLE(no input snapshots)"},
 {"system":"V1_NEW","engine_or_layer":"BASELINE_CONTROL control arm (signal_type=BASELINE_CONTROL, not_hermes_alpha=true)","magic":90011,"market":"DEMO(MT5)","live_or_paper":"DEMO","window":"2026-09-28..2026-10-02","n_closed":n_t["n"],"early_phase":"09-28..09-29","early_net_price":n_e["price"],"early_net_incl_cost":n_e["net"],"late_phase":"09-30..10-02","late_net_price":n_l["price"],"late_net_incl_cost":n_l["net"],"total_net_price":n_t["price"],"total_net_incl_cost":n_t["net"],"win_rate":n_t["wr"],"early_profit_late_decay":"PRESENT(small,~2d)","hermes_alpha_executed":"NONE(control arm)","pit_status":"PARTIAL(input hashes+truth PIT_flag)","replay_status":"INPUT_HASH_ONLY(no output replay field)"},
 {"system":"V2_PAPER","engine_or_layer":"reference_rules placeholder (decision_source=reference_rules, signal_from_agents=false)","magic":None,"market":"PAPER(no broker)","live_or_paper":"PAPER","window":"2026-09-11..2026-10-02","n_closed":0,"early_phase":"n/a","early_net_price":None,"early_net_incl_cost":None,"late_phase":"n/a","late_net_price":None,"late_net_incl_cost":None,"total_net_price":0.0,"total_net_incl_cost":0.0,"win_rate":None,"early_profit_late_decay":"NOT_EVALUABLE(zero executed trades)","hermes_alpha_executed":"NONE(reference_rules placeholder; 0 trades)","pit_status":"UNKNOWN(all evidence point_in_time_valid=unknown)","replay_status":"PARTIAL(G3 replay_mismatch=[] but provenance_missing; verdict FAIL)"},
]
with open(os.path.join(OUT,"CROSS_SYSTEM_COMPARISON.csv"),"w",encoding="utf-8",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows: w.writerow(r)

# ---------- 2. PIT audit ----------
er = jl(os.path.join(BASE,"trader_v2","state","evidence_registry.jsonl"))
ver = collections.defaultdict(list)
for r in er:
    ver[r["evidence_id"]].append({"retrieved_at":r.get("retrieved_at"),"published_at":r.get("published_at"),
                                  "sha":r.get("content_sha256"),"prev":r.get("previous_content_sha256")})
for k in ver: ver[k].sort(key=lambda x: str(x.get("retrieved_at")))
revised_ids = {k for k,vs in ver.items() if any(v.get("prev") for v in vs)}
multi_row_ids = {k for k,vs in ver.items() if len(vs) > 1}
opp = jl(os.path.join(BASE,"trader_v2","state","opportunity_ledger.jsonl"))
opr = [r for r in opp if r.get("evidence_ids")]
leak, pub_after, checked, missing, used_older_than_latest = 0,0,0,0,0
ex=[]
for d in opr:
    t = to_epoch(d.get("detected_at"))
    if t is None: continue
    for eid in set(d.get("evidence_ids") or []):
        vs = ver.get(eid)
        if not vs: missing += 1; continue
        checked += 1
        avail = None
        for v in vs:
            rt = to_epoch(v.get("retrieved_at"))
            if rt is not None and rt <= t: avail = v
        if avail is None:
            leak += 1
            if len(ex)<5: ex.append({"eid":eid,"decision":d.get("detected_at"),"first_retrieved":vs[0].get("retrieved_at")})
            continue
        p = to_epoch(avail.get("published_at"))
        if p is not None and p > t: pub_after += 1
        if avail.get("sha") != vs[-1].get("sha"): used_older_than_latest += 1
# V1_NEW truth PIT status
sp = jl(os.path.join(BASE,"trader_v1","v1_upgrade","truth","evidence","decision_snapshots.jsonl"))
pitstat = collections.Counter(s.get("PIT_status") for s in sp)
pit = {"schema":"alpha_drift_pit_audit/1","generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
 "word_table":{"observation_time":"witness","publication_time":"release","availability_time":"retrievable","vintage_time":"revision"},
 "checks":[
  {"field_group":"V2 news evidence (published_at/retrieved_at)","rule":"availability_time <= decision_time",
   "opportunities_checked":len(opr),"evidence_refs_checked":checked,"refs_missing_from_registry":missing,
   "refs_with_no_version_at_decision_time":leak,"refs_published_after_decision":pub_after,
   "refs_using_version_older_than_latest":used_older_than_latest,
   "status":"PASS_NO_LEAK_OBSERVED" if leak==0 and pub_after==0 else "LEAK_SUSPECTED",
   "note":"earliest-retrieved version at/before decision time; conservative"},
  {"field_group":"V2 K-line bars","rule":"no unclosed/future bar","status":"PASS",
   "evidence":"trader_v2/research/PIT_VALIDATION_REPORT.md 未收盘bar=0 (5m/15m/60m/4h/1d), monotonic"},
  {"field_group":"V2 macro releases vintage","rule":"release_timestamp + vintage","status":"FAIL_UNKNOWN",
   "evidence":"878/878 release_timestamp_unknown=true, confidence=low; 38 revision_changed=true"},
  {"field_group":"V2 evidence registry PIT flag","rule":"point_in_time_valid","status":"UNKNOWN",
   "evidence":f"{len(er)}/{len(er)} rows point_in_time_valid=unknown"},
  {"field_group":"V2 evidence content revisions (vintage)","rule":"earlier content reconstructible at decision time",
   "status":"PARTIAL_CONTENT_UNRECONSTRUCTIBLE",
   "evidence":f"{len(revised_ids)} evidence_ids carry previous_content_sha256 (content replaced) but only {len(multi_row_ids)} retain >1 row -> earlier content not stored for the rest; stored content may be a later revision than what a decision saw",
   "note":"availability-time leak NOT observed, but content-vintage for revised items is UNKNOWN"},
  {"field_group":"V1_NEW decision snapshots","rule":"PIT_status recorded per decision",
   "status":"PASS" if pitstat.get("PIT_OK")==len(sp) else "PARTIAL","evidence":f"{len(sp)} snapshots PIT_status={dict(pitstat)}"},
  {"field_group":"V1_OLD decisions","rule":"availability_time <= decision_time","status":"UNKNOWN",
   "evidence":"early-phase full inputs rotated; only state_summary remains (v1_audit class-E DATA_GAP)"}],
 "revision_backfill":{"real_revision_ids":len(revised_ids),
   "note":"multi-version rows = genuine revisions (previous_content_sha256 set); klines no backfill; macro revision unverifiable"},
 "leak_examples":ex}
json.dump(pit,open(os.path.join(OUT,"PIT_AUDIT.json"),"w",encoding="utf-8",newline="\n"),indent=1,ensure_ascii=False)
print("PIT news: checked=",checked,"leak=",leak,"pub_after=",pub_after,"missing=",missing,"older_than_latest=",used_older_than_latest,"revised_ids=",len(revised_ids))
print("V1_NEW truth PIT_status:",dict(pitstat),"n=",len(sp))

# ---------- 3. replay ----------
led = jl(os.path.join(BASE,"trader_v1","v1_upgrade","ledger","v1_upgrade_ledger.jsonl"))
dec_led=[e for e in led if e.get("event")=="DECISION"]
rr=[
 {"system":"V1_OLD","sample":"109 trades","replay_status":"NOT_POSSIBLE","input_hash_saved":False,
  "reason":"no Hermes input snapshots preserved (state rotated); v1_audit class-E DATA_GAP"},
 {"system":"V1_NEW","sample":f"{len(dec_led)} ledger DECISION + {len(sp)} truth snapshots","replay_status":"INPUT_HASH_ONLY",
  "input_hash_saved":True,"output_replay_performed":False,
  "reason":"hermes_input_hash + sha256 stored per truth snapshot; input BODY not stored -> output replay not performed this pass; ledger replay_match=null (field never populated)",
  "prior_audit_note":"2026-09-14 cycle recorded replay MATCH (mechanical control-arm map, not_hermes_alpha)"},
 {"system":"V2_PAPER","sample":"run V2-SHADOW-20260917-021627-f80e (2 cycles)","replay_status":"PARTIAL",
  "input_hash_saved":True,"output_replay_performed":True,
  "reason":"replay_mismatch=[] but provenance_missing=DEC-ctx_4cd398fb0547.json; overall verdict FAIL",
  "evidence":"trader_v2/research/V2_G3_VERDICT.json"},
]
with open(os.path.join(OUT,"REPLAY_RESULTS.jsonl"),"w",encoding="utf-8",newline="\n") as fh:
    for r in rr: fh.write(json.dumps(r,ensure_ascii=False)+"\n")

# ---------- 4. restart facts ----------
RESTART_UTC = "2026-10-01T13:52:15+00:00"; r0 = to_epoch(RESTART_UTC)
before = [s for s in sp if to_epoch(s.get("ts_utc")) and to_epoch(s.get("ts_utc"))<r0]
after  = [s for s in sp if to_epoch(s.get("ts_utc")) and to_epoch(s.get("ts_utc"))>=r0]
def uniq(rs,k): return sorted({tuple(v) if isinstance(v,list) else v for v in (s.get(k) for s in rs) if v is not None})
facts={"schema":"alpha_drift_restart_facts/1",
 "V1_NEW":{"restart_utc":RESTART_UTC,"snapshots_before":len(before),"snapshots_after":len(after),
   "code_version_before":uniq(before,"code_version"),"code_version_after":uniq(after,"code_version"),
   "config_hash_before":uniq(before,"config_hash"),"config_hash_after":uniq(after,"config_hash"),
   "data_source_before":uniq(before,"data_source"),"data_source_after":uniq(after,"data_source"),
   "PIT_status_before":uniq(before,"PIT_status"),"PIT_status_after":uniq(after,"PIT_status")},
 "V1_OLD":{"restarts_documented":["2026-09-09~06:07-06:12Z(Windows update)","2026-09-14"],"input_snapshots":"rotated -> UNKNOWN"},
 "V2_PAPER":{"note":"runs restarted per-cycle; see V2_LONG_RUN_AUDIT (run windows), MT5 source fallback issue"},
}
json.dump(facts,open(os.path.join(OUT,"RESTART_FACTS.json"),"w",encoding="utf-8",newline="\n"),indent=1,ensure_ascii=False)
print("restart facts:",json.dumps(facts["V1_NEW"],ensure_ascii=False))
