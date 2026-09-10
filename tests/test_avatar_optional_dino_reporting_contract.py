"""Optional DINO availability reporting contract.

Production evidence (2026-09-07 backend E2E, two logical runs, four candidates):
the runtime QA signal runner never emits the optional ``dino`` key, the debug
document defaulted it to ``"unavailable"``, and ``preview_policy`` treats any
``"unavailable"`` model as a systemic outage. Every candidate, including the two
whose QA decision was ``hard_pass``, was therefore demoted to ``needs_review``.

Canonical semantics fixed here:
* optional signal absent -> ``not_required`` (not an outage)
* signal explicitly reported unavailable -> preserved verbatim in the record

Updated 2026-09-10. The original fix also asserted that an *explicitly*
unavailable ``dino`` kept gating. That was wrong, and it contradicted the
repository's own readiness contract: ``qa_preflight`` declares dino with
``critical=False, status=not_required, reason="not_in_active_qa_contract"``,
``QARuntimeReadiness.blocking_components`` is "critical and not available", and
``signalCoverage`` maps every QA decision to a *required* component
(``dinoRerank -> not_required_in_active_qa_contract``). A signal no decision
consults cannot make a decision less trustworthy by failing. The report is still
recorded; it just no longer withholds a candidate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.preview_policy import (  # noqa: E402
    is_preview_eligible,
    passes_absolute_preview_checks,
)
from avatar_generation.qa import AvatarQAThresholds, _qa_debug_document  # noqa: E402
from avatar_generation.qa_contract import (  # noqa: E402
    OPTIONAL_SIGNAL_NAMES,
    required_signal_failure_codes,
)

FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "avatar_live_qa_reports_20260907.json"

RUNTIME_AVAILABILITY_WITHOUT_OPTIONAL = {
    "faceDetector": "available",
    "visualRisk": "available",
    "faceSimilarity": "available",
    "localSafetyRisk": "available",
    "mediapipe": "available",
}


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


def _hard_pass_qa(debug):
    return {
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


def _candidate(qa, *, status="hard_pass"):
    return {"candidateId": "contract", "status": status, "qa": dict(qa)}


def test_dino_is_the_only_optional_signal_in_the_active_contract():
    assert OPTIONAL_SIGNAL_NAMES == ("dino",)


def test_optional_dino_absent_is_reported_not_required():
    debug = _debug(RUNTIME_AVAILABILITY_WITHOUT_OPTIONAL)
    assert debug["modelAvailability"]["dino"] == "not_required"
    assert debug["signalContract"]["optional"] == ["dino"]


def test_optional_dino_absent_does_not_trip_systemic_unavailable_gate():
    debug = _debug(RUNTIME_AVAILABILITY_WITHOUT_OPTIONAL)
    candidate = _candidate(_hard_pass_qa(debug))
    assert passes_absolute_preview_checks(candidate) is True
    assert is_preview_eligible(candidate) is True


def test_explicitly_unavailable_dino_is_preserved_but_does_not_gate():
    """The report is testimony and is kept. It is not authority over preview.

    dino is declared critical=False / not_in_active_qa_contract in qa_preflight,
    so withholding a candidate over it is a fabricated outage, not fail-closed
    behaviour.
    """

    debug = _debug({**RUNTIME_AVAILABILITY_WITHOUT_OPTIONAL, "dino": "unavailable"})
    assert debug["modelAvailability"]["dino"] == "unavailable"
    assert debug["signalContract"]["requiredSignalFailures"] == []
    candidate = _candidate(_hard_pass_qa(debug))
    assert passes_absolute_preview_checks(candidate) is True
    assert is_preview_eligible(candidate) is True


def test_required_signal_unavailable_still_blocks_preview():
    debug = _debug({**RUNTIME_AVAILABILITY_WITHOUT_OPTIONAL, "faceSimilarity": "unavailable"})
    candidate = _candidate(_hard_pass_qa(debug))
    assert passes_absolute_preview_checks(candidate) is False


def _live_fixture_candidates():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "avatar_live_qa_report_fixture_v1"
    return payload["candidates"]


def _with_reporting_fix(qa):
    """Apply only the reporting change under test to a recorded QA document."""
    fixed = json.loads(json.dumps(qa))
    if fixed["debug"]["modelAvailability"].get("dino") == "unavailable":
        fixed["debug"]["modelAvailability"]["dino"] = "not_required"
    return fixed


def test_live_reports_recorded_the_optional_outage_that_caused_the_demotion():
    """The recorded evidence: every live candidate carried dino="unavailable"
    while no required signal had failed. That single value demoted all four."""

    for entry in _live_fixture_candidates():
        assert entry["qa"]["debug"]["modelAvailability"]["dino"] == "unavailable"
        availability = entry["qa"]["debug"]["modelAvailability"]
        assert required_signal_failure_codes(availability) == (), entry["label"]


def test_live_reports_are_no_longer_demoted_by_the_optional_outage():
    """Same stored documents, unmodified: the gate no longer fires on dino, so
    the hard_pass candidates are previewable and the needs_review ones are not
    -- decided by their own QA verdict rather than by an unrelated signal."""

    for entry in _live_fixture_candidates():
        candidate = _candidate(entry["qa"], status=entry["qaDecisionTier"])
        expected = entry["qaDecisionTier"] == "hard_pass"
        assert is_preview_eligible(candidate) is expected, entry["label"]


def test_live_hard_pass_reports_become_previewable_with_reporting_fix():
    tiers = {}
    for entry in _live_fixture_candidates():
        fixed = _with_reporting_fix(entry["qa"])
        candidate = _candidate(fixed, status=entry["qaDecisionTier"])
        tiers[entry["label"]] = (entry["qaDecisionTier"], is_preview_eligible(candidate))
    hard_pass = {label for label, (tier, _) in tiers.items() if tier == "hard_pass"}
    assert len(hard_pass) == 2
    for label, (tier, eligible) in tiers.items():
        assert eligible is (tier == "hard_pass"), (label, tier, eligible)


def test_live_identifiability_medium_reports_stay_needs_review_with_reporting_fix():
    medium = [e for e in _live_fixture_candidates() if e["identifiabilityRisk"] == "medium"]
    assert len(medium) == 2
    for entry in medium:
        fixed = _with_reporting_fix(entry["qa"])
        assert fixed["requiresHumanReview"] is True
        assert fixed["privacyQa"] == "needs_review"
        assert "actual_qa_signal_review" in fixed["reviewReasons"]
        candidate = _candidate(fixed, status="needs_review")
        assert passes_absolute_preview_checks(candidate) is False, entry["label"]
        assert is_preview_eligible(candidate) is False, entry["label"]
