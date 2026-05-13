from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ASSET_QA_TYPE = "seolleyeon_visual_verdict_asset_v3"
IDENTITY_QA_TYPE = "seolleyeon_visual_verdict_identity_v3"
DISTRIBUTION_QA_TYPE = "seolleyeon_visual_verdict_distribution_v3"

PASS_THRESHOLD = 90
NORMALIZED_KEYS = ("score", "verdict", "category_match", "differences", "suggestions", "reasoning")
NORMALIZED_VERDICTS = {"pass", "revise", "fail"}
PROJECT_DECISIONS = {"approved", "needs_review", "rejected"}
DISTRIBUTION_DECISIONS = {"approved", "needs_manual_review", "needs_more_generation"}

ASSET_REQUIRED_KEYS = {
    "assetId",
    "profileId",
    "gender",
    "shotType",
    "targetFaceType",
    "observedFaceType",
    "targetLooksLevelBand",
    "observedLooksLevelBand",
    "adultVisual",
    "photoRealism",
    "brandFit",
    "shotTypeReadable",
    "metadataMismatch",
    "decision",
}
IDENTITY_REQUIRED_KEYS = {
    "profileId",
    "gender",
    "targetFaceType",
    "observedFaceType",
    "targetLooksLevelBand",
    "observedLooksLevelBand",
    "assetIds",
    "assetDecisions",
    "faceToSilhouetteConsistency",
    "faceToVibeConsistency",
    "sameIdentity",
    "completeIdentityDecision",
    "countsTowardDistribution",
}
DISTRIBUTION_REQUIRED_KEYS = {
    "finalDecision",
    "approvedCompleteIdentityCount",
    "approvedImageCount",
    "femaleApprovedIdentityCount",
    "maleApprovedIdentityCount",
    "globalFaceTypeCounts",
    "globalLooksLevelBandCounts",
    "invalidIdentities",
    "nextGenerationDirective",
}

FORBIDDEN_NORMALIZED_TEXT = (
    "attractiveness",
    "beauty score",
    "dateability",
    "face rating",
    "looks score",
    "real-person identification",
    "identify the real person",
    "identify this person",
    "celebrity lookalike",
    "ethnicity",
    "religion",
    "political",
    "medical condition",
    "sexual orientation",
)


