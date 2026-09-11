# B3-L1 Watermark Human-Label Evidence Contract

Status: `APPROVED` 2026-09-11 for the label schema, label guide, storage and
privacy contract, and synthetic controls. **This approval does not authorize any
G004 raw image (§2) or any production image (§3).**
Date: 2026-09-11
Schema: [`tests/fixtures/avatar_watermark_label_schema_v2.json`](../../tests/fixtures/avatar_watermark_label_schema_v2.json)
Controls: [`scripts/avatar_watermark_controls.py`](../../scripts/avatar_watermark_controls.py)

This contract says which data may be labelled, how it is labelled, and when the
labels are good enough to evaluate a watermark model or policy. It changes no
policy, threshold, model or live classifier.

Current state: **0 human labels, 0 known-positive controls in any real corpus.**
B3 is `B3_DATA_INSUFFICIENT_LABELING_REQUIRED` until this contract's gate is met.

## 1. Data sources

| | A. G004 cohort | B. Repo synthetic fixtures | C. QA benchmark images | D. Separately approved calibration corpus | E. Production candidates |
|---|---|---|---|---|---|
| Raw image exists | Yes, in a private operator review bundle | No: model-output JSON only | None in the repo (0 image files) | None identified | Yes, in the temp/candidate buckets |
| Where | Local operator bundle. GCS copies are deleted after download by `persist_review_bundle_and_delete_remote` | `tests/fixtures/` | none | none | GCS, private |
| Retention | `temporaryRetention: "bounded"`, `retention: "delete_after_bounded_human_review"` | permanent (no user data) | n/a | n/a | Candidate `expiresAt` plus retention jobs |
| Consent purpose | `calibrationPurpose` (scope `g004_quality_calibration`), `sourceImageUse`, `azureExternalAiProcessing`, `qaScoring`, `humanReview` | n/a | n/a | n/a | `consentPurposes` records `avatarGeneration` only (20 of 86 jobs carry the map; the rest carry none) |
| QA / human-review permission | Flags present | n/a | n/a | n/a | **No** |
| Watermark-labeling permission | **Unverified**: see §2 | n/a (no user data) | n/a | n/a | **No** |
| May derive and store a label | Only if §2 is resolved | Yes | n/a | n/a | **No** |
| May extend retention | **No** | n/a | n/a | n/a | **No** |
| May export or copy | **No** | Yes | n/a | n/a | **No** |

Synthetic controls (§8) are a sixth source. They carry no user data and have
the same permissions as B.

## 2. G004 authorization: `G004_LABELING_AUTHORIZATION_UNVERIFIED`

What the source proves:

- The G004 exact-consent contract (`calibration_runner._exact_consent`,
  `calibration_service._current_source_contract_matches`) requires these flags
  to be true: `calibrationPurpose`, `sourceImageUse`, `azureExternalAiProcessing`,
  `qaScoring`, `humanReview`. It also requires `temporaryRetention`,
  `calibrationDate` and `calibrationVersion`. The staging scope must equal
  `g004_quality_calibration`.
- The G004 plan's human rubric asks reviewers to score the generated avatar
  result only: quality, resemblance, over-beautification, trait consistency,
  background cleanup naturalness, and a safety result (approve / needs review /
  reject).

What it does not prove:

1. **The consent wording.** The text participants agreed to is not in the
   repository, and no client copy matches these flags. A boolean named
   `humanReview` does not show that watermark/text/logo labeling was within
   what was described to participants.
2. **That the retention window is still open.** Retention was bounded and
   delete-after-review. The benchmark recorded the bundle as present on
   2026-08-27. Labeling now could hold images past the window participants
   agreed to, which this contract forbids.

To unblock, the owner records either the consent text or a data-use decision
showing that (a) watermark/text/logo labeling of generated results falls within
`g004_quality_calibration` human review, and (b) the bundle is still inside its
bounded retention window. Until then **no G004 image is opened**, and G004
supplies no labels. The 2026-09-11 approval of this contract covers the schema,
guide, storage rules and synthetic controls only; it is **not** that record.

Even when authorized, G004 is exploratory. It has 20 candidates from 5
participants, and its machine evidence has confidence `unknown` on every region.
See §9.

## 3. Production user data: not authorized

Production `consentPurposes` covers `avatarGeneration`. It does not cover QA
research, human review, or labeling. Production candidate images are therefore
not a labeling source. Read-only aggregates of production **metadata** remain
allowed, and are how B3 measured its replay.

