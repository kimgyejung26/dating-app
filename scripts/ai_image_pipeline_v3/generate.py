from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable

from .config import (
    DEFAULT_CONCURRENCY,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_QUALITY,
    DEFAULT_SIZE,
    ensure_base_dirs,
    now_utc,
    pipeline_paths,
    shot_sort_key,
    to_portable_path,
)
from .identity import attach_resolved_reference, face_reference_candidates, filter_rows_for_profile, parse_profile_id
from .manifest import load_generation_manifest, write_generation_outputs
from .retry_plan import select_retryable_assets


def identity_reference_prompt(prompt: str) -> str:
    return (
        "Use the provided face_card image only as a same-person identity reference. "
        "Keep facial identity, visual age, natural grooming, and trust-based campus tone consistent. "
        "Do not copy the exact composition; follow the requested shot type below.\n\n"
        f"{prompt}"
    )


def select_assets(
    rows: Iterable[dict[str, Any]],
    *,
    limit: int | None,
    retry_only: bool,
    profile_id: str | None = None,
    shot_type: str | None = None,
    active_only: bool = False,
    max_attempts: int = 3,
    force: bool = False,
) -> list[dict[str, Any]]:
    ordered = sorted([dict(row) for row in rows], key=shot_sort_key)
    ordered = filter_rows_for_profile(ordered, profile_id)
    if shot_type:
        ordered = [row for row in ordered if str(row.get("shotType")) == str(shot_type)]
    if active_only:
        ordered = [row for row in ordered if bool(row.get("activeForTarget", True))]
    if retry_only:
        ordered = select_retryable_assets(ordered, max_attempts=max_attempts, force=force)
    if limit:
        ordered = ordered[:limit]
    return ordered


def generation_sequence(
    rows: Iterable[dict[str, Any]],
    *,
    selected_ids: set[str],
    two_pass_reference: bool,
) -> list[dict[str, Any]]:
    selected = [row for row in rows if str(row.get("assetId")) in selected_ids]
    if not two_pass_reference:
        return selected
    face_cards = [row for row in selected if str(row.get("shotType")) == "face_card"]
    dependent_cards = [row for row in selected if str(row.get("shotType")) != "face_card"]
    return [*face_cards, *dependent_cards]


