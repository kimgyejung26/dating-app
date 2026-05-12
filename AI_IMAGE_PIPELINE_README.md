# Seolleyeon AI Image Pipeline v3

Production pipeline for Seolleyeon's synthetic cold-start preference-learning profile assets.

## Contract

See `AI_IMAGE_QUALITY_CONTRACT.md` for the locked quality contract. The key interpretation is:

- **720 final approved images = 240 complete approved identities × 3 shots**.
- Final approved split: **120 female identities** and **120 male identities**.
- Reserves exist so raw attempts may exceed 720.
- Full default manifest scope: 240 primary identities + 40 reserve identities = 840 prepared asset rows.

## Source And Output

- Prompt source: `lib/ai_recommend_model/seolleyeon_ai_profile_prompt_v3_package/seolleyeon_ai_profile_prompt_v3.py`
- Pipeline code: `scripts/ai_image_pipeline_v3/`
- Raw attempt images: `ai_image/raw/{assetId}__attemptXX.png`
- Final approved images: `ai_image/{gender}/{numeric_id}/{shotType}.png`
- Approved review copies: `ai_image/approved/{assetId}.png`
- Rejected attempts: `ai_image/rejected/{assetId}__attemptXX.png`
- State/manifests: `ai_image/manifests/`
- Reports: `ai_image/reports/`

## Generation Mode

```text
Codex built-in $imagegen only
No OpenAI Image API
No Batch API
No OPENAI_API_KEY required for image generation
```

Dependent shots wait for an approved `face_card`, then use that face image as the same-person reference. If the Codex `$imagegen` surface cannot use the reference image, stop and report `reference_blocked`; do not silently fall back to text-only independent generation.

## Main Commands

```bash
mingw32-make ai-image-dry-run
mingw32-make ai-image-prepare-smoke
mingw32-make ai-image-prepare-pilot
mingw32-make ai-image-prepare-720
mingw32-make ai-image-next
mingw32-make ai-image-recover
mingw32-make ai-image-qa
mingw32-make ai-image-retry
mingw32-make ai-image-summary
mingw32-make ai-image-contact-sheets
```

Equivalent Python entrypoints for the interruptible generation loop:

```bash
python scripts/prepare_ai_image_assets_v3.py --female_count 120 --male_count 120 --reserve_female_count 20 --reserve_male_count 20
python scripts/next_codex_imagegen_prompt_v3.py
# run the printed $imagegen prompt in Codex
python scripts/recover_pending_imagegen_v3.py
```

## Stages

- Dry-run: 3 assets, no API calls and no `$imagegen` calls.
- Smoke: 3 identities × 3 shots = 9 images.
- Pilot: 24 identities × 3 shots = 72 images.
- Full: stop only when 240 identities / 720 assets are approved.

Full mode remains gated until real smoke and pilot gates pass.

## QA Outputs

The pipeline writes strict JSONL and CSV reports:

```text
ai_image/reports/qa_report.csv
ai_image/reports/shot_type_qa_report.jsonl
ai_image/reports/vision_qa_report.jsonl
ai_image/reports/vision_qa_report.csv
ai_image/reports/identity_consistency_report.jsonl
ai_image/reports/identity_consistency_report.csv
ai_image/reports/duplicate_similarity_report.csv
ai_image/reports/distribution_report.csv
ai_image/reports/contact_sheets/pilot_contact_sheet_*.png
ai_image/reports/contact_sheets/full_contact_sheet_*.png
ai_image/reports/summary.json
```

## Reserve / Retry Behavior

- Primary identities are active by default.
- Reserve identities are written as `identityScope=reserve`, `isReserve=true`, `reserveStatus=standby`, `activeForTarget=false`.
- If an active identity exhausts `--max_attempts`, the complete identity is rejected and the next standby reserve from the same gender bucket is activated.
- Approved files are never overwritten unless `--force` is explicitly passed.

## Safety

- Do not hardcode API keys.
- Do not call OpenAI Image API or Batch API.
- Do not modify recommender, SVD, KNN, CLIP, or RRF scripts.
- Keep all generated state under `ai_image/manifests` and all reports under `ai_image/reports`.
