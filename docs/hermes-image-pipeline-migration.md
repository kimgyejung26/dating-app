# Seolleyeon Hermes Image Pipeline Migration

This document is the staged migration plan for making the existing OMX-based Seolleyeon AI image pipeline usable from Hermes without deleting or weakening the current workflow.

Seolleyeon AI profile images are synthetic cold-start preference-learning assets for a university-only, trust-based relationship product. They are not dating-game cards, attractiveness scoring material, influencer content, or real-person identification material.

## Current OMX Pipeline Map

Primary entrypoints:

- `python scripts/run_ai_image_pipeline_v3.py ...` is the cross-platform dispatcher.
- `python scripts/run_bounded_imagegen_chunk_v3.py ...` wraps the bounded chunk executor.
- `python scripts/next_codex_imagegen_prompt_v3.py ...` writes the next `pending-imagegen.json` and prints a Codex `$imagegen` prompt.
- `python scripts/recover_pending_imagegen_v3.py ...` imports the generated Codex image from the generated-images directory into `ai_image/`.
- `bash scripts/codex_imagegen_chunk_autopilot_v3.sh` runs the older OMX chunk autopilot loop.
- `bash scripts/codex_imagegen_supervisor_v3.sh` runs the supervisor that prefers bounded chunk execution and still carries Ralph-style fallback prompts.
- `python scripts/codex_imagegen_supervisor_v3.py ...` exposes the Python supervisor status path.

OMX and Ralph usage:

- `scripts/codex_imagegen_chunk_autopilot_v3.sh` calls `omx exec -C .` with `ai_image/prompts/RALPH_DISTRIBUTION_AWARE_CHUNK_PROMPT.md`.
- `scripts/codex_imagegen_supervisor_v3.sh` contains `$ralph` fallback prompts for chunk, identity, and asset ticks.
- `scripts/ai_image_pipeline_v3/bounded_batch_executor.py` defaults to an `omx` agent command and falls back to `codex` when available.
- The image generation mode remains Codex built-in `$imagegen` only. No OpenAI Image API, Batch API, or `OPENAI_API_KEY` is required for generation.

Prompt and metadata source:

- `lib/ai_recommend_model/seolleyeon_ai_profile_prompt_v3_package/seolleyeon_ai_profile_prompt_v3.py`
- The migration must not rewrite this prompt builder and must not modify recommender scripts.

## Existing Artifact Layout

Current local image artifacts:

- Raw attempts: `ai_image/raw/{assetId}__attemptXX.png`
- Final candidate/approved image path: `ai_image/{gender}/{numeric_id}/{shotType}.png`
- Approved review copy: `ai_image/approved/{assetId}.png`
- Rejected attempt copy: `ai_image/rejected/{assetId}__attemptXX.png`

Current state and manifests:

- `ai_image/manifests/generation_manifest.jsonl`
- `ai_image/manifests/imagegen_queue.jsonl`
- `ai_image/manifests/pending-imagegen.json`
- `ai_image/manifests/completed_pending_imagegen.jsonl`
- `ai_image/manifests/current_chunk_plan.json`
- `ai_image/manifests/current_chunk_state.json`
- `ai_image/manifests/asset_qa_manifest.jsonl`
- `ai_image/manifests/identity_qa_manifest.jsonl`
- `ai_image/manifests/approved_identity_manifest.jsonl`
- `ai_image/manifests/rejected_identity_manifest.jsonl`
- `ai_image/manifests/needs_review_identity_manifest.jsonl`
- `ai_image/manifests/manual_review_required.flag`

Current chunk reports:

- `ai_image/reports/chunks/{chunkId}/chunk_report.json`
- `ai_image/reports/chunks/{chunkId}/events.jsonl`
- `ai_image/reports/chunks/{chunkId}/transactions/{assetId}_attemptN.json`
- `ai_image/reports/chunks/{chunkId}/forbidden_file_backups/`
- `ai_image/reports/chunks/{chunkId}/identity_context/`
- `ai_image/reports/chunks/plan_history/`

Visual QA and visual-verdict outputs:

