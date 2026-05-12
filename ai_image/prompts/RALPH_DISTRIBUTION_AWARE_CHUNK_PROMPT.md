$ralph "Run the next Seolleyeon distribution-aware Codex Image Gen chunk.

Use internal Image Gen only.
Do not use OpenAI Image API.
Do not use Batch API.
Do not require OPENAI_API_KEY.
Do not modify SVD/KNN/CLIP/RRF recommender scripts.

Brand and safety contract:
- Seolleyeon is a university-only, trust-based relationship platform.
- It is not a lightweight dating app.
- These are synthetic profile assets for cold-start preference learning.
- Images must look like realistic adult Korean university student profile photos.
- Images must support Quiet Romance / Clear Trust.
- Images must not feel like dating-app face-rating game assets.

Hard reject and stop for QA if an image shows:
- appears under 20
- childlike or teenager-like
- school uniform
- idol trainee styling
- celebrity lookalike
- influencer photoshoot
- glamour studio lighting
- nightclub / party / neon / bar / luxury hotel mood
- sexualized styling
- revealing outfit / swimsuit / lingerie
- heavy beauty filter
- plastic skin
- distorted face
- distorted hands / fingers / arms / legs / body
- unrealistic body proportions
- visible school logo
- readable university name
- brand logo
- watermark
- generated text inside image
- image feels like a dating-app face-rating game asset

Goal for this run:
Generate at most 24 incomplete identities × 3 shots = 72 images maximum.

Overall final target:
- 240 approved complete identities
- 720 approved images
- 120 female approved complete identities
- 120 male approved complete identities
- exact faceType distribution
- exact looksLevelBand distribution

Before generating:
1. Recover any pending Image Gen result.
2. Run file QA for recovered assets.
3. If ai_image/manifests/manual_review_required.flag exists, stop for manual review.
4. If completion check already passes, stop.
5. Read:
   - ai_image/config/AI_IMAGE_DISTRIBUTION_TARGETS_V3.json
   - ai_image/reports/latest_distribution_audit.json
   - ai_image/manifests/approved_identity_manifest.jsonl
   - ai_image/manifests/identity_qa_manifest.jsonl
   - ai_image/manifests/imagegen_queue.jsonl
6. Compute remaining deficits by:
   - gender
   - faceType
   - looksLevelBand
   - genderFaceType
   - genderLooksLevelBand
7. Run mingw32-make ai-image-next-distribution-chunk or the equivalent distribution-aware selector script to prepare the next chunk.

Image Gen identity and checkpoint rules:
- Treat Image Gen as interruptible.
- Before every Image Gen call, write ai_image/manifests/pending-imagegen.json.
- Use pending-imagegen.json as the sole asset identity source. Do not infer identity from the generated image.
- Invoke $imagegen only for the selected distribution-aware prompt. Do not invent extra prompts.
- After every Image Gen result, recover/import the generated image before any further generation, QA, or audit step.
- If recovery/import cannot be confirmed in the same run, stop so the next run can recover the pending result first.

Generation selection rules:
- Select only identities whose gender + faceType + looksLevelBand are currently under quota.
- Do not generate quota-full buckets.
- Do not generate looksLevelBand 4.4-5.0.
- Prefer buckets with largest combined deficit.
- If visual-verdict previously found metadata mismatch for a bucket, reduce priority for that bucket until prompt is improved.
- Use reserve identities only for deficit buckets.
- Do not overwrite approved images.

For each selected identity:
1. Generate face_card first.
2. Checkpoint before Image Gen.
3. Recover/import after Image Gen.
4. Generate silhouette_card using face_card as same-person reference when supported.
5. Checkpoint and recover.
6. Generate vibe_card using face_card as same-person reference when supported.
7. Checkpoint and recover.

After generation:
- Run file QA.
- Create contact sheets:
  - identity-level sheets
  - gender + shotType sheets
  - chunk overview sheet
- Prepare visual-verdict instructions for:
  - asset QA
  - identity QA
  - distribution audit
- Run visual-verdict asset QA, identity QA, and distribution audit with strict JSON only.
- If visual-verdict is unavailable, invalid, cannot return strict JSON, or cannot be applied, write ai_image/manifests/manual_review_required.flag and stop.
- Apply visual-verdict output to manifests only after strict JSON schema validation succeeds.
- Run numeric distribution audit.
- Update latest_distribution_audit.json.
- Summarize progress.
- Stop after this chunk.

Do not continue to another chunk in the same run.
If manual review is required, write ai_image/manifests/manual_review_required.flag and stop.

Quality rules:
- Approved images must look like realistic adult Korean university student profile photos.
- Keep the mood calm, sincere, campus-based, and appropriate for a trust-based platform.
- Do not create influencer, idol, celebrity-like, glamour studio, nightlife, or dating-app face-rating content.
- Reject or retry under-20, childlike, school uniform, sexualized styling, logos, readable text, watermarks, distorted anatomy, plastic skin, or heavy filter results."
