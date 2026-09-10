"""One crop convention on both sides -- measured, and consumed by nothing.

The effective identity score compares two different quantities. In
``build_candidate_qa_signals`` the candidate side is
``_crop_face(candidate_image, primary_face.bbox)`` -- a tight detector box --
while the source side is ``_crop_face(source_image, source_primary_bbox)``, and
that box comes from ``_source_primary_bbox(source_analysis)``, which reads
``sourceAnalysis.primaryFaceBbox``. ``SourceAnalysisResult.to_document`` never
writes that field, deliberately: a face box is not allowed to persist. So the
lookup returns None in production, ``_crop_face(image, None)`` returns
``image.copy()``, and the comparison is a whole photograph against a face crop.

The fix here is *not* to replace the effective score. The live calibration
(threshold 0.799743, review margin 0.185528, artifact ``g004-staging-20260823-v1``)
was fitted to the asymmetric distribution. Substituting a differently-shaped
score under thresholds fitted to the old one is a semantic bug, not a
correction. So:

  * the effective asymmetric score keeps its exact current behaviour
  * the symmetric score is recorded under its own name and read by nothing
  * no threshold, corridor, or lower bound is defined for it here

What a symmetric score *will* look like is an open question. These tests assert
that it is measured and attributable -- not that it is higher, and not that it
correlates better. Those are claims for a calibration with a labelled corpus,
and the corpus does not exist yet.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.analysis.schema import FaceDetection, FaceDetectorResult  # noqa: E402
from avatar_generation.analysis.small_face.config import SmallFacePipelineConfig  # noqa: E402
from avatar_generation.identity_crop import (  # noqa: E402
    EXPAND_BOTTOM,
    EXPAND_HORIZONTAL,
    EXPAND_TOP,
    IDENTITY_CROP_METHOD,
    IDENTITY_CROP_VERSION,
    TARGET_SIZE,
    crop_identity_region,
    identity_crop_provenance,
)
from avatar_generation.qa_signals import (  # noqa: E402
    SENSITIVE_EXACT_KEYS,
    SYMMETRIC_IDENTITY_SHADOW_ENV,
    SYMMETRIC_SHADOW_DISABLED,
    SYMMETRIC_SHADOW_MEASURED,
    SYMMETRIC_SHADOW_NO_SOURCE_FACE,
    _crop_face,
    build_candidate_qa_signals,
    symmetric_identity_shadow_enabled,
)

SOURCE_FACE = (0.30, 0.14, 0.28, 0.22)
CANDIDATE_FACE = (0.32, 0.18, 0.30, 0.24)


class _StubDetector:
    provider_name = "stub_detector"

    def __init__(self, faces_by_size):
        self._faces_by_size = faces_by_size
        self.calls = []

    def detect(self, image):
        self.calls.append(image.size)
        bbox = self._faces_by_size.get(image.size)
        faces = [FaceDetection(bbox=bbox, confidence=0.9)] if bbox else []
        return FaceDetectorResult(
            provider="stub_detector",
            image_width=image.size[0],
            image_height=image.size[1],
            faces=faces,
            model_availability={"faceDetector": "available", "mediapipe": "available"},
        )


class _StubVisualRisk:
    provider = "stub_visual"

    def analyze(self, image, *, primary_face_bbox_xyxy=None):
        from avatar_generation.analysis.visual_risk import VisualRiskAnalysis

        return VisualRiskAnalysis(
            provider="stub_visual",
            provider_available=True,
            regions=(),
            detector_availability={"<OCR_WITH_REGION>": "available", "<OD>": "available"},
            background_complexity="low",
        )


class _StubClipRisk:
    def __call__(self, image):
        from avatar_generation.qa_signals import LocalSafetyRiskResult

        return LocalSafetyRiskResult(
            provider="clip",
            available=True,
            calibrated=True,
            childlike_score=0.03,
            sexualized_score=0.02,
            beautification_score=0.4,
            brand_mismatch_score=0.2,
            severe_artifact_score=0.1,
            adult_like_score=0.9,
            brand_fit_score=0.8,
            calibration_version="clip-cal-v1",
        )


class _StubSimilarity:
    """Returns a different score per crop-pair size so the two comparisons are
    distinguishable."""

    def __init__(self):
        self.calls = []

    def compare(self, source_crop, candidate_crop, *, calibration_policy=None):
        self.calls.append((source_crop.size, candidate_crop.size))
        symmetric = source_crop.size == candidate_crop.size == (TARGET_SIZE, TARGET_SIZE)
        score = 0.82 if symmetric else 0.61

        class _Result:
            available = True
            identity_reliable = True
            needs_review = False
            identity_decision = "low_similarity_risk"
            calibration_version = "g004-staging-20260823-v1"

        result = _Result()
        result.score = score
        return result


def _image(size, colour):
    return Image.new("RGB", size, colour)


def _build(monkeypatch, *, enabled, source_size=(900, 1200), candidate_size=(768, 768)):
    if enabled:
        monkeypatch.setenv(SYMMETRIC_IDENTITY_SHADOW_ENV, "true")
    else:
        monkeypatch.delenv(SYMMETRIC_IDENTITY_SHADOW_ENV, raising=False)
    detector = _StubDetector({source_size: SOURCE_FACE, candidate_size: CANDIDATE_FACE})
    similarity = _StubSimilarity()
    result = build_candidate_qa_signals(
        source_image=_image(source_size, (180, 160, 150)),
        candidate_image=_image(candidate_size, (170, 150, 140)),
        # Exactly what production carries: no primaryFaceBbox, because
        # SourceAnalysisResult.to_document refuses to write one.
        source_analysis={"status": "ok", "face": {"count": 1}},
        reference_preprocess={"stage": "ok"},
        face_detector=detector,
        visual_risk_adapter=_StubVisualRisk(),
        local_risk_adapter=_StubClipRisk(),
        similarity_adapter=similarity,
        trait_qa_context={"traitQaMode": "disabled_by_pipeline", "traitQaAuthority": "server"},
    )
    return result, detector, similarity


# ---------------------------------------------------------------------------
# 1. The asymmetry is real
# ---------------------------------------------------------------------------


def test_production_source_analysis_carries_no_face_box():
    from avatar_generation.qa_runtime import _source_primary_bbox

    assert _source_primary_bbox({"status": "ok", "face": {"count": 1, "areaRatio": 0.08}}) is None


def test_crop_face_with_no_box_returns_the_whole_image():
    """This is the mechanism: the source side is not a crop at all."""

    image = _image((900, 1200), (10, 20, 30))
    assert _crop_face(image, None).size == (900, 1200)
    assert _crop_face(image, CANDIDATE_FACE).size != (900, 1200)


def test_effective_comparison_is_whole_image_against_face_crop(monkeypatch):
    _, _, similarity = _build(monkeypatch, enabled=False)
    source_size, candidate_size = similarity.calls[0]
    assert source_size == (900, 1200)
    assert candidate_size != source_size


# ---------------------------------------------------------------------------
# 2. The symmetric crop is genuinely symmetric
# ---------------------------------------------------------------------------


def test_both_sides_get_the_same_crop_convention(monkeypatch):
    _, _, similarity = _build(monkeypatch, enabled=True)
    assert len(similarity.calls) == 2
    shadow_source, shadow_candidate = similarity.calls[1]
    assert shadow_source == shadow_candidate == (TARGET_SIZE, TARGET_SIZE)


def test_the_same_detector_answers_for_both_sides(monkeypatch):
    _, detector, _ = _build(monkeypatch, enabled=True)
    assert detector.calls == [(768, 768), (900, 1200)]


def test_crop_geometry_comes_from_the_canonical_cropper_not_from_this_module():
    """The audit suggested "hull x 1.6". These numbers are the ones the
    repository's own HeadShouldersCropper already uses."""

    config = SmallFacePipelineConfig()
    assert EXPAND_HORIZONTAL == config.crop_expand_horizontal
    assert EXPAND_TOP == config.crop_expand_top
    assert EXPAND_BOTTOM == config.crop_expand_bottom
    assert TARGET_SIZE == config.primary_crop_target_size