- Prompt files: `ai_image/prompts/VISUAL_VERDICT_*_PROMPT.md`
- Latest outputs: `ai_image/reports/visual_verdict/*_latest.json`
- History/parts/logs/invalid outputs: `ai_image/reports/visual_verdict/history/`, `parts/`, `logs/`, and `invalid/`
- Applied manifests: `ai_image/manifests/asset_qa_manifest.jsonl` and `ai_image/manifests/identity_qa_manifest.jsonl`
- Numeric audit authority: `ai_image/reports/latest_distribution_audit.json`

Ralph and OMX run state:

- Repository-local OMX state is under `.omx/state/`, including `ralph-progress.json`, `ralph-state.json`, `ralplan-state.json`, and session-specific state.
- The image pipeline's durable production progress is primarily in `ai_image/manifests/` and `ai_image/reports/chunks/`, not only in `.omx/state/`.

## Bounded Pipeline State Model

The bounded chunk executor owns:

- Planning: `bounded-chunk-plan` writes `current_chunk_plan.json` and `current_chunk_state.json`.
- Execution: `bounded-chunk-run` and `bounded-chunk-resume` process planned assets.
- Status: `bounded-chunk-status` reads plan, state, validation, manual review flag, and pending state.
- Reconcile: `bounded-chunk-reconcile` can reconstruct receipts from existing files.
- QA/finalize: `bounded-chunk-qa` and `bounded-chunk-finalize`.

The current model uses one global pending file:

- `ai_image/manifests/pending-imagegen.json`

The current one-asset receipt model uses:

- `ai_image/reports/chunks/{chunkId}/transactions/{assetId}_attemptN.json`

The current bounded executor snapshots forbidden files before child execution and detects forbidden mutations afterwards. The forbidden set includes global chunk state, visual QA manifests, distribution audit outputs, and recommender files.

Same-person reference flow today:

- `face_card` is generated first.
- `silhouette_card` and `vibe_card` require the completed `face_card` final path as `referenceImagePath`.
- If reference image input is unavailable, the executor must fail closed instead of generating a text-only independent dependent shot.

## Proposed Hermes Wrapper Contract

Run A adds a wrapper around the existing pipeline rather than replacing it.

Wrapper entrypoint:

```powershell
python scripts/run_ai_image_pipeline_v3.py hermes-wrapper --root . --run-id <run-id> --task-brief "<brief>" --execution-mode dry-run
```

Standalone wrapper entrypoint:

```powershell
python scripts/run_hermes_image_pipeline_v3.py --root . --run-id <run-id> --task-brief "<brief>" --execution-mode dry-run
```

The wrapper should:

- Create a deterministic run directory under `ai_image/runs/<run-id>/` by default.
- Write `brief.md`, `run.json`, `manifest.jsonl`, and `logs/`.
- Create compatibility folders: `prompts/`, `generated/raw/`, `generated/processed/`, `verdicts/`, `diffs/`, and `final/`.
- Accept reference image paths for audit and future provider handoff.
- Accept `--pass-threshold` and `--max-attempts`.
- Run non-interactively.
- Refuse real generation modes unless explicitly allowed.
- Record the exact existing pipeline command it ran or would run.
- Preserve existing `ai_image/` manifests and chunk state ownership.

Wrapper manifest JSONL rows should include:

- `run_id`
- `attempt`
- `prompt` or `prompt_path`
- `model` or `provider`
- `raw_image`
- `processed_image`
- `reference_images`
- `verdict_path`
- `score`
- `verdict`
- `category_match`
- `created_at`
- `command_used`
- `error`

## Run A Wrapper Commands

Normal local dry-run, with deterministic artifacts and no image generation:

```powershell
python scripts/run_ai_image_pipeline_v3.py hermes-wrapper --root . --run-id hermes-local-dry-run --task-brief "Fixture-safe Seolleyeon AI image pipeline wrapper check." --execution-mode dry-run
```

Standalone wrapper dry-run:

