from __future__ import annotations

import copy
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.model_adapters.azure_contracts import AzureProviderError  # noqa: E402
from avatar_generation.model_adapters.azure_reservation import (  # noqa: E402
    FirestoreAzureReservationStore,
    ReservationPolicy,
    reserve_router_slot,
    reservation_interval_seconds,
)


def _policy(**overrides) -> ReservationPolicy:
    values = {
        "safety_guard_seconds": 0.25,
        "max_bounded_wait_seconds": 20.0,
        "reservation_grace_seconds": 5.0,
        "deadline_guard_seconds": 10.0,
    }
    values.update(overrides)
    return ReservationPolicy(**values)


def test_pacing_interval_is_derived_from_rpm_plus_configurable_guard():
    assert reservation_interval_seconds(2.0, safety_guard_seconds=0.25) == 30.25
    assert reservation_interval_seconds(6.0, safety_guard_seconds=0.4) == 10.4


def test_near_slot_is_atomically_reserved_before_worker_waits():
    state = {
        "sequence": 1,
        "endpoints": {
            "ep1": {"nextAvailableAtEpochSeconds": 110.0},
        },
    }

    updated, decision = reserve_router_slot(
        state,
        endpoint_rpms={"ep1": 2.0},
        now_epoch_seconds=100.0,
        remaining_deadline_seconds=150.0,
        request_timeout_seconds=90.0,
        policy=_policy(),
    )

    assert decision.reservation is not None
    assert decision.reservation.reserved_at_epoch_seconds == 110.0
    assert decision.reservation.wait_seconds == 10.0
    assert updated["endpoints"]["ep1"]["nextAvailableAtEpochSeconds"] == 140.25


def test_far_or_deadline_risky_slot_defers_without_consuming_a_reservation():
    state = {
        "sequence": 7,
        "endpoints": {"ep1": {"nextAvailableAtEpochSeconds": 130.0}},
    }
    original = copy.deepcopy(state)

    updated, decision = reserve_router_slot(
        state,
        endpoint_rpms={"ep1": 2.0},
        now_epoch_seconds=100.0,
        remaining_deadline_seconds=80.0,
        request_timeout_seconds=90.0,
        policy=_policy(),
    )

    assert decision.reservation is None
    assert decision.reason in {"bounded_wait_exceeded", "request_deadline_risk"}
    assert updated == original


def test_five_two_rpm_endpoints_reserve_ten_paced_starts_without_global_burst():
    state = {}
    starts = []
    endpoint_rpms = {f"ep{index}": 2.0 for index in range(1, 6)}

    for _ in range(10):
        state, decision = reserve_router_slot(
            state,
            endpoint_rpms=endpoint_rpms,
            now_epoch_seconds=0.0,
            remaining_deadline_seconds=1000.0,
            request_timeout_seconds=90.0,
            policy=_policy(max_bounded_wait_seconds=60.0),
        )
        assert decision.reservation is not None
        starts.append(decision.reservation.reserved_at_epoch_seconds)

    assert starts[:5] == [0.0] * 5
    assert starts[5:] == [30.25] * 5
    assert sum(1 for value in starts if value < 60.0) == 10


def test_quota_decrease_applies_new_longer_interval_without_code_change():
    state = {
        "sequence": 1,
        "endpoints": {
            "ep1": {
                "rpmLimit": 6.0,
                "lastReservedAtEpochSeconds": 100.0,
                "nextAvailableAtEpochSeconds": 110.25,
            }
        },
    }

    _, decision = reserve_router_slot(
        state,
        endpoint_rpms={"ep1": 2.0},
        now_epoch_seconds=105.0,
        remaining_deadline_seconds=895.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=60.0),
    )

    assert decision.reservation is not None
    assert decision.reservation.reserved_at_epoch_seconds == 130.25


