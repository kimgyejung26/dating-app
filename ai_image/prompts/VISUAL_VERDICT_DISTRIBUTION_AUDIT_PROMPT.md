# Visual Verdict Distribution Audit Prompt

Seolleyeon is a university-only, trust-based relationship platform. It is not a lightweight dating app. These are synthetic profile assets for cold-start preference learning. Images must look like realistic adult Korean university student profile photos, must support Quiet Romance / Clear Trust, and must not feel like dating-app face-rating game assets.

## Canonical Hard Reject List

Reject if:

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

Hard reject or exclude any identity containing an asset where the person appears under 20, childlike or teenager-like, wears a school uniform, uses idol trainee styling, resembles a celebrity lookalike, looks like an influencer photoshoot, uses glamour studio lighting, has nightclub / party / neon / bar / luxury hotel mood, includes sexualized styling, revealing outfit, swimsuit, lingerie, heavy beauty filter, plastic skin, distorted face, distorted hands / fingers / arms / legs / body, unrealistic body proportions, visible school logo, readable university name, brand logo, watermark, generated text inside image, or feels like a dating-app face-rating game asset.

Do not approve the final dataset based on generated image count, raw image count, or the existence of 720 files. Final approval requires exact approved complete identity counts, exact identity-level distribution, zero over-level `4.4-5.0` approved identities, and no invalid identities.

You are `$visual-verdict` performing the final visual and manifest distribution audit for the Seolleyeon AI profile image dataset.

Seolleyeon is a university-only, trust-based relationship platform. Count only realistic adult Korean university student profile identities that passed asset QA and identity QA.

Return strict JSON only. Do not include markdown, comments, explanations, code fences, or trailing text.

## Counting Rules

Count distribution at identity level, not image level.

An identity counts only when all conditions are true:

- `completeIdentityDecision` is `approved`.
- `countsTowardDistribution` is true.
- `face_card`, `silhouette_card`, and `vibe_card` all exist.
- all three assets are approved.
- same-person identity consistency passed.
- no metadata mismatch remains unresolved.
- no visual bucket ambiguity remains unresolved.
- `observedLooksLevelBand` is not `4.4-5.0`.

Do not count `needs_review`, rejected, metadata mismatch, unresolved bucket mismatch, inactive reserve, missing-shot, or over-level identities.

## Exact Targets

Final target:

- approved complete identities: 240
- approved images: 720
- female approved complete identities: 120
- male approved complete identities: 120

Global faceType targets:

- `cat_like`: 34
- `dog_like`: 38
- `hamster_like`: 24
- `bear_like`: 29
- `fox_like`: 29
- `deer_like`: 43
- `horse_like`: 19
- `mixed_neutral`: 24

Female faceType targets:

- `cat_like`: 17
- `dog_like`: 19
- `hamster_like`: 12
- `bear_like`: 15
- `fox_like`: 14
- `deer_like`: 22
- `horse_like`: 9
- `mixed_neutral`: 12

Male faceType targets:

- `cat_like`: 17
- `dog_like`: 19
- `hamster_like`: 12
- `bear_like`: 14
- `fox_like`: 15
- `deer_like`: 21
- `horse_like`: 10
- `mixed_neutral`: 12

Global looksLevelBand targets:

- `1.5-2.4`: 36
- `2.5-3.2`: 108
- `3.3-3.8`: 72
- `3.9-4.3`: 24
- `4.4-5.0`: 0

Female looksLevelBand targets:

- `1.5-2.4`: 18
- `2.5-3.2`: 54
- `3.3-3.8`: 36
- `3.9-4.3`: 12
- `4.4-5.0`: 0

Male looksLevelBand targets:

- `1.5-2.4`: 18
- `2.5-3.2`: 54
- `3.3-3.8`: 36
- `3.9-4.3`: 12
- `4.4-5.0`: 0

## Required JSON Schema

Return exactly one JSON object with this shape:

