from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.model_adapters.azure_contracts import (  # noqa: E402
    AzureGenerationAudit,
    AzureGenerationResult,
    AzureGptImage2Config,
    AzureProviderError,
    AzureTransportError,
    AzureUnknownOutcomeError,
)
from avatar_generation.model_adapters.azure_endpoint_config import AzureEndpointConfig  # noqa: E402
from avatar_generation.model_adapters.azure_reservation import (  # noqa: E402
    EndpointReservation,
    ReservationDecision,
    ReservationPolicy,
)
from avatar_generation.model_adapters.azure_router import (  # noqa: E402
    AzureEndpointRouter,
    build_azure_endpoint_router,
)


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 32), color=(20, 60, 90)).save(output, format="PNG")
    return output.getvalue()


def _result() -> AzureGenerationResult:
    data = _png()
    return AzureGenerationResult(
        image_bytes=data,
        audit=AzureGenerationAudit(
            attempts=1,
            latency_seconds=1.0,
            provider_status=200,
            outcome="success",
            output_format="png",
            output_bytes=len(data),
        ),
    )


def _endpoint(endpoint_id: str) -> AzureEndpointConfig:
    return AzureEndpointConfig(
        endpoint_id=endpoint_id,
        rpm_limit=2.0,
        provider_config=AzureGptImage2Config(
            endpoint=f"https://{endpoint_id}.example.invalid",
            deployment="gpt-image-2",
            api_version="preview",
            api_key=f"SECRET_{endpoint_id}",
            max_attempts=1,
        ),
    )


def _reservation(
    endpoint_id: str,
    *,
    reserved_at: float,
    expires_at: float,
    wait_seconds: float | None = None,
) -> EndpointReservation:
    return EndpointReservation(
        endpoint_id=endpoint_id,
        sequence=1,
        reserved_at_epoch_seconds=reserved_at,
        expires_at_epoch_seconds=expires_at,
        wait_seconds=(
            max(0.0, reserved_at - 100.0)
            if wait_seconds is None
            else wait_seconds
        ),
        token="opaque-token",
    )


class FakeClock:
    def __init__(self, *, oversleep: float = 0.0):
        self.epoch = 100.0
        self.mono = 50.0
        self.oversleep = oversleep
        self.sleeps = []

    def time(self):
        return self.epoch

    def monotonic(self):
        return self.mono

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        elapsed = seconds + self.oversleep
        self.epoch += elapsed
        self.mono += elapsed


class FakeStore:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.reservations = []
        self.capacity_feedback = []

    def reserve(self, **kwargs):
        self.reservations.append(kwargs)
        return self.decisions.pop(0)

    def record_capacity_feedback(self, **kwargs):
        self.capacity_feedback.append(kwargs)


class FakeProvider:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _call(router):
    return router.generate(
        source_image_bytes=b"jpeg",
        source_content_type="image/jpeg",
        prompt="fixed",
        idempotency_key="job:candidate",
        deadline_monotonic=500.0,
    )


def test_near_reserved_slot_waits_inside_worker_after_atomic_reservation():
    clock = FakeClock()
    store = FakeStore(
        [ReservationDecision(_reservation("ep1", reserved_at=110.0, expires_at=115.0), "reserved")]
    )
    provider = FakeProvider([_result()])
    router = AzureEndpointRouter(
        endpoint_configs=[_endpoint("ep1")],
        reservation_store=store,
        providers={"ep1": provider},
        policy=ReservationPolicy(max_bounded_wait_seconds=20.0),
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )

    _call(router)

    assert len(store.reservations) == 1
    assert clock.sleeps == [10.0]
    assert len(provider.calls) == 1


