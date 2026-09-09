"""Fidelity QA provenance: record the calibration that actually decided.

Production candidates observe face similarity around 0.64-0.68 and every one of
them reports faceSimilarityScore = null. That is not a wiring gap. The producer
policy in image_similarity.py splits on the calibration artifact:

    threshold     = 0.799743
    reviewMargin  = 0.185528
    review band   = [0.614215, 0.799743)

An observed score inside that band yields identity_decision="review_similarity"
and identity_reliable=False, and qa_signals only promotes the observed score to
the canonical faceSimilarityScore when identity_reliable is True.

So the artifact is the decision authority. The QA record does not say so:

  A. The producer computes threshold and calibration_version, and even exposes
     them from SimilarityResult.to_document() -- which no production caller
     invokes. _add_similarity_signals reads calibration_version only as a
     truthiness gate and records neither number. Meanwhile thresholdSnapshot
     reports the env thresholds (AVATAR_QA_FACE_SIMILARITY_REVIEW/REJECT), which
     _resolve_identifiability_risk consults only on the fallback path. A reader
     sees configured numbers and no way to tell whether they were applied.

  B. The canonical score is absent with no machine-readable reason for its
     absence.

  C. Corridor criticalSignalsAvailable is a seven-way conjunction, reported as
     one bool, and four distinct causes collapse into the single reason code
     "fidelity_signal_unavailable". trait_coverage_status -- one of the
     conjuncts -- never reaches the document at all.

These tests pin provenance only. The decision-diff tests below must hold
identically before and after the fix: no threshold moves, no margin shrinks, no
score is promoted, no shadow signal becomes blocking.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation import qa_signals  # noqa: E402
from avatar_generation.fidelity_corridor import (  # noqa: E402
    CorridorMode,
    CorridorPolicy,
    IdentityPrivacySignal,
    evaluate_fidelity_corridor,
)
from avatar_generation.fidelity_signals import (  # noqa: E402
    FIDELITY_COMPONENT_KEYS,
    FidelitySignalBundle,
)
from avatar_generation.model_adapters.image_similarity import (  # noqa: E402
    CalibrationPolicy,
    SimilarityResult,
    compare_image_similarity,
)
from avatar_generation.qa import (  # noqa: E402
    AvatarQAThresholds,
    build_avatar_qa_from_signals,
)

# The artifact pinned into the production worker image.
CALIBRATION_VERSION = "g004-staging-20260823-v1"
ARTIFACT_THRESHOLD = 0.799743
ARTIFACT_REVIEW_MARGIN = 0.185528
REVIEW_BAND_LOW = round(ARTIFACT_THRESHOLD - ARTIFACT_REVIEW_MARGIN, 6)

# A production-observed magnitude, inside the review band. No identifiers.
OBSERVED_IN_BAND = 0.6646

ARTIFACT_PATH = (
    AI_MODEL_DIR
    / "avatar_generation"
    / "artifacts"
    / "avatar_qa_calibration_v1.json"
)


def _similarity(
    *,
    score,
    decision,
    reliable,
    needs_review,
    calibration_version=CALIBRATION_VERSION,
    threshold=ARTIFACT_THRESHOLD,
    review_margin=ARTIFACT_REVIEW_MARGIN,
    available=True,
):
    return SimilarityResult(
        provider="clip",
        provider_version="clip-vit-large-patch14",
        available=available,
        score=score,
        broad_consistency=score,
        identity_decision=decision,
        identity_reliable=reliable,
        needs_review=needs_review,
        calibration_version=calibration_version,
        threshold=threshold,
        review_margin=review_margin,
    )


def _review_band():
    return _similarity(
        score=OBSERVED_IN_BAND,
        decision="review_similarity",
        reliable=False,
        needs_review=True,
    )


def _reliable_low_risk():
    return _similarity(
        score=0.41,
        decision="low_similarity_risk",
        reliable=True,
        needs_review=False,
    )


def _uncalibrated():
    return _similarity(
        score=OBSERVED_IN_BAND,
        decision="uncertain",
        reliable=False,
        needs_review=True,
        calibration_version="",
        threshold=None,
        review_margin=None,
    )


def _emit(similarity):
    signals: dict = {}
    availability: dict = {}
    qa_signals._add_similarity_signals(signals, availability, similarity)
    return signals, availability


# --------------------------------------------------------------------------
# A. the calibration that actually decided must be in the record
# --------------------------------------------------------------------------


class _FixedEncoder:
    provider = "dummy"
    version = "test-v1"

    def __init__(self, vectors):
        self.vectors = list(vectors)

    def is_available(self):
        return True

    def encode_image(self, image):
        return self.vectors.pop(0)


def test_producer_carries_the_margin_it_actually_applied():
    """The fixtures above assume this; without it they would be fiction."""

    policy = CalibrationPolicy(
        calibration_version=CALIBRATION_VERSION,
        threshold=ARTIFACT_THRESHOLD,
        review_margin=ARTIFACT_REVIEW_MARGIN,
    )

    result = compare_image_similarity(
        "a",
        "b",
        encoder=_FixedEncoder([[1.0, 0.0], [0.66, 0.7512389898822546]]),
        calibration_policy=policy,
    )

    assert result.identity_decision == "review_similarity"
    assert result.identity_reliable is False
    assert result.review_margin == ARTIFACT_REVIEW_MARGIN
    assert result.threshold == ARTIFACT_THRESHOLD


def test_review_band_record_names_the_calibration_that_decided():
    signals, _ = _emit(_review_band())

    effective = signals.get("effectiveProducerCalibration")
    assert effective is not None, (
        "the artifact decided this candidate; the record must say which one"
    )
    assert effective["calibrationVersion"] == CALIBRATION_VERSION
    assert effective["threshold"] == ARTIFACT_THRESHOLD
    assert effective["reviewMargin"] == ARTIFACT_REVIEW_MARGIN
    assert effective["reviewBandLow"] == REVIEW_BAND_LOW
    assert effective["reviewBandHigh"] == ARTIFACT_THRESHOLD


def test_effective_calibration_explains_why_the_observed_score_was_not_promoted():
    signals, _ = _emit(_review_band())
    effective = signals["effectiveProducerCalibration"]

    assert (
        effective["reviewBandLow"]
        <= signals["faceSimilarityObservedScore"]
        < effective["reviewBandHigh"]
    ), "the recorded band must be the one the observed score actually fell into"


def test_qa_record_separates_configured_thresholds_from_the_applied_authority():
    signals, availability = _emit(_review_band())
    signals["modelAvailability"] = availability
    thresholds = AvatarQAThresholds(
        face_similarity_review=0.68,
        face_similarity_reject=0.72,
    )

    debug = build_avatar_qa_from_signals(signals, thresholds=thresholds).debug

    assert debug["fidelityDecisionMode"] == "producer_calibration", (
        "the artifact band decided; the record must not imply the env "
        "thresholds were applied"
    )
    configured = debug["configuredQaThresholds"]
    assert configured["faceSimilarityReview"] == 0.68
    assert configured["faceSimilarityReject"] == 0.72
    assert configured["applied"] is False


def test_fallback_path_reports_the_configured_thresholds_as_applied():
    signals, availability = _emit(_uncalibrated())
    signals["modelAvailability"] = availability
    thresholds = AvatarQAThresholds(
        face_similarity_review=0.68,
        face_similarity_reject=0.72,
    )

    debug = build_avatar_qa_from_signals(signals, thresholds=thresholds).debug

    assert debug["fidelityDecisionMode"] == "configured_thresholds"
    assert debug["configuredQaThresholds"]["applied"] is True


# --------------------------------------------------------------------------
# B. canonical score absence needs a machine-readable reason
# --------------------------------------------------------------------------


def test_review_band_absence_reason_is_machine_readable():
    signals, _ = _emit(_review_band())

    assert signals["faceSimilarityCanonicalScoreAvailable"] is False
    assert (
        signals["faceSimilarityCanonicalUnavailableReason"]
        == "identity_within_calibrated_review_band"
    )


def test_uncalibrated_absence_has_its_own_reason():
    signals, _ = _emit(_uncalibrated())

    assert signals["faceSimilarityCanonicalScoreAvailable"] is False
    assert (
        signals["faceSimilarityCanonicalUnavailableReason"]
        == "producer_calibration_absent"
    )


def test_unavailable_similarity_has_its_own_reason():
    signals, _ = _emit(
        _similarity(
            score=None,
            decision="",
            reliable=False,
            needs_review=True,
            available=False,
        )
    )

    assert signals["faceSimilarityCanonicalScoreAvailable"] is False
    assert (
        signals["faceSimilarityCanonicalUnavailableReason"]
        == "similarity_signal_unavailable"
    )


def test_reliable_candidate_reports_the_canonical_score_as_available():
    signals, _ = _emit(_reliable_low_risk())

    assert signals["faceSimilarityCanonicalScoreAvailable"] is True
    assert "faceSimilarityCanonicalUnavailableReason" not in signals


# --------------------------------------------------------------------------
# C. criticalSignalsAvailable must name the conjunct that failed
# --------------------------------------------------------------------------


def _bundle(*, trait_coverage_status="sufficient", conflicting=False):
    return FidelitySignalBundle(
        fidelity_score=0.7,
        broad_visual_score=0.7,
        geometry_score=0.7,
        trait_consistency_score=0.7,
        composition_score=0.7,
        adult_naturalness_score=0.7,
        bands={
            "fidelity": "high",
            "traitConsistency": "high",
            "composition": "high",
        },
        model_availability={key: "available" for key in FIDELITY_COMPONENT_KEYS},
        model_versions={key: f"{key.lower()}_v1" for key in FIDELITY_COMPONENT_KEYS},
        timing_ms={"total": 5.0},
        trait_coverage_status=trait_coverage_status,
        lower_bound_decision="pass",
        conflicting=conflicting,
    )


def _active_pass():
    return {
        "previewAllowed": True,
        "requiresHumanReview": False,
        "softPass": False,
        "rejectReasons": [],
        "reviewReasons": [],
        "selectedForPreview": True,
        "adultQa": "pass",
        "childlikeRisk": "low",
        "beautificationRisk": "low",
        "cropConsistency": "pass",
        "cropIsolationQuality": "pass",
        "uniqueMarkCopyRisk": "low",
        "logoTextWatermarkRisk": "low",
        "textLogoWatermarkRisk": "low",
        "backgroundLeakageRisk": "low",
        "secondaryFaceLeakageRisk": "low",
    }


def _corridor(bundle, *, policy=None):
    return evaluate_fidelity_corridor(
        active_qa=_active_pass(),
        identity_signal=IdentityPrivacySignal(
            available=True,
            calibrated=True,
            upper_bound_decision="pass",
            risk_band="low",
            model_version="identity_privacy_v1",
        ),
        fidelity_signals=bundle,
        policy=policy
        or CorridorPolicy(
            mode=CorridorMode.SHADOW,
            calibration_version="corridor_calibration_fixture_v1",
        ),
    )


def test_corridor_names_the_missing_trait_coverage_conjunct():
    document = _corridor(_bundle(trait_coverage_status="unavailable")).to_document()

    assert document["criticalSignalsAvailable"] is False
    assert "traitCoverage" in document["criticalSignalGaps"], (
        "trait coverage is a conjunct of criticalSignalsAvailable and never "
        "reaches the document, so the false cannot be explained"
    )


def test_corridor_names_the_uncalibrated_policy_conjunct():
    document = _corridor(
        _bundle(), policy=CorridorPolicy(mode=CorridorMode.SHADOW)
    ).to_document()

    assert document["criticalSignalsAvailable"] is False
    assert "policyCalibration" in document["criticalSignalGaps"]


def test_corridor_reports_no_gaps_when_critical_signals_are_available():
    document = _corridor(_bundle()).to_document()

    assert document["criticalSignalsAvailable"] is True
    assert document["criticalSignalGaps"] == []


# --------------------------------------------------------------------------
# decision diff = 0 -- these must hold identically before and after C0
# --------------------------------------------------------------------------

DECISION_KEYS = (
    "faceSimilarityScore",
    "faceSimilarityObservedScore",
    "faceSimilarityReliable",
    "faceSimilarityNeedsReview",
    "faceSimilarityCalibrationState",
    "faceSimilarityDecision",
)


def test_review_band_decision_outputs_are_unchanged():
    signals, availability = _emit(_review_band())

    assert {key: signals.get(key) for key in DECISION_KEYS} == {
        "faceSimilarityScore": None,
        "faceSimilarityObservedScore": OBSERVED_IN_BAND,
        "faceSimilarityReliable": False,
        "faceSimilarityNeedsReview": True,
        "faceSimilarityCalibrationState": "calibrated_review_band",
        "faceSimilarityDecision": "review_similarity",
    }
    assert availability["faceSimilarity"] == "available"


def test_reliable_decision_outputs_are_unchanged():
    signals, availability = _emit(_reliable_low_risk())

    assert {key: signals.get(key) for key in DECISION_KEYS} == {
        "faceSimilarityScore": 0.41,
        "faceSimilarityObservedScore": 0.41,
        "faceSimilarityReliable": True,
        "faceSimilarityNeedsReview": False,
        "faceSimilarityCalibrationState": "calibrated",
        "faceSimilarityDecision": "low_similarity_risk",
    }
    assert availability["faceSimilarity"] == "available"


def test_uncalibrated_decision_outputs_are_unchanged():
    signals, availability = _emit(_uncalibrated())

    assert signals.get("faceSimilarityScore") is None
    assert signals["faceSimilarityReliable"] is False
    assert signals["faceSimilarityNeedsReview"] is True
    assert "faceSimilarityCalibrationState" not in signals
    assert availability["faceSimilarity"] == "uncalibrated"


def test_review_band_identifiability_risk_stays_medium():
    signals, availability = _emit(_review_band())
    signals["modelAvailability"] = availability

    result = build_avatar_qa_from_signals(
        signals,
        thresholds=AvatarQAThresholds(
            face_similarity_review=0.68,
            face_similarity_reject=0.72,
        ),
    )

    assert result.identifiabilityRisk == "medium"
    assert result.faceSimilarityScore is None


def test_calibration_artifact_numbers_are_untouched():
    face = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))["faceSimilarity"]

    assert face["threshold"] == ARTIFACT_THRESHOLD
    assert face["reviewMargin"] == ARTIFACT_REVIEW_MARGIN


def test_corridor_stays_in_shadow_and_grants_no_new_eligibility():
    decision = _corridor(_bundle(trait_coverage_status="unavailable"))

    assert decision.mode is CorridorMode.SHADOW
    assert decision.eligible_for_ranking is False
