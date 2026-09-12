# B3-L6 — human ground truth, OWLv2 calibration, H3 feasibility

Offline and decision-neutral. No live policy change, no detector integration, no
fusion, no build, no deploy. Aggregate only: no image, crop, embedding,
filename, path, hash, UID, OCR text or detector box appears here.

**Verdicts: `OWLV2_EVIDENCE_INSUFFICIENT` and `H3_EVIDENCE_INSUFFICIENT`, both
gated on `BLOCKED_HUMAN_LABELS_REQUIRED`.** OWLv2's injected-logo recall and its
score separation are strong enough to justify continuing, and the worker has
ample memory headroom — but clean-image precision cannot be measured without the
two-rater labels, and no owner-defined precision floor exists, so neither the
detector nor H3 can be validated here.

## 1. What was measured, and what could not be

| Question | Answer |
|---|---|
| Does OWLv2 find an injected graphical mark on real avatars? | Yes — 20/20, and it holds across a wide threshold range |
| Is there a threshold separating injected marks from clean-image responses? | Yes — clean responses reach 0 at 0.25 while injected recall is still 20/20 |
| Are the clean-image detections real marks or noise? | **Unknown** — needs human labels |
| Can a threshold be selected? | **No** — selection requires labels; not selected |
| Does H3 reduce H2's review flood? | Yes on this corpus (5 or 8 of 20 vs H2's 15) |
| Is H3 safe? | Escalate-only: 0 hard-reject bypass, 0 new misses, measured |
| Does the worker have room for OWLv2? | Yes — 32 GiB limit, ~20 GiB projected headroom |

## 2. Human ground truth (Part A)

**Tooling built, no labels collected.** This session had no human raters, and a
label may never be fabricated, so everything label-dependent stops at
`BLOCKED_HUMAN_LABELS_REQUIRED`.

* `scripts/avatar_watermark_label_local.py` builds one self-contained HTML page
  per rater into the restricted local directory. Verified on the generated
  pages: 0 occurrences of any detector name, score, Florence output,
  `watermarkQaAction`, H1/H2/H3 action, `reviewReasons`/`rejectReasons` or
  preview result; 0 URLs; 0 filenames or paths (images are inlined as data URIs
  and identified only by opaque evaluation ID); a CSP meta tag blocks any future
  network fetch. 20 items per rater, 4.7 MB per page.
* `scripts/avatar_watermark_label_ingest.py` ingests two independent exports. It
  rejects a single rater labelling twice (`RATERS_NOT_DISTINCT`) and rejects a
  second pass whose label content is identical to the first
  (`RATER_PASSES_IDENTICAL_NOT_INDEPENDENT`), keeps only the allowed fields, and
  marks any primary-label or visible-mark disagreement `UNCERTAIN` with
  `adjudicationState = unresolved_disagreement` unless an adjudicator resolves
  it.
* Taxonomy is the PR #114 schema unchanged, plus the three typed detector
  fields (`visibleGraphicalMark`, `markIntegration`, `markType`). No raw
  transcription is collected or stored.

**Primary corpus:** the 20 generated avatars. The 8 source photos stay secondary
and are outside any acceptance gate.

**To collect labels:** open `label-rater-A.html` and `label-rater-B.html` from
the restricted directory in a browser, label every item, click Export, then run
the ingest script on the two exports. Until `complete: true`, the calibration
script refuses to emit precision, recall, H3-C or a selected threshold.

## 3. OWLv2 calibration (Part B)

One capture pass over 40 conditions (20 clean avatars + the injected
graphical-logo derivative of each) at a **floor** score of 0.01, storing every
detection. OWLv2 scores each text query independently, so the sweep and the
ablation are computed by filtering those stored rows — zero re-inference.

**Group split, frozen before analysis** (participant groups, never per image):
development G1–G3 (12 images), holdout G4–G5 (8 images). Group identity comes
from corpus provenance, not from any result.

### Threshold sweep (combined prompts)

