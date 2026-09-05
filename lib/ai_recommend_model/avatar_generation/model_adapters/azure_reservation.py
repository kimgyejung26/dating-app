from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Optional, Protocol

from .azure_contracts import AzureProviderError


ROUTER_STATE_COLLECTION = "avatarProviderRouterState"
ROUTER_STATE_DOCUMENT = "gpt-image-2"
ROUTER_STATE_SCHEMA = "azure_router_state_v1"


@dataclass(frozen=True)
class ReservationPolicy:
    safety_guard_seconds: float = 0.25
    max_bounded_wait_seconds: float = 20.0
    reservation_grace_seconds: float = 5.0
    deadline_guard_seconds: float = 10.0


@dataclass(frozen=True)
class EndpointReservation:
    endpoint_id: str
    sequence: int
    reserved_at_epoch_seconds: float
    expires_at_epoch_seconds: float
    wait_seconds: float
    token: str


@dataclass(frozen=True)
class ReservationDecision:
    reservation: Optional[EndpointReservation]
    reason: str
    retry_after_seconds: float = 0.0


class AzureReservationStore(Protocol):
    def reserve(
        self,
        *,
        endpoint_rpms: Mapping[str, float],
        now_epoch_seconds: float,
        deadline_epoch_seconds: Optional[float],
        request_timeout_seconds: float,
        policy: ReservationPolicy,
        excluded_endpoint_ids: frozenset[str] = frozenset(),
    ) -> ReservationDecision:
        ...

    def record_capacity_feedback(
        self,
        *,
        endpoint_id: str,
        now_epoch_seconds: float,
        retry_after_seconds: float,
    ) -> None:
        ...


def reservation_interval_seconds(
    rpm_limit: float,
    *,
    safety_guard_seconds: float,
) -> float:
    rpm = float(rpm_limit)
    guard = float(safety_guard_seconds)
    if rpm <= 0.0:
        raise ValueError("rpm_limit must be positive")
    if guard < 0.0:
        raise ValueError("safety_guard_seconds must not be negative")
    return (60.0 / rpm) + guard


