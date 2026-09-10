from __future__ import annotations

from typing import Any, Mapping

from .qa_contract import blocking_signal_failure_codes
from .unique_mark_policy import (
    normalize_unique_mark_qa_state,
    unique_mark_qa_satisfied,
)


PASS_FIELDS = ("adultQa", "privacyQa", "brandQa", "cropConsistency")
LOW_RISK_FIELDS = (
    "childlikeRisk",
    "beautificationRisk",
    "identifiabilityRisk",
    "logoTextWatermarkRisk",
)
OPTIONAL_PASS_FIELDS = ("cropIsolationQuality",)
OPTIONAL_LOW_RISK_FIELDS = (
    "backgroundLeakageRisk",
    "secondaryFaceLeakageRisk",
    "textLogoWatermarkRisk",
)

# Product decision (2026-09-07): a needs_review candidate may be offered for
# preview when the ONLY reasons for review are soft, calibrated-uncertainty
# signals (identity similarity in the review band, generic uncertain-signal
# codes). Hard privacy/safety signals (second person, watermark/logo, leakage,
# crop failure, adult/childlike, model outages, explicit trait/watermark review
# actions) keep the candidate out of preview and route the user to a new
# generation. The gate is switched by AdaptiveGenerationPolicy
# .needs_review_low_risk_enabled (AVATAR_PREVIEW_FILL_WITH_NEEDS_REVIEW_LOW_RISK).
SOFT_REVIEW_REASONS = frozenset(
    {
        "actual_qa_signal_review",
        "qa_model_signal_review",
        "qa_signal_uncertain",
        "review_similarity",
        "identifiability_review",
    }
)
SOFT_REVIEW_TIER = "soft_review"
HARD_REVIEW_TIER = "hard_review"
# privacyQa may sit in needs_review for a soft candidate; every other required
# status field must still pass outright.
SOFT_REVIEW_PASS_FIELDS = tuple(field for field in PASS_FIELDS if field != "privacyQa")
SOFT_REVIEW_LOW_RISK_FIELDS = tuple(
    field for field in LOW_RISK_FIELDS if field != "identifiabilityRisk"
)


def is_hard_reject(candidate: Mapping[str, Any]) -> bool:
    qa = qa_doc(candidate)
    return bool(qa.get("rejectReasons")) or str(
        candidate.get("status") or ""
    ).strip().lower() == "rejected"


def is_hard_pass(candidate: Mapping[str, Any]) -> bool:
    qa = qa_doc(candidate)
    status = str(candidate.get("status") or "").strip().lower()
    return status == "preview_ready" or (
        qa.get("previewAllowed") is True and qa.get("requiresHumanReview") is not True
    )


def is_soft_pass(candidate: Mapping[str, Any]) -> bool:
    qa = qa_doc(candidate)
    status = str(candidate.get("status") or "").strip().lower()
    return (
        status == "soft_pass"
        or qa.get("softPass") is True
        or qa.get("soft_pass") is True
    )


def is_needs_review(candidate: Mapping[str, Any]) -> bool:
    qa = qa_doc(candidate)
    status = str(candidate.get("status") or "").strip().lower()
    return status == "needs_review" or qa.get("requiresHumanReview") is True


def passes_absolute_preview_checks(candidate: Mapping[str, Any]) -> bool:
    if is_hard_reject(candidate):
        return False

    qa = qa_doc(candidate)
    if _qa_model_unavailable(qa):
        return False
    if not passes_unique_mark_qa_check(candidate):
        return False
    required_pass = all(_status_is_pass(qa.get(field)) for field in PASS_FIELDS)
    required_low = all(
        _risk_is_low(qa.get(field)) for field in LOW_RISK_FIELDS
    )
    optional_pass = all(
        _status_is_pass(qa.get(field)) for field in OPTIONAL_PASS_FIELDS if field in qa
    )
    optional_low = all(
        _risk_is_low(qa.get(field)) for field in OPTIONAL_LOW_RISK_FIELDS if field in qa
    )
    return required_pass and required_low and optional_pass and optional_low


def is_preview_eligible(
    candidate: Mapping[str, Any],
    *,
    allow_soft_review: bool = False,
) -> bool:
    if is_needs_review(candidate):
        return bool(allow_soft_review) and is_soft_review(candidate)
    if not passes_absolute_preview_checks(candidate):
        return False
    return is_hard_pass(candidate) or is_soft_pass(candidate)


def classify_review_tier(candidate: Mapping[str, Any]) -> str | None:
    """Return "soft_review" / "hard_review" for a needs_review candidate, else None."""

    if not is_needs_review(candidate):
        return None
    if is_hard_reject(candidate):
        return HARD_REVIEW_TIER
    qa = qa_doc(candidate)
    reasons = {
        str(reason or "").strip().lower()
        for reason in (qa.get("reviewReasons") or ())
        if str(reason or "").strip()
    }
    if not reasons or not reasons <= SOFT_REVIEW_REASONS:
        return HARD_REVIEW_TIER
    if not passes_soft_review_absolute_checks(candidate):
        return HARD_REVIEW_TIER
    return SOFT_REVIEW_TIER


