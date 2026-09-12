# B3-L5 Part B — graphical-logo detector benchmark

LOCAL_CPU_BENCHMARK, offline, decision-neutral. No detector is integrated, no
live policy changed, no fusion implemented. Aggregate only: no image, crop,
embedding, filename, path or box from a real image appears here.

**Verdict: `LOGO_DETECTOR_SHADOW_CANDIDATE_FOUND`** — `owlv2-base-patch16-ensemble`.

## 1. Why

B3-L4 measured that Florence gives essentially no graphical-logo signal: the
injected mark was found on 0 of 8 source photos and 5 of 20 avatars by OCR, and
`<OD>` never localized it (0 logo/sign-kind hits). That is a MODEL gap, so
other local detectors were benchmarked on the same corpus, the same injected
ground truth and the same match rule (IoU ≥ 0.3).

## 2. Candidates

Two candidates, both zero-shot open-vocabulary detectors that localize a mark
from a text query (not OCR models relabelled as logo detectors). Licenses read
from the official Hugging Face model cards; no blog or forum was used as
license authority.

| Candidate | Repository | Revision | License | Commercial restriction on card | Weights on disk |
|---|---|---|---|---|---|
| owlv2-base-patch16-ensemble | `google/owlv2-base-patch16-ensemble` | `cfd3195ba4ea9592eec887ded089f4c08eff231d` | apache-2.0 | none stated | 593 MB |
| grounding-dino-tiny | `IDEA-Research/grounding-dino-tiny` | `a2bb814dd30d776dcf7e30523b00659f4f141c71` | apache-2.0 | none stated | 658 MB |

Considered and **not** downloaded or evaluated: Ultralytics YOLOv8 / YOLO-World.
Its licence (AGPL-3.0) carries obligations whose fit with this product's
distribution model is an owner decision, not one this benchmark makes, so it is
`EXCLUDED_PENDING_PRODUCT_LICENSE_DECISION` — not a statement that the licence
forbids use. Also not benchmarked: `google/owlvit-base-patch32` (apache-2.0, the
OWLv2 predecessor), dropped for local disk headroom, not on merit.

Frozen before inference: prompts `("a logo", "a watermark", "a brand emblem",
"a graphic symbol")` — generic, no brand name; OWLv2 threshold 0.10; Grounding
DINO box/text thresholds 0.25/0.25 (the model card defaults). No threshold was
tuned after seeing results.

Pre-registered preprocessing: an image whose long side exceeds 2048 px is
downscaled (LANCZOS) before injection, with ground truth scaled identically.
Both detectors resize internally far below that (OWLv2 960², Grounding DINO
~800 short side), so this changes nothing either model sees; it exists because
the OWLv2 image processor upcasts to float64 and allocated ~0.5 GB per 5712 px
photo. Avatars and controls are untouched by it. Both candidates were re-run
under this identical rule.

## 3. Injected graphical-logo recall (ground truth by construction)

| Detector | Source (8) hit / recall / mean IoU | Avatar (20) hit / recall / mean IoU | Synthetic ctl-08 |
|---|---|---|---|
| Florence `<OCR_WITH_REGION>` | 0.00 / 0.00 / – | 0.25 / 0.25 / 0.233 | miss |
| Florence `<OD>` | 0.00 | 0.00 | miss (whole image labelled `poster`) |
| **owlv2-base-patch16-ensemble** | **1.00 / 1.00 / 0.928** | **1.00 / 1.00 / 0.924** | **hit, IoU 0.950** |
| grounding-dino-tiny | 0.875 / 0.875 / 0.733 | 1.00 / 1.00 / 0.868 | hit, IoU 0.852 |

Both candidates close the gap Florence leaves. OWLv2 is perfect on all 29
injected conditions and localizes more tightly.

## 4. Clean-image region response (no human labels — not false positives)

CLEAN_IMAGE_REGION_RESPONSE_RATE: how often each detector returns any region on
an image with no injected mark. These images have no human logo label, so a
detection here is not scored as an error; some may be real marks in the photo.

| Detector | Source: images with ≥1 / mean per image | Avatar: images with ≥1 / mean | Synthetic (9 clean controls) |
|---|---|---|---|
| Florence OCR (regions) | 8/8 / 1.5 | 20/20 / 1.0 | 1 region on every control |
| owlv2 | 5/8 / 4.6 | **12/20 / 0.95** | 9/9 / 3.3 |
| grounding-dino-tiny | 8/8 / 2.9 | 17/20 / 2.65 | 9/9 / 8.8 |

OWLv2 is the quieter of the two on the production-like avatar domain; Grounding
DINO fires on 17 of 20 clean avatars. This is the reason no fusion policy is
proposed yet: a naive "any logo detection → review" rule would flood review
exactly as H2 does (Part A), and distinguishing a real mark from a response
needs human labels that do not exist.

## 5. Resource cost (local CPU; not a production GPU number)

| Detector | Load | Mean latency / image | Max | Peak RSS | Disk |
|---|---|---|---|---|---|
| owlv2-base-patch16-ensemble | 9.3 s | 12.2 s (avatar) – 13.5 s (source) | 16.1 s | **5.82 GB** | 593 MB |
| grounding-dino-tiny | 9.7 s | 9.3 s (avatar) – 11.7 s (source) | 14.9 s | 2.89 GB | 658 MB |
| Florence (B3-L4, both tasks) | 6.7–13.8 s | 33.7 s (avatar) | 48.4 s | 4.51 GB | 1.5 GB |

Both candidates are cheaper per image than the Florence OCR+OD pair already in
the pipeline. OWLv2's 5.82 GB peak RSS is the one resource caveat: it exceeds
Grounding DINO's by 2.9 GB and would need checking against the worker's memory
limit before any shadow wiring. Loading two detectors in one process segfaulted
this 16 GB machine, so each ran in its own process.

## 6. Candidate verdicts

| Candidate | Verdict | Basis |
|---|---|---|
| owlv2-base-patch16-ensemble | **SUITABLE_FOR_SHADOW** | recall 1.00 on all 29 injected conditions, tightest IoU, quietest on clean avatars, apache-2.0, 593 MB. Caveat: 5.82 GB peak RSS. |
| grounding-dino-tiny | SUITABLE_FOR_SHADOW (second) | recall 1.00 avatar / 0.875 source, looser boxes, 2.8× the clean-avatar response rate. Lighter (2.89 GB). |
| Ultralytics YOLO-World | LICENSE_REVIEW_REQUIRED | AGPL-3.0. Obligation acceptance is an owner decision; not downloaded, not evaluated, no compatibility claim made either way. |

Overall: `LOGO_DETECTOR_SHADOW_CANDIDATE_FOUND`.

## 7. What this does not establish

Natural-occurrence production logo prevalence or accuracy; whether the clean
detections are real marks; behaviour on actual third-party brand logos (only a
synthetic geometric mark was injected); GPU latency or memory; and whether any
fusion of Florence + a detector is safe — no fusion was designed or run.

Next step, if the owner wants it: a shadow-only fusion proposal with OWLv2
behind a flag, evaluated on this same corpus plus human labels for the clean
images. Not implemented here.