```powershell
python scripts/run_hermes_image_pipeline_v3.py --root . --run-id hermes-standalone-dry-run --task-brief "Fixture-safe Seolleyeon AI image pipeline wrapper check." --execution-mode dry-run
```

Fixture mode, which writes a prompt and a strict pass verdict fixture without invoking `$imagegen`:

```powershell
python scripts/run_ai_image_pipeline_v3.py hermes-wrapper --root . --run-id hermes-fixture --task-brief "Fixture-safe wrapper contract check." --execution-mode fixture
```

Hermes background terminal status polling command:

```powershell
python scripts/run_ai_image_pipeline_v3.py hermes-wrapper --root . --run-id hermes-status-check --task-brief "Poll current bounded chunk status and preserve logs." --execution-mode status
```

Hermes Kanban worker example command body:

```text
Read the brief, then run: python scripts/run_ai_image_pipeline_v3.py hermes-wrapper --root . --run-id <kanban-task-id> --task-brief-file <brief-path> --execution-mode status
Return the run directory, manifest path, log paths, and any failures.
```

Production bounded execution through the wrapper is available but intentionally gated because it may invoke Codex built-in `$imagegen`:

```powershell
python scripts/run_ai_image_pipeline_v3.py hermes-wrapper --root . --run-id hermes-bounded-run --task-brief "Run the existing bounded image pipeline." --execution-mode bounded-run --allow-real-imagegen
```

Existing OMX/Ralph-style entrypoints remain available:

```powershell
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-status --root .
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-plan --root . --production --force-replan
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-run --root .
bash scripts/codex_imagegen_chunk_autopilot_v3.sh
```

## Phase E Hermes Execution Consolidation

Run E adds the execution guide at `docs/hermes-migration/phase-e-hermes-execution.md` and the handoff at `docs/hermes-migration/handoffs/run-e-handoff.md`.

The consolidated operating modes are:

- OMX mode remains the current durable production path for live Codex built-in `$imagegen` work. Canonical state stays in `ai_image/manifests/` and `ai_image/reports/chunks/`; `.omx/state/` is orchestration state.
- Hermes background terminal mode is the Hermes surface for durable long-running local commands, status polling, fixture checks, and explicitly approved real generation commands. Do not use Hermes delegate_task as the durable long-running mechanism.
- Hermes `/goal` mode is supervised single-session mode for edits, fixture tests, small scripts, and status checks. It is not durable production mode.
- Hermes Kanban mode is durable task coordination. Each card should include command, input brief, expected artifacts, stop condition, and whether it is fixture/mock only or may run real generation.

Identity-parallel bounded generation under Hermes:

- `bounded-identity-parallel-run` is currently fixture/mock only.
- One worker owns one identity and generates `face_card`, then `silhouette_card`, then `vibe_card`.
- Dependent shots use the completed `face_card` final path as the same-person reference.
- Child workers write per-asset pending files and receipts; the parent updates global manifests and chunk state.

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py bounded-identity-parallel-run --root . --run-id hermes-identity-fixture --workers 3 --fixture
```

Per-asset pending status and asset recovery:

- Per-asset pending files live under `ai_image/manifests/pending/{assetId}.json`.
- Legacy `ai_image/manifests/pending-imagegen.json` remains supported.
- Asset recovery must use pending metadata, not visual guesswork.

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py pending-status --root . --asset-id female_001__silhouette_card__v001
```

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py recover --root . --asset-id female_001__face_card__v001
```

visual-verdict Skill installation:

```powershell
New-Item -ItemType Directory -Force ~/.hermes/skills/creative | Out-Null
Copy-Item -Recurse -Force hermes/skills/creative/visual-verdict ~/.hermes/skills/creative/visual-verdict
```

Provider/backend limitations:

- The default provider remains `codex-built-in-imagegen`.
- No OpenAI Image API or Batch API is used.
- Image generation does not require `OPENAI_API_KEY`.
- `HermesNativeImageProvider` is a scaffold and rejects reference images until reference-capable backend support is verified.
- Dependent same-person shots must fail closed if reference support is unavailable.
- All generated image artifacts must end up under `ai_image/`.

Run E fixture/mock only verification:

```powershell
python -m unittest tests.test_hermes_migration_e2e_v3
```

## Proposed Identity Worker Parallelization Design

Run B should keep this design separate from Run A's wrapper:

- One child worker owns exactly one identity such as `female_001`.
- The child processes `face_card`, then `silhouette_card`, then `vibe_card`.
- Dependent shots use the completed `face_card` final image as the same-person reference.
- The parent coordinator is the only process allowed to update global manifests or chunk state.
- Child workers write per-asset pending files, per-asset receipts, per-identity receipts, and worker-local logs.
- The parent acquires identity leases, spawns children, verifies receipts, checks forbidden global writes, updates global state, and releases or marks leases.

Proposed future pending layout:

```text
ai_image/manifests/pending/
  female_001__face_card__v001.json
  female_001__silhouette_card__v001.json
  female_001__vibe_card__v001.json
