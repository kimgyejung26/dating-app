# Visual Verdict Schema

This skill supports two JSON families:

- External Hermes `/visual-verdict`: one normalized verdict object.
- Seolleyeon project-local visual QA: the existing nested v3 contracts consumed by `scripts/ai_image_pipeline_v3/visual_verdict.py` and `active_visual_verdict_runner.py`.

## Product Safety

Visual verdicts are synthetic asset QA for Seolleyeon, a university-only trust product. They are not dating-game cards or human evaluation output. Use no attractiveness scoring, no face rating, no real-person identification, and no sensitive trait inference. Do not identify people, infer ethnicity, religion, politics, health, sexuality, or other sensitive attributes. Do not compare an image to a celebrity or influencer.

Looks-level bands are project-local generation metadata. Preserve them only as contract fields; do not reinterpret them as attractiveness scores.

## Normalized External Verdict

Use this exact object for general Hermes `/visual-verdict` calls:

| Field | Type | Rule |
| --- | --- | --- |
| `score` | integer | `0` through `100` |
| `verdict` | string | `pass`, `revise`, or `fail`; input `retry` may be accepted only as an alias normalized to `revise` |
| `category_match` | boolean | `true` only when the generated image matches the requested category |
| `differences` | string array | concrete mismatches |
| `suggestions` | string array | actionable edits |
| `reasoning` | string | short reason, without sensitive inference |

Pass threshold: `verdict: "pass"` requires `score >= 90` and `category_match: true`.

```json
{
  "score": 94,
  "verdict": "pass",
  "category_match": true,
  "differences": [],
  "suggestions": [],
  "reasoning": "The generated image matches the reference category and no blocking visual differences remain."
}
```

Compatibility mapping for external callers:

| Input or project signal | Normalized verdict |
| --- | --- |
| `pass` or project `approved` | `pass` when score is at least 90 |
| `revise`, `retry`, or project `needs_review` | `revise` |
| `fail` or project `rejected` | `fail` |

## Project Asset QA Contract

Canonical `qaType`: `seolleyeon_visual_verdict_asset_v3`

Top-level shape:

- `qaType`: exact string above
- `sheetId`: contact sheet identifier
- `assets`: non-empty array unless the caller explicitly allows empty payloads
- `summary`: optional counts

Each asset object must preserve the fields required by `visual_verdict.py`: `assetId`, `profileId`, `gender`, `shotType`, `targetFaceType`, `observedFaceType`, `targetLooksLevelBand`, `observedLooksLevelBand`, `adultVisual`, `photoRealism`, `brandFit`, `shotTypeReadable`, `metadataMismatch`, and `decision`.

Valid project decisions are `approved`, `needs_review`, and `rejected`.

```json
{
  "qaType": "seolleyeon_visual_verdict_asset_v3",
  "sheetId": "fixture_asset_sheet",
  "assets": [
    {
      "assetId": "female_001__face_card__v001",
      "profileId": "female_001",
      "gender": "female",
      "shotType": "face_card",
      "targetFaceType": "deer_like",
      "observedFaceType": "deer_like",
      "faceTypeConfidence": 0.92,
      "targetLooksLevelBand": "2.5-3.2",
      "observedLooksLevelBand": "2.5-3.2",
      "looksLevelConfidence": 0.88,
      "adultVisual": true,
      "photoRealism": 4.6,
      "campusRealism": 4.4,
      "brandFit": 4.5,
      "shotTypeReadable": true,
      "influencerRisk": 0.2,
      "childlikeRisk": 0.0,
      "schoolUniformRisk": 0.0,
      "sexualizationRisk": 0.0,
      "artifactRisk": 0.2,
      "metadataMismatch": false,
      "mismatchFields": [],
      "decision": "approved",
      "rejectReasons": [],
      "notes": "fixture only"
    }
  ],
  "summary": {
    "approvedCount": 1,
    "needsReviewCount": 0,
    "rejectedCount": 0
  }
}
```

## Project Identity QA Contract

Canonical `qaType`: `seolleyeon_visual_verdict_identity_v3`

Top-level shape:

