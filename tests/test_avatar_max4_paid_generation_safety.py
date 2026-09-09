"""max4 must bound paid provider calls per job, not just per worker run.

A production job was observed with four durable candidates and
job.candidateCount == 2. The scalar is written once from the request payload
(worker.py, "candidateCount": payload.candidate_count) and never reconciled
after the extra round; the accurate totals live in generationPlan.totalGenerated
and candidateIds. So the scalar means "requested initial count", not generated.

The scalar being stale is only an accounting defect. The safety question is
whether anything durable bounds paid generation across runs:

  - plan_generation_round derives remaining_capacity from len(existing
    candidates), but the worker passes [] for the initial round and only this
    run's in-process candidate_summaries for the extra round.
  - _evaluate_worker_admission(phase="initial") passes
    existing_candidate_count=0 as a literal.
  - The worker never reads the avatarCandidates collection. It only writes it.
  - avatarMedia's retry reuses contract.jobId, sets status back to "queued",
    and deletes no candidates. "queued"/"failed"/"processing" are not in
    TERMINAL_JOB_STATUSES, so _assert_job_can_run admits the redelivery.
  - No caller ever sets regenerate_requested, so the worker cannot tell an
    intentional regeneration from an unmarked redelivery.

The existing idempotency guards -- generationClaim, deterministic
candidate_id_for(job_id, index), Storage artifact recovery -- protect the
in-flight round. None of them bound the job lifetime.

A fifth *distinct* durable candidate is impossible: ids are deterministic and
per-run capacity caps indexes at 0..3, so a rerun overwrites. The exposure is
paid calls, not row count.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.model_adapters.azure_contracts import (  # noqa: E402
    AZURE_GPT_IMAGE_2_MODEL_ID,
)
from avatar_generation.qa import AvatarQAResult  # noqa: E402
import avatar_generation.worker as worker_module  # noqa: E402
from avatar_generation.worker import (  # noqa: E402
    candidate_id_for,
    process_avatar_generation_payload,
)
from tests.test_avatar_azure_worker_integration import (  # noqa: E402
    FakeAzureProvider,
    _passing_qa,
)
from tests.test_avatar_generation_worker import (  # noqa: E402
    _fake_firestore,
    _fake_storage,
    _payload,
)


def _seed_durable_candidates(fs, payload, count, *, status="qa_pending"):
    job_id = payload["jobId"]
    candidates = fs.data.setdefault("avatarCandidates", {})
    ids = []
    for index in range(count):
        candidate_id = candidate_id_for(job_id, index)
        ids.append(candidate_id)
        candidates[candidate_id] = {
            "jobId": job_id,
            "uid": payload["uid"],
            "candidateId": candidate_id,
            "candidateIndex": index,
            "status": status,
        }
    return ids


def _requeued_job(fs, payload, *, candidate_ids, stale_count):
    """What avatarMedia's retry leaves behind: same jobId, status back to queued."""

    job = fs.data["avatarJobs"][payload["jobId"]]
    job["status"] = "queued"
    job["candidateCount"] = stale_count
    job["candidateIds"] = list(candidate_ids)
    job.pop("generationClaim", None)
    return job


def _run(payload, fs, st, provider, monkeypatch, qa_runner=None):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setattr(
        worker_module, "get_azure_gpt_image2_provider", lambda: provider
    )
    return process_avatar_generation_payload(
        payload,
        firestore_client=fs,
        storage_client=st,
        qa_runner=qa_runner or _passing_qa,
        mode=AZURE_GPT_IMAGE_2_MODEL_ID,
    )


def _azure_payload(job_id, *, candidate_count=2):
    payload = _payload(job_id=job_id)
    payload.update(
        {
            "modelId": AZURE_GPT_IMAGE_2_MODEL_ID,
            "candidateCount": candidate_count,
        }
    )
    return payload


