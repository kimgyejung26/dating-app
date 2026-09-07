"""Concurrent provider calls + streaming artifacts for one generation round.

Production evidence (2026-09-07): the two initial gpt-image-2 calls ran
sequentially (~99s + ~120s) on different router endpoints. Running them
concurrently bounds the round by the slowest call, and yielding artifacts as
they land lets QA of the first candidate overlap the remaining provider
latency. Post-send semantics are unchanged: no retry, no failover, the
lowest-index error is raised after in-flight calls finish.
"""

from __future__ import annotations

import io
import sys
import threading
import time
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.model_adapters.azure_contracts import (  # noqa: E402
    AZURE_GPT_IMAGE_2_MODEL_ID,
    AzureGenerationAudit,
    AzureGenerationResult,
    AzureUnknownOutcomeError,
)
import avatar_generation.worker as worker_module  # noqa: E402
from avatar_generation.worker import (  # noqa: E402
    CANONICAL_AZURE_WORKER_MODE,
    candidate_id_for,
    DEFAULT_GENERATION_PARALLELISM,
    ENV_GENERATION_PARALLELISM,
    MAX_GENERATION_PARALLELISM,
    generate_candidate_artifacts,
    generation_parallelism_from_env,
    iter_candidate_artifacts,
    parse_avatar_generation_payload,
)


def _jpeg_bytes():
    out = io.BytesIO()
    Image.new("RGB", (32, 32), color=(120, 90, 80)).save(out, format="JPEG", quality=90)
    return out.getvalue()


def _png_bytes():
    out = io.BytesIO()
    Image.new("RGB", (8, 8), color=(10, 20, 30)).save(out, format="PNG")
    return out.getvalue()


_JOB_ID = "avatar_job_parallel"


def _payload(candidate_count=2):
    return parse_avatar_generation_payload(
        {
            "jobId": _JOB_ID,
            "uid": "u_parallel",
            "sourcePhotoIds": ["src_001"],
            "sourcePhotoRefs": ["gs://seolleyeon-final-private-source-photos/users/u_parallel/source/src_001.jpg"],
            "candidateCount": candidate_count,
            "modelId": AZURE_GPT_IMAGE_2_MODEL_ID,
            "jobType": "avatar_generation",
            "schemaVersion": "avatar_job_v1",
            "idempotencyKey": "u_parallel:src_001:avatar_generation_v1",
        }
    )


class LatencyProvider:
    """Fake router: per-call latency keyed by candidate index; thread-safe log."""

    model_id = AZURE_GPT_IMAGE_2_MODEL_ID
    version = "gpt-image-2"

    def __init__(self, latencies, *, ambiguous_indexes=()):
        self.latencies = dict(latencies)
        self.ambiguous_indexes = set(ambiguous_indexes)
        self.calls = []
        self.in_flight = 0
        self.max_in_flight = 0
        self._lock = threading.Lock()

    def _index_for(self, key: str) -> int:
        for index in range(0, 8):
            if f":candidate:{candidate_id_for(_JOB_ID, index)}:" in key:
                return index
        raise AssertionError(f"unexpected idempotency key {key!r}")

    def generate(self, **kwargs):
        index = self._index_for(str(kwargs.get("idempotency_key") or ""))
        with self._lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            self.calls.append(index)
        try:
            time.sleep(self.latencies.get(index, 0.0))
            if index in self.ambiguous_indexes:
                raise AzureUnknownOutcomeError(attempts=1)
            return AzureGenerationResult(
                image_bytes=_png_bytes(),
                audit=AzureGenerationAudit(
                    attempts=1,
                    latency_seconds=self.latencies.get(index, 0.0),
                    provider_status=200,
                    outcome="success",
                    output_format="png",
                    output_bytes=len(_png_bytes()),
                ),
            )
        finally:
            with self._lock:
                self.in_flight -= 1


def _run(provider, *, candidate_count=2, parallelism=None):
    usage = {}
    started = time.perf_counter()
    artifacts = generate_candidate_artifacts(
        _payload(candidate_count),
        Image.new("RGB", (32, 32)),
        mode=CANONICAL_AZURE_WORKER_MODE,
        candidate_count=candidate_count,
        source_image_bytes=_jpeg_bytes(),
        azure_provider=provider,
        provider_usage_doc=usage,
        parallelism=parallelism,
    )
    return artifacts, usage, time.perf_counter() - started