def _require_mapping(payload: Any, label: str = "payload") -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _require_keys(payload: Mapping[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


def _require_str_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    out: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"{label}[{index}] must be a string")
        out.append(item)
    return out


def _is_plain_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_normalized_safety_text(payload: Mapping[str, Any]) -> None:
    text_parts: list[str] = []
    text_parts.extend(_require_str_list(payload.get("differences"), "differences"))
    text_parts.extend(_require_str_list(payload.get("suggestions"), "suggestions"))
    reasoning = payload.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ValueError("reasoning must be a non-empty string")
    text_parts.append(reasoning)
    lowered = "\n".join(text_parts).lower()
    for phrase in FORBIDDEN_NORMALIZED_TEXT:
        if phrase in lowered:
            raise ValueError(f"normalized verdict contains forbidden review content: {phrase}")


def normalize_verdict_value(value: Any) -> str:
    verdict = str(value or "").strip().lower()
    if verdict == "retry":
        return "revise"
    if verdict not in NORMALIZED_VERDICTS:
        raise ValueError("verdict must be pass, revise, or fail")
    return verdict


def validate_normalized_verdict(payload: Mapping[str, Any]) -> dict[str, Any]:
    payload = _require_mapping(payload)
    extra = sorted(set(payload) - set(NORMALIZED_KEYS))
    missing = sorted(set(NORMALIZED_KEYS) - set(payload))
    if missing or extra:
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        raise ValueError("normalized verdict must use the exact schema (" + "; ".join(details) + ")")

    score = payload.get("score")
    if not _is_plain_int(score) or score < 0 or score > 100:
        raise ValueError("score must be an integer from 0 through 100")
    category_match = payload.get("category_match")
    if not isinstance(category_match, bool):
        raise ValueError("category_match must be a boolean")
    verdict = normalize_verdict_value(payload.get("verdict"))
    if verdict == "pass" and score < PASS_THRESHOLD:
        raise ValueError(f"pass verdict requires score >= {PASS_THRESHOLD}")
    if verdict == "pass" and category_match is not True:
        raise ValueError("pass verdict requires category_match=true")

    _check_normalized_safety_text(payload)
    return {
        "score": score,
        "verdict": verdict,
        "category_match": category_match,
        "differences": list(payload["differences"]),
        "suggestions": list(payload["suggestions"]),
        "reasoning": str(payload["reasoning"]),
    }


def _validate_project_decision(value: Any, label: str) -> str:
    decision = str(value or "").strip()
    if decision not in PROJECT_DECISIONS:
        raise ValueError(f"{label} must be one of: {', '.join(sorted(PROJECT_DECISIONS))}")
    return decision


def _validate_asset_payload(payload: Mapping[str, Any], *, allow_empty: bool) -> dict[str, Any]:
    if payload.get("qaType") != ASSET_QA_TYPE:
        raise ValueError(f"Unexpected qaType: {payload.get('qaType') or '<missing>'}")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ValueError("asset visual QA requires assets[]")
    if not assets and not allow_empty:
        raise ValueError("asset visual QA assets[] is empty")
    for index, row in enumerate(assets):
        row = _require_mapping(row, f"assets[{index}]")
        _require_keys(row, ASSET_REQUIRED_KEYS, f"assets[{index}]")
        _validate_project_decision(row.get("decision"), f"assets[{index}].decision")
    return {"kind": "asset", "qaType": ASSET_QA_TYPE, "count": len(assets)}


def _validate_identity_payload(payload: Mapping[str, Any], *, allow_empty: bool) -> dict[str, Any]:
    if payload.get("qaType") != IDENTITY_QA_TYPE:
        raise ValueError(f"Unexpected qaType: {payload.get('qaType') or '<missing>'}")
    identities = payload.get("identities")
    if not isinstance(identities, list):
        raise ValueError("identity visual QA requires identities[]")
    if not identities and not allow_empty:
        raise ValueError("identity visual QA identities[] is empty")
    for index, row in enumerate(identities):
        row = _require_mapping(row, f"identities[{index}]")
        _require_keys(row, IDENTITY_REQUIRED_KEYS, f"identities[{index}]")
        if not isinstance(row.get("assetIds"), Mapping):
            raise ValueError(f"identities[{index}].assetIds must be an object")
        if not isinstance(row.get("assetDecisions"), Mapping):
            raise ValueError(f"identities[{index}].assetDecisions must be an object")
        _validate_project_decision(row.get("completeIdentityDecision"), f"identities[{index}].completeIdentityDecision")
    return {"kind": "identity", "qaType": IDENTITY_QA_TYPE, "count": len(identities)}


def _validate_distribution_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("qaType") != DISTRIBUTION_QA_TYPE:
        raise ValueError(f"Unexpected qaType: {payload.get('qaType') or '<missing>'}")
    _require_keys(payload, DISTRIBUTION_REQUIRED_KEYS, "distribution")
    final_decision = str(payload.get("finalDecision") or "").strip()
    if final_decision not in DISTRIBUTION_DECISIONS:
        raise ValueError(f"finalDecision must be one of: {', '.join(sorted(DISTRIBUTION_DECISIONS))}")
    if not isinstance(payload.get("globalFaceTypeCounts"), Mapping):
        raise ValueError("globalFaceTypeCounts must be an object")
    if not isinstance(payload.get("globalLooksLevelBandCounts"), Mapping):
        raise ValueError("globalLooksLevelBandCounts must be an object")
    if not isinstance(payload.get("invalidIdentities"), list):
        raise ValueError("invalidIdentities must be an array")
    if not isinstance(payload.get("nextGenerationDirective"), Mapping):
        raise ValueError("nextGenerationDirective must be an object")
    return {"kind": "distribution", "qaType": DISTRIBUTION_QA_TYPE, "count": 1}


def validate_project_visual_verdict_payload(payload: Mapping[str, Any], *, allow_empty: bool = False) -> dict[str, Any]:
    payload = _require_mapping(payload)
    qa_type = payload.get("qaType")
    if qa_type == ASSET_QA_TYPE:
        return _validate_asset_payload(payload, allow_empty=allow_empty)
    if qa_type == IDENTITY_QA_TYPE:
        return _validate_identity_payload(payload, allow_empty=allow_empty)
    if qa_type == DISTRIBUTION_QA_TYPE:
        return _validate_distribution_payload(payload)
    raise ValueError(f"Unexpected qaType: {qa_type or '<missing>'}")


def validate_any_visual_verdict_payload(payload: Mapping[str, Any], *, allow_empty: bool = False) -> dict[str, Any]:
    payload = _require_mapping(payload)
    if "qaType" in payload:
        return validate_project_visual_verdict_payload(payload, allow_empty=allow_empty)
    return validate_normalized_verdict(payload)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Hermes visual-verdict JSON without running vision or image generation.")
    parser.add_argument("json_path", help="Path to a JSON verdict payload.")
    parser.add_argument("--schema", choices=("auto", "normalized", "project"), default="auto")
    parser.add_argument("--allow-empty", action="store_true", help="Allow empty project assets[] or identities[] payloads.")
    args = parser.parse_args(argv)

    try:
        payload = _read_json(Path(args.json_path))
        if args.schema == "normalized":
            result = validate_normalized_verdict(payload)
        elif args.schema == "project":
            result = validate_project_visual_verdict_payload(payload, allow_empty=args.allow_empty)
        else:
            result = validate_any_visual_verdict_payload(payload, allow_empty=args.allow_empty)
    except Exception as exc:  # noqa: BLE001 - CLI should return a concise validation error.
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps({"valid": True, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
