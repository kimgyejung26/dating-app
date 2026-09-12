# B3-L4 — Florence model ceiling + H1 shadow evaluation

Status: LOCAL_CPU_BENCHMARK, decision-neutral. Live policy unchanged. H1 stays SHADOW ONLY.

This report is aggregate-only. It contains no image, thumbnail, raw OCR
transcription, filename, image hash, UID, participant identity or private path.
Raw Florence outputs, the opaque-ID mapping and per-condition rows live only in
a restricted local directory on the operator machine and are never committed.

## 1. Authorities (kept separate)

| Authority | Value |
|---|---|
| A. Source (fresh `github/main`) | `ae7e289c820a991bf77e7dd1d3fd8b504becdcfb` |
| B. Deployed worker | `seolleyeon-avatar-worker-qa103-106-46485a05` (asia-southeast1, 100%), image digest `sha256:5aed9540…d679`, built from `46485a05` |
| C. Local benchmark environment | Windows, CPU only, torch 2.8.0+cpu, transformers 4.57.6, Pillow 11.3.0, numpy 1.26.4 |
| D. Source-photo dataset | `LOCAL_G004_SOURCE_PHOTO_SET`, 8 images |
| E. Generated-avatar dataset | `LOCAL_G004_GENERATED_AVATAR_SET`, 20 images |

B vs A: the decision path (`visual_risk.py`, `watermark.py`,
`florence2_visual.py`, Dockerfile, worker requirements) is identical. `main`
adds only the shadow module `watermark_construct_shadow.py`, its wiring in
`qa_signals.py`/`qa.py`, and the #107 availability-resolver refactor in
`preview_policy.py`. Persisted production documents therefore carry typed
evidence but no `shadowWatermark`; H1 is recomputed offline from that evidence.

## 2. Data authority

Owner decision (2026-09-11, supersedes the B3-L2 re-consent/disposition
proposal for this purpose): the two local sets below are authorized for
Florence model-ceiling, OCR/OD capability, watermark/text/logo QA research,
deterministic local derivatives, H1 shadow and current-vs-H1 offline replay.
Local processing only. The images are not deleted, moved, renamed or modified.

| Set | Alias | Authorized count |
|---|---|---|
| Source photos | `LOCAL_G004_SOURCE_PHOTO_SET` | 8 |
| Generated avatars | `LOCAL_G004_GENERATED_AVATAR_SET` | 20 |
| Total | | 28 |

Not included (not authorized by this decision): GCS calibration copies, any
production candidate image, any other user image, other review bundles or
calibration runs, pytest temporary directories. General production data is used
only as persisted typed metadata (`UNAUTHORIZED_RAW_PRODUCTION_CORPUS` for raw
images; never opened).

## 3. Florence model authority

Production reads `AVATAR_QA_VISUAL_RISK_MODEL_ID=/app/models/qa/florence2`, baked
in the Dockerfile by `snapshot_download(repo_id='florence-community/Florence-2-large-ft', revision=QA_FLORENCE_REVISION)`.
The `microsoft/Florence-2-large-ft` string in `florence2_visual.py` is only a
constructor default and is not what the worker loads.

| Field | Production | Benchmark |
|---|---|---|
| Repository | `florence-community/Florence-2-large-ft` | same |
| Revision | `26b734a54fdfbf9c398351eedfabb7f27fc470b7` (Dockerfile pin) | same, verified from download metadata |
| Classes | `Florence2Processor` / `Florence2ForConditionalGeneration` (native transformers) | same |
| transformers | `>=4.45,<5` (calibration preprocessing string pins 4.57.6) | 4.57.6 |
| torch | 2.8.0 (CUDA base image) | 2.8.0+cpu |
| dtype / device | adapter sets neither: fp32, model not moved | fp32, CPU |
| Tasks | `<OCR_WITH_REGION>`, `<OD>` | same |
| Generation | `num_beams=3`, `max_new_tokens=1024`, `return_dict_in_generate`, `output_scores` | same (production adapter `_run_task` called directly) |
| Model generation_config | `early_stopping=True`, `no_repeat_ngram_size=3`, `length_penalty=1.0` | same checkpoint |
| Post-process | `processor.post_process_generation` + `analyze_florence_visual_risk_outputs` | same functions |
| `local_files_only` | True, `HF_HUB_OFFLINE=1` | True, `HF_HUB_OFFLINE=1` |

