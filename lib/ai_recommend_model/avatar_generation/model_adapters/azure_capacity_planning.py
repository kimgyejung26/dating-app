from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Sequence


@dataclass(frozen=True)
class AzureCapacityPlan:
    endpoint_rpm_limits: tuple[float, ...]
    nominal_provider_rpm: float
    calls_per_job: int
    nominal_job_rpm: float
    provider_p50_seconds: float
    provider_p95_seconds: float
    minimum_provider_call_concurrency_p50: int
    minimum_provider_call_concurrency_p95: int
    headroom_factor: float
    recommended_provider_call_concurrency: int
    container_request_concurrency: int
    recommended_inflight_job_requests: int
    recommended_cloud_run_max_instances: int
    recommended_cloud_tasks_max_concurrent_dispatches: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _little_law_concurrency(*, rpm: float, latency_seconds: float) -> int:
    return max(1, math.ceil((float(rpm) / 60.0) * float(latency_seconds)))


def calculate_capacity_plan(
    *,
    endpoint_rpm_limits: Sequence[float],
    provider_p50_seconds: float,
    provider_p95_seconds: float,
    calls_per_job: int = 4,
    container_request_concurrency: int = 1,
    headroom_factor: float = 1.2,
) -> AzureCapacityPlan:
    rpm_limits = tuple(float(value) for value in endpoint_rpm_limits)
    if not rpm_limits or any(value <= 0 for value in rpm_limits):
        raise ValueError("endpoint_rpm_limits must contain positive values")
    if provider_p50_seconds <= 0 or provider_p95_seconds <= 0:
        raise ValueError("provider latency values must be positive")
    if provider_p95_seconds < provider_p50_seconds:
        raise ValueError("provider_p95_seconds must be >= provider_p50_seconds")
    if int(calls_per_job) < 1 or int(container_request_concurrency) < 1:
        raise ValueError("calls_per_job and container concurrency must be positive")
    if float(headroom_factor) < 1.0:
        raise ValueError("headroom_factor must be >= 1")

    nominal_rpm = sum(rpm_limits)
    p50_concurrency = _little_law_concurrency(
        rpm=nominal_rpm,
        latency_seconds=provider_p50_seconds,
    )
    p95_concurrency = _little_law_concurrency(
        rpm=nominal_rpm,
        latency_seconds=provider_p95_seconds,
    )
    recommended_calls = max(
        p95_concurrency,
        math.ceil(
            (nominal_rpm / 60.0)
            * float(provider_p95_seconds)
            * float(headroom_factor)
        ),
    )
    # Each avatar request executes provider calls sequentially, so every
    # concurrent provider call requires one in-flight job request.
    inflight_jobs = recommended_calls
    per_instance = int(container_request_concurrency)
    max_instances = math.ceil(inflight_jobs / per_instance)
    return AzureCapacityPlan(
        endpoint_rpm_limits=rpm_limits,
        nominal_provider_rpm=nominal_rpm,
        calls_per_job=int(calls_per_job),
        nominal_job_rpm=nominal_rpm / int(calls_per_job),
        provider_p50_seconds=float(provider_p50_seconds),
        provider_p95_seconds=float(provider_p95_seconds),
        minimum_provider_call_concurrency_p50=p50_concurrency,
        minimum_provider_call_concurrency_p95=p95_concurrency,
        headroom_factor=float(headroom_factor),
        recommended_provider_call_concurrency=recommended_calls,
        container_request_concurrency=per_instance,
        recommended_inflight_job_requests=inflight_jobs,
        recommended_cloud_run_max_instances=max_instances,
        recommended_cloud_tasks_max_concurrent_dispatches=inflight_jobs,
    )


__all__ = ["AzureCapacityPlan", "calculate_capacity_plan"]
