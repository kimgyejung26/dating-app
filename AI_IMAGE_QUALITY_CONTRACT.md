# Seolleyeon AI Image Quality Contract

This is the locked acceptance contract for Seolleyeon synthetic AI profile images. The images are cold-start preference-learning assets for a university-only, trust-based relationship platform. They are not dating-game cards, decorative avatars, influencer content, or face-rating material.

## Final Target

- Final approved output: **720 approved assets**.
- Identity interpretation: **240 complete approved identities × 3 shots**.
- Gender split: **120 female approved identities** and **120 male approved identities**.
- Every approved identity must include:
  - `face_card`
  - `silhouette_card`
  - `vibe_card`

Do **not** interpret the run as “generate exactly 720 raw images.” Raw attempts may exceed 720 because failed identities are retried or replaced by reserves. The acceptance target is 240 complete approved identity groups.

## Generation Mode

Current mode: **Codex built-in `$imagegen` only**.

Hard rules:

- Do not call OpenAI Image API.
- Do not create Batch API JSONL.
- Do not require `OPENAI_API_KEY` for image generation.
- Treat `$imagegen` as interruptible.
- Before every `$imagegen` call, write `ai_image/manifests/pending-imagegen.json`.
- After every `$imagegen` result, the next turn must first run pending recovery/import.
- Asset identity is determined by `pending-imagegen.json`, not by visual guesswork.

## Source Of Truth

- Prompt and metadata source: `lib/ai_recommend_model/seolleyeon_ai_profile_prompt_v3_package/seolleyeon_ai_profile_prompt_v3.py`
- Pipeline code: `scripts/ai_image_pipeline_v3/`
- Prompt queue: `ai_image/manifests/imagegen_queue.jsonl`
- Pending checkpoint: `ai_image/manifests/pending-imagegen.json`
- Raw generated attempt files: `ai_image/raw/{assetId}__attemptXX.png`
- Final candidate/approved files: `ai_image/{gender}/{numericId}/{shotType}.png`
- Approved review copies: `ai_image/approved/{assetId}.png`
- Rejected attempt copies: `ai_image/rejected/{assetId}__attemptXX.png`
- Manifests/state: `ai_image/manifests/`
- Reports: `ai_image/reports/`

## Two-Pass Reference Pipeline

1. Prepare identity metadata and prompts from the prompt source.
2. Generate active `face_card` images first from text prompts.
3. Run QA on each recovered `face_card`.
4. Generate `silhouette_card` and `vibe_card` only after the identity has an approved `face_card`.
5. For dependent shots, include the approved `face_card` path in `pending-imagegen.json` and in the printed prompt instructions.
6. If the Codex `$imagegen` surface cannot use the reference image, stop with `reference_blocked`; do not silently generate independent text-only dependent shots.
7. Skip already approved assets unless `--force` is explicitly passed.

## Reserve Identity Policy

Default full scope:

- Primary identities: 240
  - Female primary: 120
  - Male primary: 120
- Reserve identities: 40
  - Female reserve: 20
  - Male reserve: 20

If any active identity fails after `--max_attempts` (default `3`), reject the complete identity group and activate the next standby reserve identity from the same gender bucket. Activated reserve identities may count toward the final 120/120 approved identity split after all three shots are approved.

## Distribution Counting Contract

Distribution targets are stored in `ai_image/config/AI_IMAGE_DISTRIBUTION_TARGETS_V3.json`.

Rules:

- Count at identity level, not image level.
- Count only identities whose `face_card`, `silhouette_card`, and `vibe_card` are all approved.
- Do not count `needs_review` identities.
- Do not count rejected identities.
- Do not count metadata mismatch identities.
- Do not count `targetLooksLevelBand` `4.4-5.0`; approved output in this band fails the audit.
- Final approval requires exact counts for total identities, total images, gender, `targetFaceType`, and `targetLooksLevelBand`.

## Hard Reject Rules

Reject or retry any asset with:

- appears under 20
- childlike appearance
- teenager look
- school uniform
- idol styling or idol trainee styling
- celebrity lookalike styling
- influencer photoshoot
- glamour studio lighting
- sexualized styling
- revealing outfit
- swimsuit / lingerie
- nightlife / club / neon scene
- bar / party / luxury hotel mood
- readable school name
- readable university name
- visible logo / watermark
- brand logo
- generated text inside image
- distorted face / hands / body
- distorted fingers / arms / legs
- unrealistic body proportions
- plastic skin / heavy beauty filter
- dating-app face-rating game asset tone

Additional reject examples: celebrity lookalike styling, swimsuit, lingerie, party pose, luxury hotel background, brand text, personal text, extra fingers, or unrealistic proportions.

## Looks Level Rubric