Download: 13 files, 1,546,348,323 bytes, ~66 s. No other model was downloaded.

Parity deviations (disclosed):

1. No face detector was run (MediaPipe assets are a separate download), so
   `primary_face_bbox_xyxy=None`. This only moves OD persons between
   `person` and `background-person`; it does not enter the watermark policy.
2. Production passes the participant's source-photo Florence regions into the
   watermark policy (`compareSourceVisualRisk=True`). The avatar→source pairing
   could not be restored from metadata without reading files outside the
   authorized sets, so every condition is scored with no source regions
   (`sourceConsistency=not_available`). This can only remove the
   `source_consistent` allow path, i.e. the replay is at least as strict as
   production on the review branch.
3. CPU instead of GPU/CUDA kernels: numerics may differ slightly from the
   deployed runtime; decisions are not expected to change.

## 4. Method

Pre-registered before inference (`scripts/avatar_florence_ceiling.py`, plan
digest recorded in the local run metadata): variant table, curve design, curve
bases, `IOU_MATCH=0.3`, transcription normalisation (uppercase, keep `[A-Z0-9]`).

Domains, reported separately end to end:

* `SOURCE_PHOTO_DOMAIN` — 8 real source photos.
* `GENERATED_AVATAR_DOMAIN` — 20 real Azure G004 avatars.
* `PURE_SYNTHETIC_CONTROL_DOMAIN` — the 10 unchanged PR #114 controls.

Core variants (same specification on both real domains; `V*` on source, `A*` on avatar):

| Code | Construct | Text | Placement | Rel. size | Alpha | Ground-truth class |
|---|---|---|---|---|---|---|
| 0 | clean | – | – | – | – | none (unlabeled) |
| 1 | corner opaque watermark | SAMPLE | bottom-right corner | 0.035 | 1.0 | OVERLAY_WATERMARK |
| 2 | edge small watermark | PREVIEW | top edge | 0.022 | 1.0 | OVERLAY_WATERMARK |
| 3 | transparent watermark | DEMO | center | 0.12 | 0.35 | OVERLAY_WATERMARK |
| 4 | tiled repeated watermark | SAMPLE ×12 | 3×4 grid | 0.04 | 0.45 | OVERLAY_WATERMARK |
| 5 | center overlay text | PREVIEW | center | 0.07 | 0.85 | OVERLAY_TEXT |
| 6 | fragmented corner text | N E W | bottom-left corner | 0.035 | 1.0 | FRAGMENTED_OVERLAY_TEXT |
| 7 | fragmented center text | A 1 X | upper center | 0.05 | 1.0 | GENERATIVE_TEXT_ARTIFACT_PROXY |
| 8 | graphical logo-like mark | – | top-right corner | 0.08 | 0.9 | OVERLAY_LOGO |
| 9 | benign fragmented garment text | NO 23 ST | garment zone | 0.04 | 1.0 | BENIGN_FRAGMENTED_SCENE_TEXT |

Relative size is font height (logo diameter) / min(W, H). Variant 9 is added as
the benign-by-construction control H1 needs; variant 7 is the matching
risk proxy. They differ only in location, which is exactly the distinction H1
draws.

Curves (OCR only, matched design, 4 bases per real domain): per placement
(corner / edge / center), alpha 1.0 / 0.65 / 0.35 / 0.15 at medium size, and
size large / medium / small at alpha 1.0 — 18 conditions per base.

Execution: `FULL_MATRIX`. Derivatives are rendered in memory and never written
to disk; originals are opened read-only and fingerprinted before and after.

Metric vocabulary:

* Injected conditions: region recall (IoU ≥ 0.3 per ground-truth box), IoU,
  normalized exact match, CER, WER — model ceiling on a real background, not
  production prevalence.
* Clean images: `OBSERVED_RESPONSE_DISTRIBUTION` only. No precision, recall,
  hallucination or correctness claims (no human watermark/text/logo labels).