def test_redelivered_job_with_four_durable_candidates_makes_no_paid_call(monkeypatch):
    """D3: the absolute question. Four paid candidates already exist."""

    payload = _azure_payload("azure_job_redelivered_four")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()
    ids = _seed_durable_candidates(fs, payload, 4)
    _requeued_job(fs, payload, candidate_ids=ids, stale_count=2)

    _run(payload, fs, st, provider, monkeypatch)

    assert len(provider.calls) == 0, (
        "four paid candidates already exist for this job; max4 must bound paid "
        "generation across runs, not only within one run"
    )


def test_stale_candidate_count_alone_cannot_authorize_paid_generation(monkeypatch):
    """D4-3/D4-11: the scalar disagreeing with durable state authorizes nothing."""

    payload = _azure_payload("azure_job_stale_scalar")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()
    ids = _seed_durable_candidates(fs, payload, 4)
    _requeued_job(fs, payload, candidate_ids=ids, stale_count=0)

    _run(payload, fs, st, provider, monkeypatch)

    assert len(provider.calls) == 0


def test_two_durable_candidates_still_allow_only_the_remaining_two(monkeypatch):
    """D4: the guard is capacity-based, not a blanket block."""

    payload = _azure_payload("azure_job_two_durable")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()
    ids = _seed_durable_candidates(fs, payload, 2)
    _requeued_job(fs, payload, candidate_ids=ids, stale_count=2)

    _run(payload, fs, st, provider, monkeypatch)

    assert len(provider.calls) <= 2, (
        "two candidates are already paid for; at most two more fit under max4"
    )


def test_durable_candidates_from_another_job_do_not_reduce_capacity(monkeypatch):
    """The guard must key on this job, not on the collection as a whole."""

    payload = _azure_payload("azure_job_scoped")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()
    other = fs.data.setdefault("avatarCandidates", {})
    for index in range(4):
        other[f"other_job_cand_{index}"] = {
            "jobId": "some_other_job",
            "uid": payload["uid"],
            "candidateIndex": index,
            "status": "qa_pending",
        }

    _run(payload, fs, st, provider, monkeypatch)

    assert len(provider.calls) == 2, (
        "another job's candidates must not starve this job's initial round"
    )


def test_fresh_job_is_unaffected(monkeypatch):
    """Regression guard: the normal path keeps its two initial paid calls."""

    payload = _azure_payload("azure_job_fresh_baseline")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()

    result = _run(payload, fs, st, provider, monkeypatch)

    assert result.status == "preview_ready"
    assert len(provider.calls) == 2


def _job(fs, payload):
    return fs.data["avatarJobs"][payload["jobId"]]


def _job_candidate_ids(fs, payload):
    return {
        doc_id
        for doc_id, data in fs.data.get("avatarCandidates", {}).items()
        if data.get("jobId") == payload["jobId"]
    }


def test_repeated_deliveries_never_exceed_four_paid_calls_in_total(monkeypatch):
    """D4-4/D4-6: max4 is a lifetime bound, so a third delivery buys nothing."""

    payload = _azure_payload("azure_job_repeated_delivery")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()

    _run(payload, fs, st, provider, monkeypatch)
    for _ in range(2):
        # What avatarMedia's retry leaves behind between deliveries.
        _job(fs, payload)["status"] = "queued"
        _run(payload, fs, st, provider, monkeypatch)

    assert len(provider.calls) <= 4, "paid generation must be bounded per job"
    assert len(_job_candidate_ids(fs, payload)) <= 4


def test_redelivery_does_not_double_count_the_canonical_total(monkeypatch):
    """D4-6: reprocessing must not inflate the recorded totals."""

    payload = _azure_payload("azure_job_no_double_count")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()

    _run(payload, fs, st, provider, monkeypatch)
    _job(fs, payload)["status"] = "queued"
    _run(payload, fs, st, provider, monkeypatch)

    job = _job(fs, payload)
    assert job["generationPlan"]["totalGenerated"] <= 4
    assert len(job["candidateIds"]) == len(set(job["candidateIds"]))
    assert len(job["candidateIds"]) <= 4


