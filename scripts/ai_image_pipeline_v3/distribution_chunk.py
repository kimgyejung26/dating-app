from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .codex_imagegen import build_pending_payload, pending_path, read_pending, write_pending
from .config import MAX_ATTEMPTS, SHOT_ORDER, ensure_base_dirs, now_utc, pipeline_paths, to_portable_path
from .distribution_selection import select_distribution_buckets
from .manifest import load_generation_manifest, manifest_path, write_generation_outputs
from .pending_state import pending_is_unresolved, pending_requires_recovery, pending_unresolved_reason
from .retry_plan import APPROVED_STATUSES, attempt_count


def _pending_requires_recovery(payload: Mapping[str, Any] | None) -> bool:
    return pending_requires_recovery(payload)


def _image_exists(row: Mapping[str, Any]) -> bool:
    for key in ("finalPath", "approvedPath", "localPath"):
        value = row.get(key)
        if value and Path(str(value)).exists() and Path(str(value)).stat().st_size > 0:
            return True
    return False


def _is_approved(row: Mapping[str, Any]) -> bool:
    return str(row.get("status") or "") in APPROVED_STATUSES and _image_exists(row)


def _face_ready(by_shot: Mapping[str, Mapping[str, Any]]) -> bool:
    face = by_shot.get("face_card")
    return bool(face and (_is_approved(face) or _image_exists(face)))


def choose_next_asset_for_identities(
    rows: list[Mapping[str, Any]],
    selected_profile_ids: list[str],
    *,
    max_attempts: int,
    force: bool = False,
) -> dict[str, Any] | None:
    rows_by_profile: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_profile.setdefault(str(row.get("profileId") or ""), []).append(dict(row))
    for profile_id in selected_profile_ids:
        profile_rows = rows_by_profile.get(profile_id, [])
        by_shot = {str(row.get("shotType") or ""): row for row in profile_rows}
        for shot_type in SHOT_ORDER:
            row = by_shot.get(shot_type)
            if not row:
                continue
            if not force and _is_approved(row):
                continue
            if str(row.get("status") or "") == "pending_imagegen":
                continue
            if shot_type != "face_card" and not _face_ready(by_shot):
                continue
            if attempt_count(row) >= max_attempts and not force:
                continue
            return dict(row)
    return None


def next_distribution_chunk(
    *,
    root: Path | str | None = None,
    max_identities: int = 24,
    max_attempts: int = MAX_ATTEMPTS,
    force: bool = False,
    refresh_audit: bool = True,
) -> dict[str, Any]:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    manual_flag = paths.manifests / "manual_review_required.flag"
    if manual_flag.exists():
        return {"status": "manual_review_required", "manualReviewFlag": to_portable_path(manual_flag)}

    pending_file = pending_path(root)
    pending = read_pending(pending_file)
    if _pending_requires_recovery(pending):
        return {
            "status": "pending_requires_recovery",
            "pendingPath": to_portable_path(pending_file),
            "assetId": pending.get("assetId"),
        }
    if pending_is_unresolved(pending):
        return {
            "status": "unresolved_pending_imagegen",
            "pendingPath": to_portable_path(pending_file),
            "reason": pending_unresolved_reason(pending),
        }

    selection = select_distribution_buckets(
        root=root,
        refresh_audit=refresh_audit,
        max_identities=max_identities,
        max_attempts=max_attempts,
    )
    selected_profile_ids = [str(row["profileId"]) for row in selection["selectedIdentities"]]
    rows = load_generation_manifest(paths)
    row = choose_next_asset_for_identities(rows, selected_profile_ids, max_attempts=max_attempts, force=force)
    chunk_path = paths.manifests / "current_distribution_chunk.json"
    chunk_payload = {
        **selection,
        "status": "selected" if row else "no_eligible_asset",
        "selectedAssetId": row.get("assetId") if row else "",
        "updatedAt": now_utc(),
    }
    chunk_path.write_text(json.dumps(chunk_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if not row:
        return {**chunk_payload, "chunkPath": to_portable_path(chunk_path)}

    attempt = attempt_count(row) + 1
    payload = build_pending_payload(
        paths_root=root,
        row=row,
        attempt=attempt,
        queue_file=paths.manifests / "imagegen_queue.jsonl",
        manifest_file=manifest_path(paths),
        out_pending=pending_file,
    )
    payload["distributionChunkPath"] = to_portable_path(chunk_path)
    payload["distributionChunkProfileIds"] = selected_profile_ids
    write_pending(pending_file, payload)

    updated: list[dict[str, Any]] = []
    for item in rows:
        out = dict(item)
        if str(out.get("assetId")) == str(row.get("assetId")):
            out.update(
                {
                    "status": "pending_imagegen",
                    "attempt": attempt,
                    "attemptCount": attempt,
                    "pendingPath": to_portable_path(pending_file),
                    "expectedRawPath": payload["expectedRawPath"],
                    "expectedFinalPath": payload["expectedFinalPath"],
                    "expectedApprovedPath": payload["expectedApprovedPath"],
                    "expectedRejectedPath": payload["expectedRejectedPath"],
                    "finalPath": payload["expectedFinalPath"],
                    "approvedPath": payload["expectedApprovedPath"],
                    "rejectedPath": payload["expectedRejectedPath"],
                    "resolvedReferencePath": payload["referenceImagePath"],
                    "updatedAt": now_utc(),
                    "error": "",
                }
            )
        updated.append(out)
    write_generation_outputs(paths, updated)
    history_path = paths.manifests / "distribution_chunk_history.jsonl"
    with history_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(chunk_payload, ensure_ascii=False) + "\n")
    return {
        **chunk_payload,
        "status": "pending_written",
        "pendingPath": to_portable_path(pending_file),
        "assetId": payload["assetId"],
        "profileId": payload["profileId"],
        "shotType": payload["shotType"],
        "attempt": payload["attempt"],
        "prompt": payload["prompt"],
        "imagegenCommand": "$imagegen " + json.dumps(payload["prompt"], ensure_ascii=False),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a deficit-aware Codex $imagegen pending checkpoint for the next chunk.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--max_identities", type=int, default=24)
    parser.add_argument("--chunk_identities", dest="max_identities", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--max_attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no_refresh_audit", action="store_true")
    parser.add_argument("--targets_json", default=None, help="Compatibility option; targets are loaded from ai_image/config.")
    parser.add_argument("--audit_json", default=None, help="Compatibility option; latest audit path remains standardized.")
    parser.add_argument("--queue", default=None, help="Compatibility option; imagegen queue path remains standardized.")
    parser.add_argument("--out_pending", default=None, help="Compatibility option; pending path remains standardized.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = next_distribution_chunk(
        root=args.root,
        max_identities=args.max_identities,
        max_attempts=args.max_attempts,
        force=args.force,
        refresh_audit=not args.no_refresh_audit,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "prompt"}, ensure_ascii=False, indent=2))
    if result.get("prompt"):
        print("\n--- CODEX_IMAGEGEN_PROMPT ---")
        print(result["prompt"])
    return 0 if result.get("status") in {"pending_written", "no_eligible_asset"} else 2