```json
{
  "qaType": "seolleyeon_visual_verdict_distribution_v3",
  "finalDecision": "approved|needs_more_generation|needs_manual_review|rejected",
  "approvedCompleteIdentityCount": 0,
  "approvedImageCount": 0,
  "femaleApprovedIdentityCount": 0,
  "maleApprovedIdentityCount": 0,
  "globalFaceTypeCounts": {},
  "globalFaceTypeDeficits": {},
  "globalFaceTypeSurpluses": {},
  "genderFaceTypeCounts": {
    "female": {},
    "male": {}
  },
  "genderFaceTypeDeficits": {
    "female": {},
    "male": {}
  },
  "genderFaceTypeSurpluses": {
    "female": {},
    "male": {}
  },
  "globalLooksLevelBandCounts": {},
  "globalLooksLevelBandDeficits": {},
  "globalLooksLevelBandSurpluses": {},
  "genderLooksLevelBandCounts": {
    "female": {},
    "male": {}
  },
  "genderLooksLevelBandDeficits": {
    "female": {},
    "male": {}
  },
  "genderLooksLevelBandSurpluses": {
    "female": {},
    "male": {}
  },
  "invalidIdentities": [
    {
      "profileId": "string",
      "reason": "string",
      "recommendedAction": "retry|replace_with_reserve|manual_review|remove"
    }
  ],
  "nextGenerationDirective": {
    "shouldGenerateMore": true,
    "targetBuckets": [
      {
        "gender": "female|male",
        "faceType": "cat_like|dog_like|hamster_like|bear_like|fox_like|deer_like|horse_like|mixed_neutral",
        "looksLevelBand": "1.5-2.4|2.5-3.2|3.3-3.8|3.9-4.3",
        "neededIdentities": 0,
        "priority": "high|medium|low"
      }
    ],
    "stopGeneratingBuckets": [
      {
        "gender": "female|male|any",
        "faceType": "string",
        "looksLevelBand": "string",
        "reason": "quota_full|surplus|over_level_risk"
      }
    ]
  },
  "notes": "short summary"
}
```

All count maps must include every target bucket, even when the value is `0`.

## Deficits And Surpluses

For each bucket:

- `count` is the number of approved complete identities that count toward distribution.
- `deficit = max(0, target - count)`.
- `surplus = max(0, count - target)`.

Never create a `targetBuckets` entry for `4.4-5.0`. The target for `4.4-5.0` is always `0`.

Add `stopGeneratingBuckets` entries when:

- a bucket has no deficit.
- a bucket has surplus.
- the looks level band is `4.4-5.0`.

## Next Generation Directive

Set `nextGenerationDirective.shouldGenerateMore=true` when any valid deficit exists.

`targetBuckets` must include only deficit buckets that are allowed for generation:

- `gender` must be `female` or `male`.
- `faceType` must be one of the eight approved face types.
- `looksLevelBand` must be one of `1.5-2.4`, `2.5-3.2`, `3.3-3.8`, `3.9-4.3`.
- `neededIdentities` must be the number of identities still needed for that gender + faceType + looksLevelBand combination.

Use priority:

- `high` for large deficits or buckets blocking gender-level targets.
- `medium` for moderate deficits.
- `low` for small deficits.

## Invalid Identities

Add an `invalidIdentities` item for any identity that should not count because of:

- missing shot
- any asset not approved
- same-person identity mismatch
- visual bucket ambiguity
- metadata mismatch
- observed `4.4-5.0`
- hard reject or brand/safety violation
- unresolved manual review

Use `recommendedAction`:

- `retry` for bad or missing individual shots.
- `replace_with_reserve` for identity-level failure or exhausted retries.
- `manual_review` for ambiguity or audit disagreement.
- `remove` for unsafe, off-brand, or unusable identity groups.

## Final Decision Rules

Set `finalDecision` to `approved` only if all of these are true:

- `approvedCompleteIdentityCount = 240`
- `approvedImageCount = 720`
- `femaleApprovedIdentityCount = 120`
- `maleApprovedIdentityCount = 120`
- every global faceType count exactly matches target
- every gender faceType count exactly matches target
- every global looksLevelBand count exactly matches target
- every gender looksLevelBand count exactly matches target
- `4.4-5.0` count is `0` globally and for each gender
- `invalidIdentities` is empty

Set `finalDecision` to `needs_more_generation` if valid deficits exist and there is no blocking ambiguity.

Set `finalDecision` to `needs_manual_review` if visual bucket ambiguity, metadata mismatch, Python/visual audit disagreement, or unresolved review prevents exact counting.

Set `finalDecision` to `rejected` if systemic safety violations, systemic brand violations, widespread under-20/childlike appearances, or widespread non-realistic/influencer/idol-style assets are present.

The final set is approved only when every exact count matches. Do not approve partial completion.