* MODEL MISS: Florence produced no evidence on the injected region (OCR, or OCR/OD for the logo).
  POLICY MISS: evidence present, action `allow`, on a risk-positive construct.

## 5. Inputs

| Domain | Count | Decodable | Formats | Dimensions | Bytes total | Exact duplicates |
|---|---|---|---|---|---|---|
| SOURCE_PHOTO_DOMAIN | 8 / 8 | 8 | 5 PNG, 3 JPG, RGB | 6 distinct, 1122–5712 px wide | 53,507,488 | 0 |
| GENERATED_AVATAR_DOMAIN | 20 / 20 | 20 | 20 PNG, RGB | all 1254×1254 | 32,739,206 | 0 |

Duplicate groups: source↔source 0, avatar↔avatar 0, source↔avatar 0. Effective
unique source 8, avatar 20. The 20 avatars are 5 groups × 4 candidates by
filename pattern (opaque group keys only).

Evaluated conditions (FULL_MATRIX, plan digest prefix `91e0caae719d`):

| | Source | Avatar | Pure synthetic |
|---|---|---|---|
| Raw clean | 8 | 20 | – |
| Core injected (9 variants) | 72 | 180 | – |
| Curves (OCR only) | 72 | 72 | – |
| PR #114 controls | – | – | 10 |
| Total | 152 | 272 | 10 |

## 6. Model ceiling — injected text regions

Image hit = at least one ground-truth box matched (IoU ≥ 0.3). Box recall counts
every ground-truth box (12 per tiled image).

| Variant | Source hit | Source box recall | Source mean / median IoU | Avatar hit | Avatar box recall | Avatar mean / median IoU | Δ box recall (avatar − source) |
|---|---|---|---|---|---|---|---|
| 1 corner opaque | 1.00 | 1.00 | 0.872 / 0.883 | 1.00 | 1.00 | 0.849 / 0.842 | 0.00 |
| 2 edge small | 1.00 | 1.00 | 0.840 / 0.842 | 1.00 | 1.00 | 0.819 / 0.808 | 0.00 |
| 3 transparent α0.35 | 0.75 | 0.75 | 0.635 / 0.866 | 0.95 | 0.95 | 0.841 / 0.885 | +0.20 |
| 4 tiled ×12 α0.45 | 1.00 | 0.948 | 0.770 / 0.821 | 1.00 | 0.888 | 0.702 / 0.823 | −0.06 |
| 5 center overlay text | 1.00 | 1.00 | 0.910 / 0.905 | 1.00 | 1.00 | 0.908 / 0.910 | 0.00 |
| 6 fragmented corner | 1.00 | 1.00 | 0.888 / 0.890 | 1.00 | 1.00 | 0.833 / 0.836 | 0.00 |
| 7 fragmented center | 0.875 | 0.875 | 0.719 / 0.818 | 1.00 | 1.00 | 0.783 / 0.770 | +0.125 |
| 8 graphical logo (OCR) | 0.00 | 0.00 | 0.000 / 0.000 | 0.25 | 0.25 | 0.233 / 0.000 | +0.25 |
| 9 benign garment fragments | 1.00 | 1.00 | 0.840 / 0.847 | 1.00 | 1.00 | 0.841 / 0.843 | 0.00 |

Domain gap: no construct is worse on generated avatars than on source photos
except tiled box recall (−0.06). Transparent text and the logo are *easier* on
the avatar background (flatter, cleaner). No MODEL_DOMAIN_SENSITIVITY that would
hide an overlay on the avatar domain. The avatar-domain numbers are the more
production-like ceiling.

## 7. Transcription (injected text only, normalized)

