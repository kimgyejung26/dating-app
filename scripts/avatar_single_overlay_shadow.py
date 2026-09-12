"""H2: single non-repeated overlay escalation. SHADOW ONLY, read by nothing.

Why this exists
---------------
B3-L4 measured that Florence finds injected single overlay text at or near
ceiling on real source photos and real generated avatars, while the live policy
allows it: the only single-region escalation paths are ``confidenceBand=high``
(the adapter emits no per-region score, so it is always ``unknown``) and
``textQuality=implausible`` (Florence merges spaced single glyphs into one word,
so it is not produced for that construct). The loss is a POLICY miss, not a
model miss.

What H2 is
----------
Three pre-registered candidate rules (see
docs/avatar-production/b3-single-overlay-shadow-preregistration.md), all
ESCALATE-ONLY: the shadow action is max(live action, proposed action) on
allow < review < reject. No live review or reject can be downgraded, so a
hard-reject bypass or a new overlay/artifact miss cannot be introduced by
construction -- and is still measured.

H2 is not H1 and does not modify it. H1 removed review from fragmented
non-overlay text and lost a known generative artifact (ctl-10); that hypothesis
stays rejected.

Consumes only persisted typed evidence (``watermarkEvidence.regionEvidence``):
no raw OCR text, no image. ``consumedByPolicy`` is always False.
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

SINGLE_OVERLAY_SHADOW_VERSION = "single_overlay_shadow_v1"

RULE_A = "H2-A"
RULE_B = "H2-B"
RULE_C = "H2-C"
H2_RULES = (RULE_A, RULE_B, RULE_C)

_SEVERITY = {
    WATERMARK_QA_ACTION_ALLOW: 0,
    WATERMARK_QA_ACTION_REVIEW: 1,
    WATERMARK_QA_ACTION_REJECT: 2,
}
_ACTIONS = frozenset(_SEVERITY)
_CORNER_OR_EDGE = frozenset({"corner", "edge"})


def _proposes_review(item: Any, rule: str) -> bool:
    """One region's contribution under one candidate rule."""

    if not item.overlay_like or item.source_consistent is True:
        return False
    if rule == RULE_A:
        return True
    if rule == RULE_B:
        # Pre-registered bound: the existing small area band, no new constant.
        return item.area_ratio <= 0.03
    if rule == RULE_C:
        return item.location in _CORNER_OR_EDGE or item.artifact_hint
    raise ValueError(f"unknown rule {rule}")


def classify_single_overlay_shadow(
    evidence: Optional[Mapping[str, Any]],
    *,
    rule: str = RULE_A,
) -> Optional[dict[str, Any]]:
    """Escalate-only shadow action from typed evidence. None if not the current schema."""

    if rule not in H2_RULES:
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

    replayed = classify_watermark_evidence_document(evidence)
    live_action = replayed.watermark_qa_action if replayed is not None else WATERMARK_QA_ACTION_ALLOW
    escalating = sum(1 for item in regions if _proposes_review(item, rule))
    proposed = WATERMARK_QA_ACTION_REVIEW if escalating else WATERMARK_QA_ACTION_ALLOW
    action = live_action if _SEVERITY[live_action] >= _SEVERITY[proposed] else proposed
    return {
        "policyVersion": SINGLE_OVERLAY_SHADOW_VERSION,
        "inputSchemaVersion": WATERMARK_EVIDENCE_SCHEMA_VERSION,
        "rule": rule,
        "consumedByPolicy": False,
        "evidenceReplayWatermarkAction": live_action,
        "shadowWatermarkAction": action,
        "escalatedFromReplay": action != live_action,
        "escalatingRegionCount": escalating,
        "regionCount": len(regions),
    }


def sanitize_single_overlay_shadow(value: Any) -> dict[str, Any]:
    """Persisted form: fixed vocabulary only, so no transcription can ride along."""

    if not isinstance(value, Mapping):
        return {}
    if value.get("policyVersion") != SINGLE_OVERLAY_SHADOW_VERSION:
        return {}
    action = value.get("shadowWatermarkAction")
    replay = value.get("evidenceReplayWatermarkAction")
    rule = value.get("rule")
    if action not in _ACTIONS or replay not in _ACTIONS or rule not in H2_RULES:
        return {}
    result = {
        "policyVersion": SINGLE_OVERLAY_SHADOW_VERSION,
        "rule": rule,
        "consumedByPolicy": False,
        "shadowWatermarkAction": action,
        "evidenceReplayWatermarkAction": replay,
        "escalatedFromReplay": bool(value.get("escalatedFromReplay")),
    }
    for key in ("escalatingRegionCount", "regionCount"):
        count = value.get(key)
        if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
            result[key] = count
    if value.get("inputSchemaVersion") == WATERMARK_EVIDENCE_SCHEMA_VERSION:
        result["inputSchemaVersion"] = WATERMARK_EVIDENCE_SCHEMA_VERSION
    return result


__all__ = [
    "H2_RULES",
    "RULE_A",
    "RULE_B",
    "RULE_C",
    "SINGLE_OVERLAY_SHADOW_VERSION",
    "classify_single_overlay_shadow",
    "sanitize_single_overlay_shadow",
]
