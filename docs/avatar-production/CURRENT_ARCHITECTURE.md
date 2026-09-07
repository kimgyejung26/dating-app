# Avatar generation: current architecture

This file is the current repository authority as of 2026-09-07. Older dated,
PR-numbered, migration, audit, and incident documents are historical evidence;
they are not deployment instructions when they conflict with this file.

## Retired

- Local-model avatar image generation and every provider fallback to it
- Local-model worker/deployment modes and model downloads
- Single-photo avatar-generation admission
- The separately gated Phase 3 orchestrator/runtime experiment

Unsupported worker/provider configuration fails closed. It is never silently
translated to the canonical provider.

## Canonical flow

Flutter uploads 2–6 onboarding photos individually and receives opaque,
server-issued source references. Pressing Next calls only
`beginAvatarGenerationFromOnboardingPhotos`. The server validates the complete
set and creates one logical selection job. The user immediately continues the
remaining onboarding steps; avatar generation is not a blocking screen.

The worker hard-gates each normalized original for exactly one primary face,
ranks eligible originals deterministically, transactionally locks the best
original-direct source, and only then calls Azure GPT Image 2. Candidate QA and
preview selection follow. Every candidate uses the same selected source. Azure
input is the selected normalized original, not a face crop.

Generation policy is `initial=2`, `extra=2`, `max=4`, with
`minSafeBeforeExtra=2`, `minPreview=1`, `previewCount=2`, and
`requireFour=false`. The production router owns five explicit endpoint slots
(EP1–EP5); their mapping is authoritative and is not a release blocker. Router
reservation, redaction, cooldown, capacity, and fail-closed behavior are covered
by contract tests.

When the active job reaches preview-ready during onboarding, one global
three-second banner is shown for that job:

> 아바타 생성이 완료되었어요! 프로필 가입 마지막 화면에서 아바타 사진을 선택할 수 있어요

The final onboarding step reads the job-scoped candidate set and requires the
user to choose an avatar. A persisted `bannerShownForJobId` guard prevents the
same completion from being announced repeatedly.

## Time budget

Azure transport timeout is 240 seconds per provider call and the maximum
candidate count is four. The conservative provider budget is therefore
`240 × 4 + 360 = 1320` seconds. Worker request and job defaults are 1500
seconds, leaving a 180-second internal margin while staying below the 1800-second
Cloud Run request timeout. Deployment configuration may tighten these values
but must not silently reduce them below the validated provider budget.

## Dependency ownership

| Dependency/runtime | Legacy generation only | Current consumer | Decision |
| --- | --- | --- | --- |
| Diffusers image pipeline | yes | none | removed |
| Local image checkpoint/tokenizer | yes | none | removed |
| Torch/CUDA runtime | no | QA, CLIP, similarity | preserved |
| Transformers/Hugging Face Hub | no | pinned Florence and CLIP QA assets | preserved |
| MediaPipe and OpenCV | no | source selector and face-quality gates | preserved |
| HTTP client and Pillow | no | Azure transport and response normalization | preserved |

CLIP recommendation is a separate consent-controlled pipeline and is not a
generation fallback. The retired single-photo callable is not registered. Its
factory remains only as a side-effect-free tombstone that immediately returns
`avatar_single_photo_generation_retired`; it cannot be enabled by
configuration and cannot write Storage, Firestore, Tasks, or call Azure.

## Release safety

Run `scripts/staging_avatar_live_preflight.py` before any deployment. It checks
the canonical source-set export, Azure-only worker mode, 2/2/4 policy, selector
files, detector assets declared in the container, Azure quota/provider modules,
and absence of the retired generation dependency.

Build the worker once, deploy the candidate revision with zero traffic, verify
`/readyz`, and only then move traffic. Readiness verification must make zero
Azure image-generation calls. Real client E2E requires separate test-account,
Auth, App Check, consent, and paid-call authority.
