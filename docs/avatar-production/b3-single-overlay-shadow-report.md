# B3-L5 Part A — H2 single-overlay shadow: results

Shadow only. Live policy unchanged (`watermarkQaAction`, `previewAllowed`,
`rejectReasons`, `reviewReasons` untouched). Rules, bounds and acceptance
criteria were frozen in
[b3-single-overlay-shadow-preregistration.md](b3-single-overlay-shadow-preregistration.md)
before this replay. No new inference: this replays the stored B3-L4 Florence
outputs and persisted production metadata.

**Verdict: `H2_SHADOW_TOO_AGGRESSIVE`.** All three safety invariants hold and
single-overlay policy misses drop ~61%, but the review-flood bounds fail: 15 of
20 clean real avatars would go to review (bound: 5), and 2 of 5 G004 groups
would lose every watermark-allowed candidate.

## 1. The three candidates collapse to one

H2-A, H2-B and H2-C produced identical actions on all 434 local conditions and
all 12 production candidates.

* **H2-C is structurally equivalent to H2-A.** `overlayLike` is defined as
  *corner and area ≤ 0.08* or *edge and area ≤ 0.03*, so `location ∈ {corner,
  edge}` is already implied; the `artifactHint` clause never fires
  (`artifactHint` is False on all 12 production regions and every local region).
* **H2-B** differs from H2-A only for a corner region with area in (0.03, 0.08].
  No such region occurred in either real domain.

So the pre-registered family has one effective member. Reported below as H2-A,
with H2-B/H2-C equal everywhere.

## 2. Source consistency

Local real-domain core conditions use the PRE-INJECTION BASELINE analogue (the
same base image's own clean Florence regions). Resulting distribution:

| Domain | consistent | inconsistent | mixed | unknown | not_applicable |
|---|---|---|---|---|---|
| Source core (72) | 2 | 57 | 9 | 3 | 1 |
| Avatar core (180) | 8 | 171 | 1 | – | – |

Production (12 typed candidates, real source-photo comparison):
`sourceConsistency = inconsistent` in 12 of 12, `sourceConsistent = False` on
all 12 regions. The corroborator exists and is reachable, but in this sample it
is near-constant, so it removes almost nothing.

## 3. Efficacy — single non-repeated overlay

Policy miss = Florence found the injected region and the policy allowed it.

| Domain | Model misses | Policy miss (current) | Policy miss (H2-A) | Reduction |
|---|---|---|---|---|
| Source | 2 | 37 | 14 | **62.2%** |
| Avatar | 1 | 99 | 39 | **60.6%** |

What H2-A still allows: the **center** constructs only — transparent centered
watermark (V3/A3: 8 and 20) and centered overlay text (V5/A5: 8 and 20). Those
are not `overlayLike` (central geometry), so a centered stamp stays invisible to
the policy. Corner and edge overlays (V1, V2, V6) are escalated in full.

Flag rate on injected single-overlay conditions rises from 1/40 to 24/40
(source) and 0/100 to 60/100 (avatar).

## 4. Safety invariants — all hold

| Invariant | Source | Avatar |
|---|---|---|
| Known overlay miss increase | 0 | 0 |
| Generative artifact miss increase | 0 | 0 |
| Hard-reject bypass | 0 | 0 |

Escalate-only makes these structurally true (H2 action = max(live, proposed));
they were measured rather than assumed. The tiled hard reject is untouched
(reject 8/8 and 20/20), and ctl-10 stays `review` under all three rules — the
regression that sank H1 does not occur here.

## 5. Cost — review flood

| Measure | Current | H2-A | Pre-registered bound |
|---|---|---|---|
| Clean real avatars in review (of 20) | 3 | **15** | ≤ 5 |
| Clean source photos in review (of 8) | 0 | 5 | – |
| G004 groups with ≥1 watermark-allowed candidate (of 5) | 5 | **3** | – |
| G004 groups with zero allowed | 0 | **2** | – |
| Benign injected garment text flagged | 8/8, 19/20 | 8/8, 19/20 | unchanged |
| Synthetic benign controls flagged (of 4) | 0 | 1 (ctl-06 signage) | – |

Transitions are `allow→review` only: 34 of 80 source conditions and 81 of 200
avatar conditions.

The clean-image numbers come from unlabeled images, so they are a
CLEAN_REAL_AVATAR_REVIEW_DELTA, not a false-positive rate. Two caveats, in both
directions:

* Clean local conditions are scored with no source regions
  (`sourceConsistent=None`), because the avatar→source pairing is unavailable.
  In production the comparison would run — but it returned `inconsistent` in 12
  of 12 production regions, so it is unlikely to rescue many.
* The driver is B3-L4's finding that Florence returns at least one OCR region on
  every image, and 75% of clean avatars carry a corner/edge (overlay-shaped)
  region. H2 escalates exactly those.

## 6. Production typed-metadata replay (read-only)

299 candidates / 62 jobs; 12 carry the current typed schema.

| | Current | H2-A |
|---|---|---|
| Candidate transitions | – | `allow→review` 2, same 10 |
| Hard-reject bypass | – | 0 |
| Jobs changed (strict) | – | 0 |
| Jobs changed (soft review) | – | 1 |
| Jobs losing their last preview | – | 0 |
| Job preview distribution, strict | zero 4, one 1 | zero 4, one 1 |
| Job preview distribution, soft | one 3, two_plus 2 | one 4, two_plus 1 |

No job loses its last preview in this sample, but 12 typed candidates is far too
small to bound the production review rate. The local clean-avatar delta is the
stronger signal, and it is the one that fails.

## 7. Verdict and what would change it

`H2_SHADOW_TOO_AGGRESSIVE` — safe but not shippable as written.
`H2_LIVE_POLICY_READY` is not claimed and is not available at this stage.

The blocker is not the rule's shape; it is that `overlayLike` geometry alone
cannot separate an injected corner stamp from whatever Florence reads in the
corner of a clean avatar. Making it usable needs a corroborator that is
discriminative, and today's evidence has none:

* `confidenceBand` is dead (`unknown` 100%) — a per-region OCR score would make
  the existing high-confidence branch reachable and give H2 a real second
  condition.
* `repeated` needs identical per-tile tokens; `artifactHint` needs the mark to
  literally spell "watermark".
* `sourceConsistent` is `inconsistent` in 12/12 production regions.

A useful next hypothesis needs new evidence (per-region OCR confidence, or a
detector that localizes marks), not another geometry threshold. Center overlays
(V3/V5) remain unaddressed by any current-evidence rule.
