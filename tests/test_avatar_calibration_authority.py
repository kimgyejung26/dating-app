"""Which calibration authority actually decided, recorded rather than inferred.

Phase C0 made the QA record say *what* the producer calibration was. It still
cannot say *where that calibration came from*, and three separate ambiguities
sit on that path:

  1. `_similarity_policy_from_env` resolves in three tiers -- the artifact named
     by AVATAR_QA_CALIBRATION_ARTIFACT_PATH, else the AVATAR_QA_SIMILARITY_*
     env triple, else None -- and a caller cannot tell which tier answered. An
     artifact that fails its own sha256/model/preprocessing checks is swallowed
     by `except CalibrationArtifactError: return None` and degrades to the same
     silent None as "nothing was configured at all". Those are very different
     situations and the record shows neither.

  2. The active artifact declares calibrationVersion "g004-staging-20260823-v1".
     Nothing at runtime carries that declaration, so a staging-labelled
     calibration is indistinguishable from a promoted one. (Recording the
     declaration is not the same as trusting it -- the name alone proves
     nothing, which is exactly why it belongs in the record instead of in a
     branch.)

  3. thresholdSnapshot reports requireReliableFaceSimilarityForTooIdentifiable
     as though it governed the too_identifiable decision. It has no consumer
     anywhere in the repository: the flag is declared, read from env, and
     printed. A reader auditing why a candidate was or was not rejected would
     credit a flag that does nothing.

These tests pin provenance only. The decision-diff guards at the bottom must
hold identically before and after: same artifact, same threshold, same margin,
same decisions.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation import qa_runtime  # noqa: E402
from avatar_generation.qa import (  # noqa: E402
    AvatarQAThresholds,
    build_avatar_qa_from_signals,
)

ARTIFACT_SOURCE = "calibration_artifact"
ENV_SOURCE = "env_threshold_triple"
NO_SOURCE = "none"

BUNDLED_ARTIFACT = (
    AI_MODEL_DIR / "avatar_generation" / "artifacts" / "avatar_qa_calibration_v1.json"
)
BUNDLED_VERSION = "g004-staging-20260823-v1"
BUNDLED_THRESHOLD = 0.799743
BUNDLED_MARGIN = 0.185528

CALIBRATION_ENV = (
    "AVATAR_QA_CALIBRATION_ARTIFACT_PATH",
    "AVATAR_QA_CALIBRATION_ARTIFACT_SHA256",
    "AVATAR_QA_CALIBRATION_EXPECTED_MODELS_JSON",
    "AVATAR_QA_CALIBRATION_EXPECTED_PREPROCESSING_JSON",
    "AVATAR_QA_SIMILARITY_CALIBRATION_VERSION",
    "AVATAR_QA_SIMILARITY_THRESHOLD",
    "AVATAR_QA_SIMILARITY_REVIEW_MARGIN",
)


def _clear(monkeypatch):
    for name in CALIBRATION_ENV:
        monkeypatch.delenv(name, raising=False)


def _use_bundled_artifact(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("AVATAR_QA_CALIBRATION_ARTIFACT_PATH", str(BUNDLED_ARTIFACT))


def _use_env_triple(monkeypatch, *, version="env-cal-v1", threshold="0.75", margin="0.1"):
    _clear(monkeypatch)
    monkeypatch.setenv("AVATAR_QA_SIMILARITY_CALIBRATION_VERSION", version)
    monkeypatch.setenv("AVATAR_QA_SIMILARITY_THRESHOLD", threshold)
    monkeypatch.setenv("AVATAR_QA_SIMILARITY_REVIEW_MARGIN", margin)


def _broken_artifact(tmp_path, mutate):
    payload = json.loads(BUNDLED_ARTIFACT.read_text(encoding="utf-8"))
    mutate(payload)
    path = tmp_path / "broken_calibration.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# A. an effective artifact must be named as the authority
# --------------------------------------------------------------------------


def test_artifact_tier_is_recorded_as_the_effective_authority(monkeypatch):
    _use_bundled_artifact(monkeypatch)

    policy, provenance = qa_runtime.resolve_similarity_calibration()

    assert policy is not None
    assert policy.threshold == BUNDLED_THRESHOLD
    assert policy.review_margin == BUNDLED_MARGIN
    assert provenance["source"] == ARTIFACT_SOURCE
    assert provenance["calibrationVersion"] == BUNDLED_VERSION
    assert provenance["artifactConfigured"] is True
    assert provenance.get("fallbackReason") is None


def test_declared_release_posture_travels_with_the_calibration(monkeypatch):
    """The name proves nothing, which is why it must be carried, not branched on."""

    _use_bundled_artifact(monkeypatch)

    _, provenance = qa_runtime.resolve_similarity_calibration()

    assert provenance["declaredReleasePosture"] == "staging"
    assert provenance["postureSource"] == "calibration_version_label"


# --------------------------------------------------------------------------
# B/C/D. absent, invalid and mismatched artifacts need distinct provenance
# --------------------------------------------------------------------------


def test_env_triple_fallback_is_recorded_as_a_fallback(monkeypatch):
    _use_env_triple(monkeypatch)

    policy, provenance = qa_runtime.resolve_similarity_calibration()

    assert policy is not None
    assert policy.calibration_version == "env-cal-v1"
    assert provenance["source"] == ENV_SOURCE
    assert provenance["artifactConfigured"] is False
    assert provenance["fallbackReason"] == "artifact_not_configured"


def test_no_calibration_at_all_is_distinguishable_from_a_fallback(monkeypatch):
    _clear(monkeypatch)

    policy, provenance = qa_runtime.resolve_similarity_calibration()

    assert policy is None
    assert provenance["source"] == NO_SOURCE
    assert provenance["fallbackReason"] == "no_calibration_configured"
    assert provenance.get("calibrationVersion") is None


def test_invalid_artifact_does_not_look_like_an_absent_one(monkeypatch, tmp_path):
    """A tampered artifact and an unconfigured one must not read alike."""

    broken = _broken_artifact(tmp_path, lambda d: d["faceSimilarity"].__setitem__("threshold", 2.5))
    _clear(monkeypatch)
    monkeypatch.setenv("AVATAR_QA_CALIBRATION_ARTIFACT_PATH", str(broken))

    policy, provenance = qa_runtime.resolve_similarity_calibration()

    assert policy is None, "an invalid artifact must never become an effective policy"
    assert provenance["source"] == NO_SOURCE
    assert provenance["artifactConfigured"] is True
    assert provenance["fallbackReason"] == "artifact_invalid"


def test_artifact_sha256_mismatch_is_reported_as_invalid_not_missing(monkeypatch, tmp_path):
    broken = _broken_artifact(tmp_path, lambda d: d.__setitem__("cohortPolicyVersion", "tampered"))
    _clear(monkeypatch)
    monkeypatch.setenv("AVATAR_QA_CALIBRATION_ARTIFACT_PATH", str(broken))
    monkeypatch.setenv("AVATAR_QA_CALIBRATION_ARTIFACT_SHA256", "0" * 64)

    policy, provenance = qa_runtime.resolve_similarity_calibration()

    assert policy is None
    assert provenance["artifactConfigured"] is True
    assert provenance["fallbackReason"] == "artifact_invalid"


def test_invalid_artifact_never_silently_falls_through_to_the_env_triple(monkeypatch, tmp_path):
    """Failing closed: a rejected artifact must not hand authority to env."""

    broken = _broken_artifact(tmp_path, lambda d: d["faceSimilarity"].__setitem__("threshold", 2.5))
    monkeypatch.setenv("AVATAR_QA_CALIBRATION_ARTIFACT_PATH", str(broken))
    monkeypatch.setenv("AVATAR_QA_SIMILARITY_CALIBRATION_VERSION", "env-cal-v1")
    monkeypatch.setenv("AVATAR_QA_SIMILARITY_THRESHOLD", "0.5")
    monkeypatch.setenv("AVATAR_QA_SIMILARITY_REVIEW_MARGIN", "0.1")

    policy, provenance = qa_runtime.resolve_similarity_calibration()

    assert policy is None
    assert provenance["source"] == NO_SOURCE


# --------------------------------------------------------------------------
# E. the record must not credit configuration that governs nothing
# --------------------------------------------------------------------------


def test_unenforced_configured_flags_are_marked_as_such():
    thresholds = AvatarQAThresholds(
        face_similarity_review=0.68,
        face_similarity_reject=0.72,
    )

    debug = build_avatar_qa_from_signals({}, thresholds=thresholds).debug

    unenforced = debug["configuredQaThresholds"]["unenforced"]
    assert "requireReliableFaceSimilarityForTooIdentifiable" in unenforced, (
        "the flag has no consumer in the repository; thresholdSnapshot must not "
        "present it as though it governed too_identifiable"
    )


def test_configured_thresholds_say_whether_they_came_from_env_or_default(monkeypatch):
    monkeypatch.delenv("AVATAR_QA_FACE_SIMILARITY_REVIEW_THRESHOLD", raising=False)
    monkeypatch.delenv("AVATAR_QA_FACE_SIMILARITY_REJECT_THRESHOLD", raising=False)

    from avatar_generation.qa import qa_thresholds_from_env

    defaults = qa_thresholds_from_env()
    debug = build_avatar_qa_from_signals({}, thresholds=defaults).debug

    assert debug["configuredQaThresholds"]["faceSimilarityReview"] == 0.50
    assert debug["configuredQaThresholds"]["faceSimilarityReject"] == 0.65


# --------------------------------------------------------------------------
# decision diff = 0 -- must hold identically before and after C1A
# --------------------------------------------------------------------------


def test_bundled_artifact_values_are_untouched():
    face = json.loads(BUNDLED_ARTIFACT.read_text(encoding="utf-8"))["faceSimilarity"]

    assert face["threshold"] == BUNDLED_THRESHOLD
    assert face["reviewMargin"] == BUNDLED_MARGIN
    assert face["semanticRole"] == "identity_privacy_upper_bound"
    assert face["thresholdDirection"] == "gte_review"


def test_artifact_tier_still_wins_over_the_env_triple(monkeypatch):
    monkeypatch.setenv("AVATAR_QA_CALIBRATION_ARTIFACT_PATH", str(BUNDLED_ARTIFACT))
    monkeypatch.setenv("AVATAR_QA_SIMILARITY_CALIBRATION_VERSION", "env-cal-v1")
    monkeypatch.setenv("AVATAR_QA_SIMILARITY_THRESHOLD", "0.5")
    monkeypatch.setenv("AVATAR_QA_SIMILARITY_REVIEW_MARGIN", "0.2")

    policy = qa_runtime._similarity_policy_from_env()

    assert policy is not None
    assert policy.calibration_version == BUNDLED_VERSION
    assert policy.threshold == BUNDLED_THRESHOLD
    assert policy.review_margin == BUNDLED_MARGIN


def test_legacy_entry_point_returns_exactly_what_the_resolver_returns(monkeypatch):
    for setup in (
        lambda: _use_bundled_artifact(monkeypatch),
        lambda: _use_env_triple(monkeypatch),
        lambda: _clear(monkeypatch),
    ):
        setup()
        legacy = qa_runtime._similarity_policy_from_env()
        resolved, _ = qa_runtime.resolve_similarity_calibration()
        assert legacy == resolved