def is_soft_review(candidate: Mapping[str, Any]) -> bool:
    return classify_review_tier(candidate) == SOFT_REVIEW_TIER


def annotate_review_tier(qa: Mapping[str, Any]) -> dict[str, Any]:
    """Copy of the QA document with reviewTier stamped for needs_review results."""

    updated = dict(qa)
    tier = classify_review_tier({"status": "needs_review" if qa.get("requiresHumanReview") is True else "", "qa": updated})
    if tier is None:
        updated.pop("reviewTier", None)
    else:
        updated["reviewTier"] = tier
    return updated


def passes_soft_review_absolute_checks(candidate: Mapping[str, Any]) -> bool:
    """Absolute privacy/safety floor for a soft-review candidate.

    Identical to passes_absolute_preview_checks except that identifiabilityRisk
    may be "medium" and privacyQa may be "needs_review" (the calibrated identity
    review band). Any explicit watermark/trait review action stays blocking.
    """

    if is_hard_reject(candidate):
        return False
    qa = qa_doc(candidate)
    if _qa_model_unavailable(qa):
        return False
    if not passes_unique_mark_qa_check(candidate):
        return False
    if not all(_status_is_pass(qa.get(field)) for field in SOFT_REVIEW_PASS_FIELDS):
        return False
    if str(qa.get("privacyQa") or "").strip().lower() not in {"pass", "passed", "ok", "needs_review"}:
        return False
    if not all(_risk_is_low(qa.get(field)) for field in SOFT_REVIEW_LOW_RISK_FIELDS):
        return False
    if str(qa.get("identifiabilityRisk") or "").strip().lower() not in {"low", "none", "medium"}:
        return False
    if not all(_status_is_pass(qa.get(field)) for field in OPTIONAL_PASS_FIELDS if field in qa):
        return False
    if not all(_risk_is_low(qa.get(field)) for field in OPTIONAL_LOW_RISK_FIELDS if field in qa):
        return False
    for action_field in ("watermarkQaAction", "traitQaAction", "uniqueMarkQaAction"):
        action = str(qa.get(action_field) or "allow").strip().lower()
        if action != "allow":
            return False
    return True


def qa_doc(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    qa = candidate.get("qa")
    return qa if isinstance(qa, Mapping) else {}


def passes_unique_mark_qa_check(candidate: Mapping[str, Any]) -> bool:
    """Evaluate unique-mark preview eligibility through its applicability state."""

    qa = qa_doc(candidate)
    if _risk_is_high(qa.get("uniqueMarkCopyRisk")):
        return False
    state = normalize_unique_mark_qa_state(qa)
    if state is not None:
        return unique_mark_qa_satisfied(state.applicability, state.action)
    # Legacy/custom QA runners may not carry the new typed state yet.  Preserve
    # the existing low-risk gate until a server-authoritative state is present.
    return _risk_is_low(qa.get("uniqueMarkCopyRisk"))



def _qa_model_unavailable(qa: Mapping[str, Any]) -> bool:
    qa_version = str(qa.get("qaVersion") or "").strip().lower()
    if "model_unavailable" in qa_version:
        return True
    # A reported capability outage. These codes come from
    # CandidateQASignalResult.models_unavailable, which only ever names a
    # capability the QA run actually tried and failed to use.
    for reason in qa.get("reviewReasons") or ():
        lowered = str(reason or "").strip().lower()
        if lowered == "model_unavailable" or lowered.endswith("_unavailable"):
            return True
    debug = qa.get("debug")
    if not isinstance(debug, Mapping):
        return False
    model_availability = debug.get("modelAvailability")
    if not isinstance(model_availability, Mapping):
        return False
    # Only a *required* capability may withhold a candidate. Scanning every
    # value made any entry in the flat map a systemic outage, which contradicts
    # qa_preflight's own rule -- blocking_components is "critical and not
    # available" -- and withheld candidates over signals no QA decision reads.
    return bool(blocking_signal_failure_codes(model_availability))


def _status_is_pass(value: Any) -> bool:
    return str(value or "").strip().lower() in {"pass", "passed", "ok", "low"}


def _risk_is_low(value: Any) -> bool:
    return str(value or "").strip().lower() in {"low", "none", "pass", "passed", "ok"}


def _risk_is_high(value: Any) -> bool:
    return str(value or "").strip().lower() in {"high", "critical", "fail", "failed", "reject", "rejected"}


__all__ = [
    "HARD_REVIEW_TIER",
    "SOFT_REVIEW_REASONS",
    "SOFT_REVIEW_TIER",
    "annotate_review_tier",
    "classify_review_tier",
    "is_hard_pass",
    "is_hard_reject",
    "is_needs_review",
    "is_preview_eligible",
    "is_soft_pass",
    "is_soft_review",
    "passes_soft_review_absolute_checks",
    "passes_unique_mark_qa_check",
    "passes_absolute_preview_checks",
    "qa_doc",
]
