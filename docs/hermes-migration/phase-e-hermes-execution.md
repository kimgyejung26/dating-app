# Phase E Hermes Execution

Run E documents how to operate the Seolleyeon AI image pipeline from Hermes while preserving the existing OMX workflow and local resumable artifact model.

This phase does not replace production generation. It explains supervised and durable execution surfaces, fixture-safe verification, and the limits of the current provider abstraction.

## Execution Modes

### OMX mode

OMX mode remains the current durable production path for live Codex built-in `$imagegen` work.

- Use existing bounded chunk, pending, recovery, QA, and supervisor commands.
- Keep canonical state under `ai_image/manifests/` and `ai_image/reports/chunks/`.
- Keep `.omx/state/` as OMX/Ralph orchestration state, not the only source of pipeline truth.
- Do not delete or break the existing OMX workflow during Hermes migration.

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py bounded-chunk-status --root .
```

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py recover --root . --asset-id female_001__face_card__v001
```

### Hermes background terminal mode

Hermes background terminal mode is the recommended Hermes surface for durable long-running local work. It can run bounded status, planning, fixture checks, or explicitly approved real generation commands while keeping logs and resumable artifacts local.

- Use it for long-running supervised local commands that may need status polling.
- Write outputs under `ai_image/`; wrapper audit outputs go under `ai_image/runs/<run-id>/`.
- Check `pending-imagegen.json` and `ai_image/manifests/pending/*.json` before starting another generation prompt.
- Do not use Hermes delegate_task as the durable long-running mechanism.

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py hermes-wrapper --root . --run-id hermes-background-status --task-brief "Poll bounded chunk state from Hermes background terminal." --execution-mode status
```

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py bounded-identity-parallel-run --root . --run-id hermes-background-identity-fixture --workers 3 --fixture
```

### Hermes /goal mode

Hermes `/goal` mode is supervised single-session mode. It is useful for short, operator-visible work where the agent can inspect, edit, test, and report before the session ends.

- Use `/goal` for migration edits, fixture tests, documentation, small helper scripts, and status checks.
- Do not treat `/goal` as durable production mode.
- Do not rely on `/goal` alone for unattended full, pilot, or smoke production generation.
- If `/goal` invokes a wrapper run, keep it fixture-safe unless the operator explicitly allows real Codex `$imagegen`.

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py hermes-wrapper --root . --run-id hermes-goal-fixture --task-brief "Fixture-safe /goal verification." --execution-mode fixture
```

### Hermes Kanban mode

Hermes Kanban mode is a durable task coordination surface for splitting bounded work into cards. Each card should own a narrow command, input brief, expected artifacts, and stop condition.

- Use Kanban for background status polling, chunk planning, visual-verdict validation, fixture runs, and bounded identity batches.
- Keep each card explicit about whether it is fixture/mock only or may run real generation.
- Do not use Hermes delegate_task as the durable long-running mechanism.
- Card outputs should include run directory, manifest path, log paths, pending status, and failures.

Example Kanban card body:

```text
Example command:
python scripts/run_ai_image_pipeline_v3.py hermes-wrapper --root . --run-id <kanban-task-id> --task-brief-file <brief-path> --execution-mode status

Return the run directory, manifest path, stdout/stderr log paths, pending status, and any failures.
```

## Identity Parallel Bounded Generation

`bounded-identity-parallel-run` is the Hermes-facing fixture-safe identity parallel command added by Run B.

- One worker owns one identity.
- The worker writes `face_card`, then `silhouette_card`, then `vibe_card`.
- Dependent shots use the completed `face_card` final path as the same-person reference.
- Child workers write per-asset pending files and receipts.
- The parent updates global manifests and chunk state.
- Current CLI behavior is fixture/mock only and must not run real image generation.

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py bounded-identity-parallel-run --root . --run-id hermes-identity-fixture --workers 3 --fixture
```

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py bounded-identity-worker --root . --run-id hermes-one-identity-fixture --identity-id female_001 --worker-id worker-001 --fixture
```

## Per-Asset Pending Status

Run B adds per-asset pending files under:

```text
ai_image/manifests/pending/{assetId}.json
```

The legacy pending file remains supported:

```text
ai_image/manifests/pending-imagegen.json
```

Use per-asset pending status when checking a specific identity-parallel asset.

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py pending-status --root . --asset-id female_001__silhouette_card__v001
```

Use the legacy status when checking the single global pending imagegen slot.

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py pending-status --root .
```

## Asset Recovery

Asset recovery must use pending metadata, not visual guesswork. Recovery imports generated Codex output into the expected local raw and final paths under `ai_image/`.

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py recover --root . --asset-id female_001__face_card__v001
```

Example command:

```powershell
python scripts/run_ai_image_pipeline_v3.py recover --root . --pending ai_image/manifests/pending-imagegen.json
```

Recovery remains local and resumable. Do not overwrite completed or approved images unless `--force` is passed.

## visual-verdict Skill installation

Install the repo-local Hermes visual-verdict Skill before using Hermes visual review workflows.

Example command:

```powershell
New-Item -ItemType Directory -Force ~/.hermes/skills/creative | Out-Null
Copy-Item -Recurse -Force hermes/skills/creative/visual-verdict ~/.hermes/skills/creative/visual-verdict
```

Validate verdict JSON without running real vision or image generation.

Example command:

```powershell
python hermes/skills/creative/visual-verdict/scripts/validate_visual_verdict_schema.py ai_image/runs/hermes-goal-fixture/verdicts/attempt01_fixture_verdict.json
```

## Provider/Backend Limitations

Current provider/backend limitations are intentional migration guardrails:

- The default provider remains `codex-built-in-imagegen`.
- Python does not call the OpenAI Image API.
- The pipeline does not create Batch API JSONL.
- Image generation does not require `OPENAI_API_KEY`.
- `HermesNativeImageProvider` is a scaffold, not an enabled production generator.
- Reference images are not supported by the Hermes-native scaffold until a reference-capable backend is explicitly verified.
- Dependent shots must fail closed when same-person reference support is unavailable.
- All generated image artifacts must end up under `ai_image/`.

## Fixture E2E Verification

Run E adds a fixture/mock only end-to-end test. It does not invoke `$imagegen`, real vision, OpenAI Image API, or Batch API.

Example command:

```powershell
python -m unittest tests.test_hermes_migration_e2e_v3
```

The fixture test covers:

- Hermes wrapper fixture artifacts under `ai_image/runs/<run-id>/`.
- Default `codex-built-in-imagegen` provider metadata.
- Visual-verdict schema validation of the wrapper fixture verdict.
- Identity parallel fixture generation for one identity.
- Per-asset pending status for a dependent shot.
- Local final fixture files under `ai_image/{gender}/{numeric_id}/`.
