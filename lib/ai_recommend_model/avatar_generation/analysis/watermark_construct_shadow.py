"""Construct-valid shadow classification of watermark/text evidence. SHADOW ONLY.

What the live classifier actually reads
---------------------------------------
Florence ``<OCR_WITH_REGION>`` returns *transcribed text* per region. The
transformers post-processor builds ``labels = [inst["text"] for inst in parsed]``
from ``parse_ocr_from_text_and_spans``; there is no semantic class in that
output. ``visual_risk._classify_ocr_label`` then decides whether a region is a
logo or a sign by substring-matching the transcription, so a shirt reading
DESIGN becomes a "sign", LOGON and Brandon become "logo".

That is not a missing word boundary. The input is not a semantic descriptor, so
no tokenisation of it can make "the letters s-i-g-n occur in the transcription"
mean "the image contains a sign". A literal region reading SIGN is still just a
transcription.

It is action-inert under the current policy: forcing text/logo/sign on
identical geometry and tokens changes the watermark action in 0 cases, because
kind only renames the decision class (overlay_watermark vs
generated_overlay_logo, both reject). Actions are driven by typed evidence --
text quality, overlay geometry, repetition, confidence state. What
it poisons is meaning -- every persisted ``visualRegionCounts`` entry keyed by
kind, and any future rule that reads kind as if it were a detector.

What this module does
---------------------
Classifies from the typed evidence the live policy already derives and
persists -- geometry, repetition, text quality, confidence band, source
consistency, artifact hint -- and never from kind or text. Because it consumes
exactly ``watermarkEvidence.regionEvidence``, it replays on stored production
documents with no raw OCR and no image.

It is read by nothing. ``consumedByPolicy`` is always False, and the effective
``watermarkQaAction`` / ``rejectReasons`` / ``reviewReasons`` / ``previewAllowed``
are untouched.

One hypothesis, stated as a hypothesis
--------------------------------------
H1: a fragmented transcription (several tokens, at least one of <=2 chars) is
artifact evidence only when it also sits in overlay geometry. The live
``_token_quality`` rule reviews fragmented text anywhere, so NEW YORK NY on a
shirt or NO 23 ST on a background sign is withheld from preview exactly like a
fragmented corner stamp. H1 keeps review for the overlay case and allows the
rest. Its expected effect is fewer benign-text reviews; its risk is missing a
real generated text artifact that happens to land mid-image. Neither is
measured yet -- there are no human labels -- which is why this is shadow.

Every other branch reproduces the live policy exactly, including the repeated
overlay hard reject and the high-confidence branch. That branch is unreachable
with the current Florence <OCR_WITH_REGION> adapter and region-confidence
schema, which carry no per-region score, so every band is "unknown". A future
adapter that emits a real per-region score would make it reachable.

What current evidence cannot distinguish
----------------------------------------
Listed so nobody reads a shadow class as more than it is: a third-party logo vs
text, a brand mark, an OCR hallucination, background signage vs overlay text,
and confirmation that fragmented text is a generative artifact. Each needs the
image, a logo detector, or a human label.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from .watermark import (
    WATERMARK_EVIDENCE_SCHEMA_VERSION,
    WATERMARK_QA_ACTION_ALLOW,
    WATERMARK_QA_ACTION_REJECT,
    WATERMARK_QA_ACTION_REVIEW,
    _region_from_typed_document,
    classify_watermark_evidence_document,
)

WATERMARK_CONSTRUCT_SHADOW_VERSION = "watermark_construct_shadow_v1"

SHADOW_NO_TEXT_REGION = "no_text_region"
SHADOW_REPEATED_OVERLAY_TEXT = "repeated_overlay_text"
SHADOW_FRAGMENTED_OVERLAY_TEXT = "fragmented_overlay_text"
SHADOW_OVERLAY_GEOMETRY_TEXT = "overlay_geometry_text"
SHADOW_SOURCE_CONSISTENT_TEXT = "source_consistent_text"
SHADOW_GARMENT_ZONE_TEXT = "garment_zone_text"
SHADOW_SCENE_TEXT = "scene_text"
SHADOW_UNKNOWN_TEXT_REGION = "unknown_text_region"

SHADOW_CLASSES = frozenset(
    {
        SHADOW_NO_TEXT_REGION,
        SHADOW_REPEATED_OVERLAY_TEXT,
        SHADOW_FRAGMENTED_OVERLAY_TEXT,
        SHADOW_OVERLAY_GEOMETRY_TEXT,
        SHADOW_SOURCE_CONSISTENT_TEXT,
        SHADOW_GARMENT_ZONE_TEXT,
        SHADOW_SCENE_TEXT,
        SHADOW_UNKNOWN_TEXT_REGION,
    }
)

HYPOTHESIS_FRAGMENTED_TEXT_REQUIRES_OVERLAY = "H1_fragmented_text_requires_overlay_geometry"
SHADOW_HYPOTHESES = (HYPOTHESIS_FRAGMENTED_TEXT_REQUIRES_OVERLAY,)

NOT_DISTINGUISHABLE_FROM_CURRENT_EVIDENCE = (
    "third_party_logo_vs_text",
    "brand_mark",
    "ocr_hallucination",
    "background_signage_vs_overlay_text",
    "generative_text_artifact_confirmation",
)

_ACTIONS = frozenset(
    {WATERMARK_QA_ACTION_ALLOW, WATERMARK_QA_ACTION_REVIEW, WATERMARK_QA_ACTION_REJECT}
)
_SEVERITY = {
    WATERMARK_QA_ACTION_ALLOW: 0,
    WATERMARK_QA_ACTION_REVIEW: 1,
    WATERMARK_QA_ACTION_REJECT: 2,
}


def classify_watermark_construct_shadow(
    evidence: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    """Shadow class and hypothetical action from typed watermark evidence.

    Returns None when the evidence is not the current typed schema. Legacy or
    malformed evidence is never guessed at; absence of a shadow block means
    "not measured", not "clean".
    """

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

    if not regions:
        shadow_action = WATERMARK_QA_ACTION_ALLOW
        shadow_class = SHADOW_NO_TEXT_REGION
        replay_action = WATERMARK_QA_ACTION_ALLOW
        counts: dict[str, int] = {}
    else:
        counts = {}
        shadow_action = WATERMARK_QA_ACTION_ALLOW
        shadow_class = SHADOW_UNKNOWN_TEXT_REGION
        best = -1
        for item in regions:
            region_class = _region_class(item)
            region_action = _region_action(item)
            counts[region_class] = counts.get(region_class, 0) + 1
            if _SEVERITY[region_action] > best:
                best = _SEVERITY[region_action]
                shadow_action = region_action
                shadow_class = region_class
        replayed = classify_watermark_evidence_document(evidence)
        replay_action = (
            replayed.watermark_qa_action if replayed is not None else WATERMARK_QA_ACTION_ALLOW
        )

    return {
        "policyVersion": WATERMARK_CONSTRUCT_SHADOW_VERSION,
        "inputSchemaVersion": WATERMARK_EVIDENCE_SCHEMA_VERSION,
        "consumedByPolicy": False,
        "shadowWatermarkClass": shadow_class,
        "shadowWatermarkAction": shadow_action,
        # The live action replayed from the same typed evidence, so the diff is
        # apples to apples. The effective action the worker wrote is persisted
        # separately as qa.watermarkQaAction and is not recomputed here.
        "evidenceReplayWatermarkAction": replay_action,
        "agreesWithEvidenceReplay": shadow_action == replay_action,
        "regionClassCounts": dict(sorted(counts.items())),
        "hypotheses": list(SHADOW_HYPOTHESES),
    }


def _region_class(item: Any) -> str:
    # Repetition in overlay geometry outranks source consistency, exactly as
    # the live policy's strong_overlay does.
    if item.overlay_like and item.repeated:
        return SHADOW_REPEATED_OVERLAY_TEXT
    if item.source_consistent is True:
        return SHADOW_SOURCE_CONSISTENT_TEXT
    if item.overlay_like and item.token_quality == "implausible":
        return SHADOW_FRAGMENTED_OVERLAY_TEXT
    if item.overlay_like:
        return SHADOW_OVERLAY_GEOMETRY_TEXT
    if item.location == "clothing_zone":
        return SHADOW_GARMENT_ZONE_TEXT
    if item.location in {"central", "edge", "corner"}:
        return SHADOW_SCENE_TEXT
    return SHADOW_UNKNOWN_TEXT_REGION


def _region_action(item: Any) -> str:
    strong_overlay = item.overlay_like and (
        item.repeated
        or (
            item.source_consistent is not True
            and item.confidence_band == "high"
            and (item.token_quality == "implausible" or item.artifact_hint)
        )
    )
    if strong_overlay:
        return WATERMARK_QA_ACTION_REJECT
    if item.source_consistent is True:
        return WATERMARK_QA_ACTION_ALLOW
    if item.token_quality == "implausible" and item.overlay_like:
        return WATERMARK_QA_ACTION_REVIEW
    # H1: fragmented text outside overlay geometry is not, on its own,
    # evidence of a generated artifact.
    return WATERMARK_QA_ACTION_ALLOW


def sanitize_watermark_construct_shadow(value: Any) -> dict[str, Any]:
    """The persisted form. Every string is checked against a fixed vocabulary,
    so a transcription cannot ride along even if a producer ever put one here."""

    if not isinstance(value, Mapping):
        return {}
    if value.get("policyVersion") != WATERMARK_CONSTRUCT_SHADOW_VERSION:
        return {}
    shadow_class = value.get("shadowWatermarkClass")
    shadow_action = value.get("shadowWatermarkAction")
    replay_action = value.get("evidenceReplayWatermarkAction")
    if shadow_class not in SHADOW_CLASSES or shadow_action not in _ACTIONS:
        return {}
    result: dict[str, Any] = {
        "policyVersion": WATERMARK_CONSTRUCT_SHADOW_VERSION,
        "consumedByPolicy": False,
        "shadowWatermarkClass": shadow_class,
        "shadowWatermarkAction": shadow_action,
    }
    if value.get("inputSchemaVersion") == WATERMARK_EVIDENCE_SCHEMA_VERSION:
        result["inputSchemaVersion"] = WATERMARK_EVIDENCE_SCHEMA_VERSION
    if replay_action in _ACTIONS:
        result["evidenceReplayWatermarkAction"] = replay_action
        result["agreesWithEvidenceReplay"] = shadow_action == replay_action
    counts = value.get("regionClassCounts")
    if isinstance(counts, Mapping):
        result["regionClassCounts"] = {
            str(key): int(count)
            for key, count in counts.items()
            if key in SHADOW_CLASSES and isinstance(count, int) and not isinstance(count, bool)
        }
    hypotheses = value.get("hypotheses")
    if isinstance(hypotheses, Sequence) and not isinstance(hypotheses, (str, bytes)):
        result["hypotheses"] = [item for item in hypotheses if item in SHADOW_HYPOTHESES]
    return result


__all__ = [
    "HYPOTHESIS_FRAGMENTED_TEXT_REQUIRES_OVERLAY",
    "NOT_DISTINGUISHABLE_FROM_CURRENT_EVIDENCE",
    "SHADOW_CLASSES",
    "SHADOW_HYPOTHESES",
    "WATERMARK_CONSTRUCT_SHADOW_VERSION",
    "classify_watermark_construct_shadow",
    "sanitize_watermark_construct_shadow",
]
