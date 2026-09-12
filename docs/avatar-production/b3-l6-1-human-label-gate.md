# B3-L6.1 — human label gate: owner-approved provisional gate + rater procedure

Frozen **before any human label exists**, so it cannot be retuned once labels
arrive. Current status: `HUMAN_LABEL_PAGES_READY_WAITING_FOR_TWO_RATERS`.

No live policy change, no detector integration, no GPU routing change, no worker
memory change, no build, no deploy.

## 1. What this gate is, and is not

It is a **small-sample pilot gate**: it decides only whether the work proceeds
to the next shadow-evaluation stage, on a 20-image corpus.

It is **not** a production validation threshold. Results are reported as
`PROVISIONAL_G004_SHADOW_EVIDENCE` / `G004_CLEAN_AVATAR_PILOT_PRECISION`. These
phrasings are prohibited and are asserted against in the tests: "production
precision established", "80% production precision proven", "model validated for
production". Confidence intervals are reported, but a CI lower bound is **not**
used as the gate on this pilot.

## 2. Owner-approved criteria (frozen)

Encoded as constants and a gate function in
`scripts/avatar_owlv2_calibration.py` (`GATE_VERSION = owlv2_provisional_shadow_gate_v1`),
so the numbers are machine-checked rather than prose.

| # | Criterion | Value | Notes |
|---|---|---|---|
| A | Adjudicated clean-avatar image-level precision | **≥ 0.80** | `PROVISIONAL_PRECISION_FLOOR` |
| B | New detector-induced review rate among human-negative clean avatars | **≤ 0.10** | at N=20, **at most 2 images** |
| C | Known injected graphical-mark recall | **20 / 20** | `INJECTED_RECALL_REQUIREMENT = 1.0` |
| D | Generative-artifact safety regression | **0** | |
| E | Hard-reject bypass | **0** | |

A and B are label-derived. The gate function returns
`BLOCKED_HUMAN_LABELS_REQUIRED` whenever they are absent — absence is never a
pass.

## 3. Threshold 0.25 is not selected

B3-L6 measured a clean separation at 0.25 (injected 20/20, clean response 0/20).
That is **not** a selected threshold, because a clean response of 0 is equally
consistent with a real mark being missed. Selection procedure, unchanged:

1. threshold candidates come only from **development groups G1–G3** with
   completed human labels;
2. the chosen threshold is frozen;
3. **holdout G4–G5 is evaluated exactly once**, afterwards, and never used to
   re-choose.

## 4. Rater assignment

* **Rater A** — the owner.
* **Rater B** — one separate person the owner designates.

Both perform the first pass fully independently and do not look at each other's
JSON. The agent never acts as a rater and never writes a label.

## 5. Instructions for both raters

Open your own page, label all 20 images, click **Export**, and save the JSON.

You are **not** judging whether any detector was right. Look at the image only
and decide, independently, whether a relevant text or mark is actually visible.
Do not try to guess what OWLv2, Florence or the QA pipeline said — none of it is
shown to you, by design.

For each image pick one **primary label**:

`NO_VISIBLE_RELEVANT_TEXT_OR_MARK`, `GARMENT_TEXT`, `BACKGROUND_SIGNAGE`,
`BRAND_TEXT_OR_MARK`, `OVERLAY_TEXT`, `OVERLAY_WATERMARK`, `GRAPHICAL_LOGO`,
`GENERATIVE_TEXT_ARTIFACT`, `UNCERTAIN`.

Tick every class you can see under **all visible classes**, then answer:

* `visibleGraphicalMark` — yes / no / uncertain
* `markIntegration` — scene_native (part of the scene or garment) / overlay_like
  (stamped on top) / uncertain / not_applicable
* `markType` — brand_or_object_mark / graphical_logo / watermark / other_mark /
  none / uncertain
* confidence — high / medium / low

Do **not** transcribe any text you see. The class is enough; the wording is
never recorded.

If the two of you disagree on an item, it stays `UNCERTAIN` unless a third
person adjudicates it.

## 6. Next hypothesis (noted, not pre-registered here)

B3-L6 found that OWLv2 localizes the injected mark on 20/20 images while H3-A
flags 10/20, because H3 escalates only regions Florence already produced. If
OWLv2 passes this gate, the next hypothesis to pre-register is whether detector
evidence can be shadow review evidence **independently of whether a Florence
region exists** — a different design. The existing H3-A/H3-B will not be
threshold-tuned to manufacture 20/20.

## 7. Resource note (unchanged, no action)

Worker: 32 GiB, 8 CPU, 1×L4. OWLv2 local peak ~5.12 GiB; static projection says
memory is feasible, but co-residency was never measured, and the visual-risk
adapter passes no device, so Florence runs on CPU even in the GPU container.
GPU routing, worker memory and deploys are all out of scope here and belong to a
separate performance task if a detector shadow is ever approved.

`approveAvatarCandidate` remains a separate release blocker: an exact production
deploy carrying current-main approval parity is required before public rollout.
Not done here.
