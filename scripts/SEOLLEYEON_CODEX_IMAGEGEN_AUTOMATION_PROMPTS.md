# Seolleyeon Codex Image Gen Automation Prompts v3

## 1. Codex implementation prompt

```text
Use the seolleyeon-ai-profile-imagegen workflow.

Implement unattended automation for Seolleyeon Codex internal Image Gen production.

Critical change:
A single Ralph full-production prompt is not reliable enough for 720 images. Implement a supervisor-driven automation system that can run chunk mode for 10 chunks without user intervention, verify whether it succeeded, and automatically fall back to identity-tick or asset-tick mode if chunk mode fails.

Generation mode:
- Internal Codex Image Gen only.
- Do not use OpenAI Image API.
- Do not use Batch API.
- Do not require OPENAI_API_KEY for image generation.
- Do not modify SVD/KNN/CLIP/RRF recommender scripts.

Final target:
- 240 approved complete identities.
- 720 approved images.
- 120 female approved complete identities.
- 120 male approved complete identities.
- exact faceType distribution.
- exact looksLevelBand distribution.

Implement:
1. scripts/codex_imagegen_supervisor_v3.sh
2. Makefile target: ai-image-supervisor-720
3. Makefile target: ai-image-supervisor-chunk-only
4. Makefile target: ai-image-supervisor-identity-only
5. Makefile target: ai-image-supervisor-asset-only
6. ai_image/reports/chunk_unattended_verification.txt output

Supervisor behavior:
- MODE=auto by default.
- First try chunk mode.
- A chunk is at most 24 identities × 3 shots = 72 images.
- Required unattended chunk verification: 10 successful chunks without manual stop patterns.
- If 10 chunk runs succeed, write `chunk_unattended_verification=PASS` to ai_image/reports/chunk_unattended_verification.txt.
- If a chunk fails, shows no progress, triggers manual review, detects Image Gen unavailable, or hits quota/rate/usage limit, fall back to identity mode.
- Identity mode processes exactly one identity × 3 shots per OMX run.
- If identity mode fails, fall back to asset mode.
- Asset mode processes exactly one asset/Image Gen per OMX run.

Before every run:
- completion check.
- manual_review_required.flag check.
- pending Image Gen recovery.
- file QA.
- distribution audit.

After every run:
- pending Image Gen recovery.
- file QA.
- contact sheet generation.
- distribution audit.
- summary.
- stop if target complete.

Stop patterns:
Stop or fall back if the log contains:
- manual review
- approval required
- awaiting user
- please confirm
- Image Gen unavailable
- imagegen unavailable
- quota
- usage limit
- rate limit
- cannot continue
- fatal
- permission denied

Chunk prompt requirements:
- Run only one bounded chunk.
- Do not continue to another chunk in the same Ralph run.
- Generate only deficit buckets.
- Do not generate quota-full buckets.
- Do not generate looksLevelBand 4.4-5.0.
- Generate face_card first.
- Generate silhouette_card and vibe_card using face_card as same-person reference when supported.
- Checkpoint before and after every Image Gen.
- Apply visual-verdict QA when available.
- If visual-verdict and numeric audit disagree, write manual_review_required.flag.

Acceptance:
- `MODE=chunk MAX_CHUNKS=1 bash scripts/codex_imagegen_supervisor_v3.sh` runs one bounded chunk.
- `MODE=auto REQUIRED_UNATTENDED_CHUNKS=10 bash scripts/codex_imagegen_supervisor_v3.sh` verifies 10 chunk runs or falls back.
- Completion check passes only when exact distribution and 720 approved assets are complete.
- No recommender scripts are modified.
```

## 2. Supervisor run prompt template

The shell supervisor embeds bounded chunk, identity, and asset prompts. Use `scripts/codex_imagegen_supervisor_v3.sh` as the source of truth for the exact prompts.