| Threshold | Injected hit, dev | Injected hit, holdout | Clean response, dev | Clean response, holdout | Clean detections/image (all) |
|---|---|---|---|---|---|
| 0.05 | 12/12 | 8/8 | 11/12 | 8/8 | 2.25 |
| 0.10 | 12/12 | 8/8 | 6/12 | 6/8 | 0.95 |
| 0.15 | 12/12 | 8/8 | 3/12 | 5/8 | 0.50 |
| 0.20 | 12/12 | 8/8 | 2/12 | 0/8 | 0.10 |
| **0.25** | **12/12** | **8/8** | **0/12** | **0/8** | 0.00 |
| 0.30 | 12/12 | 8/8 | 0/12 | 0/8 | 0.00 |
| 0.40 | 9/12 | 8/8 | 0/12 | 0/8 | 0.00 |
| 0.50 | 1/12 | 3/8 | 0/12 | 0/8 | 0.00 |

Injected recall is 20/20 (Wilson 95% [0.839, 1.0]) from 0.05 through 0.30 and
collapses by 0.50. Clean-image responses fall monotonically to zero at 0.25.

**This separation is not a precision result.** "Clean response 0 at 0.25" is
consistent with two very different worlds: the low-score detections are noise
that a higher threshold removes, or some clean avatars carry a real mark that a
higher threshold *misses*. Only human labels distinguish them, which is exactly
why no threshold is selected. Holdout was computed once and no threshold was
re-chosen after seeing it.

### Prompt ablation (at 0.10)

| Prompt mode | Injected hit | Clean response | Clean detections/image |
|---|---|---|---|
| `a graphic symbol` alone | **20/20** | 8/20 | 0.50 |
| `a logo` alone | 0/20 | 2/20 | 0.15 |
| `a watermark` alone | 0/20 | 2/20 | 0.10 |
| `a brand emblem` alone | 0/20 | 2/20 | 0.20 |
| all four combined | 20/20 | 12/20 | 0.95 |

The entire injected-logo recall comes from one query, `a graphic symbol`. The
other three contribute only clean-image responses at this threshold.

**Caveat that limits this finding:** the injected mark is an abstract geometric
shape (a filled circle plus a triangle), which is precisely what "a graphic
symbol" describes. This ablation therefore characterises the *synthetic
construct*, not real brand logos, and must not be used to drop the `a logo` /
`a watermark` queries from a future prompt set. A real-logo corpus would be
needed for that, and none exists in the authorized data.

## 4. Resource feasibility (Part C)

Fresh read-only inventory of the deployed worker
(`seolleyeon-avatar-worker-qa103-106-46485a05`, asia-southeast1):

| Property | Value |
|---|---|
| Memory limit | **32 GiB** |
| CPU | 8 |
| GPU | 1 × NVIDIA L4 (`run.googleapis.com/accelerator`) |
| Container concurrency | 1 |
| Request timeout | 1800 s |
| Max instances | 1 |
| Startup probe | TCP 8080, 240 s period, failureThreshold 1 |

Baked models: Florence-2-large-ft, CLIP ViT-L/14, CLIP ViT-B/32, plus MediaPipe
face assets; DINOv2-base is configured by env.

| Memory line | Value | Source |
|---|---|---|
| Worker limit | 32.0 GiB | live config, read-only |
| Florence peak (standalone) | 4.51 GiB | B3-L4 measurement, up to 2048 px input |
| OWLv2 peak (standalone) | **5.12 GiB** | this capture, at production-like 1254² avatar resolution |
| Runtime margin allowance | 2.0 GiB | assumption, stated as such |
| **Projected co-resident total** | **~11.6 GiB** | sum of the above |
| **Projected headroom** | **~20.4 GiB** | 32.0 − 11.6 |

**Co-residency was not measured.** Two detectors in one process segfaulted this
16 GiB machine during B3-L5, and the Florence snapshot was deleted to make disk
room (1.8 GiB free), so a Florence + OWLv2 co-load could not be run safely. The
figure above is a **static projection**, labelled as such. The worker's memory
limit was not touched.

**Latency.** OWLv2 averaged 13.9 s per avatar on this CPU, with a 36 s model
load. That is the relevant projection rather than a GPU estimate, because the
visual-risk adapter passes no device and nothing in the worker moves it to the
L4: `qa_runtime.get_default_visual_risk_adapter()` constructs the adapter with
`model_id` and `local_files_only` only, and no env var sets a device (only
`AVATAR_SAM_DEVICE` exists, for SAM). So Florence already runs on CPU inside a
GPU container, and OWLv2 would too. At concurrency 1 and 4 candidates per job,
adding OWLv2 projects to roughly +56 s per job against a 1800 s timeout. No GPU
speed is invented here.

