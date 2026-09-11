"""The Python half of the approval parity guard.

``apply_avatar_qa_rejection_logic`` owns what a hard reject is.
``avatarApprovalBlockReason`` in functions/src/avatarApproval.ts is the last
server-side authority before a face becomes the user's public profile, and it
has to refuse the same set. Two implementations in two languages drift unless
something checks.

``functions/src/avatarQaHardRejectContract.json`` is the shared statement, and
both sides verify it *behaviourally* rather than by reading each other's source:

  * this module executes the real Python function for every entry
  * functions/src/avatarApprovalParity.test.ts asserts the TypeScript gate
    refuses every entry, on a document whose previewAllowed is true and whose
    rejectReasons are empty

So a hard reject added to Python without updating the contract fails here; a
contract entry the TypeScript gate does not honour fails there. Neither reads
the other's source text, which is what makes this survive refactors.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.qa import (  # noqa: E402
    AvatarQAResult,
    _risk_is_high,
    apply_avatar_qa_rejection_logic,
)

CONTRACT_PATH = REPO_ROOT / "functions" / "src" / "avatarQaHardRejectContract.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

HEALTHY = CONTRACT["healthyQa"]
HARD = CONTRACT["hardRejectConditions"]
SOFT = CONTRACT["softValuesThatMustNotHardReject"]


def _result(**overrides) -> AvatarQAResult:
    fields = {key: value for key, value in HEALTHY.items() if key != "rejectReasons"}
    fields["rejectReasons"] = []
    fields.update(overrides)
    return AvatarQAResult(**fields)


def test_contract_file_is_not_vacuous():
    assert CONTRACT["schemaVersion"] == "avatar_qa_hard_reject_parity_v1"
    assert len(HARD) >= 12
    assert len(SOFT) >= 12


def test_the_healthy_fixture_is_actually_healthy():
    """Guard the guard: if the baseline already rejected, every case below
    would pass for the wrong reason."""

    resolved = apply_avatar_qa_rejection_logic(_result())
    assert list(resolved.rejectReasons) == []


@pytest.mark.parametrize("condition", HARD, ids=[c["id"] for c in HARD])
def test_contract_condition_is_a_real_python_hard_reject(condition):
    resolved = apply_avatar_qa_rejection_logic(
        _result(**{condition["field"]: condition["value"]})
    )
    assert condition["rejectReason"] in resolved.rejectReasons, (
        f"{condition['field']}={condition['value']} is declared a hard reject in "
        f"{CONTRACT_PATH.name} but apply_avatar_qa_rejection_logic did not produce "
        f"{condition['rejectReason']}"
    )
    assert resolved.previewAllowed is False


@pytest.mark.parametrize(
    "soft", SOFT, ids=[f"{s['field']}={s['value']}" for s in SOFT]
)
def test_soft_values_are_not_hard_rejects(soft):
    """medium / needs_review / review is the soft-review band. If Python ever
    starts hard-rejecting one of these, the TypeScript side must not be quietly
    left permitting it."""

    resolved = apply_avatar_qa_rejection_logic(
        _result(**{soft["field"]: soft["value"]})
    )
    assert list(resolved.rejectReasons) == [], (
        f"{soft['field']}={soft['value']} became a hard reject in Python; update "
        f"{CONTRACT_PATH.name} and functions/src/avatarApproval.ts together"
    )


def test_risk_high_vocabulary_matches_the_python_predicate():
    """The TypeScript gate hardcodes this set; it must be the same set."""

    for value in CONTRACT["riskHighVocabulary"]:
        assert _risk_is_high(value) is True, value
    for value in ("low", "medium", "none", "unknown", "", "review"):
        assert _risk_is_high(value) is False, value


def test_declared_python_match_semantics_are_what_python_does():
    """Python is not uniform, and the contract says so rather than pretending.

    childlikeRisk / identifiabilityRisk / uniqueMarkCopyRisk /
    beautificationRisk use an exact == "high"; backgroundLeakageRisk and
    secondaryFaceLeakageRisk go through _risk_is_high, which also accepts
    critical/fail/failed. This pins each field's declared behaviour so the
    asymmetry cannot quietly change under the approval gate.
    """

    extra = [v for v in CONTRACT["riskHighVocabulary"] if v != "high"]
    for condition in HARD:
        if condition["band"] != "risk_high":
            continue
        field = condition["field"]
        assert apply_avatar_qa_rejection_logic(
            _result(**{field: "high"})
        ).rejectReasons, f"{field}=high must hard reject"
        for value in extra:
            rejected = bool(
                apply_avatar_qa_rejection_logic(_result(**{field: value})).rejectReasons
            )
            if condition["pythonMatch"] == "risk_high_vocabulary":
                assert rejected, f"{field}={value} must hard reject"
            else:
                assert not rejected, (
                    f"{field}={value} now hard rejects in Python; the contract "
                    'declares pythonMatch="exact" -- update it'
                )


def test_the_exact_match_asymmetry_is_unreachable_from_the_producer():
    """Why the asymmetry is latent rather than a live bug: the four
    exact-match fields are produced by _risk_from_score, whose domain is
    low/medium/high, so "critical" never reaches a real document."""

    from avatar_generation.qa import _risk_from_score

    produced = {
        _risk_from_score(score, review_threshold=0.5, reject_threshold=0.9)
        for score in (0.0, 0.3, 0.5, 0.7, 0.9, 1.0)
    }
    assert produced <= {"low", "medium", "high"}, produced


def test_contract_covers_every_hard_reject_field_the_python_logic_reads():
    """A crude completeness net: any QA field that can flip a healthy result to
    rejected should be represented in the contract.

    Deliberately behavioural -- it sweeps candidate values rather than reading
    the function's source, so a refactor that keeps the semantics keeps passing.
    """

    declared = {condition["field"] for condition in HARD}
    probes = {
        "adultQa": ["fail"],
        "privacyQa": ["fail"],
        "brandQa": ["fail"],
        "cropConsistency": ["fail"],
        "cropIsolationQuality": ["fail"],
        "childlikeRisk": ["high", "critical"],
        "beautificationRisk": ["high", "critical"],
        "identifiabilityRisk": ["high", "critical"],
        "uniqueMarkCopyRisk": ["high", "critical"],
        "backgroundLeakageRisk": ["high", "critical"],
        "secondaryFaceLeakageRisk": ["high", "critical"],
        "watermarkQaAction": ["reject"],
        "logoTextWatermarkRisk": ["high"],
        "textLogoWatermarkRisk": ["high"],
    }
    undeclared = []
    for field, values in probes.items():
        for value in values:
            resolved = apply_avatar_qa_rejection_logic(_result(**{field: value}))
            if resolved.rejectReasons and field not in declared:
                undeclared.append(f"{field}={value} -> {list(resolved.rejectReasons)}")
    assert undeclared == [], (
        "these fields hard-reject in Python but are absent from "
        f"{CONTRACT_PATH.name}, so the approval gate does not know about them: "
        f"{undeclared}"
    )
