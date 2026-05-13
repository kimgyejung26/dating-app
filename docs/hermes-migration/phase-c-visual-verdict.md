# Phase C Visual Verdict Skill

Run C adds the repo-local Hermes skill at `hermes/skills/creative/visual-verdict/`.

## Install

Copy the skill into Hermes:

```powershell
New-Item -ItemType Directory -Force ~/.hermes/skills/creative | Out-Null
Copy-Item -Recurse -Force hermes/skills/creative/visual-verdict ~/.hermes/skills/creative/visual-verdict
```

Installed path:

```text
~/.hermes/skills/creative/visual-verdict/
```

## Schema

The skill preserves the current project contracts:

- `seolleyeon_visual_verdict_asset_v3`
- `seolleyeon_visual_verdict_identity_v3`
- `seolleyeon_visual_verdict_distribution_v3`

It also defines a normalized external Hermes `/visual-verdict` object:

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

`retry` is accepted only as a compatibility input alias for the normalized external object and is stored as `revise`. Project-local asset and identity decisions remain `approved`, `needs_review`, or `rejected`.

## Validate

Validation is fixture-safe and does not run real vision or image generation:

```powershell
python hermes/skills/creative/visual-verdict/scripts/validate_visual_verdict_schema.py path/to/verdict.json
```
