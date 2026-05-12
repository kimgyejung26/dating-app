from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from .config import MAX_ATTEMPTS, SHOT_ORDER, now_utc, pipeline_paths
from .manifest import load_generation_manifest, write_generation_outputs
from .retry_plan import APPROVED_STATUSES, attempt_count


TERMINAL_REJECT_STATUSES = {"failed", "missing", "qa_rejected", "vision_rejected"}


def group_rows_by_profile(rows: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("profileId", ""))].append(dict(row))
    return dict(grouped)


def _image_exists(row: Mapping[str, Any]) -> bool:
    for key in ("finalPath", "localPath"):
        path = Path(str(row.get(key) or ""))
        if path.exists() and path.stat().st_size > 0:
            return True
    return False


def _asset_approved(row: Mapping[str, Any]) -> bool:
    return str(row.get("status") or "") in APPROVED_STATUSES and _image_exists(row)


def approved_identity_report(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    grouped = group_rows_by_profile(rows)
    approved_profiles: list[str] = []
    gender_counts = {"female": 0, "male": 0}
    approved_assets = 0
    for profile_id, profile_rows in grouped.items():
        if not profile_rows or not bool(profile_rows[0].get("activeForTarget", True)):
            continue
        by_shot = {str(row.get("shotType")): row for row in profile_rows}
        if all(shot in by_shot and _asset_approved(by_shot[shot]) for shot in SHOT_ORDER):
            approved_profiles.append(profile_id)
            gender = str(profile_rows[0].get("gender", ""))
            if gender in gender_counts:
                gender_counts[gender] += 1
            approved_assets += len(SHOT_ORDER)
    return {
        "approvedIdentities": len(approved_profiles),
        "approvedAssets": approved_assets,
        "approvedFemaleIdentities": gender_counts["female"],
        "approvedMaleIdentities": gender_counts["male"],
        "approvedProfileIds": sorted(approved_profiles),
    }


def target_reached(rows: list[Mapping[str, Any]], *, target_identities: int, target_assets: int) -> bool:
    report = approved_identity_report(rows)
    return int(report["approvedIdentities"]) >= target_identities and int(report["approvedAssets"]) >= target_assets


def _profile_exhausted(profile_rows: list[Mapping[str, Any]], *, max_attempts: int) -> bool:
    return any(
        str(row.get("status") or "") in TERMINAL_REJECT_STATUSES and attempt_count(row) >= max_attempts
        for row in profile_rows
    )


def _next_standby_reserve(grouped: dict[str, list[dict[str, Any]]], *, gender: str) -> str | None:
    candidates = []
    for profile_id, profile_rows in grouped.items():
        if not profile_rows:
            continue
        first = profile_rows[0]
        if (
            str(first.get("gender")) == gender
            and bool(first.get("isReserve"))
            and str(first.get("reserveStatus") or "standby") == "standby"
            and not bool(first.get("activeForTarget", False))
        ):
            candidates.append(profile_id)
    return sorted(candidates)[0] if candidates else None


def apply_reserve_policy(
    *,
    root: Path | str | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> dict[str, int]:
    paths = pipeline_paths(root)
    rows = load_generation_manifest(paths)
    grouped = group_rows_by_profile(rows)
    rejected_profiles: list[str] = []
    activated_profiles: list[str] = []

    for profile_id, profile_rows in list(grouped.items()):
        if not profile_rows:
            continue
        first = profile_rows[0]
        if not bool(first.get("activeForTarget", True)):
            continue
        if str(first.get("identityDecision") or "") == "rejected":
            continue
        if not _profile_exhausted(profile_rows, max_attempts=max_attempts):
            continue
        rejected_profiles.append(profile_id)
        gender = str(first.get("gender"))
        for row in rows:
            if str(row.get("profileId")) == profile_id:
                row["identityDecision"] = "rejected"
                row["activeForTarget"] = False
                row["updatedAt"] = now_utc()
                if bool(row.get("isReserve")):
                    row["reserveStatus"] = "rejected"
        reserve_profile_id = _next_standby_reserve(grouped, gender=gender)
        if reserve_profile_id:
            activated_profiles.append(reserve_profile_id)
            for row in rows:
                if str(row.get("profileId")) == reserve_profile_id:
                    row["reserveStatus"] = "activated"
                    row["activeForTarget"] = True
                    row["identityDecision"] = ""
                    row["updatedAt"] = now_utc()
            # Update grouped snapshot so the same reserve cannot be activated twice in this pass.
            for row in grouped[reserve_profile_id]:
                row["reserveStatus"] = "activated"
                row["activeForTarget"] = True

    if rejected_profiles or activated_profiles:
        write_generation_outputs(paths, rows)
    return {
        "rejectedIdentities": len(rejected_profiles),
        "activatedReserveIdentities": len(activated_profiles),
    }


def summarize_target_state(*, root: Path | str | None = None) -> dict[str, Any]:
    rows = load_generation_manifest(pipeline_paths(root))
    report = approved_identity_report(rows)
    active = [row for row in rows if bool(row.get("activeForTarget", True))]
    standby_reserve_profiles = {
        str(row.get("profileId"))
        for row in rows
        if bool(row.get("isReserve")) and str(row.get("reserveStatus") or "standby") == "standby"
    }
    report.update(
        {
            "activeAssets": len(active),
            "standbyReserveIdentities": len(standby_reserve_profiles),
        }
    )
    return report