class _Snapshot:
    def __init__(self, data, server_epoch):
        self._data = data
        self.exists = data is not None
        self.read_time = datetime.fromtimestamp(server_epoch, tz=timezone.utc)

    def to_dict(self):
        return copy.deepcopy(self._data or {})


class _Doc:
    def __init__(self, client):
        self.client = client

    def get(self, transaction=None):
        return _Snapshot(self.client.state, self.client.server_epoch)


class _Collection:
    def __init__(self, client):
        self.client = client

    def document(self, _doc_id):
        return _Doc(self.client)


class _Transaction:
    _codex_fake_transaction = True

    def __init__(self, client):
        self.client = client

    def set(self, _ref, value, merge=True):
        assert merge is True
        self.client.state = copy.deepcopy(value)


class _AtomicClient:
    def __init__(self):
        self.state = {}
        self.server_epoch = 100.0
        self.lock = threading.Lock()

    def collection(self, _name):
        return _Collection(self)

    def transaction(self):
        return _Transaction(self)

    def run_transaction(self, callback):
        with self.lock:
            return callback(self.transaction())


def test_firestore_transaction_twelve_concurrent_reservations_never_share_a_slot():
    client = _AtomicClient()
    store = FirestoreAzureReservationStore(client)
    reservations = []
    errors = []

    def reserve_one():
        try:
            decision = store.reserve(
                endpoint_rpms={"ep1": 2.0},
                remaining_deadline_seconds=900.0,
                request_timeout_seconds=90.0,
                policy=_policy(max_bounded_wait_seconds=400.0),
            )
            reservations.append(decision.reservation)
        except Exception as exc:  # pragma: no cover - assertion reports it
            errors.append(exc)

    threads = [threading.Thread(target=reserve_one) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    starts = [item.reserved_at_epoch_seconds for item in reservations if item]
    assert len(starts) == 12
    assert len(set(starts)) == 12
    assert set(client.state) <= {"schemaVersion", "sequence", "endpoints", "updatedAtEpochSeconds"}
    assert "url" not in repr(client.state).lower()
    assert "key" not in repr(client.state).lower()


def test_transaction_callback_retry_reports_attempts_and_commits_one_slot():
    class NoCommitTransaction(_Transaction):
        def set(self, _ref, _value, merge=True):
            assert merge is True

    class RetryingClient(_AtomicClient):
        def run_transaction(self, callback):
            with self.lock:
                callback(NoCommitTransaction(self))
                return callback(self.transaction())

    client = RetryingClient()
    decision = FirestoreAzureReservationStore(client).reserve(
        endpoint_rpms={"ep1": 2.0},
        remaining_deadline_seconds=900.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=100.0),
    )

    assert decision.transaction_attempts == 2
    assert decision.reservation is not None
    assert client.state["sequence"] == 1
    assert client.state["endpoints"]["ep1"]["lastReservationSequence"] == 1


def test_429_capacity_feedback_never_returns_the_consumed_slot():
    client = _AtomicClient()
    store = FirestoreAzureReservationStore(client)
    first = store.reserve(
        endpoint_rpms={"ep1": 2.0},
        remaining_deadline_seconds=900.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=100.0),
    ).reservation
    assert first is not None

    client.server_epoch = 101.0
    store.record_capacity_feedback(
        endpoint_id="ep1",
        retry_after_seconds=5.0,
    )
    second = store.reserve(
        endpoint_rpms={"ep1": 2.0},
        remaining_deadline_seconds=899.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=100.0),
    ).reservation

    assert second is not None
    assert second.reserved_at_epoch_seconds >= 130.25


def test_firestore_failure_fails_closed():
    class BrokenClient(_AtomicClient):
        def run_transaction(self, callback):
            raise RuntimeError("firestore down")

    store = FirestoreAzureReservationStore(BrokenClient())
    with pytest.raises(AzureProviderError) as caught:
        store.reserve(
            endpoint_rpms={"ep1": 2.0},
            remaining_deadline_seconds=1000.0,
            request_timeout_seconds=90.0,
            policy=_policy(),
        )

    assert caught.value.error_code == "azure_router_firestore_unavailable"
    assert caught.value.retryable is True