def test_parallelism_env_default_and_clamp(monkeypatch):
    monkeypatch.delenv(ENV_GENERATION_PARALLELISM, raising=False)
    assert generation_parallelism_from_env() == DEFAULT_GENERATION_PARALLELISM == 2
    monkeypatch.setenv(ENV_GENERATION_PARALLELISM, "0")
    assert generation_parallelism_from_env() == 1
    monkeypatch.setenv(ENV_GENERATION_PARALLELISM, "99")
    assert generation_parallelism_from_env() == MAX_GENERATION_PARALLELISM == 4


def test_initial_round_calls_run_concurrently_and_keep_index_order():
    provider = LatencyProvider({0: 0.3, 1: 0.3})
    artifacts, usage, elapsed = _run(provider, parallelism=2)
    assert [a.candidate_index for a in artifacts] == [0, 1]
    assert provider.max_in_flight == 2
    assert elapsed < 0.5, elapsed  # bounded by the slowest call, not the sum
    assert usage["requestCount"] == 2 and usage["successCount"] == 2


def test_parallelism_one_is_strictly_sequential():
    provider = LatencyProvider({0: 0.15, 1: 0.15})
    artifacts, _usage, elapsed = _run(provider, parallelism=1)
    assert [a.candidate_index for a in artifacts] == [0, 1]
    assert provider.max_in_flight == 1
    assert provider.calls == [0, 1]
    assert elapsed >= 0.3


def test_env_parallelism_is_used_when_not_passed(monkeypatch):
    monkeypatch.setenv(ENV_GENERATION_PARALLELISM, "1")
    provider = LatencyProvider({0: 0.1, 1: 0.1})
    _run(provider)
    assert provider.max_in_flight == 1


def test_streaming_yields_the_first_finished_artifact_before_the_slow_one():
    provider = LatencyProvider({0: 0.4, 1: 0.05})
    started = time.perf_counter()
    stream = iter_candidate_artifacts(
        _payload(2),
        Image.new("RGB", (32, 32)),
        mode=CANONICAL_AZURE_WORKER_MODE,
        candidate_count=2,
        source_image_bytes=_jpeg_bytes(),
        azure_provider=provider,
        provider_usage_doc={},
        parallelism=2,
    )
    first = next(stream)
    first_at = time.perf_counter() - started
    assert first.candidate_index == 1
    assert first_at < 0.3, first_at
    rest = list(stream)
    assert [a.candidate_index for a in rest] == [0]


def test_post_send_ambiguous_error_is_raised_without_retry_after_inflight_calls_finish():
    provider = LatencyProvider({0: 0.05, 1: 0.2}, ambiguous_indexes={0})
    with pytest.raises(AzureUnknownOutcomeError):
        _run(provider, parallelism=2)
    # Both calls were sent exactly once: no retry, no failover.
    assert sorted(provider.calls) == [0, 1]
    assert provider.in_flight == 0


def test_lowest_index_error_wins_when_several_calls_fail():
    provider = LatencyProvider({0: 0.2, 1: 0.05}, ambiguous_indexes={0, 1})
    usage = {}
    with pytest.raises(AzureUnknownOutcomeError):
        list(
            iter_candidate_artifacts(
                _payload(2),
                Image.new("RGB", (32, 32)),
                mode=CANONICAL_AZURE_WORKER_MODE,
                candidate_count=2,
                source_image_bytes=_jpeg_bytes(),
                azure_provider=provider,
                provider_usage_doc=usage,
                parallelism=2,
            )
        )
    assert usage["unknownOutcomeCount"] == 2
    assert sorted(provider.calls) == [0, 1]


def test_warmup_preloads_qa_runtime_in_azure_mode(monkeypatch):
    import avatar_generation.qa_runtime as qa_runtime

    calls = []
    monkeypatch.setenv("AVATAR_WORKER_MODE", AZURE_GPT_IMAGE_2_MODEL_ID)
    monkeypatch.setattr(worker_module, "get_azure_gpt_image2_provider", lambda: calls.append("provider"))
    monkeypatch.setattr(qa_runtime, "get_default_qa_runtime", lambda: calls.append("qa_runtime"))
    result = worker_module.warmup_avatar_model(mode=AZURE_GPT_IMAGE_2_MODEL_ID)
    assert result["status"] == "ok"
    assert result["warmed"] is True
    assert result["qaRuntimeWarmed"] is True
    assert calls == ["provider", "qa_runtime"]
