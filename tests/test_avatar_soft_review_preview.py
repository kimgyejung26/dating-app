"""Soft-review preview contract (product decision 2026-09-07).

A needs_review candidate may be offered for preview when its only review
signals are soft (calibrated identity review band / generic uncertain-signal
codes) and every hard privacy/safety floor still holds. Hard review signals keep
the candidate out of preview so the client routes the user to a new generation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.adaptive_generation import (  # noqa: E402
    AdaptiveGenerationPolicy,
    GenerationBudget,
    plan_generation_round,
)
from avatar_generation.preview_policy import (  # noqa: E402
    HARD_REVIEW_TIER,
    SOFT_REVIEW_TIER,
    annotate_review_tier,
    classify_review_tier,
    is_preview_eligible,
    is_soft_review,
)
from avatar_generation.rerank import rerank_preview_candidates  # noqa: E402

FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "avatar_live_qa_reports_20260907.json"

SOFT_REASONS = ["actual_qa_signal_review", "qa_model_signal_review", "qa_signal_uncertain"]


def _soft_review_qa(**overrides):
    qa = {
        "previewAllowed": False,
        "requiresHumanReview": True,
        "softPass": False,
        "rejectReasons": [],
        "reviewReasons": list(SOFT_REASONS),
        "adultQa": "pass",
        "privacyQa": "needs_review",
        "brandQa": "pass",
        "cropConsistency": "pass",
        "cropIsolationQuality": "pass",
        "childlikeRisk": "low",
        "beautificationRisk": "low",
        "identifiabilityRisk": "medium",
        "logoTextWatermarkRisk": "low",
        "textLogoWatermarkRisk": "low",
        "backgroundLeakageRisk": "low",
        "secondaryFaceLeakageRisk": "low",
        "uniqueMarkCopyRisk": "low",
        "watermarkQaAction": "allow",
        "traitQaAction": "allow",
        "debug": {
            "modelAvailability": {
                "faceDetector": "available",
                "visualRisk": "available",
                "faceSimilarity": "available",
                "clipSafety": "available",
                "clip": "available",
                "localSafetyRisk": "available",
                "mediapipe": "available",
                "dino": "not_required",
            }
        },
    }
    qa.update(overrides)
    return qa


def _candidate(candidate_id, qa, *, status="needs_review"):
    return {"candidateId": candidate_id, "status": status, "qa": qa}


def _live_candidates():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    out = []
    for entry in payload["candidates"]:
        qa = json.loads(json.dumps(entry["qa"]))
        # Apply only the reporting fix that is now deployed (dino optional).
        if qa["debug"]["modelAvailability"].get("dino") == "unavailable":
            qa["debug"]["modelAvailability"]["dino"] = "not_required"
        out.append((entry["label"], entry["qaDecisionTier"], entry["identifiabilityRisk"], qa))
    return out


# --- classification ---------------------------------------------------------

def test_soft_review_requires_only_soft_reasons_and_hard_floor():
    candidate = _candidate("soft", _soft_review_qa())
    assert classify_review_tier(candidate) == SOFT_REVIEW_TIER
    assert is_soft_review(candidate) is True


def test_non_review_candidates_have_no_review_tier():
    hard_pass = _candidate("pass", _soft_review_qa(previewAllowed=True, requiresHumanReview=False, privacyQa="pass", identifiabilityRisk="low", reviewReasons=[]), status="hard_pass")
    assert classify_review_tier(hard_pass) is None
    assert "reviewTier" not in annotate_review_tier(hard_pass["qa"])


def test_annotate_review_tier_stamps_soft_and_hard():
    soft = annotate_review_tier(_soft_review_qa())
    assert soft["reviewTier"] == SOFT_REVIEW_TIER
    hard = annotate_review_tier(_soft_review_qa(secondaryFaceLeakageRisk="high"))
    assert hard["reviewTier"] == HARD_REVIEW_TIER


HARD_VARIANTS = {
    "second_person": {"secondaryFaceLeakageRisk": "high"},
    "watermark_high": {"logoTextWatermarkRisk": "high"},
    "text_logo_high": {"textLogoWatermarkRisk": "high"},
    "background_leak": {"backgroundLeakageRisk": "high"},
    "crop_fail": {"cropConsistency": "fail"},
    "crop_isolation_fail": {"cropIsolationQuality": "fail"},
    "adult_fail": {"adultQa": "fail"},
    "childlike_high": {"childlikeRisk": "high"},
    "beautification_high": {"beautificationRisk": "high"},
    "identifiability_high": {"identifiabilityRisk": "high"},
    "privacy_fail": {"privacyQa": "fail"},
    "unique_mark_high": {"uniqueMarkCopyRisk": "high"},
    "watermark_review_action": {"watermarkQaAction": "review"},
    "trait_review_action": {"traitQaAction": "review"},
    "hard_reject_reason": {"rejectReasons": ["candidate_privacy_leak"]},
    "model_unavailable_reason": {"reviewReasons": SOFT_REASONS + ["visualRisk_unavailable"]},
    "watermark_artifact_reason": {"reviewReasons": SOFT_REASONS + ["watermark_artifact_review"]},
    "unexplained_review": {"reviewReasons": []},
    "critical_model_unavailable": {"debug": {"modelAvailability": {"faceSimilarity": "unavailable", "dino": "not_required"}}},
}


def test_every_hard_signal_keeps_candidate_out_of_soft_review():
    for name, overrides in HARD_VARIANTS.items():
        candidate = _candidate(name, _soft_review_qa(**overrides))
        assert classify_review_tier(candidate) == HARD_REVIEW_TIER, name
        assert is_preview_eligible(candidate, allow_soft_review=True) is False, name


# --- eligibility gate -------------------------------------------------------

def test_soft_review_is_eligible_only_when_policy_allows():
    candidate = _candidate("soft", _soft_review_qa())
    assert is_preview_eligible(candidate) is False
    assert is_preview_eligible(candidate, allow_soft_review=False) is False
    assert is_preview_eligible(candidate, allow_soft_review=True) is True


# --- rerank / preview selection --------------------------------------------

def test_rerank_fills_preview_with_soft_review_after_passes():
    candidates = [
        _candidate("soft_review", _soft_review_qa()),
        _candidate("hard_pass", _soft_review_qa(previewAllowed=True, requiresHumanReview=False, privacyQa="pass", identifiabilityRisk="low", reviewReasons=[]), status="hard_pass"),
        _candidate("hard_review", _soft_review_qa(secondaryFaceLeakageRisk="high")),
    ]
    disabled = rerank_preview_candidates(candidates, policy=AdaptiveGenerationPolicy())
    assert disabled.selected_candidate_ids == ["hard_pass"]
    assert disabled.metadata_by_candidate_id["soft_review"]["selectionTier"] == "needs_review"

    enabled = rerank_preview_candidates(
        candidates,
        policy=AdaptiveGenerationPolicy(needs_review_low_risk_enabled=True),
    )
    assert enabled.status == "preview_ready"
    assert enabled.selected_candidate_ids == ["hard_pass", "soft_review"]
    assert enabled.metadata_by_candidate_id["soft_review"]["selectionTier"] == SOFT_REVIEW_TIER
    assert enabled.metadata_by_candidate_id["soft_review"]["selectedForPreview"] is True
    assert enabled.metadata_by_candidate_id["hard_review"]["selectionTier"] == "needs_review"
    assert enabled.metadata_by_candidate_id["hard_review"]["selectedForPreview"] is False


def test_soft_review_never_outranks_a_pass_candidate():
    candidates = [
        _candidate("soft_review", _soft_review_qa()),
        _candidate("soft_pass", _soft_review_qa(requiresHumanReview=False, softPass=True, privacyQa="pass", identifiabilityRisk="low", reviewReasons=[]), status="soft_pass"),
    ]
    result = rerank_preview_candidates(
        candidates,
        policy=AdaptiveGenerationPolicy(needs_review_low_risk_enabled=True, preview_candidate_count=1),
    )
    assert result.selected_candidate_ids == ["soft_pass"]


def test_soft_review_counts_as_safe_for_extra_round_planning():
    reasons = list(SOFT_REASONS)
    candidates = [
        _candidate("a", _soft_review_qa(reviewReasons=reasons)),
        _candidate("b", _soft_review_qa(reviewReasons=reasons)),
    ]
    budget = GenerationBudget(remaining_deadline_seconds=1000, remaining_candidate_budget=2)
    without = plan_generation_round(candidates, policy=AdaptiveGenerationPolicy(), budget=budget)
    with_soft = plan_generation_round(
        candidates,
        policy=AdaptiveGenerationPolicy(needs_review_low_risk_enabled=True),
        budget=budget,
    )
    assert without.should_generate is True
    assert with_soft.should_generate is False


def test_soft_review_reasons_do_not_block_a_needed_extra_round_as_model_outage():
    for reason in (
        "qa_model_signal_review",
        "review_similarity",
        "identifiability_review",
        "qa_signal_uncertain",
    ):
        candidates = [
            _candidate("a", _soft_review_qa(reviewReasons=[reason])),
            _candidate("b", _soft_review_qa(reviewReasons=[reason])),
        ]
        plan = plan_generation_round(
            candidates,
            policy=AdaptiveGenerationPolicy(),
            budget=GenerationBudget(
                remaining_deadline_seconds=1000,
                remaining_candidate_budget=2,
            ),
        )

        assert plan.should_generate is True, reason
        assert "qa_critical_model_unavailable" not in plan.blocked_reasons, reason


# --- production evidence ----------------------------------------------------

def test_live_identifiability_medium_reports_are_soft_review():
    medium = [(label, qa) for label, _tier, risk, qa in _live_candidates() if risk == "medium"]
    assert len(medium) == 2
    for label, qa in medium:
        candidate = _candidate(label, qa)
        assert classify_review_tier(candidate) == SOFT_REVIEW_TIER, label
        assert is_preview_eligible(candidate, allow_soft_review=True) is True, label
        assert is_preview_eligible(candidate) is False, label


def test_live_reports_all_become_previewable_with_soft_review_enabled():
    candidates = [
        _candidate(label, qa, status="hard_pass" if tier == "hard_pass" else "needs_review")
        for label, tier, _risk, qa in _live_candidates()
    ]
    result = rerank_preview_candidates(
        candidates,
        policy=AdaptiveGenerationPolicy(needs_review_low_risk_enabled=True, preview_candidate_count=4),
    )
    assert result.status == "preview_ready"
    assert len(result.selected_candidate_ids) == 4
    tiers = {cid: result.metadata_by_candidate_id[cid]["selectionTier"] for cid in result.selected_candidate_ids}
    assert sorted(tiers.values()) == ["hard_pass", "hard_pass", SOFT_REVIEW_TIER, SOFT_REVIEW_TIER]
    # passes rank first
    assert [tiers[cid] for cid in result.selected_candidate_ids][:2] == ["hard_pass", "hard_pass"]