def test_firestore_server_read_time_is_the_clock_authority_across_skewed_workers():
    client = _AtomicClient()
    store = FirestoreAzureReservationStore(client)

    # Local clocks at -2s, nominal, and +2s never enter the reservation API.
    # One Firestore server read-time timeline controls all three reservations.
    local_worker_clocks = [98.0, 100.0, 102.0]
    starts = []
    for _local_clock in local_worker_clocks:
        decision = store.reserve(
            endpoint_rpms={"ep1": 2.0},
            remaining_deadline_seconds=1000.0,
            request_timeout_seconds=90.0,
            policy=_policy(max_bounded_wait_seconds=100.0),
        )
        assert decision.reservation is not None
        starts.append(decision.reservation.reserved_at_epoch_seconds)

    assert starts == [100.0, 130.25, 160.5]
    assert [later - earlier for earlier, later in zip(starts, starts[1:])] == [30.25, 30.25]


def test_quota_two_to_one_is_immediately_conservative_and_one_to_two_keeps_old_slot():
    state = {
        "sequence": 1,
        "endpoints": {
            "ep1": {
                "rpmLimit": 2.0,
                "lastReservedAtEpochSeconds": 100.0,
                "nextAvailableAtEpochSeconds": 130.25,
            }
        },
    }
    decreased, first = reserve_router_slot(
        state,
        endpoint_rpms={"ep1": 1.0},
        now_epoch_seconds=105.0,
        remaining_deadline_seconds=1000.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=100.0),
    )
    assert first.reservation is not None
    assert first.reservation.reserved_at_epoch_seconds == 160.25

    _, second = reserve_router_slot(
        decreased,
        endpoint_rpms={"ep1": 2.0},
        now_epoch_seconds=110.0,
        remaining_deadline_seconds=1000.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=200.0),
    )
    assert second.reservation is not None
    assert second.reservation.reserved_at_epoch_seconds == 220.5


def test_removed_endpoint_is_not_selected_and_readded_endpoint_keeps_stale_timeline():
    state = {
        "sequence": 0,
        "endpoints": {
            "ep1": {"lastReservedAtEpochSeconds": 100.0},
            "ep5": {
                "lastReservedAtEpochSeconds": 150.0,
                "nextAvailableAtEpochSeconds": 180.25,
            },
        },
    }
    kept, removed = reserve_router_slot(
        state,
        endpoint_rpms={"ep1": 2.0},
        now_epoch_seconds=100.0,
        remaining_deadline_seconds=1000.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=100.0),
    )
    assert removed.reservation is not None
    assert removed.reservation.endpoint_id == "ep1"
    assert "ep5" in kept["endpoints"]

    _, readded = reserve_router_slot(
        kept,
        endpoint_rpms={"ep5": 2.0},
        now_epoch_seconds=160.0,
        remaining_deadline_seconds=1000.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=100.0),
    )
    assert readded.reservation is not None
    assert readded.reservation.reserved_at_epoch_seconds == 180.25


def test_concurrent_429_feedback_only_extends_capacity_block():
    client = _AtomicClient()
    client.state = {
        "endpoints": {
            "ep1": {"capacityBlockedUntilEpochSeconds": 110.0},
        }
    }
    client.server_epoch = 101.0
    store = FirestoreAzureReservationStore(client)
    threads = [
        threading.Thread(
            target=store.record_capacity_feedback,
            kwargs={"endpoint_id": "ep1", "retry_after_seconds": value},
        )
        for value in (2.0, 30.0, 5.0, 1.0, 20.0)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert client.state["endpoints"]["ep1"]["capacityBlockedUntilEpochSeconds"] == 131.0