| Variant | Source exact | Source CER | Source WER | Avatar exact | Avatar CER | Avatar WER |
|---|---|---|---|---|---|---|
| 1 | 1.00 | 0.000 | – | 1.00 | 0.000 | – |
| 2 | 1.00 | 0.000 | – | 1.00 | 0.000 | – |
| 3 | 0.625 | 0.281 | – | 0.75 | 0.150 | – |
| 4 (per tile) | 0.667 | 0.116 | – | 0.563 | 0.188 | – |
| 5 | 1.00 | 0.000 | – | 1.00 | 0.000 | – |
| 6 `N E W` | 1.00 | 0.000 | **1.00** | 1.00 | 0.000 | **1.00** |
| 7 `A 1 X` | 0.75 | 0.167 | **1.00** | 0.85 | 0.050 | **1.00** |
| 9 `NO 23 ST` | 1.00 | 0.000 | 0.00 | 1.00 | 0.000 | 0.05 |

Characters are read almost perfectly, but spaced single glyphs (`N E W`,
`A 1 X`) come back merged into one word (WER 1.0 in 100% of those conditions,
one token per matched region). The live policy's fragmentation evidence
(`textQuality=implausible`) is therefore never produced for single-glyph
fragments, while multi-character fragments (`NO 23 ST`) keep their spaces. This
is a tokenization property of the OCR model, not a policy threshold.

## 8. Transparency / size / placement curves (box recall, 4 bases per domain)

| Placement | α 1.00 | α 0.65 | α 0.35 | α 0.15 | small | medium | large |
|---|---|---|---|---|---|---|---|
| Source corner | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Source edge | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Source center | 1.00 | 1.00 | 1.00 | 0.75 | 1.00 | 1.00 | 1.00 |
| Avatar corner | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Avatar edge | 1.00 | 1.00 | 1.00 | 0.75 | 1.00 | 1.00 | 1.00 |
| Avatar center | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

Alpha columns at medium size (0.04), size columns at α 1.0. Text with a thin
outline is found down to 2% of the short side and 15% opacity in all but one
of 4 bases per cell. (Unstroked 35%-opacity text — variant 3 — is the weakest
text construct.)

## 9. Repetition

Tiled variant: every image hit in both domains, box recall 0.948 / 0.888, and
the current policy **rejects 8/8 source and 20/20 avatar** tiled images
(repeated overlay-geometry evidence). The PR #114 tiled control (ctl-01), whose
tiles overlap into long merged strings, produces 7 regions with no two sharing
a token key, so it is **allowed**: repetition evidence depends on OCR returning
identical per-tile tokens.

## 10. Graphical logo-like mark

| Domain | n | OCR only | OD only | both | neither | OD logo/sign kind on the mark |
|---|---|---|---|---|---|---|
| Source | 8 | 0 | 0 | 0 | 8 | 0 |
| Avatar | 20 | 5 | 0 | 0 | 15 | 0 |

`<OD>` never localizes the mark; `<OCR_WITH_REGION>` sometimes reads a glyph on
it. The PR #114 graphical-logo control (ctl-08) is also missed (OCR reads one
glyph on the abstract head shape; OD labels the whole image `poster`).
Florence gives essentially no graphical-logo signal.

## 11. Pure synthetic controls (policy/model reachability)

| Control | OCR regions | Current | H1 |
|---|---|---|---|
| ctl-01 tiled watermark | 7 | allow | allow |
| ctl-02 corner watermark | 1 | allow | allow |
| ctl-03 edge watermark | 1 | allow | allow |
| ctl-04 transparent watermark | 1 | allow | allow |
| ctl-05 garment text | 1 | allow | allow |
| ctl-06 background signage | 1 | allow | allow |
| ctl-07 brand text | 1 | allow | allow |
| ctl-08 graphical logo | 1 (not on the mark) | allow | allow |
| ctl-09 no text | **1** | allow | allow |
| ctl-10 generative text artifact | 1 | **review** | **allow** |

No-text synthetic control: Florence returns one OCR region (a single glyph on
the abstract head ellipse). Because this control carries a construction label
of no text, that is a measured OCR hallucination (1/1). OD returns one region on
every control (`poster` ×7, `book`, `miniskirt`, `ball`).

## 12. Raw clean images — OBSERVED_RESPONSE_DISTRIBUTION (unlabeled)

