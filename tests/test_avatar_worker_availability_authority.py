"""One availability contract, one resolver, every consumer.

After PR #104 the preview gate and the generation planner both ask
``qa_contract.blocking_signal_failure_codes`` -- only a *required* capability may
withhold a candidate or stand down a round. ``worker._qa_critical_models_unavailable``
was not converted. It still scans the whole flat availability map and calls any
``unavailable``/``uncalibrated`` value a critical outage, which is the exact rule
``qa_preflight.QARuntimeReadiness.blocking_components`` contradicts.

It has never fired. Not by design -- by accident of shape: it reads *top-level*
``qa["modelAvailability"]``, and the QA document writes that map under
``qa["debug"]["modelAvailability"]``. Production carries the top-level key on
0 of 298 candidates, so the scan reads ``{}`` every time. ``qa["modelsUnavailable"]``
is the same story: a ``CandidateQASignalResult.to_document`` field that the QA
document never carries.

That matters because the worker's bool is not decoration. It gates the extra
round's *provider calls* (worker.py:4476) and it writes the
``extra_blocked`` / ``extra_suppressed_systemic_unavailable`` entries in
``generationPlan.rounds``. So the planner and the worker are two independent
implementations of one policy, and the moment either shape is populated they can
disagree: planner says generate, worker blocks and records a critical outage that
the contract says is not one.

These tests pin the convergence: one resolver, three consumers, and the same
answer from all of them. The fix must not turn the worker gate on for cases the
contract says are healthy, and must not turn it off for a real required outage.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.adaptive_generation import (  # noqa: E402
    AdaptiveGenerationPolicy,
    _systemic_unavailable_reason,
    plan_generation_round,
)
from avatar_generation.preview_policy import is_preview_eligible  # noqa: E402
from avatar_generation.qa import AvatarQAThresholds, _qa_debug_document  # noqa: E402
from avatar_generation.qa_contract import (  # noqa: E402
    blocking_signal_failure_codes,
    candidate_availability,
    candidate_blocking_failures,
)
from avatar_generation.worker import _qa_critical_models_unavailable  # noqa: E402

HEALTHY = {
    "faceDetector": "available",
    "visualRisk": "available",
    "faceSimilarity": "available",
    "localSafetyRisk": "available",
    "mediapipe": "available",
}


def _debug(availability, *, tier="needs_review"):
    return _qa_debug_document(
        thresholds=AvatarQAThresholds(),
        face_similarity_score=0.10,
        perceptual_similarity_score=None,
        model_availability=availability,
        decision_tier=tier,
        hard_reject_reasons=(),
        needs_review_reasons=(),
        soft_pass_reasons=(),
    )


def _qa(availability, *, reject=(), review=(), tier="needs_review"):
    return {
        "previewAllowed": False,
        "requiresHumanReview": True,
        "softPass": False,
        "rejectReasons": list(reject),
        "reviewReasons": list(review),
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
        "debug": _debug(availability, tier=tier),
    }


def _summaries(qa, n=2):
    return [
        {"candidateId": f"c{i}", "status": "needs_review", "qa": dict(qa), "seed": i}
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# The shape bug
# ---------------------------------------------------------------------------


def test_qa_document_writes_availability_under_debug_not_top_level():
    """The premise. The worker read a key the document does not have."""

    qa = _qa(HEALTHY)
    assert "modelAvailability" in qa["debug"]
    assert "modelAvailability" not in qa
    assert "modelsUnavailable" not in qa


def test_resolver_finds_the_map_where_the_document_actually_puts_it():
    qa = _qa(HEALTHY)
    assert candidate_availability(qa) == qa["debug"]["modelAvailability"]


def test_resolver_still_accepts_a_top_level_map():
    """calibration_evaluator reads that shape, so it must remain supported."""

    qa = {"modelAvailability": dict(HEALTHY)}
    assert candidate_availability(qa)["faceDetector"] == "available"


def test_resolver_returns_empty_for_a_document_with_no_map():
    assert candidate_availability({}) == {}
    assert candidate_availability({"debug": {}}) == {}


# ---------------------------------------------------------------------------
# One contract, three consumers
# ---------------------------------------------------------------------------

CASES = [
    ("A  all required available, dino unavailable", {**HEALTHY, "dino": "unavailable"}, False),
    ("B  faceDetector available, mediapipe unavailable", {**HEALTHY, "mediapipe": "unavailable"}, False),
    ("B2 mediapipe simply unreported (Haar fallback)",
     {k: v for k, v in HEALTHY.items() if k != "mediapipe"}, False),
    ("C  required faceDetector unavailable", {**HEALTHY, "faceDetector": "unavailable"}, True),
    ("D  required clipSafety uncalibrated", {**HEALTHY, "localSafetyRisk": "uncalibrated"}, True),
    ("E  required faceSimilarity unavailable", {**HEALTHY, "faceSimilarity": "unavailable"}, True),
    ("F  required visualRisk unavailable", {**HEALTHY, "visualRisk": "unavailable"}, True),
]


@pytest.mark.parametrize("label,availability,blocking", CASES, ids=[c[0] for c in CASES])
def test_all_three_consumers_agree(label, availability, blocking):
    """Divergence between the planner and the worker is the failure mode."""

    qa = _qa(availability)
    summaries = _summaries(qa)

    contract = bool(candidate_blocking_failures(qa))
    worker = _qa_critical_models_unavailable(summaries)
    planner = _systemic_unavailable_reason(summaries[0]) != ""

    assert contract is blocking, f"{label}: contract"
    assert worker is blocking, f"{label}: worker gate"
    assert planner is blocking, f"{label}: planner"


@pytest.mark.parametrize("label,availability,blocking", CASES, ids=[c[0] for c in CASES])
def test_planner_and_worker_never_disagree_about_the_extra_round(label, availability, blocking):
    qa = _qa(availability)
    summaries = _summaries(qa)
    plan = plan_generation_round(summaries, policy=AdaptiveGenerationPolicy())
    worker_blocks = _qa_critical_models_unavailable(summaries)

    if blocking:
        assert plan.reason == "extra_suppressed_systemic_unavailable", label
        assert worker_blocks is True, label
    else:
        # The planner may still decline for ordinary policy reasons; what it
        # must not do is call this a systemic outage, and the worker must not
        # veto a round the planner authorised.
        assert plan.reason != "extra_suppressed_systemic_unavailable", label
        assert worker_blocks is False, label


# ---------------------------------------------------------------------------
# Fail-closed is preserved
# ---------------------------------------------------------------------------


def test_required_outage_still_blocks_the_provider_call():
    qa = _qa({**HEALTHY, "faceSimilarity": "unavailable"})
    assert _qa_critical_models_unavailable(_summaries(qa)) is True


def test_legacy_model_unavailable_qa_version_is_preserved():
    qa = _qa(HEALTHY)
    qa["qaVersion"] = "avatar_qa_v6_model_unavailable"
    assert _qa_critical_models_unavailable(_summaries(qa)) is True


def test_required_capability_review_reason_still_blocks():
    """Every producer of a *_unavailable review reason names a real capability
    failure -- faceDetector, visualRisk, localSafetyRisk, faceSimilarity,
    sourceVisualRisk -- so the suffix match stays sound."""

    for reason in (
        "model_unavailable",
        "faceDetector_unavailable",
        "visualRisk_unavailable",
        "localSafetyRisk_unavailable",
        "faceSimilarity_unavailable",
        "sourceVisualRisk_unavailable",
        "analysis_reference_image_unavailable",
    ):
        qa = _qa(HEALTHY, review=[reason])
        assert _qa_critical_models_unavailable(_summaries(qa)) is True, reason


def test_no_optional_signal_producer_emits_an_unavailable_review_reason():
    """The suffix match is only sound while that stays true. dino/mediapipe are
    never appended to models_unavailable, so they can never reach reviewReasons."""

    import avatar_generation.qa_signals as qa_signals

    source = Path(qa_signals.__file__).read_text(encoding="utf-8")
    appended = {
        line.split('unavailable.append("')[1].split('"')[0]
        for line in source.splitlines()
        if 'unavailable.append("' in line
    }
    assert appended == {"faceDetector", "visualRisk", "localSafetyRisk", "faceSimilarity"}
    assert "dino" not in appended
    assert "mediapipe" not in appended


def test_document_with_no_availability_map_is_not_assumed_healthy():
    """Absent required capabilities fail closed rather than reading as fine."""

    assert blocking_signal_failure_codes({}) != ()
    assert candidate_blocking_failures({"debug": {}}) != ()


# ---------------------------------------------------------------------------
# Safety floor
# ---------------------------------------------------------------------------


def test_explicit_hard_reject_survives_every_availability_state():
    for availability in (HEALTHY, {**HEALTHY, "dino": "unavailable"},
                         {**HEALTHY, "faceDetector": "unavailable"}):
        qa = _qa(availability, reject=["secondary_person_generated"], tier="rejected")
        candidate = {"candidateId": "c", "status": "rejected", "qa": qa}
        assert is_preview_eligible(candidate) is False


def test_unblocking_an_optional_outage_does_not_bypass_max4():
    """The extra round becoming available again must still respect the lifetime
    cap: capacity is max_candidate_count minus what the job already paid for."""

    qa = _qa({**HEALTHY, "dino": "unavailable"})
    policy = AdaptiveGenerationPolicy()
    plan = plan_generation_round(
        _summaries(qa, n=2), policy=policy, preexisting_candidate_count=2
    )
    assert plan.reason == "max_total_reached"
    assert plan.candidate_count == 0

    plan4 = plan_generation_round(_summaries(qa, n=4), policy=policy)
    assert plan4.candidate_count == 0
    assert plan4.total_after_generation <= policy.max_candidate_count


# ---------------------------------------------------------------------------
# Absent map: one rule, all three consumers
# ---------------------------------------------------------------------------


def test_absent_map_means_no_opinion_in_every_consumer():
    """The contract function fails closed on an empty map -- an absent *required*
    key is a failure. A consumer facing a document with no map at all is a
    different question: the channel is not reporting. A QA result may carry no
    debug document, and treating that as four simultaneous capability failures
    would block extra rounds that every prior release allowed.

    The distinction is deliberate, and it must be the same in all three
    consumers or they drift apart again.
    """

    bare = {"qaVersion": "some_contract", "rejectReasons": [], "reviewReasons": []}
    assert candidate_availability(bare) == {}
    # the contract itself still fails closed when asked directly
    assert blocking_signal_failure_codes({}) != ()
    # ... but no consumer invents an outage from a silent channel
    assert _qa_critical_models_unavailable([{"candidateId": "c", "status": "x", "qa": bare}]) is False
    assert _systemic_unavailable_reason({"candidateId": "c", "status": "x", "qa": bare}) == ""


def test_absent_map_does_not_unlock_anything_a_real_marker_blocks():
    """Silence on the availability channel must not override an outage reported
    through the other channels."""

    for marker in (
        {"qaVersion": "avatar_qa_model_unavailable"},
        {"reviewReasons": ["faceSimilarity_unavailable"]},
        {"modelsUnavailable": True},
    ):
        qa = {"rejectReasons": [], "reviewReasons": [], **marker}
        assert candidate_availability(qa) == {}
        assert _qa_critical_models_unavailable(
            [{"candidateId": "c", "status": "x", "qa": qa}]
        ) is True, marker
