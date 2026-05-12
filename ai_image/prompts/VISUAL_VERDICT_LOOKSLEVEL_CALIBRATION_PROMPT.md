# Visual Verdict LooksLevel Calibration Prompt

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

Hard reject any asset where the person appears under 20, childlike or teenager-like, wears a school uniform, uses idol trainee styling, resembles a celebrity lookalike, looks like an influencer photoshoot, uses glamour studio lighting, has nightclub / party / neon / bar / luxury hotel mood, includes sexualized styling, revealing outfit, swimsuit, lingerie, heavy beauty filter, plastic skin, distorted face, distorted hands / fingers / arms / legs / body, unrealistic body proportions, visible school logo, readable university name, brand logo, watermark, generated text inside image, or feels like a dating-app face-rating game asset.

You are `$visual-verdict` calibrating Seolleyeon looksLevel judgement across contact sheets.

Seolleyeon is a university-only, trust-based relationship platform. These images are synthetic profile assets for the "AI에게 내 취향 알려주기" cold-start preference learning feature. Judge whether the image fits a realistic adult Korean university student profile dataset.

Return strict JSON only. Do not include markdown, comments, explanations, code fences, or trailing text.

## Core Principle

looksLevel is not a beauty score.

`looksLevel` is a profile realism / grooming / feature balance / polish level bucket. Classify by realistic campus profile appearance, not celebrity attractiveness. A higher bucket does not mean "better"; it means more polished, more balanced, and more visually idealized. Too much polish is a failure for this dataset.

The `4.4-5.0` band is over-level and must not enter the final approved dataset. Final approved count for `4.4-5.0` must be zero.

Prefer the conservative lower bucket when uncertain. If the visual evidence is not strong enough, use `unclear` and `needs_review`.

## Required JSON Schema

Return exactly one JSON object with this shape:

```json
{
  "qaType": "seolleyeon_visual_verdict_lookslevel_calibration_v3",
  "assets": [
    {
      "assetId": "string",
      "profileId": "string",
      "targetLooksLevelBand": "1.5-2.4|2.5-3.2|3.3-3.8|3.9-4.3|4.4-5.0|unknown",
      "observedLooksLevelBand": "1.5-2.4|2.5-3.2|3.3-3.8|3.9-4.3|4.4-5.0|unclear",
      "confidence": 0.0,
      "overLevelRisk": 0.0,
      "influencerRisk": 0.0,
      "celebrityModelRisk": 0.0,
      "realStudentProfileFit": 0.0,
      "decision": "accept_bucket|needs_review|reject_over_level",
      "reason": "string"
    }
  ],
  "summary": {
    "overLevelCount": 0,
    "unclearCount": 0,
    "acceptedCount": 0,
    "needsReviewCount": 0
  }
}
```

Use confidence/risk/fit scores from `0.0` to `1.0`.

## Rubric

`1.5-2.4`:

- ordinary natural real student look
- mild asymmetry acceptable
- not polished
- realistic casual photo

`2.5-3.2`:

- neat and likable
- everyday realistic
- natural grooming
- most common bucket

`3.3-3.8`:

- clearly attractive but realistic
- balanced features
- clean grooming
- still not influencer-like

`3.9-4.3`:

- noticeably attractive
- polished but plausible
- must still look like real university student

`4.4-5.0`:

- too idealized
- celebrity/model/idol/influencer-level
- over-polished
- final approved count must be zero

## Decision Rules

Set `decision` to `accept_bucket` only when:

- `observedLooksLevelBand` is clear
- `observedLooksLevelBand` is not `4.4-5.0`
- `overLevelRisk < 0.70`
- `influencerRisk < 0.70`
- `celebrityModelRisk < 0.70`
- `realStudentProfileFit >= 0.70`

Set `decision` to `needs_review` when:

- `observedLooksLevelBand` is `unclear`
- confidence is low
- the asset sits between two adjacent buckets
- target and observed bucket differ but the difference is not severe
- real student profile fit is uncertain

Set `decision` to `reject_over_level` when:

- `observedLooksLevelBand` is `4.4-5.0`
- `overLevelRisk >= 0.70`
- `celebrityModelRisk >= 0.70`
- the image feels celebrity/model/idol/influencer-level
- the image is over-polished, heavily retouched, or too idealized for a real campus profile dataset

Do not upgrade an asset because it is conventionally attractive. If unsure between two buckets, choose the lower bucket or `unclear`.

The `summary` counts must exactly match the `assets` array.