def test_all_four_rejected_still_respects_max4(monkeypatch):
    """D4-10: exhausting QA must not unlock a fifth paid candidate."""

    payload = _azure_payload("azure_job_all_rejected")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()

    def reject_everything(_source_ref, _candidate_ref, _metadata):
        return AvatarQAResult(
            adultQa="fail",
            privacyQa="fail",
            brandQa="fail",
            previewAllowed=False,
            requiresHumanReview=False,
            rejectReasons=["simulation_rejected"],
            qaVersion="max4_contract_test_reject",
        )

    _run(payload, fs, st, provider, monkeypatch, qa_runner=reject_everything)

    assert len(provider.calls) == 4, "the extra round may run, but only to max4"
    assert len(_job_candidate_ids(fs, payload)) == 4


def test_single_previewable_candidate_does_not_change_generated_total(monkeypatch):
    """D4-9: preview count and generated count are different quantities."""

    payload = _azure_payload("azure_job_one_previewable")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()
    seen = []

    def only_the_first_passes(source_ref, candidate_ref, metadata):
        seen.append(metadata["candidateId"])
        if len(seen) == 1:
            return _passing_qa(source_ref, candidate_ref, metadata)
        return AvatarQAResult(
            adultQa="fail",
            privacyQa="fail",
            brandQa="fail",
            previewAllowed=False,
            requiresHumanReview=False,
            rejectReasons=["simulation_rejected"],
            qaVersion="max4_contract_test_reject",
        )

    result = _run(payload, fs, st, provider, monkeypatch, qa_runner=only_the_first_passes)

    assert len(provider.calls) == 4
    assert result.preview_ready_count == 1
    assert _job(fs, payload)["generationPlan"]["totalGenerated"] == 4


def test_paid_calls_stay_bounded_after_retention_deletes_temp_artifacts(monkeypatch):
    """The reachable P0.

    Redelivery is normally free because recover_candidate_artifact finds the
    temp Storage artifact for the deterministic candidate id and reuses it. That
    protection expires: retention deletes temp candidate artifacts, while the
    avatarCandidates documents and the job survive. After that, every
    redelivery used to buy a fresh round -- 2, 4, 6, 8 -- with a completed
    generationClaim sitting right there on the job.

    Counting candidate documents cannot catch it either, because deterministic
    ids mean a rerun overwrites and the count stays flat while the bill grows.
    """

    from avatar_generation.worker import DEFAULT_AVATAR_TEMP_BUCKET

    payload = _azure_payload("azure_job_retention_expired")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()

    _run(payload, fs, st, provider, monkeypatch)
    first_round = len(provider.calls)

    for _ in range(3):
        st.buckets[DEFAULT_AVATAR_TEMP_BUCKET].blobs.clear()
        _job(fs, payload)["status"] = "queued"
        _run(payload, fs, st, provider, monkeypatch)

    assert first_round == 2
    assert len(provider.calls) <= 4, (
        "max4 must survive the loss of the storage artifacts it used to lean on"
    )


def test_recovered_redelivery_does_not_retire_budget_it_never_spent(monkeypatch):
    """Reserving before spending must be settled against real provider calls."""

    payload = _azure_payload("azure_job_recovered_settlement")
    fs = _fake_firestore(payload)
    st = _fake_storage()
    provider = FakeAzureProvider()

    _run(payload, fs, st, provider, monkeypatch)
    _job(fs, payload)["status"] = "queued"
    _run(payload, fs, st, provider, monkeypatch)

    assert len(provider.calls) == 2
    ledger = _job(fs, payload)["generationCostLedger"]
    assert ledger["paidCandidateReservations"] == 2, (
        "the recovered round paid nothing, so it must not consume max4 budget"
    )