## 4. Label unit

One generated candidate image is one unit with one primary image-level label.
Region annotations are added only when an evaluation needs localisation, for
`REGION_MISS` or `OCR_TRANSCRIPTION_MISMATCH`. Ground truth is image-first, so
it cannot inherit the OCR model's region errors.

## 5. Taxonomy

**Human image labels** (what a rater sees):
`NO_VISIBLE_RELEVANT_TEXT_OR_MARK`, `GARMENT_TEXT`, `BACKGROUND_SIGNAGE`,
`BRAND_TEXT_OR_MARK`, `OVERLAY_TEXT`, `OVERLAY_WATERMARK`, `GRAPHICAL_LOGO`,
`GENERATIVE_TEXT_ARTIFACT`, `UNCERTAIN`.

**Derived model errors** (computed, never labelled by a human):

| error | derivation |
|---|---|
| `OCR_HALLUCINATION` | primary label `NO_VISIBLE_RELEVANT_TEXT_OR_MARK`, and OCR reported at least one region |
| `OCR_MISS` | primary label is a visible-text class, and OCR reported no region |
| `REGION_MISS` | a human region with no overlapping OCR region (overlap cut pre-registered) |
| `OCR_TRANSCRIPTION_MISMATCH` | a human transcription that differs from the normalised OCR text; only the typed outcome (`match` / `mismatch` / `not_evaluated`) is stored, see §7 |

When several classes are visible, the primary label follows
`primaryLabelPrecedence`, and every visible class goes in `allVisibleClasses`.

## 6. Label guide

Each class is judged from the image alone.

**NO_VISIBLE_RELEVANT_TEXT_OR_MARK**
- Include: nothing letter-like, logo-like or mark-like anywhere.
- Exclude: faint texture that reads as letters to you (→ `GENERATIVE_TEXT_ARTIFACT` or `UNCERTAIN`).
- Boundary: a pattern on fabric with no glyphs counts as no text.
- Uncertain: you have to zoom to wonder whether something is text.

**GARMENT_TEXT**
- Include: lettering on clothing or accessories that follows folds, curvature and lighting.
- Exclude: text floating flat over the garment ignoring folds (→ `OVERLAY_TEXT`); a recognisable brand name or mark (→ `BRAND_TEXT_OR_MARK`).
- Boundary: large flat text on a flat shirt front counts as garment text if it sits under the scene's lighting.
- Uncertain: you cannot tell whether it is printed or composited.

**BACKGROUND_SIGNAGE**
- Include: signs, posters, screens and storefronts that belong to the scene, share its perspective, and can be occluded by the subject.
- Exclude: text that sits in front of the subject or ignores perspective (→ `OVERLAY_TEXT`).
- Boundary: blurred background lettering still counts as signage if it is scene-native.
- Uncertain: the only cue is position.

**BRAND_TEXT_OR_MARK**
- Include: a brand name or mark on a real object in the scene (clothing, bag, product).
- Exclude: a mark composited over the image (→ `GRAPHICAL_LOGO` / `OVERLAY_WATERMARK`).
- Boundary: an invented word styled like a brand, integrated into the scene, counts here.
- Uncertain: integrated versus composited is unclear.

**OVERLAY_TEXT**
- Include: text composited over the image that ignores scene geometry and lighting and is not a creator/provider mark.
- Exclude: creator, tool, platform or stock marks (→ `OVERLAY_WATERMARK`).
- Boundary: captions and meme text count here.
- Uncertain: it could be a mark or plain text.

**OVERLAY_WATERMARK**
- Include: creator, tool, platform or stock-provider marks; semi-transparent marks over the image; repeated or tiled marks; small marks at an edge or corner.
- Exclude: real background signs; brands printed on clothing; any scene-native text.
- Boundary: a single tiny corner mark still counts if it is composited.
- Uncertain: you cannot tell whether it is composited or scene-native.

**GRAPHICAL_LOGO**
- Include: a logo composited over the image, with or without text.
- Exclude: a logo printed on a scene object (→ `BRAND_TEXT_OR_MARK`).
- Boundary: an emblem next to a watermark word takes the primary label `OVERLAY_WATERMARK`; record both.
- Uncertain: the emblem's integration is unclear.

**GENERATIVE_TEXT_ARTIFACT**
- Include: letter-like strokes the generator invented that do not read as a real word, wherever they are.
- Exclude: legible real words (use the class for where they sit).
- Boundary: a half-legible word counts as an artifact if no language would read it.
- Uncertain: it might be a stylised real word.