def write_image_atomically(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def generate_images(
    *,
    root: Path | str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    force: bool = False,
    retry_only: bool = False,
    model: str = DEFAULT_MODEL,
    size: str = DEFAULT_SIZE,
    quality: str = DEFAULT_QUALITY,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    target_profile_id: str | None = None,
    target_approved_identity: str | None = None,
    shot_type: str | None = None,
    active_only: bool = False,
    max_attempts: int = 3,
    two_pass_reference: bool = True,
    approved_face_reference: bool = False,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict[str, int]:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    rows = load_generation_manifest(paths)
    if not rows:
        raise FileNotFoundError(f"Generation manifest not found or empty: {paths.manifests / 'generation_manifest.jsonl'}")

    if target_profile_id and target_approved_identity:
        raise ValueError("Use either target_profile_id or target_approved_identity, not both.")
    profile_filter = parse_profile_id(target_approved_identity).profile_id if target_approved_identity else target_profile_id
    prefer_approved_reference = bool(target_approved_identity)
    selected_ids = {
        str(row["assetId"])
        for row in select_assets(
            rows,
            limit=limit,
            retry_only=retry_only,
            profile_id=profile_filter,
            shot_type=shot_type,
            active_only=active_only,
            max_attempts=max_attempts,
            force=force,
        )
    }
    counts = {"selected": len(selected_ids), "completed": 0, "skipped": 0, "failed": 0, "dry_run": 0, "waiting_reference": 0}
    _ = max(1, int(concurrency))  # Compatibility only; Codex $imagegen is driven one checkpoint at a time.

    for row in generation_sequence(rows, selected_ids=selected_ids, two_pass_reference=two_pass_reference):
        asset_id = str(row["assetId"])
        local_path = Path(str(row["localPath"]))
        row["model"] = model
        row["size"] = size
        row["quality"] = quality
        row["outputFormat"] = output_format
        row.update(attach_resolved_reference(paths, row, prefer_approved=prefer_approved_reference or approved_face_reference))
        row["updatedAt"] = now_utc()

        if dry_run:
            row["status"] = "dry_run"
            row["dryRun"] = True
            row["error"] = ""
            counts["dry_run"] += 1
            continue

        if prefer_approved_reference and str(row["shotType"]) == "face_card" and not force:
            existing_anchor = next(
                (candidate for candidate in face_reference_candidates(paths, row, prefer_approved=True) if candidate.exists()),
                None,
            )
            if existing_anchor:
                row["status"] = "qa_approved"
                row["dryRun"] = False
                row["resolvedReferencePath"] = to_portable_path(existing_anchor)
                row["error"] = "Approved face_card anchor exists; target-approved-identity mode keeps it unchanged."
                counts["skipped"] += 1
                continue

        final_path = Path(str(row.get("finalPath") or ""))
        if final_path.exists() and not force and str(row.get("status")) in {"completed", "qa_approved", "vision_approved"}:
            counts["skipped"] += 1
            continue
        if local_path.exists() and not force and str(row.get("status")) == "completed":
            counts["skipped"] += 1
            continue
        if local_path.exists() and not force and str(row.get("status")) != "completed":
            row["status"] = "completed"
            row["error"] = "Existing image found; marked completed without overwrite."
            counts["skipped"] += 1
            continue

        reference_path = Path(str(row.get("resolvedReferencePath") or row.get("referenceLocalPath") or ""))
        if str(row["shotType"]) != "face_card" and not reference_path.exists():
            row["status"] = "waiting_reference"
            row["error"] = f"Missing face_card reference: {reference_path}"
            counts["waiting_reference"] += 1
            continue

        row["status"] = "queued"
        row["dryRun"] = False
        row["error"] = (
            "Direct image API generation is disabled. Use scripts/next_codex_imagegen_prompt_v3.py, "
            "Codex built-in $imagegen, then scripts/recover_pending_imagegen_v3.py."
        )
        counts["skipped"] += 1

    write_generation_outputs(paths, rows)
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Seolleyeon AI profile images from v3 manifest.")
    parser.add_argument("--root", default=None, help="Workspace root. Defaults to the repository root.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--retry_only", action="store_true")
    parser.add_argument("--target_profile_id", default=None, help="Generate only one profileId, such as female_001.")
    parser.add_argument("--shot_type", choices=["face_card", "silhouette_card", "vibe_card"], default=None)
    parser.add_argument("--active_only", action="store_true", help="Only generate rows active for target-approved production.")
    parser.add_argument(
        "--target_approved_identity",
        default=None,
        help="Generate one profileId using its approved/final face_card as reference for second-pass shots.",
    )
    parser.add_argument("--max_attempts", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument(
        "--approved_face_reference",
        action="store_true",
        help="Require dependent shots to resolve their face reference from approved/final images first.",
    )
    parser.add_argument(
        "--single_pass",
        action="store_true",
        help="Disable default two-pass reference generation. Operational use should keep two-pass enabled.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--quality", default=DEFAULT_QUALITY)
    parser.add_argument("--output_format", default=DEFAULT_OUTPUT_FORMAT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    counts = generate_images(
        root=args.root,
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force,
        retry_only=args.retry_only,
        model=args.model,
        size=args.size,
        quality=args.quality,
        output_format=args.output_format,
        target_profile_id=args.target_profile_id,
        target_approved_identity=args.target_approved_identity,
        shot_type=args.shot_type,
        active_only=args.active_only,
        max_attempts=args.max_attempts,
        two_pass_reference=not args.single_pass,
        approved_face_reference=args.approved_face_reference,
        concurrency=args.concurrency,
    )
    print(counts)
    return 0
