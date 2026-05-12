# Seolleyeon AI Image Distribution Control

This workflow controls Seolleyeon synthetic profile images for the `AI에게 내 취향 알려주기` cold-start preference-learning feature. The target is not a dating-card gallery; it is a realistic, adult Korean university student profile dataset with exact identity-level distribution.

## Final Acceptance Target

- 240 approved complete identities.
- 720 approved images.
- 120 female approved complete identities.
- 120 male approved complete identities.
- Every counted identity must have approved `face_card`, `silhouette_card`, and `vibe_card`.

Distribution is counted at identity level only. `needs_review`, rejected, metadata mismatch, inactive reserve, and `4.4-5.0` looks-level identities do not count.

## Codex Image Gen Mode

Use Codex internal `$imagegen` only.

- Do not use OpenAI Image API.
- Do not use Batch API.
- Do not require `OPENAI_API_KEY`.
- Before every image generation, write `ai_image/manifests/pending-imagegen.json`.
- After every image generation, recover the pending image before selecting another prompt.
- Do not overwrite approved files unless `--force` is passed.

## Main Commands

PowerShell-safe Python dispatcher commands:

```powershell
python scripts/run_ai_image_pipeline_v3.py --help
python scripts/run_ai_image_pipeline_v3.py prepare-720 --root .
python scripts/run_ai_image_pipeline_v3.py distribution-audit --root .
python scripts/run_ai_image_pipeline_v3.py completion-check --root .
python scripts/run_ai_image_pipeline_v3.py pending-status --root .
python -m unittest tests.test_ai_image_pipeline_v3 -q
```

Use the Python dispatcher when `make`, `mingw32-make`, or `bash` is unavailable. The dispatcher can run dry-run/status and local validation paths without Image Gen, OpenAI Image API, Batch API, or `OPENAI_API_KEY`.

```sh
mingw32-make ai-image-prepare-720
mingw32-make ai-image-distribution-audit
mingw32-make ai-image-next-distribution-chunk
mingw32-make ai-image-recover
mingw32-make ai-image-file-qa
mingw32-make ai-image-contact-sheets
mingw32-make ai-image-apply-visual-asset-qa
mingw32-make ai-image-apply-visual-identity-qa
mingw32-make ai-image-apply-visual-distribution-audit
mingw32-make ai-image-completion-check
```

`mingw32-make ai-image-next-distribution-chunk` selects deficit-only identities, writes the next pending checkpoint, and prints the Codex Image Gen prompt. It refuses to continue when a pending image still requires recovery or when `ai_image/manifests/manual_review_required.flag` exists.

## Pending Checkpoint Admin

Use these commands to inspect or resolve safe interrupted states without Image Gen:

```powershell
python scripts/run_ai_image_pipeline_v3.py pending-status --root .
python scripts/run_ai_image_pipeline_v3.py clear-cancelled-pending --root . --reason "cancelled before imagegen"
python scripts/run_ai_image_pipeline_v3.py resolve-pending --root . --reason "manual manifest review"
```

`pending-status` is read-only. `clear-cancelled-pending` only clears non-active cancelled checkpoints. `resolve-pending` refuses active `pending_imagegen` or `imagegen_started` checkpoints because those require recovery, not manual clearing. These commands do not approve assets, do not count identities, and do not overwrite files.

## Numeric Authority

`scripts/audit_ai_profile_distribution_v3.py` is the numeric authority. It writes:

- `ai_image/reports/distribution_audit.json`
- `ai_image/reports/latest_distribution_audit.json`
- `ai_image/reports/distribution_report.csv`
- `ai_image/manifests/approved_identity_manifest.jsonl`
- `ai_image/manifests/rejected_identity_manifest.jsonl`
- `ai_image/manifests/reserve_identity_manifest.jsonl`

`scripts/check_ai_image_completion_v3.py` exits successfully only when all final counts and exact distribution buckets match.

Completion also fails when `ai_image/manifests/manual_review_required.flag` exists, when `ai_image/manifests/pending-imagegen.json` is unresolved, when visual-verdict asset or identity QA is missing, or when any counted identity is needs-review, rejected, metadata-mismatched, over-level `4.4-5.0`, not same-person, or missing one of the three required shots. Raw/generated image count and the existence of 720 files never pass completion by themselves.

## Visual Verdict Flow

Prompt files live in `ai_image/prompts/`. Visual verdict outputs must be strict JSON or JSONL and can be applied with:

- `scripts/apply_visual_verdict_asset_qa_v3.py`
- `scripts/apply_visual_verdict_identity_qa_v3.py`
- `scripts/apply_visual_verdict_distribution_audit_v3.py`

Asset QA JSON is applied into `ai_image/manifests/asset_qa_manifest.jsonl`. The apply step validates the nested `assets[]` schema, preserves `originalDecision`, writes normalized `finalDecision`, applies hard reject overrides, records `metadataMismatch` and `mismatchFields`, and sets `countsTowardIdentityQa=true` only for `finalDecision=approved`.

Identity QA JSON is applied into `ai_image/manifests/identity_qa_manifest.jsonl`. The apply step validates the nested `identities[]` schema against `asset_qa_manifest.jsonl`, requires all three approved asset QA records, writes `finalCompleteIdentityDecision`, and updates:

- `ai_image/manifests/approved_identity_manifest.jsonl`
- `ai_image/manifests/rejected_identity_manifest.jsonl`
- `ai_image/manifests/needs_review_identity_manifest.jsonl`

Only `finalCompleteIdentityDecision=approved`, `countsTowardDistribution=true`, no metadata mismatch, no over-level `4.4-5.0`, and all three approved asset QA records can enter the approved identity manifest.

PowerShell-safe apply commands:

