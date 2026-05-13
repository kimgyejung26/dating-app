---
name: visual-verdict
description: Use when comparing generated images, screenshots, or contact sheets against visual references and returning Seolleyeon-compatible structured QA JSON.
version: 0.1.0
metadata:
  hermes:
    tags:
      - vision
      - image-generation
      - visual-qa
    category: creative
---

# Visual Verdict

Use this Skill when a Hermes session needs visual QA for Seolleyeon AI image pipeline artifacts. For exact field definitions and examples, read `references/verdict-schema.md` before returning or validating a verdict.

Seolleyeon AI profile images are synthetic cold-start preference-learning assets for a university-only, trust-based relationship platform. Do not use this Skill for attractiveness scoring, face rating, real-person identification, celebrity matching, or sensitive trait inference.

## Procedure

1. Verify every reference and candidate image path exists locally before analysis.
2. If the images are directly comparable, optionally run `scripts/pixel_diff.py` for debugging evidence. Pixel diff is never the sole pass/fail authority.
3. Use Hermes vision analysis when available to inspect candidate quality, reference alignment, category match, and Seolleyeon product guardrails.
4. Return strict JSON only. For the simple `/visual-verdict` contract, use:

```json
{
  "score": 94,
  "verdict": "pass",
  "category_match": true,
  "differences": [],
  "suggestions": [],
  "reasoning": "Candidate matches the reference category and product guardrails."
}
```

5. Normalize compatibility alias `retry` to `revise` for the simple contract. Project-local nested Seolleyeon payloads keep their canonical decisions.
6. Default pass threshold is `score >= 90`.
7. Persist each verdict before any next edit or generation attempt. Use the active run `verdicts/` directory or `ai_image/reports/visual_verdict/`.
8. Preserve project-local contracts when applying QA to manifests:
   - `qaType: seolleyeon_visual_verdict_asset_v3`
   - `qaType: seolleyeon_visual_verdict_identity_v3`
   - `qaType: seolleyeon_visual_verdict_distribution_v3`
9. Validate fixture or saved JSON payloads without running vision or image generation:

```powershell
python hermes/skills/creative/visual-verdict/scripts/validate_visual_verdict_schema.py path/to/verdict.json
```

## Strict Output Rules

- Output one JSON object and no prose.
- Never approve images that look childlike, school-uniform based, sexualized, celebrity-like, influencer-shot, visibly branded, watermarked, distorted, or outside the calm campus trust tone.
- Do not infer real identity, university affiliation, age beyond adult/childlike safety screening, ethnicity, disability, religion, politics, health, or other sensitive traits.
- If evidence is insufficient, use `revise` in the simple contract or `needs_review` in the project-local nested contract.

## Installation

Copy this repo-local scaffold to a Hermes-discovered skill path:

```powershell
New-Item -ItemType Directory -Force ~/.hermes/skills/creative | Out-Null
Copy-Item -Recurse -Force hermes/skills/creative/visual-verdict ~/.hermes/skills/creative/visual-verdict
```