**UNCERTAIN**
- Use this whenever the class-specific rule above says so.
- Never use it to avoid a decision you can make.
- It is excluded from primary metrics and reported separately.

## 7. Blinding, raters, storage

- **Blind the rater to:** OCR transcription, OCR sequence score, current
  `watermarkQaAction`, decision or evidence class, `rejectReasons` /
  `reviewReasons`, shadow class or action, preview or approval outcome, and the
  other rater's label in the first pass. The rater sees the candidate image, and
  optionally the source image only to judge whether a mark was already present.
- **Raters:** at least two, labeling independently. Disagreements go to a third
  adjudicator, or become `UNCERTAIN` when no adjudicator is available. Record raw
  agreement and the full class confusion matrix. Report Cohen's kappa only with a
  caution: at this size, with sparse classes, it is unstable.
- **Storage:** only `evaluationId`, `primaryLabel`, `allVisibleClasses`,
  `labelConfidence`, `raterId`, `labeledAt`, `adjudicationState` and
  `provenanceCategory`. Never UID, email, raw OCR text, human transcriptions,
  image URLs or storage paths, private source references, or participant
  ordinals. Any `evaluationId`-to-image mapping stays in a separate restricted
  local authority and is never committed or exported.
- **Transcriptions (human and raw OCR):** usable only ephemerally, inside an
  authorized evaluation process, to derive `OCR_TRANSCRIPTION_MISMATCH`. They are
  never written to the persistent label dataset, never committed, never stored
  in production debug or Firestore documents, and never logged or exported.
  After the derivation they are discarded; the stored result is the typed
  outcome only (`match` / `mismatch` / `not_evaluated`).

## 8. Known controls

`scripts/avatar_watermark_controls.py` draws ten deterministic images from
scratch: overlay (tiled), corner, edge and transparent watermarks; garment text;
background signage; brand text; graphical logo; no text; and a generative text
artifact. They contain no photograph, face, user data or real brand, and use no
network or model. Labels are construction intent.

They exist for policy reachability and model capability. The manifest forbids
using them to estimate production prevalence, precision or recall.

## 9. Sample size

No claim that N images suffice. After labeling, first record the prevalence of
each class. With `k` positives out of `n`, report an exact (Clopper–Pearson) 95%
interval. With `k = 0`, only an upper bound exists (roughly `3/n`: 15% for
`n = 20`), and recall cannot be estimated at all. If real overlay positives in
the authorized corpus are 0–1, the evaluation reports "not estimable" and names
the additional sample needed. The synthetic controls do not count toward it.

## 10. Label completion gate

| requirement | status |
|---|---|
| Labeling authorization verified | **No**: G004 unverified, production not authorized |
| Label schema finalized | **Yes**: v2 approved 2026-09-11 |
| Label guide finalized | **Yes**: §6 approved 2026-09-11 |
| Independent labels obtained | **No**: 0 labels |
| Disagreements handled | n/a (0 labels) |
| Known-positive controls exist | **Yes**: synthetic controls (§8) |
| Privacy audit green | Yes for schema, controls and shadow; not yet run on labels |

Model evaluation starts only when every row is green.

## 11. After the gate: Florence weights pre-report

The weights are not downloaded before the gate is green. When it is, report
these before asking the owner:

- download source and exact model revision (the worker pins `microsoft/Florence-2-large-ft` with `local_files_only=True`)
- license
- disk and network requirements
- expected CPU runtime (no local CUDA) and feasibility

## 12. Evaluation design (after weights are approved)

Keep **model capability** separate from **policy accuracy**.

- **Model capability:** region detection recall, visible-text false-positive
  rate, `OCR_HALLUCINATION` rate, transcription quality, overlay-watermark
  recall, garment/background confusion, and non-Latin behavior.
- **Policy accuracy:** current versus shadow actions against human labels, at
  both candidate and job level.

## 13. H1 acceptance gate

H1 ("fragmented text only counts as artifact evidence when it is
overlay-shaped") may move from shadow to live policy only when **all** of these
hold on human-labelled data:

1. The scene-native text flag rate drops.
2. The overlay and generative-artifact miss rate stays within a limit set by
   the owner before evaluation.
3. The zero-, one- and two-plus-preview job distribution does not get worse.

If the sample cannot establish these, H1 stays shadow.