def test_crop_is_square_and_size_invariant():
    """The same face in two differently-sized images must produce the same
    crop shape, or the two sides are not comparable after all."""

    small = crop_identity_region(_image((400, 600), (5, 5, 5)), SOURCE_FACE)
    large = crop_identity_region(_image((1600, 2400), (5, 5, 5)), SOURCE_FACE)
    assert small.size == large.size == (TARGET_SIZE, TARGET_SIZE)


def test_crop_off_the_edge_pads_instead_of_shifting():
    cropped = crop_identity_region(_image((300, 300), (5, 5, 5)), (0.0, 0.0, 0.12, 0.12))
    assert cropped.size == (TARGET_SIZE, TARGET_SIZE)


def test_missing_box_is_not_silently_the_whole_image():
    """The exact failure mode being fixed: no box must mean "no measurement",
    never "compare the whole photograph"."""

    assert crop_identity_region(_image((400, 600), (5, 5, 5)), None) is None


# ---------------------------------------------------------------------------
# 3. Shadow only -- nothing consumes it
# ---------------------------------------------------------------------------


def test_shadow_score_has_its_own_name(monkeypatch):
    result, _, _ = _build(monkeypatch, enabled=True)
    assert result.signals["shadowSymmetricIdentityStatus"] == SYMMETRIC_SHADOW_MEASURED
    assert result.signals["shadowSymmetricFaceSimilarityObservedScore"] == 0.82


