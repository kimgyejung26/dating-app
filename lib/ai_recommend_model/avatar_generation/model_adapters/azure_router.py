from __future__ import annotations

from dataclasses import replace
import logging
import os
import time
from typing import Any, Callable, Mapping, Optional, Sequence

from .azure_contracts import (
    AzureGenerationResult,
    AzureProviderError,
    AzureTransportError,
    AzureUnknownOutcomeError,
    provider_usage,
)
from .azure_endpoint_config import AzureEndpointConfig, load_azure_endpoint_configs
from .azure_reservation import (
    AzureReservationStore,
    FirestoreAzureReservationStore,
    ReservationPolicy,
)


logger = logging.getLogger(__name__)


class _ReservedSlotRateLimiter:
    def acquire(self, timeout: Optional[float] = None) -> bool:
        return True


class AzureEndpointRouter:
    """Route one logical image call through transactionally paced endpoints."""

    def __init__(
        self,
        *,
        endpoint_configs: Sequence[AzureEndpointConfig],
        reservation_store: AzureReservationStore,
        providers: Mapping[str, Any],
        policy: ReservationPolicy = ReservationPolicy(),
        max_provider_attempts: int = 5,
        max_stale_reservations: int = 2,
        clock_fn: Callable[[], float] = time.time,
        monotonic_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
        event_sink: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        if not endpoint_configs:
            raise ValueError("endpoint_configs must not be empty")
        if any(config.provider_config.max_attempts != 1 for config in endpoint_configs):
            raise ValueError("router endpoint providers must be configured for one send")
        self._configs = {config.endpoint_id: config for config in endpoint_configs}
        if set(self._configs) != set(providers):
            raise ValueError("providers must exactly match endpoint configs")
        self._providers = dict(providers)
        self._store = reservation_store
        self._policy = policy
        self._max_attempts = max(1, int(max_provider_attempts))
        self._max_stale = max(0, int(max_stale_reservations))
        self._clock = clock_fn
        self._monotonic = monotonic_fn
        self._sleep = sleep_fn
        self._event_sink = event_sink or self._log_event
        self.model_id = "azure_gpt_image_2"
        self.version = "gpt-image-2"

    def _log_event(self, event: dict[str, Any]) -> None:
        logger.info("azure_router_event=%s", event)

    def _emit(self, event: str, **fields: Any) -> None:
        self._event_sink({"event": event, **fields})

    def _deadline_epoch(self, deadline_monotonic: Optional[float]) -> Optional[float]:
        if deadline_monotonic is None:
            return None
        return self._clock() + max(0.0, deadline_monotonic - self._monotonic())

    def generate(
        self,
        *,
        source_image_bytes: bytes,
        source_content_type: str,
        prompt: str,
        idempotency_key: str,
        deadline_monotonic: Optional[float] = None,
        request_budget: Any = None,
    ) -> AzureGenerationResult:
        endpoint_rpms = {
            endpoint_id: config.rpm_limit
            for endpoint_id, config in self._configs.items()
        }
        excluded: set[str] = set()
        provider_attempts = 0
        stale_reservations = 0
        started = self._monotonic()

        while provider_attempts < self._max_attempts:
            if len(excluded) >= len(self._configs):
                excluded.clear()
            now = self._clock()
            request_timeout = max(
                config.provider_config.request_timeout_seconds
                for config in self._configs.values()
            )
            decision = self._store.reserve(
                endpoint_rpms=endpoint_rpms,
                now_epoch_seconds=now,
                deadline_epoch_seconds=self._deadline_epoch(deadline_monotonic),
                request_timeout_seconds=request_timeout,
                policy=self._policy,
                excluded_endpoint_ids=frozenset(excluded),
            )
            reservation = decision.reservation
            if reservation is None:
                self._emit(
                    "capacity_deferred",
                    reason=decision.reason,
                    retryAfterSeconds=round(decision.retry_after_seconds, 3),
                )
                raise AzureProviderError(
                    "azure_capacity_deferred",
                    retryable=True,
                    retry_after_seconds=decision.retry_after_seconds,
                    failure_class="capacity",
                )

            if reservation.wait_seconds > 0.0:
                self._emit(
                    "reservation_wait",
                    endpointId=reservation.endpoint_id,
                    waitSeconds=round(reservation.wait_seconds, 3),
                )
                self._sleep(reservation.wait_seconds)
            if self._clock() > reservation.expires_at_epoch_seconds:
                stale_reservations += 1
                self._emit("stale_reservation", endpointId=reservation.endpoint_id)
                if stale_reservations > self._max_stale:
                    raise AzureProviderError(
                        "azure_capacity_deferred",
                        retryable=True,
                        failure_class="capacity",
                    )
                continue

            endpoint_id = reservation.endpoint_id
            provider_attempts += 1
            try:
                result = self._providers[endpoint_id].generate(
                    source_image_bytes=source_image_bytes,
                    source_content_type=source_content_type,
                    prompt=prompt,
                    idempotency_key=idempotency_key,
                    deadline_monotonic=deadline_monotonic,
                    request_budget=request_budget,
                )
                self._emit(
                    "provider_call_succeeded",
                    endpointId=endpoint_id,
                    providerLatencySeconds=round(result.audit.latency_seconds, 3),
                    logicalAttempt=provider_attempts,
                )
                return AzureGenerationResult(
                    image_bytes=result.image_bytes,
                    audit=replace(
                        result.audit,
                        attempts=provider_attempts,
                        latency_seconds=max(0.0, self._monotonic() - started),
                    ),
                )
            except AzureUnknownOutcomeError:
                self._emit("ambiguous_failure", endpointId=endpoint_id)
                raise
            except AzureTransportError as exc:
                if exc.request_sent:
                    self._emit("ambiguous_failure", endpointId=endpoint_id)
                    raise AzureUnknownOutcomeError(provider_attempts) from exc
                excluded.add(endpoint_id)
                self._emit("pre_send_failure", endpointId=endpoint_id)
                if provider_attempts >= self._max_attempts:
                    raise AzureTransportError(
                        exc.error_code,
                        request_sent=False,
                        attempts=provider_attempts,
                        provider_usage=provider_usage(
                            attempts=provider_attempts,
                            outcome="failure",
                        ),
                    ) from exc
            except AzureProviderError as exc:
                if exc.unknown_outcome or exc.failure_class == "ambiguous":
                    self._emit("ambiguous_failure", endpointId=endpoint_id)
                    raise AzureUnknownOutcomeError(provider_attempts) from exc
                if exc.provider_status == 429 or exc.failure_class == "capacity":
                    retry_after = exc.retry_after_seconds or 0.0
                    self._store.record_capacity_feedback(
                        endpoint_id=endpoint_id,
                        now_epoch_seconds=self._clock(),
                        retry_after_seconds=retry_after,
                    )
                    excluded.add(endpoint_id)
                    self._emit(
                        "capacity_feedback",
                        endpointId=endpoint_id,
                        retryAfterSeconds=round(retry_after, 3),
                    )
                    if provider_attempts >= self._max_attempts:
                        raise AzureProviderError(
                            exc.error_code,
                            retryable=True,
                            attempts=provider_attempts,
                            provider_status=429,
                            provider_usage=provider_usage(
                                attempts=provider_attempts,
                                outcome="failure",
                            ),
                            retry_after_seconds=retry_after,
                            failure_class="capacity",
                        ) from exc
                    continue
                if exc.failure_class == "server_response":
                    excluded.add(endpoint_id)
                    self._emit("server_response_failure", endpointId=endpoint_id)
                    if provider_attempts < self._max_attempts:
                        continue
                raise

        raise AzureProviderError(
            "azure_router_attempts_exhausted",
            retryable=True,
            attempts=provider_attempts,
        )


def build_azure_endpoint_router(
    *,
    firestore_client: Any = None,
    env: Optional[Mapping[str, str]] = None,
) -> AzureEndpointRouter:
    from .azure_gpt_image_2 import AzureGptImage2Provider

    source = os.environ if env is None else env
    configs = load_azure_endpoint_configs(env=source)
    if firestore_client is None:
        try:
            from google.cloud import firestore

            project = next(
                (
                    str(source.get(name, "") or "").strip()
                    for name in (
                        "AVATAR_DATA_PROJECT",
                        "FIRESTORE_PROJECT",
                        "GCP_PROJECT",
                        "GOOGLE_CLOUD_PROJECT",
                    )
                    if str(source.get(name, "") or "").strip()
                ),
                None,
            )
            database = str(source.get("FIRESTORE_DATABASE", "") or "").strip() or None
            kwargs = {}
            if project:
                kwargs["project"] = project
            if database and database != "(default)":
                kwargs["database"] = database
            firestore_client = firestore.Client(**kwargs)
        except Exception as exc:
            raise AzureProviderError(
                "azure_router_firestore_unavailable",
                retryable=True,
            ) from exc
    providers = {
        config.endpoint_id: AzureGptImage2Provider(
            config=config.provider_config,
            rate_limiter=_ReservedSlotRateLimiter(),
        )
        for config in configs
    }
    policy = ReservationPolicy(
        safety_guard_seconds=_env_float(source, "AZURE_OPENAI_PACING_GUARD_SECONDS", 0.25, 0.0, 10.0),
        max_bounded_wait_seconds=_env_float(source, "AZURE_OPENAI_MAX_BOUNDED_WAIT_SECONDS", 20.0, 0.0, 120.0),
        reservation_grace_seconds=_env_float(source, "AZURE_OPENAI_RESERVATION_GRACE_SECONDS", 5.0, 0.5, 30.0),
        deadline_guard_seconds=_env_float(source, "AZURE_OPENAI_DEADLINE_GUARD_SECONDS", 10.0, 1.0, 120.0),
    )
    return AzureEndpointRouter(
        endpoint_configs=configs,
        reservation_store=FirestoreAzureReservationStore(firestore_client),
        providers=providers,
        policy=policy,
        max_provider_attempts=_env_int(
            source,
            "AZURE_OPENAI_ROUTER_MAX_ATTEMPTS",
            max(3, len(configs)),
            1,
            10,
        ),
    )


def _env_float(
    source: Mapping[str, str], name: str, fallback: float, minimum: float, maximum: float
) -> float:
    try:
        value = float(str(source.get(name, "") or fallback))
    except (TypeError, ValueError):
        value = fallback
    return max(minimum, min(maximum, value))


def _env_int(
    source: Mapping[str, str], name: str, fallback: int, minimum: int, maximum: int
) -> int:
    try:
        value = int(str(source.get(name, "") or fallback))
    except (TypeError, ValueError):
        value = fallback
    return max(minimum, min(maximum, value))


__all__ = ["AzureEndpointRouter", "build_azure_endpoint_router"]
