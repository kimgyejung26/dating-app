from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.model_adapters.azure_capacity_planning import (  # noqa: E402
    calculate_capacity_plan,
)


def test_littles_law_uses_latency_and_nominal_rpm_not_endpoint_count():
    plan = calculate_capacity_plan(
        endpoint_rpm_limits=[2, 2, 2, 2, 2],
        provider_p50_seconds=60.0,
        provider_p95_seconds=60.0,
        calls_per_job=4,
        container_request_concurrency=1,
        headroom_factor=1.0,
    )

    assert plan.nominal_provider_rpm == 10.0
    assert plan.minimum_provider_call_concurrency_p50 == 10
    assert plan.minimum_provider_call_concurrency_p95 == 10
    assert plan.recommended_inflight_job_requests == 10
    assert plan.recommended_cloud_run_max_instances == 10
    assert plan.recommended_cloud_tasks_max_concurrent_dispatches == 10
    assert plan.nominal_job_rpm == 2.5
    assert plan.recommended_cloud_run_max_instances != len(plan.endpoint_rpm_limits)


def test_container_concurrency_changes_instance_count_but_not_required_provider_calls():
    plan = calculate_capacity_plan(
        endpoint_rpm_limits=[2, 2, 2, 2, 2],
        provider_p50_seconds=45.0,
        provider_p95_seconds=75.0,
        calls_per_job=4,
        container_request_concurrency=2,
        headroom_factor=1.2,
    )

    assert plan.minimum_provider_call_concurrency_p95 == 13
    assert plan.recommended_provider_call_concurrency == 15
    assert plan.recommended_inflight_job_requests == 15
    assert plan.recommended_cloud_run_max_instances == 8
    assert plan.recommended_cloud_tasks_max_concurrent_dispatches == 15


def test_slower_p95_increases_recommendation_without_code_constants():
    fast = calculate_capacity_plan(
        endpoint_rpm_limits=[6, 2],
        provider_p50_seconds=30,
        provider_p95_seconds=45,
        calls_per_job=2,
        container_request_concurrency=1,
    )
    slow = calculate_capacity_plan(
        endpoint_rpm_limits=[6, 2],
        provider_p50_seconds=30,
        provider_p95_seconds=120,
        calls_per_job=2,
        container_request_concurrency=1,
    )

    assert slow.recommended_cloud_run_max_instances > fast.recommended_cloud_run_max_instances
    assert fast.nominal_job_rpm == slow.nominal_job_rpm == 4.0