| | Source (8) | Avatar (20) |
|---|---|---|
| OCR region count | 1 region: 7, 4+: 1 | 1 region: 20 |
| No-region rate | 0.00 | 0.00 |
| Multi-region rate | 0.125 | 0.00 |
| Overlay-like evidence rate | 0.625 | 0.75 |
| Repeated evidence rate | 0.00 | 0.00 |
| Fragmented evidence rate | 0.00 | 0.15 |
| Locations | edge 4, corner 3, clothing 3, central 2 | corner 12, edge 4, clothing 4 |
| Current action | allow 8 | allow 17, review 3 |
| H1 action | allow 8 | allow 17, review 3 |
| OD regions per image (mean) | 6.6 | 2.05 |

Every one of the 28 real images yields at least one OCR region. Without human
labels this is not called correct or incorrect; together with ctl-09 it shows
the OCR task effectively never returns "no text". The 3 avatar reviews are
fragmented reads in corner/edge overlay geometry and stay review under H1.

OD vocabulary (raw + core, label: count):

* Source: human face 80, person 62, television 28, woman 27, watermelon 20, mobile phone 19, human mouth 17, mirror 17, drinking straw 13, human eye 14, building 12, bracelet 10, coffee cup 10, lantern 10, man 9, desk 8, picture frame 7, fancy dress 5, human head 5, human nose 5, human ear 4, tablet computer 2, chair 1, flower 1, handbag 1, walking shoe 1.
* Avatar: human face 200, woman 80, man 60, boy 50, person 10, shirt 8.
* Person-related vocabulary actually emitted: `person`, `man`, `woman`, `boy`, `human face/head/eye/ear/mouth/nose`. `girl`, `people`, `crowd` were never emitted. Only labels containing `person` or `human` become person regions in the live parser; `man`/`woman`/`boy` do not.

## 13. Model miss vs policy miss (risk-positive injected conditions)

| Variant | Source model miss | Source policy miss (current / H1) | Avatar model miss | Avatar policy miss (current / H1) |
|---|---|---|---|---|
| 1 corner opaque | 0 | 8 / 8 | 0 | 20 / 20 |
| 2 edge small | 0 | 7 / 8 | 0 | 20 / 20 |
| 3 transparent | 2 | 6 / 6 | 1 | 19 / 19 |
| 4 tiled | 0 | 0 / 0 | 0 | 0 / 0 |
| 5 center overlay text | 0 | 8 / 8 | 0 | 20 / 20 |
| 6 fragmented corner | 0 | 8 / 8 | 0 | 20 / 20 |
| 7 fragmented center | 1 | 7 / 7 | 0 | 20 / 20 |
| 8 graphical logo | 8 | 0 / 0 | 15 | 5 / 5 |

For text overlays the loss is almost entirely POLICY MISS: Florence finds the
region, and the live policy allows it. A single, non-repeated overlay token is
`ambiguous_text_evidence → allow` because the only single-region reject/review
paths need `confidenceBand=high` (unreachable: the adapter emits no per-region
confidence) or `textQuality=implausible` (lost for single-glyph fragments, §7).
The graphical logo is a MODEL MISS.

## 14. Current policy vs H1 (injected sets)

| Metric | Source current | Source H1 | Avatar current | Avatar H1 |
|---|---|---|---|---|
| Risk-positive flagged (review/reject) | 9 / 64 (0.141) | 8 / 64 (0.125) | 22 / 160 (0.138) | 22 / 160 (0.138) |
| Benign fragmented garment text flagged | 8 / 8 | 0 / 8 | 19 / 20 | 0 / 20 |
| Overlay variants allowed (1–6, 8) | 47 / 56 | 48 / 56 | 118 / 140 | 118 / 140 |
| Generative-artifact proxy allowed (7) | 8 / 8 | 8 / 8 | 20 / 20 | 20 / 20 |
| Hard-reject bypass (reject → not reject) | 0 | – | 0 | – |

Transitions current → H1: source `review→allow` 9 (variant 9 ×8, variant 2 ×1),
avatar `review→allow` 19 (variant 9), everything else `same`.

The source variant-2 transition: the injected edge watermark was allowed by both
policies; the current `review` came from a separate fragmented scene-text region
in that photo (non-overlay geometry), which H1 drops. Under the pre-registered
metric it is still one more overlay-variant allow.