def _number(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed and parsed not in (float("inf"), float("-inf")) else fallback


def _reservation_token(endpoint_id: str, sequence: int, reserved_at: float) -> str:
    material = json.dumps(
        [endpoint_id, int(sequence), round(float(reserved_at), 6)],
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:24]


def reserve_router_slot(
    state: Mapping[str, Any],
    *,
    endpoint_rpms: Mapping[str, float],
    now_epoch_seconds: float,
    deadline_epoch_seconds: Optional[float],
    request_timeout_seconds: float,
    policy: ReservationPolicy,
    excluded_endpoint_ids: frozenset[str] = frozenset(),
) -> tuple[dict[str, Any], ReservationDecision]:
    now = float(now_epoch_seconds)
    sequence = max(0, int(_number(state.get("sequence"), 0.0)))
    raw_states = state.get("endpoints")
    existing = dict(raw_states) if isinstance(raw_states, Mapping) else {}
    endpoint_ids = sorted(
        endpoint_id
        for endpoint_id in endpoint_rpms
        if endpoint_id not in excluded_endpoint_ids
    )
    if not endpoint_ids:
        return dict(state), ReservationDecision(None, "no_eligible_endpoint")

    rotation = sequence % len(endpoint_ids)
    rotated = endpoint_ids[rotation:] + endpoint_ids[:rotation]
    candidates: list[tuple[float, int, str]] = []
    for order, endpoint_id in enumerate(rotated):
        raw = existing.get(endpoint_id)
        endpoint_state = dict(raw) if isinstance(raw, Mapping) else {}
        current_interval = reservation_interval_seconds(
            endpoint_rpms[endpoint_id],
            safety_guard_seconds=policy.safety_guard_seconds,
        )
        last_reserved = _number(
            endpoint_state.get("lastReservedAtEpochSeconds"),
            float("-inf"),
        )
        available = max(
            now,
            _number(endpoint_state.get("nextAvailableAtEpochSeconds"), now),
            _number(endpoint_state.get("capacityBlockedUntilEpochSeconds"), now),
            last_reserved + current_interval,
        )
        candidates.append((available, order, endpoint_id))
    reserved_at, _, endpoint_id = min(candidates)
    wait_seconds = max(0.0, reserved_at - now)
    if wait_seconds > policy.max_bounded_wait_seconds:
        return dict(state), ReservationDecision(
            None,
            "bounded_wait_exceeded",
            retry_after_seconds=wait_seconds,
        )
    if (
        deadline_epoch_seconds is not None
        and reserved_at + float(request_timeout_seconds) + policy.deadline_guard_seconds
        >= float(deadline_epoch_seconds)
    ):
        return dict(state), ReservationDecision(
            None,
            "request_deadline_risk",
            retry_after_seconds=wait_seconds,
        )

    next_sequence = sequence + 1
    interval = reservation_interval_seconds(
        endpoint_rpms[endpoint_id],
        safety_guard_seconds=policy.safety_guard_seconds,
    )
    endpoint_state = dict(existing.get(endpoint_id) or {})
    endpoint_state.update(
        {
            "rpmLimit": float(endpoint_rpms[endpoint_id]),
            "nextAvailableAtEpochSeconds": reserved_at + interval,
            "lastReservedAtEpochSeconds": reserved_at,
            "lastReservationSequence": next_sequence,
        }
    )
    updated_endpoints = {**existing, endpoint_id: endpoint_state}
    updated = {
        "schemaVersion": ROUTER_STATE_SCHEMA,
        "sequence": next_sequence,
        "endpoints": updated_endpoints,
        "updatedAtEpochSeconds": now,
    }
    reservation = EndpointReservation(
        endpoint_id=endpoint_id,
        sequence=next_sequence,
        reserved_at_epoch_seconds=reserved_at,
        expires_at_epoch_seconds=reserved_at + policy.reservation_grace_seconds,
        wait_seconds=wait_seconds,
        token=_reservation_token(endpoint_id, next_sequence, reserved_at),
    )
    return updated, ReservationDecision(reservation, "reserved")


class FirestoreAzureReservationStore:
    def __init__(self, firestore_client: Any) -> None:
        self._client = firestore_client
        self._ref = firestore_client.collection(ROUTER_STATE_COLLECTION).document(
            ROUTER_STATE_DOCUMENT
        )

    def _run_transaction(self, callback: Any) -> Any:
        direct = getattr(self._client, "run_transaction", None)
        if callable(direct):
            return direct(callback)
        transaction_factory = getattr(self._client, "transaction", None)
        if not callable(transaction_factory):
            raise RuntimeError("firestore transaction unavailable")
        transaction = transaction_factory()
        if not getattr(transaction, "_codex_fake_transaction", False):
            try:
                from google.cloud import firestore as google_firestore

                return google_firestore.transactional(callback)(transaction)
            except ImportError:
                pass
        return callback(transaction)

    def reserve(
        self,
        *,
        endpoint_rpms: Mapping[str, float],
        now_epoch_seconds: float,
        deadline_epoch_seconds: Optional[float],
        request_timeout_seconds: float,
        policy: ReservationPolicy,
        excluded_endpoint_ids: frozenset[str] = frozenset(),
    ) -> ReservationDecision:
        def reserve_in_transaction(transaction: Any) -> ReservationDecision:
            snapshot = self._ref.get(transaction=transaction)
            state = snapshot.to_dict() if getattr(snapshot, "exists", False) else {}
            updated, decision = reserve_router_slot(
                state or {},
                endpoint_rpms=endpoint_rpms,
                now_epoch_seconds=now_epoch_seconds,
                deadline_epoch_seconds=deadline_epoch_seconds,
                request_timeout_seconds=request_timeout_seconds,
                policy=policy,
                excluded_endpoint_ids=excluded_endpoint_ids,
            )
            if decision.reservation is not None:
                transaction.set(self._ref, updated, merge=True)
            return decision

        try:
            return self._run_transaction(reserve_in_transaction)
        except AzureProviderError:
            raise
        except Exception as exc:
            raise AzureProviderError(
                "azure_router_firestore_unavailable",
                retryable=True,
            ) from exc

    def record_capacity_feedback(
        self,
        *,
        endpoint_id: str,
        now_epoch_seconds: float,
        retry_after_seconds: float,
    ) -> None:
        def update_in_transaction(transaction: Any) -> None:
            snapshot = self._ref.get(transaction=transaction)
            state = snapshot.to_dict() if getattr(snapshot, "exists", False) else {}
            state = dict(state or {})
            raw_endpoints = state.get("endpoints")
            endpoints = dict(raw_endpoints) if isinstance(raw_endpoints, Mapping) else {}
            endpoint_state = dict(endpoints.get(endpoint_id) or {})
            blocked_until = float(now_epoch_seconds) + max(0.0, float(retry_after_seconds))
            endpoint_state["capacityBlockedUntilEpochSeconds"] = max(
                _number(endpoint_state.get("capacityBlockedUntilEpochSeconds"), 0.0),
                blocked_until,
            )
            endpoints[endpoint_id] = endpoint_state
            state.update(
                {
                    "schemaVersion": ROUTER_STATE_SCHEMA,
                    "endpoints": endpoints,
                    "updatedAtEpochSeconds": float(now_epoch_seconds),
                }
            )
            transaction.set(self._ref, state, merge=True)

        try:
            self._run_transaction(update_in_transaction)
        except Exception as exc:
            raise AzureProviderError(
                "azure_router_firestore_unavailable",
                retryable=True,
            ) from exc


__all__ = [
    "AzureReservationStore",
    "EndpointReservation",
    "FirestoreAzureReservationStore",
    "ReservationDecision",
    "ReservationPolicy",
    "reserve_router_slot",
    "reservation_interval_seconds",
]
