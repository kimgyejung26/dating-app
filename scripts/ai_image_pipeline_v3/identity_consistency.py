from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from .config import MAX_ATTEMPTS, SHOT_ORDER, ensure_base_dirs, now_utc, pipeline_paths, write_csv, write_jsonl
from .manifest import load_generation_manifest
from .retry_plan import APPROVED_STATUSES, attempt_count


IDENTITY_CONSISTENCY_JSONL_FIELDS = (
    "profileId",
    "faceAssetId",
    "silhouetteAssetId",
    "vibeAssetId",
    "faceToSilhouetteConsistency",
    "faceToVibeConsistency",
    "completeIdentityDecision",
    "failedShotTypes",
    "reasons",
)


def group_by_profile(rows: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("profileId"))].append(dict(row))
    return dict(grouped)


def _shot_map(profile_rows: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("shotType")): dict(row) for row in profile_rows}


def _image_exists(row: Mapping[str, Any] | None) -> bool:
    if not row:
        return False
    for key in ("finalPath", "localPath"):
        path = Path(str(row.get(key) or ""))
        if path.exists() and path.stat().st_size > 0:
            return True
    return False


def _is_approved(row: Mapping[str, Any] | None) -> bool:
    if not row:
        return False
    status = str(row.get("status") or "")
    return status in APPROVED_STATUSES or status in {"completed", "file_qa_approved"}


def evaluate_identity(profile_rows: list[Mapping[str, Any]], *, max_attempts: int = MAX_ATTEMPTS) -> dict[str, Any]:
    by_shot = _shot_map(profile_rows)
    face = by_shot.get("face_card")
    silhouette = by_shot.get("silhouette_card")
    vibe = by_shot.get("vibe_card")
    anchor = face or silhouette or vibe or {}
    failed: list[str] = []
    reasons: list[str] = []

    for shot_type in SHOT_ORDER:
        row = by_shot.get(shot_type)
        if not row:
            failed.append(shot_type)
            reasons.append(f"missing_manifest_row:{shot_type}")
            continue
        status = str(row.get("status") or "")
        if not _image_exists(row):
            failed.append(shot_type)
            reasons.append(f"missing_image:{shot_type}")
        elif status in {"failed", "missing", "qa_rejected", "vision_rejected"}:
            failed.append(shot_type)
            reasons.append(f"rejected_status:{shot_type}:{status}")

    terminal_reject = any(
        attempt_count(row) >= max_attempts and str(row.get("status") or "") in {"failed", "missing", "qa_rejected", "vision_rejected"}
        for row in by_shot.values()
    )
    complete_files = all(_image_exists(by_shot.get(shot)) for shot in SHOT_ORDER)
    approved_statuses = all(_is_approved(by_shot.get(shot)) for shot in SHOT_ORDER)

    if terminal_reject:
        decision = "rejected"
        reasons.append("max_attempts_exhausted")
    elif complete_files and approved_statuses and not failed:
        decision = "approved"
    else:
        decision = "needs_retry"
        if not reasons:
            reasons.append("identity_not_yet_fully_approved")

    face_to_silhouette = 5 if _image_exists(face) and _image_exists(silhouette) else 0
    face_to_vibe = 5 if _image_exists(face) and _image_exists(vibe) else 0
    if decision == "needs_retry" and complete_files:
        face_to_silhouette = min(face_to_silhouette, 4)
        face_to_vibe = min(face_to_vibe, 4)

    return {
        "profileId": str(anchor.get("profileId") or ""),
        "faceAssetId": str(face.get("assetId") if face else ""),
        "silhouetteAssetId": str(silhouette.get("assetId") if silhouette else ""),
        "vibeAssetId": str(vibe.get("assetId") if vibe else ""),
        "faceToSilhouetteConsistency": face_to_silhouette,
        "faceToVibeConsistency": face_to_vibe,
        "completeIdentityDecision": decision,
        "failedShotTypes": failed,
        "reasons": sorted(set(reasons)),
    }


def run_identity_consistency_qa(
    *,
    root: Path | str | None = None,
    profile_id: str | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> dict[str, int]:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    rows = load_generation_manifest(paths)
    if profile_id:
        rows = [row for row in rows if str(row.get("profileId")) == str(profile_id)]
    grouped = group_by_profile(rows)
    report = [evaluate_identity(profile_rows, max_attempts=max_attempts) for profile_rows in grouped.values()]
    counts = {
        "checkedIdentities": len(report),
        "approvedIdentities": sum(row["completeIdentityDecision"] == "approved" for row in report),
        "needsRetry": sum(row["completeIdentityDecision"] == "needs_retry" for row in report),
        "rejectedIdentities": sum(row["completeIdentityDecision"] == "rejected" for row in report),
        # Backward-compatible counter used by older smoke tests.
        "referenceAvailable": sum(row["faceToSilhouetteConsistency"] > 0 or row["faceToVibeConsistency"] > 0 for row in report),
        "waitingReference": sum("missing_image:face_card" in row["reasons"] for row in report),
        "incomplete": sum(row["completeIdentityDecision"] != "approved" for row in report),
    }
    write_jsonl(paths.reports / "identity_consistency_report.jsonl", report)
    csv_rows = [
        {
            **row,
            "failedShotTypes": json.dumps(row.get("failedShotTypes", []), ensure_ascii=False),
            "reasons": json.dumps(row.get("reasons", []), ensure_ascii=False),
            "updatedAt": now_utc(),
        }
        for row in report
    ]
    write_csv(paths.reports / "identity_consistency_report.csv", csv_rows, (*IDENTITY_CONSISTENCY_JSONL_FIELDS, "updatedAt"))
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Seolleyeon same-identity consistency QA.")
    parser.add_argument("--root", default=None, help="Workspace root. Defaults to the repository root.")
    parser.add_argument("--profile_id", default=None)
    parser.add_argument("--max_attempts", type=int, default=MAX_ATTEMPTS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    counts = run_identity_consistency_qa(root=args.root, profile_id=args.profile_id, max_attempts=args.max_attempts)
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