- `1.5-2.4`: ordinary natural real student look, mild asymmetry acceptable, not highly polished.
- `2.5-3.2`: neat and likable, everyday realistic, natural grooming.
- `3.3-3.8`: clearly attractive but realistic, balanced features, clean grooming, not influencer-like.
- `3.9-4.3`: noticeably attractive but still plausible as a real university student; must not be celebrity/model-like.
- `4.4-5.0`: too idealized, celebrity/model/idol/influencer-level, over-polished; reject or mark `over_level`. Final approved count must be zero.

## Face Type Descriptor Contract

`faceType` descriptors may guide prompt diversity, but they must stay grounded in realistic adult Korean university student portraits. Use them as subtle facial-impression cues, never as literal animal features, caricature, cosplay, or childlike styling.

cat_like:
- almond-shaped eyes
- slightly lifted outer eye corners
- composed or chic expression
- sharper but not harsh facial impression
- moderate-to-defined jawline

dog_like:
- rounder eyes
- soft cheeks
- gentle, approachable expression
- warm smile or friendly resting face
- softer jawline

hamster_like:
- compact rounded face
- fuller cheeks
- smaller soft nose impression
- cute-warm but still adult
- must not look childlike

bear_like:
- stable, warm, grounded impression
- broader facial structure
- thicker natural brows
- calm and reliable mood
- soft but sturdy presence

fox_like:
- slightly narrow or elongated eyes
- refined nose bridge
- elongated or slim face line
- subtle chic expression
- elegant but not celebrity-like

deer_like:
- soft oval face
- medium-large calm eyes
- gentle, quiet expression
- delicate jawline
- calm intellectual or sincere mood

horse_like:
- longer face proportion
- higher nose bridge
- more defined cheekbones
- elegant mature impression
- must be described as mature/elegant, never caricatured

mixed_neutral:
- no single animal-like faceType strongly dominates
- balanced everyday impression
- natural real student profile look

## Vision QA JSONL Contract

`ai_image/reports/vision_qa_report.jsonl` must contain strict JSONL rows with:

- `assetId`
- `profileId`
- `shotType`
- `adultVisual`
- `photoRealism` 0-5
- `campusRealism` 0-5
- `brandFit` 0-5
- `influencerRisk` 0-5
- `childlikeRisk` 0-5
- `schoolUniformRisk` 0-5
- `sexualizationRisk` 0-5
- `artifactRisk` 0-5
- `shotTypeReadable`
- `decision`: `approved` | `needs_review` | `rejected`
- `reasons`

Auto-reject if:

- `adultVisual` is false
- `childlikeRisk >= 2`
- `schoolUniformRisk >= 1`
- `sexualizationRisk >= 1`
- `artifactRisk >= 3`
- `photoRealism < 4`
- `brandFit < 4`
- `shotTypeReadable` is false

## Identity Consistency JSONL Contract

`ai_image/reports/identity_consistency_report.jsonl` must contain strict JSONL rows with:

- `profileId`
- `faceAssetId`
- `silhouetteAssetId`
- `vibeAssetId`
- `faceToSilhouetteConsistency` 0-5
- `faceToVibeConsistency` 0-5
- `completeIdentityDecision`: `approved` | `needs_retry` | `rejected`
- `failedShotTypes`
- `reasons`

## Reports

The pipeline writes:

- `ai_image/manifests/identity_manifest.jsonl`
- `ai_image/manifests/imagegen_queue.jsonl`
- `ai_image/manifests/pending-imagegen.json`
- `ai_image/manifests/generation_manifest.jsonl`
- `ai_image/manifests/qa_manifest.jsonl`
- `ai_image/manifests/retry_manifest.jsonl`
- `ai_image/reports/generation_status.csv`
- `ai_image/reports/qa_report.csv`
- `ai_image/reports/vision_qa_report.jsonl`
- `ai_image/reports/identity_consistency_report.jsonl`
- `ai_image/reports/duplicate_similarity_report.csv`
- `ai_image/reports/distribution_report.csv`
- `ai_image/reports/contact_sheets/pilot_contact_sheet_*.png`
- `ai_image/reports/contact_sheets/full_contact_sheet_*.png`
- `ai_image/reports/summary.json`

## Staged Execution

- Dry-run: prepare/check manifests only, no API calls and no `$imagegen` calls.
- Smoke: 3 identities × 3 shots = 9 images.
- Pilot: 24 identities × 3 shots = 72 images.
- Full: target 240 approved identities = 720 approved images.

The full run is resumable and gated. It skips approved assets, retries rejected/missing assets only, never overwrites approved files unless `--force` is passed, stores state in `ai_image/manifests`, and writes reports to `ai_image/reports`.

## Local Review Loop

`mingw32-make ai-image-qa` runs file QA, shotType structural QA, and local duplicate QA. Duplicate QA uses exact hashes and pHash locally, with CLIP similarity left optional when a local CLIP stack is available. `mingw32-make ai-image-contact-sheets` creates grouped contact sheets for visual-verdict review.