```

The legacy `ai_image/manifests/pending-imagegen.json` path must remain usable for current OMX recovery while Run B adds compatibility status and recovery commands.

## Compatibility Strategy

- Keep all existing OMX commands, Makefile targets, Python dispatch commands, and shell supervisors available.
- Keep Codex built-in `$imagegen` as the default backend.
- Do not use OpenAI Image API or Batch API.
- Do not require API keys for image generation.
- Do not store images only as temporary remote URLs.
- Keep all generated image artifacts under `ai_image/`.
- Treat the wrapper's run directory as orchestration/audit metadata, not as a replacement for canonical `ai_image/raw`, final, approved, rejected, manifests, or reports.
- Keep `visual_verdict.py` and active Codex visual QA contracts intact until Run C adds the Hermes skill.

## Pending And Recovery Strategy

Current behavior:

- `next_codex_imagegen_prompt_v3.py` and bounded generation write `pending-imagegen.json` before generation.
- Recovery imports from `CODEX_GENERATED_IMAGES_DIR` into the expected raw and final paths from the pending file.
- Identity must come from pending metadata, not visual guesswork.
- The pending file must be resolved, cleared, or recovered before the next prompt.

Migration direction:

- Run A wrapper records pending status but does not alter pending semantics.
- Run B adds per-asset pending files and keeps legacy pending status/recovery available.
- Recovery by asset id or pending path should be introduced in Run B, with ambiguity refusal.

## State And Manifest Ownership Rules

Current global files remain parent/controller-owned:

- `generation_manifest.jsonl`
- `imagegen_queue.jsonl`
- `current_chunk_plan.json`
- `current_chunk_state.json`
- `approved_identity_manifest.jsonl`
- `asset_qa_manifest.jsonl`
- `identity_qa_manifest.jsonl`
- `latest_distribution_audit.json`

Run A wrapper may write only its own run directory by default. If it invokes an existing command, that command retains its existing ownership behavior.

Run B should formalize parent-only global state updates for identity parallel execution.

## Test Plan

Run A:

- Unit test wrapper dry-run and fixture/status modes without real image generation.
- Verify wrapper creates deterministic run directories and JSONL manifest records.
- Verify dispatcher exposes the wrapper command.
- Verify real generation modes are blocked unless explicitly allowed.

Run B:

- Fixture tests for identity leases, per-asset pending files, child mutation ban, receipts, and parent reconstruction.

Run C:

- Schema tests for the Hermes `visual-verdict` skill and compatibility with current `seolleyeon_visual_verdict_*_v3` contracts.

Run D:

- Provider fixture tests proving the existing backend remains default and generated outputs are local before QA.

Run E:

- End-to-end fixture test covering wrapper, identity-parallel dry/fixture mode, visual-verdict schema validation, and Hermes execution documentation.

## Rollback Notes

- Remove or stop using the Hermes wrapper command; existing `scripts/run_ai_image_pipeline_v3.py` commands remain available.
- Existing Makefile targets remain unchanged unless a later phase intentionally adds aliases.
- Existing bounded chunk plan/state, pending recovery, visual QA, and supervisor paths remain the source of truth.
- No recommender files should be changed by this migration.