Pure synthetic: ctl-10 (generative text artifact in the garment zone)
`review → allow` — a real generative-artifact miss introduced by H1.

Clean 20 avatars (REAL_AVATAR_SHADOW_BEHAVIOR_DELTA): `same` 20/20
(allow→review 0, review→allow 0, reject→review 0, reject→allow 0).

G004_GROUP_LEVEL_SIMULATION (5 groups × 4, watermark action only): every group
has ≥2 watermark-allowed candidates under both policies; groups changed 0.

Production metadata replay (read-only, fresh 2026-09-11): 299 persisted
candidates / 62 jobs; 12 carry the current typed evidence schema. Evidence
replay parity mismatches 0; candidate action diff 0; jobs changed 0 with and
without soft review; newly eligible with reject reasons 0.

## 15. Latency and memory (LOCAL_CPU_BENCHMARK, i7-8550U 4C/8T, 16 GB, no GPU)

Warm-up condition excluded. Seconds per image.

| Domain | OCR mean / median / p90 | OD mean / median / p90 | Both tasks mean / median / p90 |
|---|---|---|---|
| Source | 20.5 / 15.8 / 29.8 (n=151) | 17.8 / 17.6 / 19.6 (n=79) | 38.1 / 33.8 / 48.4 (n=79) |
| Avatar | 17.3 / 15.9 / 19.8 (n=272) | 16.0 / 15.8 / 17.0 (n=200) | 33.7 / 32.1 / 39.8 (n=200) |
| Pure synthetic | 17.8 / 16.0 / 34.0 (n=10) | 15.3 / 15.2 / 16.1 (n=10) | 33.1 / 31.5 / 49.1 (n=10) |

Model load 13.8 s cold / 6.7 s warm. Peak RSS 4.51 GB (fp32 model ≈ 3.2 GB).
Derivatives are rendered in memory, so dataset size does not grow disk use;
restricted local artifacts total < 1 MB of JSON.

## 16. Verdicts

**Florence: `FLORENCE_CURRENT_MODEL_LIMITED_BUT_USABLE`.** On real generated-avatar
and source-photo backgrounds, Florence localizes injected overlay text at or near
ceiling — corner, edge, center, small (2% of the short side), transparent down to
α 0.15 with an outline, tiled — and reads it almost exactly. It is limited in
three measured ways: (1) graphical logo-like marks are essentially invisible
(0/8, 5/20, OD never), (2) spaced single-glyph fragments are merged into one
word, erasing the fragmentation evidence, (3) it returns an OCR region on every
image, including a no-text control. The text-overlay gap is a policy gap, not a
model gap; the logo gap is a model gap and needs its own benchmark.

**H1: `H1_SHADOW_NOT_SUPPORTED`.** H1 removes every benign fragmented garment-text
flag (8/8 and 19/20) with no change on the 20 clean avatars, the G004 groups or
production metadata, and no hard-reject bypass. But it fails two acceptance
items: the synthetic generative text artifact (ctl-10) goes review → allow, and
the source domain has one more overlay-variant allow (incidental, §14). Its
benefit also rests on a fragmentation signal Florence does not preserve for
single-glyph fragments. H1 stays shadow; `H1_LIVE_POLICY_READY` is not claimed.

## 17. Not established by this benchmark

Natural-occurrence production accuracy of any kind; what the OCR regions on the
28 clean images actually are (garment text, artifact, hallucination, watermark);
behaviour on real third-party watermarks or logos; GPU numerics.

## Reproduce (local only; never in CI)

```bash
python scripts/avatar_florence_ceiling_run.py --private-dir <restricted dir> --model-dir <florence2 snapshot @ 26b734a5>
python scripts/avatar_florence_ceiling_run.py --private-dir <restricted dir> --score-only --report-out <aggregate.json>
```

`<restricted dir>/restricted_manifest.json` holds the opaque-ID mapping and is
produced by a local inventory step that enforces 8 + 20 images. CI runs only
`tests/test_avatar_florence_ceiling.py` (generator, manifest, metrics, privacy,
H1 isolation, parser, domain aggregation).
