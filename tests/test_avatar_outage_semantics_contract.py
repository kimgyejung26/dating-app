"""What counts as an outage, and what an outage is allowed to conclude.

Two production false positives share one shape: a QA signal that was never
reported is written down as ``"unavailable"``, and downstream code reads that
fabricated outage as fact.

  1. ``_qa_debug_document`` hardcodes ``mediapipe`` to ``"unavailable"`` when the
     runtime did not report it. ``mediapipe`` appears in neither
     ``signalContract.required`` nor ``OPTIONAL_SIGNAL_NAMES``, so nothing
     requires it -- but ``preview_policy`` and ``adaptive_generation`` both scan
     *every* value in the flat map and treat any ``"unavailable"`` as a systemic
     outage. The OpenCV Haar fallback detector reports no ``mediapipe`` key at
     all, so a run whose face detection genuinely worked emits a record saying
     ``requiredSignalFailures: []`` and is gated anyway. ``dino`` had exactly
     this defect and was fixed on 2026-09-07; ``mediapipe`` is the same shape
     and was not.

  2. ``_is_primary_person(bbox, None)`` returns False, so when the face detector
     could not run there is no anchor and *every* person Florence's object
     detector finds is relabelled ``background-person``. One person in the frame
     becomes ``secondaryPersonGenerated`` -> the hard rejects
     ``secondary_person_generated`` and ``background_leakage``. A detector
     outage cannot observe a second person; it can only fail to rule one out.

The fix is a classification fix, not a relaxation. An absent *required* signal
still fails closed, an explicitly reported outage is still honoured verbatim,
and person evidence that does not depend on the anchor -- two or more people --
still hard-rejects with the detector down.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.adaptive_generation import (  # noqa: E402
    AdaptiveGenerationPolicy,
    _systemic_unavailable_reason,
    plan_generation_round,
)
from avatar_generation.analysis.visual_risk import (  # noqa: E402
    ACTION_NEUTRALIZE_BACKGROUND_PERSON,
    KIND_BACKGROUND_PERSON,
    KIND_PERSON,
    _actions_for,
    _classify_background_complexity,
    _parse_florence_regions,
)
from avatar_generation.preview_policy import (  # noqa: E402
    is_preview_eligible,
    passes_absolute_preview_checks,
)
from avatar_generation.qa import (  # noqa: E402
    AvatarQAThresholds,
    _qa_debug_document,
    build_avatar_qa_from_signals,
)
from avatar_generation.qa_contract import (  # noqa: E402
    OPTIONAL_SIGNAL_NAMES,
    required_signal_failure_codes,
)
from avatar_generation.qa_signals import resolve_person_evidence  # noqa: E402

# What the OpenCV Haar fallback path actually produces. MediaPipe is not
# installed, Haar answered, and Haar reports no model_availability of its own,
# so `mediapipe` is simply never mentioned.
HAAR_FALLBACK_AVAILABILITY = {
    "faceDetector": "available",
    "visualRisk": "available",
    "faceSimilarity": "available",
    "localSafetyRisk": "available",
}
# What the MediaPipe path produces.
MEDIAPIPE_AVAILABILITY = {**HAAR_FALLBACK_AVAILABILITY, "mediapipe": "available"}


def _debug(model_availability, *, decision_tier="hard_pass"):
    return _qa_debug_document(
        thresholds=AvatarQAThresholds(),
        face_similarity_score=0.10,
        perceptual_similarity_score=None,
        model_availability=model_availability,
        decision_tier=decision_tier,
        hard_reject_reasons=(),
        needs_review_reasons=(),
        soft_pass_reasons=(),
    )


def _clean_qa(debug, **overrides):
    qa = {
        "previewAllowed": True,
        "requiresHumanReview": False,
        "softPass": False,
        "rejectReasons": [],
        "reviewReasons": [],
        "adultQa": "pass",
        "privacyQa": "pass",
        "brandQa": "pass",
        "cropConsistency": "pass",
        "cropIsolationQuality": "pass",
        "childlikeRisk": "low",
        "beautificationRisk": "low",
        "identifiabilityRisk": "low",
        "logoTextWatermarkRisk": "low",
        "backgroundLeakageRisk": "low",
        "secondaryFaceLeakageRisk": "low",
        "textLogoWatermarkRisk": "low",
        "uniqueMarkCopyRisk": "low",
        "debug": debug,
    }
    qa.update(overrides)
    return qa


def _candidate(qa, *, status="hard_pass", candidate_id="c"):
    return {"candidateId": candidate_id, "status": status, "qa": dict(qa)}


# ---------------------------------------------------------------------------
# 1. An unreported, unrequired signal is not an outage
# ---------------------------------------------------------------------------


def test_mediapipe_is_neither_required_nor_declared_optional():
    """The premise: nothing in the contract asks for this signal."""

    debug = _debug(HAAR_FALLBACK_AVAILABILITY)
    assert "mediapipe" not in debug["signalContract"]["required"]
    assert "mediapipe" not in OPTIONAL_SIGNAL_NAMES


def test_unreported_mediapipe_is_not_written_down_as_an_outage():
    debug = _debug(HAAR_FALLBACK_AVAILABILITY)
    assert debug["modelAvailability"]["mediapipe"] == "not_required"


def test_haar_fallback_record_is_self_consistent():
    """No required signal failed, so nothing may claim a critical model outage."""

    debug = _debug(HAAR_FALLBACK_AVAILABILITY)
    assert debug["signalContract"]["requiredSignalFailures"] == []
    assert required_signal_failure_codes(debug["modelAvailability"]) == ()
    candidate = _candidate(_clean_qa(debug))
    assert passes_absolute_preview_checks(candidate) is True
    assert is_preview_eligible(candidate) is True
    assert _systemic_unavailable_reason(candidate) == ""


def test_mediapipe_path_is_unaffected():
    debug = _debug(MEDIAPIPE_AVAILABILITY)
    assert debug["modelAvailability"]["mediapipe"] == "available"
    assert is_preview_eligible(_candidate(_clean_qa(debug))) is True


# ---------------------------------------------------------------------------
# 2. Required outage still fails closed
# ---------------------------------------------------------------------------


def test_required_capability_unavailable_still_gates_preview():
    for required_key in ("faceDetector", "visualRisk", "faceSimilarity", "localSafetyRisk"):
        debug = _debug({**MEDIAPIPE_AVAILABILITY, required_key: "unavailable"})
        candidate = _candidate(_clean_qa(debug))
        assert passes_absolute_preview_checks(candidate) is False, required_key
        assert is_preview_eligible(candidate) is False, required_key
        assert (
            _systemic_unavailable_reason(candidate) == "qa_critical_model_unavailable"
        ), required_key


def test_required_signal_missing_entirely_still_fails_closed():
    """Absence of a *required* signal is an outage; that asymmetry is the point."""

    debug = _debug(
        {"visualRisk": "available", "faceSimilarity": "available", "localSafetyRisk": "available"}
    )
    assert debug["modelAvailability"]["faceDetector"] == "unavailable"
    assert "face_detector_unavailable" in debug["signalContract"]["requiredSignalFailures"]
    assert passes_absolute_preview_checks(_candidate(_clean_qa(debug))) is False


def test_required_model_outage_still_suppresses_extra_generation():
    debug = _debug(
        {**MEDIAPIPE_AVAILABILITY, "faceSimilarity": "unavailable"},
        decision_tier="needs_review",
    )
    qa = _clean_qa(
        debug,
        previewAllowed=False,
        requiresHumanReview=True,
        reviewReasons=["model_unavailable"],
    )
    candidates = [_candidate(qa, status="needs_review", candidate_id=f"c{i}") for i in range(2)]
    plan = plan_generation_round(candidates, policy=AdaptiveGenerationPolicy())
    assert plan.reason == "extra_suppressed_systemic_unavailable"
    assert plan.candidate_count == 0


# ---------------------------------------------------------------------------
# 3. The four availability words keep four distinct meanings
# ---------------------------------------------------------------------------


def test_the_four_availability_states_are_distinguishable():
    unreported = _debug(HAAR_FALLBACK_AVAILABILITY)
    explicit = _debug({**HAAR_FALLBACK_AVAILABILITY, "mediapipe": "unavailable"})
    uncalibrated = _debug({**MEDIAPIPE_AVAILABILITY, "localSafetyRisk": "uncalibrated"})

    assert unreported["modelAvailability"]["mediapipe"] == "not_required"
    # An explicit report is testimony and is preserved verbatim, even for a
    # signal the contract does not require. Preserved is not the same as
    # authoritative -- see test_explicit_outage_of_a_non_required_signal_*.
    assert explicit["modelAvailability"]["mediapipe"] == "unavailable"
    assert uncalibrated["modelAvailability"]["localSafetyRisk"] == "uncalibrated"

    # Only the required capability's state decides the gate.
    assert passes_absolute_preview_checks(_candidate(_clean_qa(unreported))) is True
    assert passes_absolute_preview_checks(_candidate(_clean_qa(explicit))) is True
    assert passes_absolute_preview_checks(_candidate(_clean_qa(uncalibrated))) is False


def test_absent_optional_signal_keeps_its_existing_reporting_semantics():
    debug = _debug(MEDIAPIPE_AVAILABILITY)
    assert debug["modelAvailability"]["dino"] == "not_required"
    assert debug["signalContract"]["optional"] == ["dino"]


def test_explicit_outage_of_a_non_required_signal_is_recorded_not_enforced():
    """qa_preflight declares dino critical=False / not_in_active_qa_contract, and
    QARuntimeReadiness.blocking_components is "critical and not available". A
    signal that no QA decision consults cannot make a decision less trustworthy
    by failing, so withholding a candidate over it is a fabricated outage."""

    for key in ("dino", "mediapipe"):
        debug = _debug({**MEDIAPIPE_AVAILABILITY, key: "unavailable"})
        assert debug["modelAvailability"][key] == "unavailable", key
        assert debug["signalContract"]["requiredSignalFailures"] == [], key
        candidate = _candidate(_clean_qa(debug))
        assert passes_absolute_preview_checks(candidate) is True, key
        assert is_preview_eligible(candidate) is True, key
        assert _systemic_unavailable_reason(candidate) == "", key


def test_gate_agrees_with_the_runtime_readiness_contract():
    """The two authorities must not disagree. qa_preflight decides readiness with
    "critical and not available"; the per-candidate gate now applies the same
    rule through blocking_signal_failure_codes."""

    from avatar_generation.qa_preflight import build_qa_runtime_readiness

    dino = next(
        component
        for component in build_qa_runtime_readiness().components
        if component.name == "dino"
    )
    assert dino.critical is False
    assert dino.status == "not_required"
    assert dino.reason == "not_in_active_qa_contract"


def test_optional_outage_does_not_stand_down_the_extra_generation_round():
    """Suppressing the round costs the user their remaining candidates."""

    debug = _debug({**MEDIAPIPE_AVAILABILITY, "dino": "unavailable"}, decision_tier="needs_review")
    qa = _clean_qa(
        debug,
        previewAllowed=False,
        requiresHumanReview=True,
        reviewReasons=["actual_qa_signal_review"],
    )
    candidates = [_candidate(qa, status="needs_review", candidate_id=f"c{i}") for i in range(2)]
    plan = plan_generation_round(candidates, policy=AdaptiveGenerationPolicy())
    assert plan.reason != "extra_suppressed_systemic_unavailable"


# The exact availability map carried by production jobs avatar_job_992 and
# avatar_job_78f (avatar_qa_v7_watermark_evidence_parity_v1). Every required
# signal available, rejectReasons empty, and dino reported unavailable.
PRODUCTION_DINO_OUTAGE_AVAILABILITY = {
    "faceDetector": "available",
    "visualRisk": "available",
    "faceSimilarity": "available",
    "localSafetyRisk": "available",
    "clipSafety": "available",
    "clip": "available",
    "mediapipe": "available",
    "dino": "unavailable",
}


def test_recorded_production_jobs_are_no_longer_denied_their_extra_round():
    """Read-only replay of 298 stored candidates against main showed two live
    current-contract jobs suppressed at extra_suppressed_systemic_unavailable
    with every required signal available and no rejectReasons. Their users were
    denied the extra candidates the adaptive policy had allocated, over a signal
    no QA decision reads."""

    debug = _debug(PRODUCTION_DINO_OUTAGE_AVAILABILITY, decision_tier="needs_review")
    assert debug["signalContract"]["requiredSignalFailures"] == []
    qa = _clean_qa(
        debug,
        previewAllowed=False,
        requiresHumanReview=True,
        privacyQa="needs_review",
        identifiabilityRisk="medium",
        reviewReasons=["actual_qa_signal_review"],
    )
    candidates = [_candidate(qa, status="needs_review", candidate_id=f"c{i}") for i in range(2)]
    for candidate in candidates:
        assert _systemic_unavailable_reason(candidate) == ""
    plan = plan_generation_round(candidates, policy=AdaptiveGenerationPolicy())
    assert plan.reason == "extra_insufficient_safe"
    assert plan.candidate_count > 0


def test_those_same_candidates_are_still_withheld_from_preview():
    """The fix returns the generation round, not the candidates. These stay
    needs_review on their own QA verdict."""

    debug = _debug(PRODUCTION_DINO_OUTAGE_AVAILABILITY, decision_tier="needs_review")
    qa = _clean_qa(
        debug,
        previewAllowed=False,
        requiresHumanReview=True,
        privacyQa="needs_review",
        identifiabilityRisk="medium",
        reviewReasons=["actual_qa_signal_review"],
    )
    candidate = _candidate(qa, status="needs_review")
    assert is_preview_eligible(candidate) is False


def test_mediapipe_outage_with_a_working_fallback_is_not_a_capability_failure():
    """Case D2: mediapipe is a provider of the faceDetector capability, not a
    capability. Haar answering means face detection worked."""

    debug = _debug({**MEDIAPIPE_AVAILABILITY, "mediapipe": "unavailable"})
    assert debug["modelAvailability"]["faceDetector"] == "available"
    assert is_preview_eligible(_candidate(_clean_qa(debug))) is True


def test_mediapipe_outage_with_no_working_fallback_still_fails_closed():
    """Case E: no fallback answered, so the capability itself is gone."""

    debug = _debug(
        {**MEDIAPIPE_AVAILABILITY, "mediapipe": "unavailable", "faceDetector": "unavailable"}
    )
    assert "face_detector_unavailable" in debug["signalContract"]["requiredSignalFailures"]
    candidate = _candidate(_clean_qa(debug))
    assert passes_absolute_preview_checks(candidate) is False
    assert _systemic_unavailable_reason(candidate) == "qa_critical_model_unavailable"


def test_explicit_safety_reject_is_unaffected_by_availability_semantics():
    """Case F: whatever the availability map says, a real rejection stands."""

    for availability in (
        MEDIAPIPE_AVAILABILITY,
        {**MEDIAPIPE_AVAILABILITY, "dino": "unavailable"},
        {**MEDIAPIPE_AVAILABILITY, "faceDetector": "unavailable"},
    ):
        debug = _debug(availability, decision_tier="rejected")
        qa = _clean_qa(
            debug, previewAllowed=False, rejectReasons=["secondary_person_generated"]
        )
        candidate = _candidate(qa, status="rejected")
        assert passes_absolute_preview_checks(candidate) is False
        assert is_preview_eligible(candidate) is False


# ---------------------------------------------------------------------------
# 4. The fix cannot turn an unsafe candidate into a safe one
# ---------------------------------------------------------------------------


def test_real_safety_rejection_survives_the_availability_fix():
    debug = _debug(HAAR_FALLBACK_AVAILABILITY, decision_tier="rejected")
    qa = _clean_qa(
        debug,
        previewAllowed=False,
        rejectReasons=["sexualized_or_nightlife"],
        adultQa="fail",
    )
    candidate = _candidate(qa, status="rejected")
    assert passes_absolute_preview_checks(candidate) is False
    assert is_preview_eligible(candidate) is False


def test_needs_review_candidate_is_not_promoted_by_the_availability_fix():
    debug = _debug(HAAR_FALLBACK_AVAILABILITY, decision_tier="needs_review")
    qa = _clean_qa(
        debug,
        previewAllowed=False,
        requiresHumanReview=True,
        privacyQa="needs_review",
        identifiabilityRisk="medium",
        reviewReasons=["actual_qa_signal_review"],
    )
    candidate = _candidate(qa, status="needs_review")
    assert is_preview_eligible(candidate) is False
    assert is_preview_eligible(candidate, allow_soft_review=True) is True


def test_extra_generation_follows_canonical_policy_when_nothing_is_unavailable():
    """No outage anywhere: the adaptive policy decides, not the availability gate."""

    debug = _debug(HAAR_FALLBACK_AVAILABILITY, decision_tier="rejected")
    qa = _clean_qa(debug, previewAllowed=False, rejectReasons=["severe_artifact"])
    candidates = [_candidate(qa, status="rejected", candidate_id=f"c{i}") for i in range(2)]
    plan = plan_generation_round(candidates, policy=AdaptiveGenerationPolicy())
    assert plan.reason != "extra_suppressed_systemic_unavailable"


# ---------------------------------------------------------------------------
# 5. A detector outage cannot invent a second person
# ---------------------------------------------------------------------------

ONE_PERSON = [(80.0, 60.0, 420.0, 700.0)]
TWO_PEOPLE = [(80.0, 60.0, 300.0, 700.0), (320.0, 90.0, 500.0, 700.0)]
FACE_ANCHOR = (180.0, 90.0, 320.0, 260.0)


def _florence_person_regions(person_boxes, *, anchor):
    outputs = {
        "<OCR_WITH_REGION>": {"quad_boxes": [], "labels": []},
        "<OD>": {
            "bboxes": [list(box) for box in person_boxes],
            "labels": ["person"] * len(person_boxes),
            "scores": [0.94] * len(person_boxes),
        },
    }
    regions = _parse_florence_regions(outputs, image_size=(512, 768), primary_face_bbox_xyxy=anchor)
    return regions, _actions_for(regions, _classify_background_complexity(None, regions))


def test_anchorless_object_detection_relabels_the_only_person():
    """The upstream mechanism, pinned so the fix below is understood as a
    downstream interpretation change rather than a detector change."""

    _, anchored = _florence_person_regions(ONE_PERSON, anchor=FACE_ANCHOR)
    regions, anchorless = _florence_person_regions(ONE_PERSON, anchor=None)
    assert ACTION_NEUTRALIZE_BACKGROUND_PERSON not in anchored
    assert [region.kind for region in regions] == [KIND_BACKGROUND_PERSON]
    assert ACTION_NEUTRALIZE_BACKGROUND_PERSON in anchorless


def test_healthy_detector_one_person_is_the_primary_person():
    regions, actions = _florence_person_regions(ONE_PERSON, anchor=FACE_ANCHOR)
    assert [region.kind for region in regions] == [KIND_PERSON]
    evidence = resolve_person_evidence(
        background_person_count=0, person_region_count=1, face_anchor_status="anchored"
    )
    assert evidence.secondary_person_generated is False
    assert ACTION_NEUTRALIZE_BACKGROUND_PERSON not in actions


def test_healthy_detector_second_person_still_hard_rejects():
    regions, actions = _florence_person_regions(TWO_PEOPLE, anchor=FACE_ANCHOR)
    assert KIND_BACKGROUND_PERSON in [region.kind for region in regions]
    assert ACTION_NEUTRALIZE_BACKGROUND_PERSON in actions
    evidence = resolve_person_evidence(
        background_person_count=1, person_region_count=2, face_anchor_status="anchored"
    )
    assert evidence.secondary_person_generated is True
    qa = build_avatar_qa_from_signals(
        {
            "secondaryPersonGenerated": evidence.secondary_person_generated,
            "backgroundLeakageRisk": evidence.background_leakage_risk,
        },
        thresholds=AvatarQAThresholds(),
    )
    assert "secondary_person_generated" in qa.rejectReasons


def test_detector_outage_with_one_person_does_not_hard_reject():
    """The candidate is still withheld -- by the required-signal gate, not by a
    fabricated safety finding."""

    evidence = resolve_person_evidence(
        background_person_count=1,
        person_region_count=1,
        face_anchor_status="detector_unavailable",
    )
    assert evidence.secondary_person_generated is False
    assert evidence.status == "inconclusive_no_face_anchor"
    assert evidence.background_leakage_risk == "medium"
    assert evidence.secondary_face_leakage_risk == "medium"

    qa = build_avatar_qa_from_signals(
        {
            "secondaryPersonGenerated": evidence.secondary_person_generated,
            "backgroundLeakageRisk": evidence.background_leakage_risk,
            "secondaryFaceLeakageRisk": evidence.secondary_face_leakage_risk,
        },
        thresholds=AvatarQAThresholds(),
    )
    assert "secondary_person_generated" not in qa.rejectReasons
    assert "background_leakage" not in qa.rejectReasons
    assert "secondary_face_leakage" not in qa.rejectReasons


def test_detector_outage_with_zero_people_is_also_inconclusive():
    evidence = resolve_person_evidence(
        background_person_count=0,
        person_region_count=0,
        face_anchor_status="detector_unavailable",
    )
    assert evidence.secondary_person_generated is False
    assert evidence.status == "inconclusive_no_face_anchor"


def test_detector_outage_with_two_people_still_hard_rejects():
    """Two people is anchor-independent evidence: whichever one is primary, one
    of them is not."""

    evidence = resolve_person_evidence(
        background_person_count=2,
        person_region_count=2,
        face_anchor_status="detector_unavailable",
    )
    assert evidence.secondary_person_generated is True
    assert evidence.background_leakage_risk == "high"
    assert evidence.status == "anchor_independent_multiple_people"

    qa = build_avatar_qa_from_signals(
        {
            "secondaryPersonGenerated": evidence.secondary_person_generated,
            "backgroundLeakageRisk": evidence.background_leakage_risk,
        },
        thresholds=AvatarQAThresholds(),
    )
    assert "secondary_person_generated" in qa.rejectReasons


def test_healthy_detector_that_found_no_face_keeps_its_existing_verdict():
    """An available detector reporting zero faces is evidence, not an outage: it
    already hard-rejects as no_face_generated, and the person relabel stands."""

    evidence = resolve_person_evidence(
        background_person_count=1,
        person_region_count=1,
        face_anchor_status="no_face_detected",
    )
    assert evidence.secondary_person_generated is True
    assert evidence.status == "anchored"
