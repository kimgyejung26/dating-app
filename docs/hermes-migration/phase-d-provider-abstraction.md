# Phase D Provider Abstraction

Run D adds a narrow provider contract for future Hermes image generation work without replacing the current Codex built-in `$imagegen` and OMX pipeline.

## Current Backend

The default provider remains `codex-built-in-imagegen`.

The existing production path is unchanged:

1. Write `ai_image/manifests/pending-imagegen.json`.
2. Invoke Codex built-in `$imagegen` outside Python.
3. Recover the generated image into `ai_image/raw/{assetId}__attemptXX.png`.
4. Copy the final candidate to `ai_image/{gender}/{numeric_id}/{shotType}.png`.
5. Run QA only after the image exists locally.

The provider abstraction does not call the OpenAI Image API, does not create Batch API JSONL, and does not require `OPENAI_API_KEY`.

## Provider Contract

`scripts/ai_image_pipeline_v3/image_provider.py` defines:

- `ImageProviderRequest`: prompt, local output path, optional reference image paths, provider metadata, and overwrite intent.
- `ImageProviderResult`: provider name, output path, persistence flag, and provider metadata.
- `assert_output_persisted_locally(...)`: rejects missing, empty, non-file, or out-of-`ai_image/` outputs before downstream QA.
- `default_image_provider()`: returns a non-generating descriptor for the existing Codex/OMX backend.
- `FixtureImageProvider`: writes a local PNG fixture for tests only.
- `HermesNativeImageProvider`: scaffold adapter for future Hermes-native text-to-image execution.

## Reference Image Policy

`face_card` remains the required identity anchor for dependent shots.

The Hermes-native scaffold is text-to-image only by default. It rejects `reference_image_paths` with `ReferenceImagesUnsupportedError` unless a reference-capable plugin is explicitly verified and configured. This prevents independent text-only generation of `silhouette_card` or `vibe_card` when same-person reference support is unavailable.

## Compatibility Notes

- No existing OMX, Ralph, bounded chunk, pending recovery, or visual QA commands were removed.
- Live generation remains interruptible and resumable through the current pending/recovery files.
- The fixture provider is for tests and local contract checks; it is not a quality-approved Seolleyeon image generator.
- The Codex provider is intentionally a descriptor, not a direct Python generator, because the current backend is an operator/Codex `$imagegen` surface with explicit checkpoint recovery.

## Verification

Run D tests:

```powershell
python -m unittest tests.test_image_provider_v3
```

Focused A/B/C/D regression set:

```powershell
python -m unittest tests.test_hermes_visual_verdict_skill_v3 tests.test_active_visual_verdict_runner_v3 tests.test_ai_image_visual_verdict_manifest_v3 tests.test_hermes_wrapper_v3 tests.test_identity_parallel_v3 tests.test_image_provider_v3
```
