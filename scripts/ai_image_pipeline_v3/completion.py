from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import SHOT_ORDER, pipeline_paths, read_jsonl
from .distribution_audit import audit_distribution
from .pending_state import pending_is_resolved, pending_unresolved_reason


COMPLETION_FAILURE_REASON_ORDER = (
    "manual_review_required",
    "unresolved_pending_imagegen",
    "missing_visual_verdict",
    "invalid_counted_identity",
    "distribution_mismatch",
    "surplus_bucket",
    "over_level_approved",
)


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "approved"}


def _failure_list(reasons: set[str]) -> list[str]:
    ordered = [reason for reason in COMPLETION_FAILURE_REASON_ORDER if reason in reasons]
    ordered.extend(sorted(reason for reason in reasons if reason not in set(ordered)))
    return ordered


def _pending_unresolved(pending_path: Path) -> tuple[bool, str]:
    if not pending_path.exists():
        return False, ""
    try:
        payload = json.loads(pending_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True, "pending_json_invalid"
    if not isinstance(payload, dict):
        return True, "pending_json_not_object"
    if pending_is_resolved(payload):
        return False, ""
    return True, pending_unresolved_reason(payload)


def _visual_manifest_state(root: Path | str | None) -> dict[str, Any]:
    paths = pipeline_paths(root)
    asset_rows = read_jsonl(paths.manifests / "asset_qa_manifest.jsonl")
    identity_rows = read_jsonl(paths.manifests / "identity_qa_manifest.jsonl")
    generation_rows = read_jsonl(paths.manifests / "generation_manifest.jsonl")
    asset_shots_by_profile: dict[str, set[str]] = {}
    for row in asset_rows:
        profile_id = str(row.get("profileId") or "")
        shot = str(row.get("shotType") or "")
        if profile_id and shot:
            asset_shots_by_profile.setdefault(profile_id, set()).add(shot)
    return {
        "assetRows": asset_rows,
        "identityRows": identity_rows,
        "generationRows": generation_rows,
        "identityProfiles": {str(row.get("profileId") or "") for row in identity_rows if row.get("profileId")},
        "assetShotsByProfile": asset_shots_by_profile,
        "assetQaRows": len(asset_rows),
        "identityQaRows": len(identity_rows),
        "generationRowsCount": len(generation_rows),
        "visualMissing": not asset_rows or not identity_rows,
    }


def _invalid_counted_identities(audit: dict[str, Any]) -> list[dict[str, Any]]:
    invalid: list[dict[str, Any]] = []
    required_shots = set(SHOT_ORDER)
    candidates: list[dict[str, Any]] = []
    for identity in audit.get("approvedIdentities", []):
        if isinstance(identity, dict):
            candidates.append(identity)
    for identity in audit.get("evaluatedIdentities", []):
        if not isinstance(identity, dict):
            continue
        if _as_bool(identity.get("countsTowardDistribution")):
            candidates.append(identity)
    seen_profiles: set[str] = set()
    for identity in candidates:
        if not isinstance(identity, dict):
            continue
        profile_key = str(identity.get("profileId") or "")
        if profile_key in seen_profiles:
            continue
        seen_profiles.add(profile_key)
        reasons: list[str] = []
        asset_decisions = identity.get("assetDecisions") if isinstance(identity.get("assetDecisions"), dict) else {}
        missing_shots = set(identity.get("missingShotTypes") or [])
        if str(identity.get("completeIdentityDecision") or "") != "approved":
            reasons.append("completeIdentityDecision_not_approved")
        if not _as_bool(identity.get("countsTowardDistribution")):
            reasons.append("countsTowardDistribution_false")
        if _as_bool(identity.get("metadataMismatch")):
            reasons.append("metadataMismatch_true")
        if str(identity.get("observedLooksLevelBand") or "") == "4.4-5.0":
            reasons.append("observedLooksLevelBand_4.4-5.0")
        if _as_bool(identity.get("sameIdentity"), default=True) is False:
            reasons.append("sameIdentity_false")
        if int(identity.get("approvedShotCount") or 0) != len(SHOT_ORDER):
            reasons.append("less_than_3_approved_shots")
        for shot in SHOT_ORDER:
            if str(asset_decisions.get(shot) or "") != "approved":
                reasons.append(f"{shot}_not_approved")
            if shot in missing_shots:
                reasons.append(f"{shot}_missing")
        if required_shots - set(asset_decisions):
            for shot in sorted(required_shots - set(asset_decisions)):
                reasons.append(f"{shot}_missing")
        if _as_bool(identity.get("needsReview")):
            reasons.append("needs_review")
        if _as_bool(identity.get("rejected")):
            reasons.append("rejected")
        for reason in identity.get("reasons") or []:
            if str(reason) in {"metadata_mismatch", "over_level_4.4-5.0", "sameIdentity_false"}:
                reasons.append(str(reason))
        if reasons:
            invalid.append(
                {
                    "profileId": identity.get("profileId", ""),
                    "reasons": sorted(set(reasons)),
                }
            )
    return invalid


def completion_check(*, root: Path | str | None = None) -> dict[str, Any]:
    paths = pipeline_paths(root)
    audit = audit_distribution(root=root)
    count_checks = audit["countChecks"]
    failures: set[str] = set()
    manual_flag = paths.manifests / "manual_review_required.flag"
    if manual_flag.exists():
        failures.add("manual_review_required")

    pending_unresolved, pending_reason = _pending_unresolved(paths.manifests / "pending-imagegen.json")
    if pending_unresolved:
        failures.add("unresolved_pending_imagegen")

    visual_state = _visual_manifest_state(root)
    if visual_state["visualMissing"] or audit.get("visualJsonErrors"):
        failures.add("missing_visual_verdict")
    missing_visual_rows: list[dict[str, Any]] = []
    for identity in audit.get("approvedIdentities", []):
        if not isinstance(identity, dict):
            continue
        profile_id = str(identity.get("profileId") or "")
        missing: list[str] = []
        if profile_id not in visual_state["identityProfiles"]:
            missing.append("identity_qa")
        asset_shots = visual_state["assetShotsByProfile"].get(profile_id, set())
        for shot in SHOT_ORDER:
            if shot not in asset_shots:
                missing.append(f"asset_qa:{shot}")
        if missing:
            missing_visual_rows.append({"profileId": profile_id, "missing": missing})
    if missing_visual_rows:
        failures.add("missing_visual_verdict")

    invalid_counted = _invalid_counted_identities(audit)
    if invalid_counted or audit.get("countedWithoutThreeApprovedShots"):
        failures.add("invalid_counted_identity")
    if audit.get("overLevelApprovedIdentities"):
        failures.add("over_level_approved")
    if any(int(row.get("surplus") or 0) > 0 for row in audit.get("bucketChecks", [])):
        failures.add("surplus_bucket")
    if not audit.get("exactFinalCountMatch") or not audit.get("exactDistributionMatch") or audit.get("failConditions"):
        failures.add("distribution_mismatch")

    passed = bool(audit["passed"]) and not failures
    result = {
        "schemaVersion": "seolleyeon_ai_image_completion_check_v3",
        "passed": passed,
        "failureReasons": _failure_list(failures),
        "manualReviewRequired": manual_flag.exists(),
        "manualReviewFlag": str(manual_flag) if manual_flag.exists() else "",
        "unresolvedPendingImagegen": pending_unresolved,
        "pendingReason": pending_reason,
        "missingVisualVerdict": "missing_visual_verdict" in failures,
        "visualVerdictState": {
            "assetQaRows": visual_state["assetQaRows"],
            "identityQaRows": visual_state["identityQaRows"],
            "generationRows": visual_state["generationRowsCount"],
        },
        "invalidCountedIdentities": invalid_counted,
        "missingVisualVerdictRows": missing_visual_rows,
        "approvedCompleteIdentities": audit["approvedCompleteIdentities"],
        "approvedImages": audit["approvedImages"],
        "femaleApprovedCompleteIdentities": audit["femaleApprovedCompleteIdentities"],
        "maleApprovedCompleteIdentities": audit["maleApprovedCompleteIdentities"],
        "exactFinalCountMatch": audit["exactFinalCountMatch"],
        "exactDistributionMatch": audit["exactDistributionMatch"],
        "countChecks": count_checks,
        "overLevelApprovedIdentities": audit["overLevelApprovedIdentities"],
    }
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pass only when Seolleyeon v3 AI image final targets are exactly complete.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--targets_json", default=None, help="Compatibility option; targets are loaded from ai_image/config.")
    parser.add_argument("--audit_json", default=None, help="Compatibility option; completion recomputes the numeric audit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = completion_check(root=args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1