def test_shadow_score_never_overwrites_the_effective_score(monkeypatch):
    result, _, _ = _build(monkeypatch, enabled=True)
    assert result.signals["faceSimilarityScore"] == 0.61
    assert result.signals["faceSimilarityObservedScore"] == 0.61


def test_shadow_carries_crop_provenance_without_any_geometry(monkeypatch):
    result, _, _ = _build(monkeypatch, enabled=True)
    assert result.signals["identityCropMethod"] == IDENTITY_CROP_METHOD
    assert result.signals["identityCropVersion"] == IDENTITY_CROP_VERSION
    assert result.signals["identitySourceDetector"] == result.signals["identityCandidateDetector"]


def test_provenance_document_contains_no_box():
    document = identity_crop_provenance().to_document()
    serialized = json.dumps(document).lower()
    for forbidden in ("bbox", "xmin", "x_min", "quad", "landmark", "embedding"):
        assert forbidden not in serialized, forbidden


# ---------------------------------------------------------------------------
# 4. DECISION DIFF = 0
# ---------------------------------------------------------------------------

DECISION_SIGNAL_KEYS = (
    "faceSimilarityScore",
    "faceSimilarityObservedScore",
    "faceSimilarityReliable",
    "faceSimilarityDecision",
    "faceSimilarityNeedsReview",
    "faceSimilarityCanonicalScoreAvailable",
    "cropConsistent",
    "cropIsolationQuality",
    "adultLike",
    "brandFit",
    "childlikeScore",
    "sexualizedScore",
    "beautificationScore",
    "severeArtifactScore",
    "brandMismatchScore",
    "secondaryPersonGenerated",
    "backgroundLeakageRisk",
    "secondaryFaceLeakageRisk",
    "watermarkQaAction",
    "textLogoWatermarkRisk",
    "logoTextWatermarkRisk",
    "visualRiskStatus",
)


def test_enabling_the_shadow_changes_no_signal_that_feeds_a_decision(monkeypatch):
    off, _, _ = _build(monkeypatch, enabled=False)
    on, _, _ = _build(monkeypatch, enabled=True)
    for key in DECISION_SIGNAL_KEYS:
        assert off.signals.get(key) == on.signals.get(key), key
    assert off.needs_review == on.needs_review
    assert off.models_unavailable == on.models_unavailable
    assert off.skipped_heavy_reason == on.skipped_heavy_reason