def test_late_wakeup_discards_stale_slot_and_re_reserves_before_send():
    clock = FakeClock(oversleep=3.0)
    store = FakeStore(
        [
            ReservationDecision(_reservation("ep1", reserved_at=110.0, expires_at=111.0), "reserved"),
            ReservationDecision(
                _reservation("ep2", reserved_at=113.0, expires_at=118.0, wait_seconds=0.0),
                "reserved",
            ),
        ]
    )
    providers = {"ep1": FakeProvider([_result()]), "ep2": FakeProvider([_result()])}
    router = AzureEndpointRouter(
        endpoint_configs=[_endpoint("ep1"), _endpoint("ep2")],
        reservation_store=store,
        providers=providers,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )

    _call(router)

    assert len(store.reservations) == 2
    assert providers["ep1"].calls == []
    assert len(providers["ep2"].calls) == 1


def test_far_capacity_defers_without_provider_call_or_busy_loop():
    clock = FakeClock()
    store = FakeStore([ReservationDecision(None, "bounded_wait_exceeded", 30.0)])
    provider = FakeProvider([_result()])
    router = AzureEndpointRouter(
        endpoint_configs=[_endpoint("ep1")],
        reservation_store=store,
        providers={"ep1": provider},
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )

    with pytest.raises(AzureProviderError) as caught:
        _call(router)

    assert caught.value.error_code == "azure_capacity_deferred"
    assert caught.value.retryable is True
    assert provider.calls == []
    assert len(store.reservations) == 1


def test_worker_crash_during_reserved_sleep_loses_slot_without_refund_or_send():
    clock = FakeClock()
    store = FakeStore(
        [ReservationDecision(_reservation("ep1", reserved_at=110.0, expires_at=115.0), "reserved")]
    )
    provider = FakeProvider([_result()])

    def crash(_seconds):
        raise RuntimeError("worker terminated")

    router = AzureEndpointRouter(
        endpoint_configs=[_endpoint("ep1")],
        reservation_store=store,
        providers={"ep1": provider},
        monotonic_fn=clock.monotonic,
        sleep_fn=crash,
    )

    with pytest.raises(RuntimeError, match="worker terminated"):
        _call(router)

    assert len(store.reservations) == 1
    assert store.capacity_feedback == []
    assert provider.calls == []


def test_ambiguous_failure_never_fails_over_to_another_endpoint():
    clock = FakeClock()
    store = FakeStore(
        [ReservationDecision(_reservation("ep1", reserved_at=100.0, expires_at=105.0), "reserved")]
    )
    providers = {
        "ep1": FakeProvider([AzureUnknownOutcomeError(1)]),
        "ep2": FakeProvider([_result()]),
    }
    router = AzureEndpointRouter(
        endpoint_configs=[_endpoint("ep1"), _endpoint("ep2")],
        reservation_store=store,
        providers=providers,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )

    with pytest.raises(AzureUnknownOutcomeError):
        _call(router)

    assert len(providers["ep1"].calls) == 1
    assert providers["ep2"].calls == []
    assert len(store.reservations) == 1


def test_pre_send_connect_failure_can_fail_over_safely():
    clock = FakeClock()
    store = FakeStore(
        [
            ReservationDecision(_reservation("ep1", reserved_at=100.0, expires_at=105.0), "reserved"),
            ReservationDecision(_reservation("ep2", reserved_at=100.0, expires_at=105.0), "reserved"),
        ]
    )
    providers = {
        "ep1": FakeProvider([AzureTransportError("azure_connect_error", request_sent=False)]),
        "ep2": FakeProvider([_result()]),
    }
    router = AzureEndpointRouter(
        endpoint_configs=[_endpoint("ep1"), _endpoint("ep2")],
        reservation_store=store,
        providers=providers,
        max_provider_attempts=2,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )

    result = _call(router)

    assert result.audit.attempts == 2
    assert result.audit.routing_attempt_count == 2
    assert result.audit.provider_request_attempted_count == 2
    assert result.audit.provider_definite_rejected_count == 0
    assert result.audit.provider_ambiguous_count == 0
    assert result.audit.provider_succeeded_count == 1
    assert len(providers["ep1"].calls) == 1
    assert len(providers["ep2"].calls) == 1
    assert "endpoint" not in repr(result.audit.to_dict()).lower()
    assert "region" not in repr(result.audit.to_dict()).lower()