Resource verdict: **feasible on memory** (~20 GiB headroom), with latency as the
real cost. Not `RESOURCE_BLOCKED`.

## 5. H3 detector-assisted shadow (Part D)

Three candidates frozen in the pre-registration, all **escalate-only**
(action = max(live, proposed)), evaluated at the reference threshold 0.10 with
combined prompts on 40 conditions.

| | Current | H3-A | H3-B | H3-C |
|---|---|---|---|---|
| Clean avatars in review (of 20) | 3 | **5** | 8 | blocked |
| — development / holdout | – | 3/12, 2/8 | 5/12, 3/8 | blocked |
| Injected-logo conditions flagged (of 20) | 2 | **10** | 9 | blocked |
| Hard-reject bypass | – | **0** | **0** | – |
| Transitions | – | `allow→review` 10, same 30 | `allow→review` 12, same 28 | – |

Compared with H2's 15 of 20 clean avatars, both runnable candidates are far
quieter (5 and 8) while flagging 5× more injected logos than the current policy.
H3-C is `BLOCKED_HUMAN_LABELS_REQUIRED` by construction: its "not scene-native"
term is a human `markIntegration` label, which is evaluation truth and not a
runtime feature, so it is an upper bound rather than a deployable rule.

**The structural limit found here matters more than the counts.** H3 escalates
only regions Florence already produced. OWLv2 localizes the injected mark on
20/20 images, but H3-A flags 10/20 — on the other half Florence has no region at
the mark's location, so there is nothing to escalate. Using the detector's full
recall would need an escalation path that does not require a pre-existing
Florence region, which is a different design than any H3 candidate and is not
pre-registered here.

Safety invariants (measured, and structurally guaranteed by escalate-only):
injected watermark miss increase 0, generative-artifact miss increase 0,
hard-reject bypass 0, no live review or reject downgraded.

**Production metadata replay was not repeated** for H3: it requires a per-region
detector match, which does not exist in persisted production documents (they
carry typed evidence only, no detector output). Running OWLv2 over production
candidate images is out of scope — those raw images are not authorized. This is
a genuine gap in the evidence, not an omission: H3 cannot be replayed on
production data until a detector runs there in shadow.

## 6. Acceptance gate status

| Criterion | Status |
|---|---|
| Injected graphical-logo recall not worsened | met (escalate-only; recall unchanged) |
| Injected watermark miss increase = 0 | met |
| Generative artifact miss increase = 0 | met |
| Hard-reject bypass = 0 | met |
| Clean-avatar flood materially below H2 | met (5 or 8 vs 15) |
| Holdout clean-label precision ≥ owner floor | **not evaluable** — no labels, and no owner-defined floor |
| Worker resource feasible | met (projected ~20 GiB headroom) |

Five of seven criteria are met. The two that are not are both blocked on inputs
only the owner can supply: human labels, and a precision floor. The agent does
not invent a production threshold.

## 7. Verdicts

* Detector: **`OWLV2_EVIDENCE_INSUFFICIENT`** — recall and score separation are
  strong and resources are feasible, but clean-image precision is unmeasured.
  Not `PRECISION_INSUFFICIENT` (no precision evidence exists either way) and not
  `RESOURCE_BLOCKED`.
* H3: **`H3_EVIDENCE_INSUFFICIENT`** — safe and materially better than H2 on this
  corpus, but its acceptance gate cannot close without labels and a floor.
* Overall: **`BLOCKED_HUMAN_LABELS_REQUIRED`**.

`H3_LIVE_POLICY_READY` is not claimed and was not an available outcome.

## 8. Exact next step

1. Two people label the 20 avatars with the blinded pages, independently.
2. Run the ingest script; if `complete: true`, re-run the calibration with
   `--labels` to unlock precision, H3-C and development-only threshold selection.
3. Owner sets a precision floor for the clean-avatar corpus. Without it,
   criterion 6 stays unevaluable no matter how many labels exist.
4. Only then: a shadow-fusion proposal, evaluated against that floor.

## 9. What this does not establish

Production prevalence or accuracy of any kind (20 images, labelled
`G004_CLEAN_AVATAR_HOLDOUT_EVIDENCE`); behaviour on real third-party logos;
whether the clean-image detections are real marks; GPU latency or memory;
co-resident memory as measured rather than projected; and any production
replay of H3.
