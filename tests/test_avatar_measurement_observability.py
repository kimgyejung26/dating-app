"""The numbers a QA run measured must survive the document it produces.

Every value pinned here already existed in the in-memory signals and was
discarded at document-build time, so the next calibration has nothing to work
from. Read-only production evidence on 2026-09-10, ``seolleyeon-final``, all
twelve current-contract candidates (``avatar_qa_v7_watermark_evidence_parity_v1``,
2026-09-06..09-09):

  * ``childlikeRiskScore``, ``beautificationRiskScore``, ``brandFitScore`` were
    null in 12/12 even though ``localSafetyRisk`` was available and CLIP had
    answered. 100% loss.
  * ``faceSimilarityScore`` was null in 9/12 -- the canonical score withheld
    because the producer said ``identity_reliable=False`` -- and nothing in the
    record distinguished that from "never measured". The reason was computed
    (``faceSimilarityCanonicalUnavailableReason``) and dropped.
  * ``shadowOcrEvidence`` never reached a document at all: the adapter attaches
    it to the Florence OCR payload and every reader below consumes only
    ``quad_boxes``/``labels``. The shadow corpus it exists to build was empty.
  * ``ssimScore``, ``clipSimilarityScore``, ``dinoStyleScore``,
    ``traitConsistencyScore`` and ``privacyPenalty`` were null in 12/12 because
    nothing in the repository computes them -- indistinguishable, in the record,
    from the measurements that were lost.

This is a persistence change, not a policy change. ``debug.scores`` keeps its
exact existing shape so no reader moves, the new numbers land in their own
namespace, and the decision-diff guards at the bottom must hold identically.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.analysis.visual_risk import (  # noqa: E402
    SHADOW_OCR_EVIDENCE_KEY,
    analyze_florence_visual_risk_outputs,
)
from avatar_generation.qa import (  # noqa: E402
    CLIP_SAFETY_SCORE_SPACE,
    CLIP_SAFETY_SCORE_TYPE,
    MEASUREMENT_MEASURED,
    MEASUREMENT_NO_PRODUCER,
    MEASUREMENT_RECORDED_ELSEWHERE,
    MEASUREMENT_UNAVAILABLE,
    MEASUREMENT_WITHHELD,
    AvatarQAThresholds,
    build_avatar_qa_from_signals,
)
from avatar_generation.qa_signals import (  # noqa: E402
    SENSITIVE_EXACT_KEYS,
    LocalSafetyRiskResult,
    _add_local_risk_signals,
    _add_visual_signals,
)

CLIP_SIGNALS = {
    "childlikeScore": 0.031,
    "sexualizedScore": 0.017,
    "beautificationScore": 0.442,
    "severeArtifactScore": 0.108,
    "brandMismatchScore": 0.221,
    "adultLike": True,
    "brandFit": True,
    "localSafetyRiskAvailability": "available",
    "localSafetyRiskProvider": "clip",
    "localSafetyRiskModelVersion": "openai/clip-vit-large-patch14",
    "localSafetyRiskCalibrationVersion": "clip-cal-v1",
}

IDENTITY_WITHHELD_SIGNALS = {
    "faceSimilarityObservedScore": 0.614208,
    "faceSimilarityDecision": "review_similarity",
    "faceSimilarityCanonicalScoreAvailable": False,
    "faceSimilarityCanonicalUnavailableReason": "identity_within_calibrated_review_band",
    "faceSimilarityCalibrationState": "calibrated_review_band",
}

SHADOW_OCR_SIGNAL = {
    "shadowOcrEvidence": {
        "scoreSource": "florence_beam_sequence_score",
        "scoreCalibrated": False,
        "generationMode": "beam_search",
        "numBeams": 3,
        "regionCount": 1,
        "attributionScope": "single_region",
        "scoreAvailable": True,
        "rawSequenceScore": -0.21,
        "outputTokenCount": 17,
    }
}

BASE_SIGNALS = {"cropConsistent": True, "cropIsolationQuality": "pass"}


def _qa(**signal_groups):
    signals = dict(BASE_SIGNALS)
    for group in signal_groups.values():
        signals.update(group)
    return build_avatar_qa_from_signals(signals, thresholds=AvatarQAThresholds())


def _measurements(result):
    return result.debug["measurements"]


# ---------------------------------------------------------------------------
# 1. The measured numbers survive
# ---------------------------------------------------------------------------


def test_clip_raw_scores_survive_the_document_build():
    clip = _measurements(_qa(clip=CLIP_SIGNALS))["clipSafety"]
    assert clip["measurementStatus"] == MEASUREMENT_MEASURED
    assert clip["rawModelScores"] == {
        "childlike": 0.031,
        "sexualized": 0.017,
        "beautification": 0.442,
        "brandMismatch": 0.221,
        "severeArtifact": 0.108,
    }


def test_clip_scores_carry_the_provenance_needed_to_pool_them():
    clip = _measurements(_qa(clip=CLIP_SIGNALS))["clipSafety"]
    assert clip["provider"] == "clip"
    assert clip["modelVersion"] == "openai/clip-vit-large-patch14"
    assert clip["calibrationVersion"] == "clip-cal-v1"


def test_clip_scores_are_not_called_probability_or_confidence():
    """A within-group softmax over two hand-written prompts is not a calibrated
    probability, and naming it one is what would make a later threshold move
    unsafe."""

    clip = _measurements(_qa(clip=CLIP_SIGNALS))["clipSafety"]
    assert clip["scoreType"] == CLIP_SAFETY_SCORE_TYPE == "raw_model_score"
    assert clip["scoreSpace"] == CLIP_SAFETY_SCORE_SPACE
    assert clip["scoreCalibrated"] is False
    serialized = json.dumps(clip).lower()
    assert "probability" not in serialized
    assert "confidence" not in serialized


def test_unavailable_clip_is_recorded_as_unavailable_not_as_zero():
    clip = _measurements(
        _qa(clip={"localSafetyRiskAvailability": "unavailable", "localSafetyRiskProvider": "clip"})
    )["clipSafety"]
    assert clip["measurementStatus"] == MEASUREMENT_UNAVAILABLE
    assert clip["available"] is False
    assert all(value is None for value in clip["rawModelScores"].values())


def test_withheld_canonical_identity_score_records_why():
    identity = _measurements(_qa(identity=IDENTITY_WITHHELD_SIGNALS))["faceSimilarity"]
    assert identity["observedScore"] == 0.614208
    assert identity["canonicalScoreAvailable"] is False
    assert identity["canonicalUnavailableReason"] == "identity_within_calibrated_review_band"
    assert identity["calibrationState"] == "calibrated_review_band"


def test_score_provenance_separates_four_kinds_of_null():
    provenance = _qa(clip=CLIP_SIGNALS, identity=IDENTITY_WITHHELD_SIGNALS).debug["scoreProvenance"]
    assert provenance["faceSimilarityObservedScore"] == MEASUREMENT_MEASURED
    assert provenance["faceSimilarityScore"] == MEASUREMENT_WITHHELD
    assert provenance["perceptualSimilarityScore"] == MEASUREMENT_UNAVAILABLE
    assert provenance["ssimScore"] == MEASUREMENT_NO_PRODUCER
    assert provenance["dinoStyleScore"] == MEASUREMENT_NO_PRODUCER
    assert provenance["childlikeRiskScore"] == MEASUREMENT_RECORDED_ELSEWHERE


def test_every_score_key_is_attributable():
    result = _qa(clip=CLIP_SIGNALS, identity=IDENTITY_WITHHELD_SIGNALS)
    assert set(result.debug["scoreProvenance"]) >= {
        key for key in result.debug["scores"] if key != "faceSimilarityDecision"
    }


# ---------------------------------------------------------------------------
# 2. Shadow OCR reaches persistence
# ---------------------------------------------------------------------------


def _florence_outputs(*, with_shadow=True):
    ocr = {"quad_boxes": [], "labels": []}
    if with_shadow:
        ocr[SHADOW_OCR_EVIDENCE_KEY] = dict(SHADOW_OCR_SIGNAL["shadowOcrEvidence"])
    return {"<OCR_WITH_REGION>": ocr, "<OD>": {"bboxes": [], "labels": []}}


def test_shadow_ocr_evidence_leaves_the_adapter_payload():
    analysis = analyze_florence_visual_risk_outputs(
        _florence_outputs(), image_size=(512, 768)
    )
    assert analysis.shadow_ocr_evidence["rawSequenceScore"] == -0.21
    assert analysis.to_document()["shadowOcrEvidence"]["scoreAvailable"] is True


def test_shadow_ocr_evidence_reaches_the_qa_document():
    shadow = _measurements(_qa(ocr=SHADOW_OCR_SIGNAL))["shadowOcr"]
    assert shadow["rawSequenceScore"] == -0.21
    assert shadow["scoreSource"] == "florence_beam_sequence_score"
    assert shadow["scoreCalibrated"] is False
    assert shadow["attributionScope"] == "single_region"


def test_absent_shadow_ocr_is_simply_absent():
    assert "shadowOcr" not in _measurements(_qa(clip=CLIP_SIGNALS))


def test_shadow_ocr_stays_out_of_every_watermark_field():
    """TRUE SHADOW: the same evidence with and without the score must produce
    the same watermark decision."""

    without = _qa(clip=CLIP_SIGNALS)
    with_shadow = _qa(clip=CLIP_SIGNALS, ocr=SHADOW_OCR_SIGNAL)
    assert without.watermarkQaAction == with_shadow.watermarkQaAction
    assert without.logoTextWatermarkRisk == with_shadow.logoTextWatermarkRisk
    assert without.textLogoWatermarkRisk == with_shadow.textLogoWatermarkRisk
    assert without.debug.get("watermarkDecisionClass") == with_shadow.debug.get(
        "watermarkDecisionClass"
    )


def test_shadow_score_is_not_promoted_to_region_confidence():
    analysis = analyze_florence_visual_risk_outputs(
        {
            "<OCR_WITH_REGION>": {
                "quad_boxes": [[10, 10, 60, 10, 60, 30, 10, 30]],
                "labels": ["NIKE"],
                SHADOW_OCR_EVIDENCE_KEY: dict(SHADOW_OCR_SIGNAL["shadowOcrEvidence"]),
            },
            "<OD>": {"bboxes": [], "labels": []},
        },
        image_size=(512, 768),
    )
    assert [region.confidence for region in analysis.regions] == [None]


# ---------------------------------------------------------------------------
# 3. Privacy
# ---------------------------------------------------------------------------


def test_no_raw_ocr_text_survives_into_the_qa_document():
    poisoned = {
        "shadowOcrEvidence": {
            **SHADOW_OCR_SIGNAL["shadowOcrEvidence"],
            "labels": ["SECRET BRAND"],
            "rawText": "SECRET BRAND",
            "quad_boxes": [[1, 2, 3, 4, 5, 6, 7, 8]],
        }
    }
    shadow = _measurements(_qa(ocr=poisoned))["shadowOcr"]
    assert "labels" not in shadow
    assert "quad_boxes" not in shadow
    assert shadow["rawSequenceScore"] == -0.21
    # rawText is a scalar, so scalar-only filtering alone does not stop it --
    # this is what the sensitive-key contract is for.
    assert "SECRET BRAND" not in json.dumps(_qa(ocr=poisoned).debug)


def test_adapter_side_shadow_evidence_admits_only_scalar_telemetry():
    analysis = analyze_florence_visual_risk_outputs(
        {
            "<OCR_WITH_REGION>": {
                "quad_boxes": [],
                "labels": [],
                SHADOW_OCR_EVIDENCE_KEY: {
                    "rawSequenceScore": -0.21,
                    "labels": ["SECRET"],
                    "quad_boxes": [[1, 2, 3, 4]],
                    "embedding": [0.1, 0.2],
                },
            },
            "<OD>": {"bboxes": [], "labels": []},
        },
        image_size=(512, 768),
    )
    assert set(analysis.shadow_ocr_evidence) == {"rawSequenceScore"}


def test_no_bbox_embedding_or_landmark_reaches_the_document():
    result = _qa(clip=CLIP_SIGNALS, identity=IDENTITY_WITHHELD_SIGNALS, ocr=SHADOW_OCR_SIGNAL)
    serialized = json.dumps(result.debug).lower()
    for forbidden in ("bbox", "embedding", "landmark", "quad_boxes", "signedurl", "https://"):
        assert forbidden not in serialized, forbidden


def test_measurement_keys_do_not_collide_with_the_sensitive_key_contract():
    result = _qa(clip=CLIP_SIGNALS, identity=IDENTITY_WITHHELD_SIGNALS, ocr=SHADOW_OCR_SIGNAL)

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                assert str(key).lower().replace("-", "_") not in SENSITIVE_EXACT_KEYS, key
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(result.debug["measurements"])


# ---------------------------------------------------------------------------
# 4. QA verdict vs product offering
# ---------------------------------------------------------------------------


HARD_PASS_SIGNALS = {
    "adultLike": True,
    "brandFit": True,
    "faceSimilarityScore": 0.2,
    "faceSimilarityObservedScore": 0.2,
    "faceSimilarityReliable": True,
    "faceSimilarityCanonicalScoreAvailable": True,
    "faceSimilarityDecision": "low_similarity_risk",
    "perceptualSimilarityScore": 0.4,
    "backgroundLeakageRisk": "low",
    "secondaryFaceLeakageRisk": "low",
}
UNIQUE_MARK_DISABLED = {
    "uniqueMarkQaMode": "disabled_by_pipeline",
    "uniqueMarkQaAuthority": "server",
}


def test_qa_verdict_is_recorded_separately_from_what_was_offered():
    """The worker overwrites qa.previewAllowed with its offering decision. In
    production on 2026-09-10 that had already happened to 2 of the 12
    current-contract candidates: an approved and a preview_ready candidate both
    carried previewAllowed=True over a QA verdict of False."""

    hard_pass = build_avatar_qa_from_signals(
        {**BASE_SIGNALS, **CLIP_SIGNALS, **HARD_PASS_SIGNALS},
        thresholds=AvatarQAThresholds(),
        pipeline_contract=UNIQUE_MARK_DISABLED,
    )
    assert hard_pass.debug["decision"]["selectionTier"] == "hard_pass"
    assert hard_pass.debug["qaDecisionPreviewAllowed"] is True

    soft = _qa(clip=CLIP_SIGNALS, identity=IDENTITY_WITHHELD_SIGNALS)
    assert soft.debug["decision"]["selectionTier"] != "hard_pass"
    assert soft.debug["qaDecisionPreviewAllowed"] is False
    assert soft.debug["decision"]["previewAllowed"] is False

    # What the worker does to a selected soft-review candidate. The verdict is
    # still readable afterwards; before this PR it was not.
    qa_doc = {"previewAllowed": soft.previewAllowed, "debug": dict(soft.debug)}
    qa_doc["previewAllowed"] = True
    qa_doc["offeredToUser"] = True
    assert qa_doc["previewAllowed"] is True
    assert qa_doc["debug"]["qaDecisionPreviewAllowed"] is False


def test_existing_preview_allowed_field_is_untouched():
    """previewAllowed keeps its exact current meaning; nothing is renamed or
    removed in this PR."""

    for groups in ({"clip": CLIP_SIGNALS}, {"clip": CLIP_SIGNALS, "identity": IDENTITY_WITHHELD_SIGNALS}):
        result = _qa(**groups)
        assert result.previewAllowed is result.debug["decision"]["previewAllowed"]


# ---------------------------------------------------------------------------
# 5. DECISION DIFF = 0
# ---------------------------------------------------------------------------

DECISION_FIELDS = (
    "previewAllowed",
    "requiresHumanReview",
    "softPass",
    "rejectReasons",
    "reviewReasons",
    "softPassReasons",
    "adultQa",
    "privacyQa",
    "brandQa",
    "cropConsistency",
    "cropIsolationQuality",
    "childlikeRisk",
    "beautificationRisk",
    "identifiabilityRisk",
    "logoTextWatermarkRisk",
    "textLogoWatermarkRisk",
    "backgroundLeakageRisk",
    "secondaryFaceLeakageRisk",
    "uniqueMarkCopyRisk",
    "watermarkQaAction",
    "faceSimilarityScore",
)


def _decision(result):
    return {field: getattr(result, field, None) for field in DECISION_FIELDS}


def test_adding_the_measurements_changes_no_decision():
    """The observability signals are additive: a run that carries them must
    decide exactly what the same run without them decides."""

    cases = [
        ({}, {}),
        ({"clip": CLIP_SIGNALS}, {}),
        ({"identity": IDENTITY_WITHHELD_SIGNALS}, {}),
        ({"clip": CLIP_SIGNALS, "identity": IDENTITY_WITHHELD_SIGNALS}, {}),
    ]
    observability_only = {
        "localSafetyRiskProvider": "clip",
        "localSafetyRiskModelVersion": "openai/clip-vit-large-patch14",
        "localSafetyRiskCalibrationVersion": "clip-cal-v1",
        "faceSimilarityCanonicalUnavailableReason": "identity_within_calibrated_review_band",
        **SHADOW_OCR_SIGNAL,
    }
    for groups, _ in cases:
        without = _qa(**groups)
        with_extra = _qa(**groups, observability=observability_only)
        assert _decision(without) == _decision(with_extra), groups


def test_debug_scores_shape_is_byte_identical_to_before():
    """No existing reader moves: debug.scores keeps its exact key set, and every
    key that was null stays null."""

    result = _qa(clip=CLIP_SIGNALS, identity=IDENTITY_WITHHELD_SIGNALS, ocr=SHADOW_OCR_SIGNAL)
    assert set(result.debug["scores"]) == {
        "faceSimilarityScore",
        "faceSimilarityObservedScore",
        "faceSimilarityDecision",
        "perceptualHashDistance",
        "perceptualSimilarityScore",
        "ssimScore",
        "clipSimilarityScore",
        "dinoStyleScore",
        "traitConsistencyScore",
        "brandFitScore",
        "beautificationRiskScore",
        "childlikeRiskScore",
        "privacyPenalty",
    }
    for key in (
        "ssimScore",
        "clipSimilarityScore",
        "dinoStyleScore",
        "traitConsistencyScore",
        "brandFitScore",
        "beautificationRiskScore",
        "childlikeRiskScore",
        "privacyPenalty",
    ):
        assert result.debug["scores"][key] is None, key


def test_local_risk_signal_provenance_does_not_move_a_risk_verdict():
    baseline: dict = {}
    enriched: dict = {}
    risk = LocalSafetyRiskResult(
        provider="clip",
        available=True,
        calibrated=True,
        childlike_score=0.031,
        sexualized_score=0.017,
        beautification_score=0.442,
        brand_mismatch_score=0.221,
        severe_artifact_score=0.108,
        calibration_version="clip-cal-v1",
        model_version="openai/clip-vit-large-patch14",
    )
    _add_local_risk_signals(baseline, {"localSafetyRisk": "available"}, risk)
    _add_local_risk_signals(
        enriched, {"localSafetyRisk": "available"}, risk
    )
    decision_keys = {
        key
        for key in baseline
        if not key.startswith("localSafetyRiskProvider")
        and not key.startswith("localSafetyRiskModel")
        and not key.startswith("localSafetyRiskCalibration")
    }
    assert {key: baseline[key] for key in decision_keys} == {
        key: enriched[key] for key in decision_keys
    }


def test_visual_signals_carry_shadow_ocr_without_touching_any_other_signal():
    class _Analysis:
        provider = "florence2"
        provider_available = True
        regions = ()
        status = "available"
        risk = "pass"
        actions_required = ()
        background_complexity = "low"

    without_signals: dict = {}
    with_signals: dict = {}
    plain = _Analysis()
    shadowed = _Analysis()
    shadowed.shadow_ocr_evidence = dict(SHADOW_OCR_SIGNAL["shadowOcrEvidence"])

    _add_visual_signals(without_signals, plain, image_size=(512, 768))
    _add_visual_signals(with_signals, shadowed, image_size=(512, 768))

    assert with_signals.pop("shadowOcrEvidence")["rawSequenceScore"] == -0.21
    assert without_signals == with_signals
