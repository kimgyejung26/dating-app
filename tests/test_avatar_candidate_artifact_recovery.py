from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.candidate_artifacts import (  # noqa: E402
    CandidateArtifactNeedsReview,
    generation_id_for,
    persist_candidate_artifact,
    recover_candidate_artifact,
)
from tests.test_avatar_generation_worker import (  # noqa: E402
    DEFAULT_AVATAR_TEMP_BUCKET,
    _fake_storage,
    _png_bytes,
)


def _candidate_ref() -> str:
    return (
        f"gs://{DEFAULT_AVATAR_TEMP_BUCKET}/users/u1/jobs/job1/"
        "candidates/cand_job1_00.png"
    )


def test_generation_id_is_deterministic_and_contains_no_raw_idempotency_key():
    first = generation_id_for(job_id="job1", idempotency_key="u1:private-source:job1")
    second = generation_id_for(job_id="job1", idempotency_key="u1:private-source:job1")

    assert first == second
    assert first.startswith("gen_")
    assert "private-source" not in first


def test_provider_success_is_persisted_with_atomic_recovery_metadata():
    storage = _fake_storage()
    image_bytes = _png_bytes()
    generation_id = generation_id_for(job_id="job1", idempotency_key="idem")

    persist_candidate_artifact(
        storage,
        image_ref=_candidate_ref(),
        image_bytes=image_bytes,
        generation_id=generation_id,
        candidate_index=0,
        candidate_id="cand_job1_00",
        seed=123,
        generation_params={"provider": "azure", "attempts": 1},
    )
    recovered = recover_candidate_artifact(
        storage,
        image_ref=_candidate_ref(),
        expected_generation_id=generation_id,
        expected_candidate_index=0,
        expected_candidate_id="cand_job1_00",
    )

    assert recovered is not None
    assert recovered.image_bytes == image_bytes
    assert recovered.seed == 123
    assert recovered.generation_params["provider"] == "azure"
    assert recovered.recovery_source == "deterministic_storage_object"


def test_existing_object_without_complete_manifest_needs_review_not_regeneration():
    storage = _fake_storage()
    path = "users/u1/jobs/job1/candidates/cand_job1_00.png"
    storage.buckets[DEFAULT_AVATAR_TEMP_BUCKET].blob(path).data = _png_bytes()

    with pytest.raises(CandidateArtifactNeedsReview) as caught:
        recover_candidate_artifact(
            storage,
            image_ref=_candidate_ref(),
            expected_generation_id=generation_id_for(job_id="job1", idempotency_key="idem"),
            expected_candidate_index=0,
            expected_candidate_id="cand_job1_00",
        )

    assert caught.value.error_code == "azure_candidate_artifact_manifest_incomplete"


def test_corrupt_or_mismatched_existing_object_needs_review():
    storage = _fake_storage()
    generation_id = generation_id_for(job_id="job1", idempotency_key="idem")
    persist_candidate_artifact(
        storage,
        image_ref=_candidate_ref(),
        image_bytes=_png_bytes(),
        generation_id=generation_id,
        candidate_index=0,
        candidate_id="cand_job1_00",
        seed=123,
        generation_params={"provider": "azure"},
    )

    with pytest.raises(CandidateArtifactNeedsReview, match="identity_mismatch"):
        recover_candidate_artifact(
            storage,
            image_ref=_candidate_ref(),
            expected_generation_id=generation_id,
            expected_candidate_index=1,
            expected_candidate_id="cand_job1_00",
        )