def test_enabling_the_shadow_changes_no_qa_verdict(monkeypatch):
    from avatar_generation.qa import AvatarQAThresholds, build_avatar_qa_from_signals

    off, _, _ = _build(monkeypatch, enabled=False)
    on, _, _ = _build(monkeypatch, enabled=True)
    contract = {"uniqueMarkQaMode": "disabled_by_pipeline", "uniqueMarkQaAuthority": "server"}
    a = build_avatar_qa_from_signals(
        off.signals, thresholds=AvatarQAThresholds(), pipeline_contract=contract
    )
    b = build_avatar_qa_from_signals(
        on.signals, thresholds=AvatarQAThresholds(), pipeline_contract=contract
    )
    for field in (
        "previewAllowed",
        "requiresHumanReview",
        "softPass",
        "rejectReasons",
        "reviewReasons",
        "adultQa",
        "privacyQa",
        "brandQa",
        "cropConsistency",
        "identifiabilityRisk",
        "childlikeRisk",
        "beautificationRisk",
        "logoTextWatermarkRisk",
        "backgroundLeakageRisk",
        "secondaryFaceLeakageRisk",
        "watermarkQaAction",
        "faceSimilarityScore",
    ):
        assert getattr(a, field) == getattr(b, field), field


def test_no_threshold_is_defined_for_the_shadow_score():
    """If a threshold ever appears for this score, it must arrive with a
    calibration, in its own change."""

    import avatar_generation.identity_crop as identity_crop
    import avatar_generation.qa_signals as signals_module

    for module in (identity_crop, signals_module):
        for name in dir(module):
            if "SHADOW" in name.upper() and (
                "THRESHOLD" in name.upper()
                or "MARGIN" in name.upper()
                or "CORRIDOR" in name.upper()
            ):
                pytest.fail(f"{module.__name__}.{name} defines a shadow threshold")


def test_shadow_is_off_unless_an_operator_turns_it_on(monkeypatch):
    monkeypatch.delenv(SYMMETRIC_IDENTITY_SHADOW_ENV, raising=False)
    assert symmetric_identity_shadow_enabled() is False
    result, detector, similarity = _build(monkeypatch, enabled=False)
    assert result.signals["shadowSymmetricIdentityStatus"] == SYMMETRIC_SHADOW_DISABLED
    assert "shadowSymmetricFaceSimilarityObservedScore" not in result.signals
    # No second detection, no second comparison: disabled costs nothing.
    assert detector.calls == [(768, 768)]
    assert len(similarity.calls) == 1


# ---------------------------------------------------------------------------
# 5. Privacy -- the ephemeral box must not escape
# ---------------------------------------------------------------------------


def test_no_face_box_reaches_the_signal_document(monkeypatch):
    result, _, _ = _build(monkeypatch, enabled=True)
    serialized = json.dumps(result.to_document(), default=str).lower()
    for forbidden in ("bbox", "quad_boxes", "landmark", "embedding", "0.30", "0.32"):
        assert forbidden not in serialized, forbidden


def test_no_shadow_signal_key_collides_with_the_sensitive_key_contract(monkeypatch):
    result, _, _ = _build(monkeypatch, enabled=True)
    for key in result.signals:
        assert str(key).lower().replace("-", "_") not in SENSITIVE_EXACT_KEYS, key


def test_source_face_geometry_is_not_returned_to_the_caller(monkeypatch):
    result, _, _ = _build(monkeypatch, enabled=True)
    for key, value in result.signals.items():
        if isinstance(value, (list, tuple)) and len(value) == 4:
            pytest.fail(f"signal {key} looks like a box: {value}")


# ---------------------------------------------------------------------------
# 6. Degradation
# ---------------------------------------------------------------------------


def test_no_source_face_records_why_and_measures_nothing(monkeypatch):
    monkeypatch.setenv(SYMMETRIC_IDENTITY_SHADOW_ENV, "true")
    detector = _StubDetector({(768, 768): CANDIDATE_FACE})  # source not in the map
    result = build_candidate_qa_signals(
        source_image=_image((900, 1200), (180, 160, 150)),
        candidate_image=_image((768, 768), (170, 150, 140)),
        source_analysis={"status": "ok"},
        reference_preprocess={"stage": "ok"},
        face_detector=detector,
        visual_risk_adapter=_StubVisualRisk(),
        local_risk_adapter=_StubClipRisk(),
        similarity_adapter=_StubSimilarity(),
        trait_qa_context={"traitQaMode": "disabled_by_pipeline", "traitQaAuthority": "server"},
    )
    assert result.signals["shadowSymmetricIdentityStatus"] == SYMMETRIC_SHADOW_NO_SOURCE_FACE
    assert "shadowSymmetricFaceSimilarityObservedScore" not in result.signals
    # The effective score is untouched by the shadow failing.
    assert result.signals["faceSimilarityScore"] == 0.61