```powershell
python scripts/apply_visual_verdict_asset_qa_v3.py --root . --visual_json ai_image/reports/visual_verdict/asset_qa_latest.json --out_manifest ai_image/manifests/asset_qa_manifest.jsonl
python scripts/apply_visual_verdict_identity_qa_v3.py --root . --visual_json ai_image/reports/visual_verdict/identity_qa_latest.json --asset_qa_manifest ai_image/manifests/asset_qa_manifest.jsonl --out_manifest ai_image/manifests/identity_qa_manifest.jsonl
python scripts/apply_visual_verdict_distribution_audit_v3.py --root . --visual_json ai_image/reports/visual_verdict/distribution_audit_latest.json --numeric_audit ai_image/reports/latest_distribution_audit.json
```

If visual distribution audit and Python numeric audit disagree, the pipeline writes `ai_image/manifests/manual_review_required.flag`.

Active Codex CLI visual QA fallback commands:

```powershell
python scripts/run_ai_image_pipeline_v3.py active-visual-probe --root .
python scripts/run_ai_image_pipeline_v3.py active-visual-asset-qa --root .
python scripts/run_ai_image_pipeline_v3.py active-visual-identity-qa --root .
python scripts/run_ai_image_pipeline_v3.py active-visual-distribution-qa --root .
python scripts/run_ai_image_pipeline_v3.py active-visual-qa-all --root .
```

These commands call Codex CLI with contact sheet image inputs when supported (`codex --image`, `codex -i`, `codex exec --image`, or `codex exec -i`). They do not generate images and must not fabricate approval JSON from metadata. Invalid output is saved under `ai_image/reports/visual_verdict/invalid/`, raw stdout/stderr under `ai_image/reports/visual_verdict/logs/`, and valid latest/history JSON under `ai_image/reports/visual_verdict/`.

## Bounded Chunk Executor

Chunk generation is code-owned by `scripts/ai_image_pipeline_v3/bounded_batch_executor.py`. It materializes `ai_image/manifests/current_chunk_plan.json`, tracks resumable state in `ai_image/manifests/current_chunk_state.json`, writes chunk reports under `ai_image/reports/chunks/{chunkId}/`, and appends every state transition to `events.jsonl`.

The executor selects deficit buckets only, caps each chunk at 24 identities / 72 assets, excludes `4.4-5.0`, processes assets in `face_card`, `silhouette_card`, `vibe_card` order, writes `pending-imagegen.json` before every one-asset generation call, requires recovery and file integrity QA after each asset, then requires active visual QA plus numeric distribution audit before a chunk can be finalized. Raw/generated/file-QA-only images never count as approved.

PowerShell-safe bounded commands:

```powershell
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-status --root .
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-plan --root . --dry-run
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-status --root .
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-plan --root . --production --force-replan
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-validate-plan --root .
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-run --root .
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-resume --root .
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-qa --root .
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-finalize --root .
```

`bounded-chunk-plan --dry-run` creates a non-executable plan with `dryRun=true`, `planMode=dry_run`, and `executable=false`; `bounded-chunk-run` and `bounded-chunk-resume` refuse to use it. Before real automation, create a fresh production plan with `bounded-chunk-plan --production --force-replan`, which archives the previous current plan, writes the new plan/state atomically, records input hashes, and marks the plan executable only if it is based on the latest audit and queue state. `bounded-chunk-run` may invoke `omx exec -C .` or fall back to `codex exec -C .`; use it only when real Codex internal Image Gen is intended.

## Supervisor Notes

Do not run the production supervisor until strict QA passes. Chunk mode now calls the bounded Python executor instead of one large Ralph prompt. Before each chunk run, the supervisor validates `current_chunk_plan.json`; if it is missing, dry-run, stale, or non-executable, it creates a fresh `--production --force-replan` plan and stops if production planning fails. If `bash` is unavailable, use the Python status supervisor:

```powershell
python scripts/codex_imagegen_supervisor_v3.py --root . --mode auto
python scripts/run_ai_image_pipeline_v3.py supervisor-720 --root .
```

The Python supervisor status path is cross-platform and does not invoke Image Gen. The bash supervisor remains shell-dependent and should only be used in an environment that supports `bash`, `omx`, and Codex internal Image Gen.

## Windows Validation Notes

When `make` or `bash` is unavailable, use the Python dispatcher for local QA:

```powershell
python scripts/run_ai_image_pipeline_v3.py --help
python scripts/run_ai_image_pipeline_v3.py distribution-audit --root .
python scripts/run_ai_image_pipeline_v3.py completion-check --root .
python scripts/run_ai_image_pipeline_v3.py supervisor-720 --root .
python -m unittest tests.test_ai_image_pipeline_v3 -q
```

Only run shell syntax checks such as `bash -n scripts/codex_imagegen_supervisor_v3.sh` inside Git Bash, WSL, or another environment with bash installed. Bash absence is not a pipeline QA failure when the Python dispatcher and Python supervisor status path are available.

## Git Handoff Hygiene

Before staging or handing off pipeline work, inspect scope explicitly:

```powershell
git status --short
git status --short -- seolleyeon_run_all.py seolleyeon_svd_train_export.py seolleyeon_knn_train_export.py seolleyeon_clip_train_export.py seolleyeon_clip_embedder.py seolleyeon_rrf_export.py seolleyeon_rec_common_v3.py
git status --short -- scripts ai_image AI_IMAGE_QUALITY_CONTRACT.md AI_IMAGE_DISTRIBUTION_CONTROL_README.md Makefile tests
```

Keep recommender files untouched unless explicitly requested. Stage only pipeline code, prompts, config, Makefile targets, tests, and docs that are part of this image QA workflow. Do not stage raw generated images, approved/rejected image assets, or local Codex generated output directories unless the handoff explicitly requires dataset artifacts.
