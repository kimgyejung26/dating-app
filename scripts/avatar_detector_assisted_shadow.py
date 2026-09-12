"""H3: detector-assisted watermark escalation. SHADOW ONLY, read by nothing.

Why H3 exists
-------------
H2 (B3-L5) was safe but too aggressive: geometry alone cannot separate an
injected corner stamp from whatever Florence reads in a clean avatar's corner,
so it sent 15 of 20 clean avatars to review. B3-L5 Part B measured that OWLv2
localizes an injected graphical mark on 100% of both real domains where Florence
found 0-25%. H3 therefore uses a *detector* as the corroborator H2 lacked,
instead of another geometry threshold.

Like H2, every candidate is ESCALATE-ONLY: the action is
max(live action, proposed action) over allow < review < reject. A live review or
reject can never be downgraded, so a hard-reject bypass, a new overlay miss or a
new generative-artifact miss cannot be introduced by construction. They are
still measured.

Candidates (frozen in docs/avatar-production/b3-l6-preregistration.md):

  H3-A  Florence overlayLike region AND an OWLv2 mark matching that region
  H3-B  OWLv2 matched mark AND sourceConsistent != true
  H3-C  Florence OCR region AND overlapping OWLv2 mark AND the mark is not
        scene-native

H3-C's "not scene-native" is available only as a HUMAN label in this evaluation
(`markIntegration`). That is evaluation truth, not a runtime feature, so H3-C is
an UPPER BOUND on what a runtime rule could reach and is not deployable unless a
runtime signal replaces that field. `human_mark_not_scene_native` is therefore a
required argument for H3-C and there is no default.

Consumes persisted typed evidence plus per-region match flags. No raw OCR text,
no image, no detector score. ``consumedByPolicy`` is always False.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.analysis.watermark import (  # noqa: E402
    WATERMARK_EVIDENCE_SCHEMA_VERSION,
    WATERMARK_QA_ACTION_ALLOW,
    WATERMARK_QA_ACTION_REJECT,
    WATERMARK_QA_ACTION_REVIEW,
    _region_from_typed_document,
    classify_watermark_evidence_document,
)

DETECTOR_ASSISTED_SHADOW_VERSION = "detector_assisted_shadow_v1"

RULE_A = "H3-A"
RULE_B = "H3-B"
RULE_C = "H3-C"
H3_RULES = (RULE_A, RULE_B, RULE_C)
# H3-C consumes a human evaluation field; it can never be a runtime rule as-is.
EVALUATION_ONLY_RULES = (RULE_C,)

_SEVERITY = {
    WATERMARK_QA_ACTION_ALLOW: 0,
    WATERMARK_QA_ACTION_REVIEW: 1,
    WATERMARK_QA_ACTION_REJECT: 2,
}
_ACTIONS = frozenset(_SEVERITY)

# Pre-registered box-match rule, frozen before any H3 result was inspected.
IOU_MATCH = 0.3
CONTAINMENT_MATCH = 0.5


def boxes_match(region_box: Sequence[float], mark_box: Sequence[float]) -> bool:
    """IoU >= 0.3, or the mark covers >= 50% of the region's area."""

    left, top = max(region_box[0], mark_box[0]), max(region_box[1], mark_box[1])
    right, bottom = min(region_box[2], mark_box[2]), min(region_box[3], mark_box[3])
    inter = max(0.0, right - left) * max(0.0, bottom - top)
    if inter <= 0:
        return False
    region_area = max(0.0, region_box[2] - region_box[0]) * max(0.0, region_box[3] - region_box[1])
    mark_area = max(0.0, mark_box[2] - mark_box[0]) * max(0.0, mark_box[3] - mark_box[1])
    union = region_area + mark_area - inter
    if union > 0 and inter / union >= IOU_MATCH:
        return True
    return region_area > 0 and inter / region_area >= CONTAINMENT_MATCH


def _proposes_review(item: Any, matched: bool, rule: str, human_not_scene_native: Optional[bool]) -> bool:
    if not matched:
        return False
    if rule == RULE_A:
        return bool(item.overlay_like)
    if rule == RULE_B:
        return item.source_consistent is not True
    if rule == RULE_C:
        if human_not_scene_native is None:
            raise ValueError("H3-C requires the human markIntegration field")
        return bool(human_not_scene_native)
    raise ValueError(f"unknown rule {rule}")


