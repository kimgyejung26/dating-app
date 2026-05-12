# Seolleyeon AI Image Generation Rules

## Product Identity

Seolleyeon is a university-only, trust-based relationship platform. Treat AI profile images as synthetic cold-start preference-learning assets, not dating-game cards, decorative avatars, influencer content, or face-rating material.

## Required Workflow

- Use `lib/ai_recommend_model/seolleyeon_ai_profile_prompt_v3_package/seolleyeon_ai_profile_prompt_v3.py` as the prompt and metadata source.
- Do not rewrite the prompt builder.
- Do not modify recommender scripts unless explicitly requested.
- Keep image pipeline code modular under `scripts/ai_image_pipeline_v3/`.
- Generate `face_card` before `silhouette_card` and `vibe_card`.
- Use the completed `face_card` as the same-person reference for the other shots when possible.
- Save raw generated images under `ai_image/raw/`.
- Save final approved images under `ai_image/{gender}/{numeric_id}/{shotType}.png`.
- Save approved review copies under `ai_image/approved/{assetId}.png`.
- Save rejected attempts under `ai_image/rejected/{assetId}__attemptXX.png`.
- Write `ai_image/manifests/generation_manifest.jsonl`.
- Write `ai_image/reports/generation_status.csv`.
- Keep every script resumable.
- Never overwrite completed or approved images unless `--force` is passed.
- Do not hardcode API keys.

## Image generation mode

Current mode: Codex built-in imagegen only.

Rules:
- Do not call OpenAI Image API.
- Do not create Batch API JSONL.
- Do not require OPENAI_API_KEY for image generation.
- Use `$imagegen` for image creation.
- Treat `$imagegen` as interruptible.
- Always checkpoint before image generation.
- Always recover generated images from Codex generated image output before continuing.
- All images must end up under `ai_image/`.
- Asset identity is determined by `pending-imagegen.json`, not by visual guesswork.

## Default Run Sizes

- Dry-run: 3 assets, no API calls and no `$imagegen` calls.
- Smoke: 9 images = 3 identities x 3 shots.
- Pilot: 72 images = 24 identities x 3 shots.
- Full: 720 images = 240 identities x 3 shots.
- Default full split: 120 female identities and 120 male identities.

## Image Quality Rules

Every approved image must feel like a realistic adult Korean university student profile photo with Seolleyeon's calm, sincere, campus-based trust tone.

Reject or retry images with:

- Childlike appearance or teenager look.
- School uniform.
- Idol trainee styling.
- Influencer photoshoot or celebrity lookalike styling.
- Sexualized styling, revealing outfit, swimsuit, lingerie, or nightlife pose.
- Nightclub, party, neon scene, luxury hotel background.
- Readable school name, logo, watermark, brand text, or personal text.
- Heavy retouching, plastic skin, exaggerated beauty filters.
- Distorted hands, face, body, extra fingers, or unrealistic proportions.

## Review Guardrails

If a future request requires broad unrelated changes, ask before proceeding. Keep recommender files, SVD/KNN/CLIP/RRF logic, and existing app features outside the image pipeline untouched.
