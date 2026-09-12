# B3-L6 — PRE-REGISTRATION (human labels, OWLv2 calibration, H3)

Frozen before any threshold sweep, prompt ablation or H3 replay was inspected.
Nothing below was chosen by looking at per-condition outcomes.

## 1. Human ground truth

**Primary corpus:** the 20 owner-authorized G004 generated avatars (the
production-like domain). The 8 source photos are a secondary exploratory corpus
and are **not** part of any detector acceptance gate.

**Taxonomy:** reused unchanged from the PR #114 approved label schema
(`avatar_watermark_label_schema_v2`). No new ad-hoc classes:
`NO_VISIBLE_RELEVANT_TEXT_OR_MARK`, `GARMENT_TEXT`, `BACKGROUND_SIGNAGE`,
`BRAND_TEXT_OR_MARK`, `OVERLAY_TEXT`, `OVERLAY_WATERMARK`, `GRAPHICAL_LOGO`,
`GENERATIVE_TEXT_ARTIFACT`, `UNCERTAIN`.

**Additional typed fields for detector evaluation** (rater sees only the image):

| Field | Values |
|---|---|
| `visibleGraphicalMark` | yes / no / uncertain |
| `markIntegration` | scene_native / overlay_like / uncertain / not_applicable |
| `markType` | brand_or_object_mark / graphical_logo / watermark / other_mark / none / uncertain |

No raw text transcription is recorded or stored, ever.

**Blinding:** the rater is shown the image and nothing else — no OWLv2 box or
score, no Grounding DINO output, no Florence OCR/OD, no `watermarkQaAction`, no
H1/H2/H3 action, no `reviewReasons`/`rejectReasons`, no preview result.

**Two raters:** Rater A and Rater B label independently and cannot see each
other's first-pass labels. Disagreements go to a third adjudicator if one
exists; otherwise the item stays `UNCERTAIN`. The agent never acts as a rater
and never fabricates a label.

**Completion gate:** OWLv2 precision, false-positive rate and H3 suitability
may not be judged until both raters have completed all 20 avatars. Until then
the verdict is `BLOCKED_HUMAN_LABELS_REQUIRED`.

## 2. OWLv2 calibration

**Raw capture:** one pass over the 20 avatars (clean + injected graphical-logo
derivative each, 40 conditions) storing every detection at or above a floor
score of 0.01. OWLv2 scores each text query independently, so filtering stored
rows by query label reproduces a single-prompt run, and filtering by score
reproduces that threshold. No re-inference for the sweep or the ablation.

**Threshold sweep grid (frozen):** 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50.

**Prompt ablation (frozen):** `a logo` alone, `a watermark` alone, `a brand
emblem` alone, `a graphic symbol` alone, and all four combined.

**Group split (frozen, participant-group level, never per image):** the 20
avatars are 5 groups of 4 by filename provenance (opaque keys G1–G5).

* Development: **G1, G2, G3** (12 images)
* Holdout: **G4, G5** (8 images)

Holdout is evaluated once, at the end. A threshold may not be re-chosen after
seeing holdout results.

**Threshold selection:** permitted only on development groups, and only once
human labels exist. Selection needs injected-logo recall, clean human-label
precision and clean review burden together. Without labels, the sweep is
reported as a descriptive curve and **no threshold is selected**.

**Sample-size discipline:** 20 images cannot establish production precision.
Results are labelled `G004_CLEAN_AVATAR_HOLDOUT_EVIDENCE` and reported with
Wilson 95% confidence intervals. If there are no human positives, recall is
reported as NOT ESTIMABLE.

## 3. Box-match rule (frozen)

Florence region ↔ OWLv2 region correspondence: **IoU ≥ 0.3** (identical to
B3-L4/B3-L5), OR containment — the OWLv2 box covers ≥ 0.5 of the Florence
region's area. Either condition counts as a match.

## 4. H3 candidates (frozen, escalate-only)

All three are escalate-only: H3 action = max(live action, proposed action) over
allow < review < reject, so a hard-reject bypass or a new overlay/artifact miss
cannot be introduced by construction. All are shadow; none is wired to the live
policy.

* **H3-A** — Florence `overlayLike` region AND an OWLv2 mark matching that
  region (box-match rule above) → review.
* **H3-B** — OWLv2 matched mark AND `sourceConsistent != true` → review.
* **H3-C** — Florence OCR region AND overlapping OWLv2 mark AND the mark is not
  scene-native → review.

**H3-C carries a deliberate restriction.** "Not scene-native" is available in
this evaluation only as a *human* label (`markIntegration`), which is evaluation
truth and not a runtime feature. H3-C is therefore evaluated as an *upper bound*
on what a runtime rule could achieve, and is not a deployable rule unless a
runtime signal replaces that field. This is stated wherever H3-C appears.

## 5. H3 acceptance gate (frozen)

`H3_SHADOW_PROMISING` requires all of:

1. injected graphical-logo recall not worse than the current best measured;
2. injected watermark miss increase = 0;
3. generative artifact miss increase = 0;
4. hard-reject bypass = 0;
5. clean-avatar review flood materially below H2's (H2: 15 of 20);
6. holdout clean-label precision at or above an **owner-defined floor**;
7. worker resource feasibility.

There is no owner-defined precision floor at the time of writing, so criterion 6
cannot be evaluated and the agent will not invent a production threshold.
`H3_LIVE_POLICY_READY` is not a permitted outcome of this task.

## 6. Resource feasibility (frozen method)

Headroom = worker memory limit − existing model peak − OWLv2 projected peak −
runtime margin. Standalone and co-resident figures are reported separately.
A co-residency measurement is attempted only under subprocess isolation with an
abort threshold; if the machine cannot hold it safely, a static projection is
reported and labelled as such. The worker's memory limit is never raised.
