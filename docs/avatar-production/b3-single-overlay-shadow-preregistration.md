# B3-L5 Part A — H2 single-overlay shadow: PRE-REGISTRATION

Frozen before any H2 replay. Rules, bounds and acceptance criteria below were
fixed from evidence *semantics* and production *availability* only, never by
looking at per-condition B3-L4 outcomes.

## 1. Problem (from B3-L4, merged as d58a3c5c)

Florence detects injected single overlay text at or near ceiling on both real
domains, but the live policy allows it: 37 of 39 source-domain and 99 of 100
avatar-domain single-overlay losses are POLICY misses, not model misses. A
single non-repeated overlay word can only escalate through
`confidenceBand=high` (never produced: the adapter emits no per-region score)
or `textQuality=implausible` (erased for single-glyph fragments).

H1 is not reused and not modified: it removed review from fragmented
non-overlay text and lost the ctl-10 generative artifact.

## 2. Evidence inventory

Availability measured on 299 persisted production candidates (12 carry the
current typed schema, 12 regions total) and on the B3-L4 local corpus.

| Signal | Semantic | Local | Production | Reachability | Missingness | Privacy | Current consumers |
|---|---|---|---|---|---|---|---|
| `overlayLike` | corner & area ≤ 0.08, or edge & area ≤ 0.03 | always | always | reachable | never absent | geometry only | live `strong_overlay`, H1 |
| `location` | corner / edge / central / clothing_zone | always | edge 7, corner 3, clothing 2 | reachable | never absent | geometry only | H1 class, evidence doc |
| `areaBand` | small ≤0.03 / medium ≤0.08 / large | always | small 7, medium 3, large 2 | reachable | never absent | geometry only | evidence doc |
| `repeated` | same normalized token ≥2 regions | always | **0 / 12** | reachable but rare; needs identical OCR reads per tile | never absent | token-derived, no text | live hard reject |
| `textQuality` | plausible / implausible (multi-token with a ≤2-char token) | always | plausible 9, implausible 3 | reachable | never absent | derived once from raw OCR, text discarded | live review branch, H1 |
| `confidenceBand` | high / medium / low / unknown | **unknown 100%** | **unknown 12/12** | **UNREACHABLE** — adapter emits no per-region score | always `unknown` | none | live hard-reject branch (dead) |
| `sourceConsistent` | same token also in the source analysis | see §3 | **False 12/12** (`sourceConsistency=inconsistent`) | reachable, but near-constant in this sample | `None` when source analysis absent | token-derived | live benign-allow path |
| `artifactHint` | token literally contains watermark/overlay | always | **0 / 12** | reachable only if the mark spells "watermark" | never absent | token-derived | live `strong_overlay` |
| `ocrDetectionCount` | region count | always | always | reachable | never absent | count only | evidence doc |
| OD evidence | `<OD>` regions (logo/sign/person) | always | via `visualRegionCounts` | reachable, but OD never localized an injected mark in B3-L4 | n/a | labels only | visual risk actions |
| `shadowOcrEvidence` | beam sequence log-prob, uncalibrated | present | **0 / 299 documents** | not in persisted production docs | absent | scores only | nothing |

Consequence: the only *discriminative* signals available for a single
non-repeated overlay are geometry (`overlayLike`, `location`, `areaBand`) and
`sourceConsistent`. `confidenceBand` is dead, `repeated`/`artifactHint` are
near-constant False, and `textQuality` is unreliable for single-glyph fragments.

## 3. Source consistency in the local corpus (pre-registered analogue)

Production compares a candidate against its participant's source photo
(`compareSourceVisualRisk=True`). The avatar→source pairing cannot be restored
without reading files outside the authorized sets, so for real-domain local
conditions the source regions are **the same base image's own clean (V0/A0)
Florence regions**. This is a PRE-INJECTION BASELINE analogue: it answers "did
this text exist before the overlay was injected", which is the same question the
production comparison asks, evaluated within one image. It is not the
production source-photo comparison and is labelled as such everywhere.

Pure synthetic controls have no source image; they are scored with no source
regions (`sourceConsistent=None`), exactly as today.

## 4. H2 candidates (frozen)

All three are ESCALATE-ONLY: the H2 action is `max(current action, proposed
action)` on the severity order allow < review < reject. No current review or
reject can be downgraded. Every existing branch (including the repeated-overlay
hard reject) is evaluated unchanged first.

* **H2-A** — `overlayLike AND sourceConsistent != true` → review.
* **H2-B** — H2-A **AND** `areaBand == "small"` → review. Bound reuses the
  existing `TINY_REGION_AREA` band; no new constant is introduced.
* **H2-C** — `overlayLike AND sourceConsistent != true AND (location in
  {corner, edge} OR artifactHint)` → review.

Explicitly rejected as over-broad (would re-inflate scene-native text flags):
`corner text → review`, `edge text → review`, `any overlayLike → review`.

## 5. Metrics (per domain, reported separately)

Overlay risk-positive flag rate; per-construct miss counts (corner, small edge,
transparent, center overlay, tiled); benign garment-text flag; background
signage / brand-text / generative-artifact control flags; current→H2
transitions; CLEAN_REAL_AVATAR_REVIEW_DELTA on the 20 raw avatars; production
metadata replay at candidate and job level including the zero / one / two-plus
preview distribution.

## 6. Safety invariants (must hold)

1. Known overlay miss increase = 0.
2. Generative artifact miss increase = 0.
3. Hard-reject bypass = 0.

Escalate-only makes these structurally true; they are still measured, and a
measured violation fails the candidate.

## 7. Acceptance criteria (frozen, evaluated after replay)

* `H2_SHADOW_PROMISING` — all three invariants hold **and** single-overlay
  policy misses drop by ≥50% on both real domains **and**
  CLEAN_REAL_AVATAR_REVIEW_DELTA ≤ 5 of 20 **and** production job-level
  zero-preview jobs increase = 0.
* `H2_SHADOW_TOO_AGGRESSIVE` — invariants hold but a review-flood bound above is exceeded.
* `H2_SHADOW_UNSAFE` — any invariant violated.
* `H2_EVIDENCE_INSUFFICIENT` — a required signal is unavailable or non-discriminative in production.

`H2_LIVE_POLICY_READY` is not a permitted outcome of this task.
