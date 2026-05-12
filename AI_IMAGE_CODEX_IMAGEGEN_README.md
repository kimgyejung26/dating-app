# Seolleyeon Codex `$imagegen` Workflow

This workflow uses Codex built-in `$imagegen` only. It does not use the OpenAI Image API, Batch API, or `OPENAI_API_KEY` for image generation.

## Core loop

```powershell
mingw32-make ai-image-prepare-720
mingw32-make ai-image-next
# copy the printed command into Codex:
# $imagegen "..."
mingw32-make ai-image-recover
mingw32-make ai-image-qa
mingw32-make ai-image-summary
mingw32-make ai-image-contact-sheets
```

`$imagegen` is interruptible. If a generated image appears, the next turn must recover the pending image first before creating another prompt. `mingw32-make ai-image-recover` imports the image, updates the manifest, marks `pending-imagegen.json` as recovered, and runs file QA for the recovered asset.

## Generated image import path

Default generated image root:

```text
C:/Users/samsung/.codex/generated_images
```

Override with:

```powershell
$env:CODEX_GENERATED_IMAGES_DIR="C:\Users\samsung\.codex\generated_images"
```

## Checkpoint contract

`mingw32-make ai-image-next` writes:

```text
ai_image/manifests/pending-imagegen.json
```

Required identity fields include `assetId`, `profileId`, `gender`, `numericId`, `shotType`, `attempt`, expected raw path, expected final path, prompt, and recovery instructions.
The checkpoint also records approved/rejected expected paths and the face reference path for dependent shots.

Recovery maps identity from `pending-imagegen.json` only. Do not infer identity by looking at the generated picture.

## Storage layout

```text
ai_image/
  raw/
    {assetId}__attemptXX.png
  approved/
    {assetId}.png
  rejected/
    {assetId}__attemptXX.png
  female/{numericId}/{shotType}.png
  male/{numericId}/{shotType}.png
  manifests/
    identity_manifest.jsonl
    imagegen_queue.jsonl
    pending-imagegen.json
    generation_manifest.jsonl
    qa_manifest.jsonl
    retry_manifest.jsonl
  reports/
    generation_status.csv
    qa_report.csv
    vision_qa_report.jsonl
    summary.json
    contact_sheets/
```

## Shot prompt wrappers

The prompt source remains `seolleyeon_ai_profile_prompt_v3.py`. The Codex `$imagegen` prompt is wrapped at pending-checkpoint time:

- `face_card`: one vertical realistic smartphone profile photo plus asset metadata and hard safety rules.
- `silhouette_card`: same-person reference from the approved `face_card`, realistic 3/4 or full-body smartphone profile photo.
- `vibe_card`: same-person reference from the approved `face_card`, realistic campus/cafe/library/exhibition lifestyle profile photo.

Dependent shots wait until the active identity has an approved `face_card`.

## 720 approved-image target

The full target is **240 complete approved identities × 3 shots = 720 final approved images**.

- female approved identities: 120
- male approved identities: 120
- reserve female identities: 20
- reserve male identities: 20

Reserve identities are activated only when an active same-gender identity fails after max attempts.
