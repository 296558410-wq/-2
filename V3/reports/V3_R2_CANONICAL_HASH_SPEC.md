# V3 R2 Canonical Hash Specification

`HASH_SPEC_VERSION = 1`  ·  `generated 2026-09-25T13:23:59.732787+00:00`

## Purpose

Define OUTPUT_HASH as the hash of the **research result content**, not of a run record. The previous
definition hashed a payload containing the wall-clock `ts_utc`, so identical results produced different
hashes across runs. That made the canonical hash structurally unreproducible.

## Algorithm

```text
CANONICAL_HASH_ALGORITHM = SHA256
OUTPUT_HASH = SHA256(canonical_output_payload_bytes)
```

## Serialization

```text
encoding      = UTF-8
format        = JSON, sorted keys, compact separators (",",":")
NaN/Infinity  = FORBIDDEN (allow_nan=False; any non-finite float raises)
list ordering = every list is explicitly ordered (records by opportunity_id; selection by priority then id)
pretty-print  = none (bytes are canonical)
```

## Included fields

```text
HASH_SPEC_VERSION · DATA_IDENTITY(FREEZE_HASH, INPUT_HASH, SYSTEM, PIPELINE_VERSION)
DISCOVERY(all opportunity ids/family/grid/timestamp/episode id/parent id/sub-episode/join reason/trigger/
          data_quality + TOTAL_OPPORTUNITIES + INDEPENDENT_EVENTS + CLUSTERS + GROUPING_UNIT_TESTS)
DETECTORS(F1–F6 counts, episodes, status, frequency class) · FREQUENCY · DURATION · OVERLAP(all pairs,
N_A, N_B, overlap_n, union_n, Jaccard, merge candidates, threshold) · HERMES(priority hash, weights,
selected ids, count, budget, ordering) · NEGATIVE_CONTROL(rounds, seed, null definition, observed, null
mean, decision, pass rule) · ABLATION · CONCENTRATION · SAFETY
```

## Excluded fields (RUN_METADATA, never hashed)

```text
ts_utc · run_timestamp · wall_clock_timestamp · runtime_seconds · machine_metadata · OUTPUT_HASH · SUPERSEDED_OUTPUT_HASHES · SUPERSEDED_BY_FINAL_CLOSEOUT · ledger_chain · CANONICAL_HASH_ALGORITHM · CANONICAL_SERIALIZATION
```

## Dynamic metadata policy

Any field that changes with execution time, machine, ordering or writer behaviour is RUN_METADATA and is
kept outside the payload. Each dynamic field was audited individually; the excluded list above is explicit

rather than a blanket drop.

## Hash computation

```text
payload  = canonical_output_payload.json
bytes    = canonical serialization of the payload
hash     = SHA256(bytes) = 20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624
```

## Verification procedure

```text
1. read the payload twice            -> H1, H2       (must be equal)
2. re-serialize the same content      -> H3            (must equal H1 even when ts_utc differs)
3. compare with run_summary.OUTPUT_HASH and canonical_hash_spec.json
```

## Verification results

```text
H1 = 20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624
H2 = 20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624
H3 = 20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624
H1 == H2            : True
H1 == H2 == H3      : True
payload_bytes       : 12166317
```

## Superseded hashes (kept as audit evidence, not deleted)

```text
c45ed28a9e6da1755f7e8b346dd409f9cdff48663701b1be5c2b1895911eb737
  reason = SUPERSEDED_HASH_DEFINITION_V1_TIMESTAMP_CONTAMINATION
a6490bcfc1532fe59765ffc3534e1d30ef2c1c9225c254dc9cf26098b89a02f7
  reason = SUPERSEDED_HASH_DEFINITION_V1_TIMESTAMP_CONTAMINATION
```

## Change control

`HASH_SPEC_VERSION` is inside the payload, so any future change to the hash rules changes the hash and
cannot be made silently.

## FREEZE_HASH serialization (ruling A)

```text
FREEZE_HASH = 7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f
recorded_rule = UTF8_JSON_SORTED_KEYS_DEFAULT_SEPARATORS (v1 freeze step)
recomputed_with_recorded_rule = 7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f
content_equality = True
if_recomputed_with_compact_separators = 9a7976393e4c8a0bbe90eddcbb028755a692e34183f9d33878e8802b848740e6  (differs -> gate must NOT use this)
```

The frozen registry content is unchanged. The gate verifies content equality under the rule that produced the hash; it does not re-serialize with a different rule. OUTPUT_HASH uses the canonical compact serialization; FREEZE_HASH keeps its v1 rule. Both rules are recorded.
