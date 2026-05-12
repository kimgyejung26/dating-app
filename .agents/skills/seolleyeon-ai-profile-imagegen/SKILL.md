---
name: seolleyeon-ai-profile-imagegen
description: Build, run, QA, retry, summarize, and upload Seolleyeon AI profile image generation workflows for metadata-first synthetic campus profile assets. Use when working on ai_image outputs, seolleyeon_ai_profile_prompt_v3.py, the v3 image pipeline scripts, dry-run/smoke/pilot/full image batches, Firebase upload, or QA rules for realistic adult Korean university student profile photos.
---

# Seolleyeon AI Profile Imagegen

## Overview

Use this skill to maintain and run the Seolleyeon AI profile image pipeline. The pipeline creates synthetic profile assets for cold-start preference learning on a university-only trust-based relationship platform.

## Non-Negotiables

- Treat images as trust-building campus relationship assets, not lightweight dating-app cards.
- Use `lib/ai_recommend_model/seolleyeon_ai_profile_prompt_v3_package/seolleyeon_ai_profile_prompt_v3.py` as the source of metadata-first prompts.
- Do not rewrite the prompt builder.
- Do not modify recommender scripts, SVD/KNN/CLIP/RRF files, or unrelated app code.
- Do not hardcode API keys.
- Do not call the OpenAI Image API, Batch API, `/v1/images/generations`, or `/v1/images/edits`.
- Do not require `OPENAI_API_KEY` for image generation.
- Keep pipeline code modular; do not place the workflow into one large script.
- Keep all scripts resumable.
- Never overwrite completed or approved images unless `--force` is passed.

## Image Policy

Approved images must look like realistic adult Korean university student profile photos. They should feel calm, sincere, safe, campus-based, and naturally photographed.

Reject or retry any image with childlike appearance, teenager look, school uniform, idol trainee styling, influencer photoshoot tone, celebrity lookalike styling, sexualized styling, nightclub/party/neon scene, readable school name, logo, watermark, brand text, heavy retouching, plastic skin, distorted hands, distorted face, distorted body, extra fingers, or unrealistic proportions.

## Pipeline Shape

Use this sequence:

1. Prepare metadata and prompts.
2. Generate `face_card` first.
3. Generate `silhouette_card` and `vibe_card` as same-person reference variations using the completed `face_card` when possible.
4. Before every `$imagegen` call, write `ai_image/manifests/pending-imagegen.json`.
5. Recover generated outputs from Codex generated images into `ai_image/raw/{assetId}__attemptXX.png`.
6. Copy the final candidate to `ai_image/{gender}/{numeric_id}/{shotType}.png`.
7. Run QA, then copy approved review assets to `ai_image/approved/{assetId}.png` or rejected attempts to `ai_image/rejected/{assetId}__attemptXX.png`.
8. Retry failed, missing, reference-waiting, or rejected assets.
9. Summarize status and upload final assets when requested.

## Required Files

Maintain these entrypoint scripts:

- `scripts/prepare_ai_image_assets_v3.py`
- `scripts/next_codex_imagegen_prompt_v3.py`
- `scripts/import_codex_generated_image_v3.py`
- `scripts/recover_pending_imagegen_v3.py`
- `scripts/retry_ai_images_v3.py`
- `scripts/qa_ai_images_v3.py`
- `scripts/summarize_ai_images_v3.py`
- `scripts/make_ai_image_contact_sheets_v3.py`

Maintain these outputs:

- `ai_image/manifests/ai_profile_assets_v3.jsonl`
- `ai_image/manifests/generation_manifest.jsonl`
- `ai_image/reports/generation_status.csv`
- `ai_image/reports/qa_report.csv`
- `ai_image/reports/summary.json`

## Batch Sizes

- Dry-run: 3 assets, no API calls and no `$imagegen` calls.
- Smoke: 9 images = 3 identities x 3 shots.
- Pilot: 72 images = 24 identities x 3 shots.
- Full: 720 images = 240 identities x 3 shots.
- Default full split: 120 female identities and 120 male identities.

## Commands

Use `mingw32-make ai-image-dry-run` to verify folders, manifests, and CSV output without calling `$imagegen`.

Use `mingw32-make ai-image-prepare-smoke`, `mingw32-make ai-image-prepare-pilot`, and `mingw32-make ai-image-prepare-720` to prepare increasing Codex `$imagegen` queues. Real generation is an interruptible `mingw32-make ai-image-next` / `$imagegen` / `mingw32-make ai-image-recover` loop and does not require `OPENAI_API_KEY`.

Use `mingw32-make ai-image-qa`, `mingw32-make ai-image-retry`, and `mingw32-make ai-image-summary` for operational follow-up.

## Completion Checks

Before claiming completion, run dry-run, check that manifests and `generation_status.csv` exist, and confirm no recommender files changed.
