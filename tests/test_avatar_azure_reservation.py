from __future__ import annotations

import copy
import sys
import threading
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
        deadline_epoch_seconds=250.0,
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
        deadline_epoch_seconds=180.0,
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
            deadline_epoch_seconds=1000.0,
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
        deadline_epoch_seconds=1000.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=60.0),
    )

    assert decision.reservation is not None
    assert decision.reservation.reserved_at_epoch_seconds == 130.25


class _Snapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return copy.deepcopy(self._data or {})


class _Doc:
    def __init__(self, client):
        self.client = client

    def get(self, transaction=None):
        return _Snapshot(self.client.state)


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
        self.lock = threading.Lock()

    def collection(self, _name):
        return _Collection(self)

    def transaction(self):
        return _Transaction(self)

    def run_transaction(self, callback):
        with self.lock:
            return callback(self.transaction())


def test_firestore_transaction_concurrent_reservations_never_share_a_slot():
    client = _AtomicClient()
    store = FirestoreAzureReservationStore(client)
    reservations = []
    errors = []

    def reserve_one():
        try:
            decision = store.reserve(
                endpoint_rpms={"ep1": 2.0},
                now_epoch_seconds=100.0,
                deadline_epoch_seconds=1000.0,
                request_timeout_seconds=90.0,
                policy=_policy(max_bounded_wait_seconds=400.0),
            )
            reservations.append(decision.reservation)
        except Exception as exc:  # pragma: no cover - assertion reports it
            errors.append(exc)

    threads = [threading.Thread(target=reserve_one) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    starts = [item.reserved_at_epoch_seconds for item in reservations if item]
    assert len(starts) == 8
    assert len(set(starts)) == 8
    assert set(client.state) <= {"schemaVersion", "sequence", "endpoints", "updatedAtEpochSeconds"}
    assert "url" not in repr(client.state).lower()
    assert "key" not in repr(client.state).lower()


def test_429_capacity_feedback_never_returns_the_consumed_slot():
    client = _AtomicClient()
    store = FirestoreAzureReservationStore(client)
    first = store.reserve(
        endpoint_rpms={"ep1": 2.0},
        now_epoch_seconds=100.0,
        deadline_epoch_seconds=1000.0,
        request_timeout_seconds=90.0,
        policy=_policy(max_bounded_wait_seconds=100.0),
    ).reservation
    assert first is not None

    store.record_capacity_feedback(
        endpoint_id="ep1",
        now_epoch_seconds=101.0,
        retry_after_seconds=5.0,
    )
    second = store.reserve(
        endpoint_rpms={"ep1": 2.0},
        now_epoch_seconds=101.0,
        deadline_epoch_seconds=1000.0,
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
            now_epoch_seconds=0.0,
            deadline_epoch_seconds=1000.0,
            request_timeout_seconds=90.0,
            policy=_policy(),
        )

    assert caught.value.error_code == "azure_router_firestore_unavailable"
    assert caught.value.retryable is True