def test_429_is_capacity_feedback_not_health_failure_and_can_fail_over():
    clock = FakeClock()
    events = []
    store = FakeStore(
        [
            ReservationDecision(_reservation("ep1", reserved_at=100.0, expires_at=105.0), "reserved"),
            ReservationDecision(_reservation("ep2", reserved_at=100.0, expires_at=105.0), "reserved"),
        ]
    )
    providers = {
        "ep1": FakeProvider(
            [
                AzureProviderError(
                    "azure_rate_limited",
                    retryable=True,
                    attempts=1,
                    provider_status=429,
                    retry_after_seconds=7.0,
                    failure_class="capacity",
                )
            ]
        ),
        "ep2": FakeProvider([_result()]),
    }
    router = AzureEndpointRouter(
        endpoint_configs=[_endpoint("ep1"), _endpoint("ep2")],
        reservation_store=store,
        providers=providers,
        max_provider_attempts=2,
        event_sink=events.append,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )

    result = _call(router)

    assert store.capacity_feedback[0]["endpoint_id"] == "ep1"
    assert store.capacity_feedback[0]["retry_after_seconds"] == 7.0
    assert any(event["event"] == "capacity_feedback" for event in events)
    assert all(event["event"] != "endpoint_health_failure" for event in events)
    assert result.audit.routing_attempt_count == 2
    assert result.audit.provider_definite_rejected_count == 1
    assert result.audit.provider_succeeded_count == 1


def test_5xx_application_failure_never_cross_endpoint_fails_over():
    clock = FakeClock()
    store = FakeStore(
        [ReservationDecision(_reservation("ep1", reserved_at=100.0, expires_at=105.0), "reserved")]
    )
    providers = {
        "ep1": FakeProvider(
            [
                AzureProviderError(
                    "azure_server_error",
                    retryable=False,
                    unknown_outcome=True,
                    attempts=1,
                    provider_status=500,
                    failure_class="application",
                )
            ]
        ),
        "ep2": FakeProvider([_result()]),
    }
    router = AzureEndpointRouter(
        endpoint_configs=[_endpoint("ep1"), _endpoint("ep2")],
        reservation_store=store,
        providers=providers,
        max_provider_attempts=2,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )

    with pytest.raises(AzureUnknownOutcomeError) as caught:
        _call(router)

    assert caught.value.provider_usage["providerAmbiguous"] == 1
    assert providers["ep2"].calls == []
    assert len(store.reservations) == 1


def test_router_construction_performs_no_active_health_probe_or_transaction():
    class Doc:
        pass

    class Collection:
        def document(self, _doc_id):
            return Doc()

    class FirestoreClient:
        transaction_calls = 0

        def collection(self, _name):
            return Collection()

        def transaction(self):
            self.transaction_calls += 1
            raise AssertionError("construction must not reserve or probe")

    env = {
        "AZURE_OPENAI_ENDPOINT_IDS": "ep1,ep2",
        "AZURE_OPENAI_ENDPOINT_QUOTAS": "ep1=2,ep2=2",
    }
    for endpoint_id in ("EP1", "EP2"):
        env.update(
            {
                f"AZURE_OPENAI_{endpoint_id}_ENDPOINT": "https://example.invalid",
                f"AZURE_OPENAI_{endpoint_id}_DEPLOYMENT": "gpt-image-2",
                f"AZURE_OPENAI_{endpoint_id}_API_VERSION": "preview",
                f"AZURE_OPENAI_{endpoint_id}_API_KEY": "SECRET",
            }
        )
    client = FirestoreClient()

    router = build_azure_endpoint_router(firestore_client=client, env=env)

    assert set(router._configs) == {"ep1", "ep2"}
    assert client.transaction_calls == 0
    for provider in router._providers.values():
        provider._transport.close()