def classify_detector_assisted_shadow(
    evidence: Optional[Mapping[str, Any]],
    *,
    mark_matched: Sequence[bool],
    rule: str = RULE_A,
    human_mark_not_scene_native: Optional[bool] = None,
) -> Optional[dict[str, Any]]:
    """Escalate-only shadow action. None if the evidence is not the current schema."""

    if rule not in H3_RULES:
        raise ValueError(f"unknown rule {rule}")
    if not isinstance(evidence, Mapping):
        return None
    if evidence.get("schemaVersion") != WATERMARK_EVIDENCE_SCHEMA_VERSION:
        return None
    regions_value = evidence.get("regionEvidence")
    if not isinstance(regions_value, Sequence) or isinstance(regions_value, (str, bytes)):
        return None
    regions = []
    for entry in regions_value:
        item = _region_from_typed_document(entry)
        if item is None:
            return None
        regions.append(item)
    if len(mark_matched) != len(regions):
        raise ValueError("mark_matched must be parallel to regionEvidence")

    replayed = classify_watermark_evidence_document(evidence)
    live_action = replayed.watermark_qa_action if replayed is not None else WATERMARK_QA_ACTION_ALLOW
    escalating = sum(
        1
        for item, matched in zip(regions, mark_matched)
        if _proposes_review(item, bool(matched), rule, human_mark_not_scene_native)
    )
    proposed = WATERMARK_QA_ACTION_REVIEW if escalating else WATERMARK_QA_ACTION_ALLOW
    action = live_action if _SEVERITY[live_action] >= _SEVERITY[proposed] else proposed
    return {
        "policyVersion": DETECTOR_ASSISTED_SHADOW_VERSION,
        "inputSchemaVersion": WATERMARK_EVIDENCE_SCHEMA_VERSION,
        "rule": rule,
        "evaluationOnly": rule in EVALUATION_ONLY_RULES,
        "consumedByPolicy": False,
        "evidenceReplayWatermarkAction": live_action,
        "shadowWatermarkAction": action,
        "escalatedFromReplay": action != live_action,
        "escalatingRegionCount": escalating,
        "regionCount": len(regions),
        "matchedMarkRegionCount": sum(1 for matched in mark_matched if matched),
    }


def sanitize_detector_assisted_shadow(value: Any) -> dict[str, Any]:
    """Persisted form: fixed vocabulary only. No score, no box, no text."""

    if not isinstance(value, Mapping):
        return {}
    if value.get("policyVersion") != DETECTOR_ASSISTED_SHADOW_VERSION:
        return {}
    action, replay, rule = (
        value.get("shadowWatermarkAction"),
        value.get("evidenceReplayWatermarkAction"),
        value.get("rule"),
    )
    if action not in _ACTIONS or replay not in _ACTIONS or rule not in H3_RULES:
        return {}
    result = {
        "policyVersion": DETECTOR_ASSISTED_SHADOW_VERSION,
        "rule": rule,
        "evaluationOnly": rule in EVALUATION_ONLY_RULES,
        "consumedByPolicy": False,
        "shadowWatermarkAction": action,
        "evidenceReplayWatermarkAction": replay,
        "escalatedFromReplay": bool(value.get("escalatedFromReplay")),
    }
    for key in ("escalatingRegionCount", "regionCount", "matchedMarkRegionCount"):
        count = value.get(key)
        if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
            result[key] = count
    if value.get("inputSchemaVersion") == WATERMARK_EVIDENCE_SCHEMA_VERSION:
        result["inputSchemaVersion"] = WATERMARK_EVIDENCE_SCHEMA_VERSION
    return result


__all__ = [
    "CONTAINMENT_MATCH",
    "DETECTOR_ASSISTED_SHADOW_VERSION",
    "EVALUATION_ONLY_RULES",
    "H3_RULES",
    "IOU_MATCH",
    "RULE_A",
    "RULE_B",
    "RULE_C",
    "boxes_match",
    "classify_detector_assisted_shadow",
    "sanitize_detector_assisted_shadow",
]