- `qaType`: exact string above
- `sheetId`: optional contact sheet identifier
- `identities`: non-empty array unless the caller explicitly allows empty payloads
- `summary`: optional counts

Each identity object must preserve the fields required by `visual_verdict.py`: `profileId`, `gender`, `targetFaceType`, `observedFaceType`, `targetLooksLevelBand`, `observedLooksLevelBand`, `assetIds`, `assetDecisions`, `faceToSilhouetteConsistency`, `faceToVibeConsistency`, `sameIdentity`, `completeIdentityDecision`, and `countsTowardDistribution`.

Valid `completeIdentityDecision` values are `approved`, `needs_review`, and `rejected`. `retryShotTypes` is a project-specific array of shot types; it is not a verdict status.

```json
{
  "qaType": "seolleyeon_visual_verdict_identity_v3",
  "sheetId": "fixture_identity_sheet",
  "identities": [
    {
      "profileId": "female_001",
      "gender": "female",
      "targetFaceType": "deer_like",
      "observedFaceType": "deer_like",
      "targetLooksLevelBand": "2.5-3.2",
      "observedLooksLevelBand": "2.5-3.2",
      "assetIds": {
        "face_card": "female_001__face_card__v001",
        "silhouette_card": "female_001__silhouette_card__v001",
        "vibe_card": "female_001__vibe_card__v001"
      },
      "assetDecisions": {
        "face_card": "approved",
        "silhouette_card": "approved",
        "vibe_card": "approved"
      },
      "faceToSilhouetteConsistency": 4.2,
      "faceToVibeConsistency": 4.2,
      "sameIdentity": true,
      "completeIdentityDecision": "approved",
      "countsTowardDistribution": true,
      "failedShotTypes": [],
      "retryShotTypes": [],
      "rejectReasons": [],
      "notes": "fixture only"
    }
  ],
  "summary": {
    "approvedCompleteIdentities": 1,
    "needsReviewIdentities": 0,
    "rejectedIdentities": 0
  }
}
```

## Project Distribution QA Contract

Canonical `qaType`: `seolleyeon_visual_verdict_distribution_v3`

Required fields are the fields validated by `active_visual_verdict_runner.py`: `finalDecision`, `approvedCompleteIdentityCount`, `approvedImageCount`, `femaleApprovedIdentityCount`, `maleApprovedIdentityCount`, `globalFaceTypeCounts`, `globalLooksLevelBandCounts`, `invalidIdentities`, and `nextGenerationDirective`.

Valid `finalDecision` values are `approved`, `needs_manual_review`, and `needs_more_generation`.

```json
{
  "qaType": "seolleyeon_visual_verdict_distribution_v3",
  "finalDecision": "needs_more_generation",
  "approvedCompleteIdentityCount": 1,
  "approvedImageCount": 3,
  "femaleApprovedIdentityCount": 1,
  "maleApprovedIdentityCount": 0,
  "globalFaceTypeCounts": {
    "deer_like": 1
  },
  "globalFaceTypeDeficits": {},
  "globalFaceTypeSurpluses": {},
  "genderFaceTypeCounts": {
    "female": {
      "deer_like": 1
    },
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
  "globalLooksLevelBandCounts": {
    "2.5-3.2": 1
  },
  "globalLooksLevelBandDeficits": {},
  "globalLooksLevelBandSurpluses": {},
  "genderLooksLevelBandCounts": {
    "female": {
      "2.5-3.2": 1
    },
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
  "invalidIdentities": [],
  "nextGenerationDirective": {
    "shouldGenerateMore": true,
    "targetBuckets": [],
    "stopGeneratingBuckets": []
  },
  "notes": "fixture only"
}
```

## Installation

Copy the skill folder into the Hermes skill directory:

```powershell
New-Item -ItemType Directory -Force ~/.hermes/skills/creative | Out-Null
Copy-Item -Recurse -Force hermes/skills/creative/visual-verdict ~/.hermes/skills/creative/visual-verdict
```

Then validate fixtures without image generation:

```powershell
python hermes/skills/creative/visual-verdict/scripts/validate_visual_verdict_schema.py path/to/verdict.json
```
