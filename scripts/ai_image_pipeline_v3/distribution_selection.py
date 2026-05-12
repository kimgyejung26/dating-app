from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from .config import MAX_ATTEMPTS, SHOT_ORDER, ensure_base_dirs, pipeline_paths, read_jsonl
from .distribution_audit import audit_distribution, group_by_profile
from .distribution_targets import FACE_TYPES, LOOKS_LEVEL_BANDS, target_face_type, target_looks_level_band
from .manifest import load_generation_manifest
from .retry_plan import APPROVED_STATUSES, attempt_count


def _latest_audit(root: Path | str | None = None, *, refresh: bool = False) -> dict[str, Any]:
    paths = pipeline_paths(root)
    latest = paths.reports / "latest_distribution_audit.json"
    if refresh or not latest.exists():
        return audit_distribution(root=root)
    return json.loads(latest.read_text(encoding="utf-8"))


def deficit_sets(audit: Mapping[str, Any]) -> dict[str, dict[str, set[str]]]:
    result: dict[str, dict[str, set[str]]] = {
        "global": {"faceType": set(), "looksLevelBand": set()},
        "female": {"faceType": set(), "looksLevelBand": set()},
        "male": {"faceType": set(), "looksLevelBand": set()},
    }
    for row in audit.get("bucketChecks", []):
        if not isinstance(row, Mapping):
            continue
        if int(row.get("deficit") or 0) <= 0:
            continue
        scope = str(row.get("scope") or "")
        dimension = str(row.get("dimension") or "")
        bucket = str(row.get("bucket") or "")
        if scope in result and dimension in result[scope]:
            result[scope][dimension].add(bucket)
    return result


def is_bucket_allowed(gender: str, face_type: str, looks_band: str, deficits: Mapping[str, Mapping[str, set[str]]]) -> bool:
    return (
        face_type in deficits.get("global", {}).get("faceType", set())
        and face_type in deficits.get(gender, {}).get("faceType", set())
        and looks_band in deficits.get("global", {}).get("looksLevelBand", set())
        and looks_band in deficits.get(gender, {}).get("looksLevelBand", set())
        and looks_band != "4.4-5.0"
    )


def _identity_complete(profile_rows: list[Mapping[str, Any]]) -> bool:
    by_shot = {str(row.get("shotType") or ""): row for row in profile_rows}
    return all(str(by_shot.get(shot, {}).get("status") or "") in APPROVED_STATUSES for shot in SHOT_ORDER)


def _abandoned_profile_ids(root: Path | str | None = None) -> set[str]:
    rows = read_jsonl(pipeline_paths(root).manifests / "abandoned_chunk_manifest.jsonl")
    return {str(row.get("profileId") or "") for row in rows if row.get("profileId")}


def select_distribution_buckets(
    *,
    root: Path | str | None = None,
    refresh_audit: bool = False,
    max_identities: int = 24,
    max_attempts: int = MAX_ATTEMPTS,
    exclude_abandoned: bool = True,
    exclude_profile_ids: set[str] | None = None,
) -> dict[str, Any]:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    audit = _latest_audit(root, refresh=refresh_audit)
    deficits = deficit_sets(audit)
    rows = load_generation_manifest(paths)
    grouped = group_by_profile(rows)
    allowed_identities: list[dict[str, Any]] = []
    forbidden_buckets: list[dict[str, Any]] = []
    seen_forbidden: set[tuple[str, str, str]] = set()
    excluded_profiles = set(exclude_profile_ids or set())
    if exclude_abandoned:
        excluded_profiles.update(_abandoned_profile_ids(root))

    for profile_id, profile_rows in sorted(grouped.items()):
        if profile_id in excluded_profiles:
            continue
        anchor = profile_rows[0]
        gender = str(anchor.get("gender") or "")
        if gender not in {"female", "male"}:
            continue
        if not bool(anchor.get("activeForTarget", True)):
            continue
        if _identity_complete(profile_rows):
            continue
        face_type = target_face_type(anchor)
        looks_band = target_looks_level_band(anchor)
        key = (gender, face_type, looks_band)
        if not is_bucket_allowed(gender, face_type, looks_band, deficits):
            if key not in seen_forbidden:
                seen_forbidden.add(key)
                forbidden_buckets.append({"gender": gender, "targetFaceType": face_type, "targetLooksLevelBand": looks_band})
            continue
        if all(attempt_count(row) >= max_attempts and str(row.get("status") or "") not in APPROVED_STATUSES for row in profile_rows):
            continue
        allowed_identities.append(
            {
                "profileId": profile_id,
                "gender": gender,
                "targetFaceType": face_type,
                "targetLooksLevelBand": looks_band,
                "shotStatuses": {str(row.get("shotType") or ""): str(row.get("status") or "") for row in profile_rows},
            }
        )
        if len(allowed_identities) >= max_identities:
            break

    allowed_bucket_keys = sorted(
        {
            (identity["gender"], identity["targetFaceType"], identity["targetLooksLevelBand"])
            for identity in allowed_identities
        }
    )
    return {
        "schemaVersion": "seolleyeon_next_distribution_buckets_v3",
        "maxIdentities": int(max_identities),
        "allowedBuckets": [
            {"gender": gender, "targetFaceType": face_type, "targetLooksLevelBand": looks_band}
            for gender, face_type, looks_band in allowed_bucket_keys
        ],
        "forbiddenBuckets": forbidden_buckets,
        "selectedIdentities": allowed_identities,
        "deficitSets": {
            scope: {dimension: sorted(values) for dimension, values in dimensions.items()}
            for scope, dimensions in deficits.items()
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select deficit-only distribution buckets for the next Seolleyeon imagegen chunk.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--refresh_audit", action="store_true")
    parser.add_argument("--max_identities", type=int, default=24)
    parser.add_argument("--chunk_identities", dest="max_identities", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--max_attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--targets_json", default=None, help="Compatibility option; targets are loaded from ai_image/config.")
    parser.add_argument("--audit_json", default=None, help="Compatibility option; latest audit path remains standardized.")
    parser.add_argument("--queue", default=None, help="Compatibility option; imagegen queue path remains standardized.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = select_distribution_buckets(
        root=args.root,
        refresh_audit=args.refresh_audit,
        max_identities=args.max_identities,
        max_attempts=args.max_attempts,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