def test_shadow_failure_cannot_break_the_qa_run(monkeypatch):
    monkeypatch.setenv(SYMMETRIC_IDENTITY_SHADOW_ENV, "true")

    class _ExplodingOnSecondCall(_StubDetector):
        def detect(self, image):
            if len(self.calls) >= 1:
                self.calls.append(image.size)
                raise RuntimeError("detector blew up on the source side")
            return super().detect(image)

    detector = _ExplodingOnSecondCall({(768, 768): CANDIDATE_FACE, (900, 1200): SOURCE_FACE})
    result = build_candidate_qa_signals(
        source_image=_image((900, 1200), (180, 160, 150)),
        candidate_image=_image((768, 768), (170, 150, 140)),
        source_analysis={"status": "ok"},
        reference_preprocess={"stage": "ok"},
        face_detector=detector,
        visual_risk_adapter=_StubVisualRisk(),
        local_risk_adapter=_StubClipRisk(),
        similarity_adapter=_StubSimilarity(),
        trait_qa_context={"traitQaMode": "disabled_by_pipeline", "traitQaAuthority": "server"},
    )
    assert result.signals["faceSimilarityScore"] == 0.61
    assert result.signals["faceSimilarityReliable"] is True
    assert result.signals["shadowSymmetricIdentityStatus"] == "similarity_adapter_error"


# ---------------------------------------------------------------------------
# 7. The shadow score must reach persistence
# ---------------------------------------------------------------------------


def _qa_from(signal_result):
    from avatar_generation.qa import AvatarQAThresholds, build_avatar_qa_from_signals

    return build_avatar_qa_from_signals(
        signal_result.signals,
        thresholds=AvatarQAThresholds(),
        pipeline_contract={
            "uniqueMarkQaMode": "disabled_by_pipeline",
            "uniqueMarkQaAuthority": "server",
        },
    )


def test_shadow_score_survives_the_document_build(monkeypatch):
    """shadowOcrEvidence was computed and dropped for its whole lifetime. This
    score must not repeat that."""

    result, _, _ = _build(monkeypatch, enabled=True)
    shadow = _qa_from(result).debug["symmetricIdentityShadow"]
    assert shadow["status"] == SYMMETRIC_SHADOW_MEASURED
    assert shadow["symmetricObservedScore"] == 0.82
    assert shadow["asymmetricObservedScore"] == 0.61
    assert shadow["identityCropVersion"] == IDENTITY_CROP_VERSION


def test_persisted_shadow_states_that_nothing_consumes_it(monkeypatch):
    result, _, _ = _build(monkeypatch, enabled=True)
    shadow = _qa_from(result).debug["symmetricIdentityShadow"]
    assert shadow["consumedByPolicy"] is False
    assert shadow["scoreCalibrated"] is False


def test_disabled_shadow_is_recorded_as_disabled_not_as_a_score(monkeypatch):
    result, _, _ = _build(monkeypatch, enabled=False)
    shadow = _qa_from(result).debug["symmetricIdentityShadow"]
    assert shadow["status"] == SYMMETRIC_SHADOW_DISABLED
    assert "symmetricObservedScore" not in shadow


def test_persisted_shadow_carries_no_geometry(monkeypatch):
    result, _, _ = _build(monkeypatch, enabled=True)
    serialized = json.dumps(_qa_from(result).debug, default=str).lower()
    for forbidden in ("bbox", "quad_boxes", "landmark", "embedding"):
        assert forbidden not in serialized, forbidden


def test_persisting_the_shadow_does_not_move_the_effective_score(monkeypatch):
    off = _qa_from(_build(monkeypatch, enabled=False)[0])
    on = _qa_from(_build(monkeypatch, enabled=True)[0])
    assert off.debug["scores"] == on.debug["scores"]
    assert off.debug["thresholdSnapshot"] == on.debug["thresholdSnapshot"]
    assert off.debug["decision"] == on.debug["decision"]
