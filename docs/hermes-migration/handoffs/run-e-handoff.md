# Run E Handoff

```json
{
  "run": "Run E: Phase 4 Hermes /goal/Kanban docs/scripts + end-to-end fixture test",
  "status": "complete",
  "docs_changed": [
    "docs/hermes-migration/phase-e-hermes-execution.md",
    "docs/hermes-image-pipeline-migration.md",
    "docs/hermes-migration/handoffs/run-e-handoff.md"
  ],
  "scripts_changed": [],
  "tests_changed": [
    "tests/test_hermes_migration_e2e_v3.py"
  ],
  "e2e_fixture_command": "python -m unittest tests.test_hermes_migration_e2e_v3",
  "tests_run": [
    "python -m unittest tests.test_hermes_migration_e2e_v3",
    "python -m unittest tests.test_hermes_visual_verdict_skill_v3 tests.test_hermes_wrapper_v3 tests.test_identity_parallel_v3 tests.test_image_provider_v3"
  ],
  "final_run_instructions": [
    "OMX mode: use existing bounded chunk and recovery commands for production state, for example `python scripts/run_ai_image_pipeline_v3.py bounded-chunk-status --root .`.",
    "Hermes background terminal mode: use durable background commands for status, fixture checks, and explicitly approved real generation; do not use Hermes delegate_task as the durable long-running mechanism.",
    "Hermes /goal mode: use supervised single-session fixture checks, docs, scripts, and status work; do not treat /goal as durable production mode.",
    "Hermes Kanban mode: create explicit cards with command, input brief, expected artifacts, stop condition, and whether the work is fixture/mock only or real generation.",
    "Identity parallel fixture: run `python scripts/run_ai_image_pipeline_v3.py bounded-identity-parallel-run --root . --run-id <run-id> --workers 3 --fixture`.",
    "Per-asset pending status: run `python scripts/run_ai_image_pipeline_v3.py pending-status --root . --asset-id <assetId>`.",
    "Asset recovery: run `python scripts/run_ai_image_pipeline_v3.py recover --root . --asset-id <assetId>` after confirming pending metadata identifies the intended asset.",
    "Visual-verdict Skill installation: copy `hermes/skills/creative/visual-verdict` to `~/.hermes/skills/creative/visual-verdict` before Hermes visual review workflows."
  ],
  "remaining_todos": [
    "Enable real Hermes-native image generation only after a reference-capable backend is verified.",
    "Keep production live generation on the existing Codex built-in $imagegen plus pending/recovery workflow until the provider backend changes.",
    "Decide later whether to add non-fixture identity parallel execution; current CLI remains fixture/mock only."
  ],
  "migration_risks": [
    "Hermes /goal is supervised single-session mode and can lose durability expectations if used for unattended production generation.",
    "Hermes Kanban/background terminal work must still respect pending-imagegen and per-asset pending ownership to avoid ambiguous recovery.",
    "The Hermes-native provider scaffold rejects reference images today; dependent silhouette/vibe generation must not proceed text-only without same-person reference support.",
    "Existing OMX/Ralph state remains present; migration docs must keep distinguishing orchestration state from canonical ai_image manifests and reports."
  ]
}
```
