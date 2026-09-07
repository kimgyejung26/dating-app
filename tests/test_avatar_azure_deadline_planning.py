from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.model_adapters.azure_deadline_planning import (  # noqa: E402
    AzureDeadlineBudget,
    deadline_budget_from_env,
)
from avatar_generation.worker import (  # noqa: E402
    AvatarGenerationRetryableError,
    AvatarWorkerDeadline,
    _ensure_azure_round_deadline_budget,
)


def test_worst_safe_duration_is_calculated_for_two_and_four_calls():
    budget = AzureDeadlineBudget()

    assert budget.remaining_round_seconds(2) == 350.0
    assert budget.worst_safe_job_seconds(2) == 410.0
    assert budget.worst_safe_job_seconds(4) == 720.0


def test_deadline_budget_is_configurable_and_invalid_values_fail_closed():
    budget = deadline_budget_from_env(
        {
            "AZURE_OPENAI_TIMEOUT_SECONDS": "120",
            "AZURE_OPENAI_MAX_BOUNDED_WAIT_SECONDS": "15",
            "AVATAR_QA_BUDGET_SECONDS_PER_CANDIDATE": "45",
        }
    )
    assert budget.provider_timeout_seconds == 120.0
    assert budget.max_reservation_wait_seconds == 15.0
    assert budget.qa_seconds_per_candidate == 45.0

    with pytest.raises(ValueError, match="AZURE_OPENAI_TIMEOUT_SECONDS"):
        deadline_budget_from_env({"AZURE_OPENAI_TIMEOUT_SECONDS": "not-a-number"})


def test_worker_default_deadline_can_hold_production_four_call_budget(monkeypatch):
    for name in (
        "AVATAR_WORKER_MAX_REQUEST_SECONDS",
        "AVATAR_WORKER_MAX_JOB_SECONDS",
        "AVATAR_WORKER_SOFT_STOP_MARGIN_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    deadline = AvatarWorkerDeadline.from_env()
    production_budget = deadline_budget_from_env(
        {"AZURE_OPENAI_TIMEOUT_SECONDS": "240"}
    )

    assert production_budget.worst_safe_job_seconds(4) == 1320.0
    assert deadline.max_request_seconds == 1500
    assert deadline.max_job_seconds == 1500
    assert deadline.remaining_seconds() >= (
        production_budget.worst_safe_job_seconds(4)
        + deadline.soft_stop_margin_seconds
    )
    assert deadline.remaining_seconds() <= 1650


def test_round_budget_defers_before_reservation_when_remaining_time_is_unsafe():
    deadline = AvatarWorkerDeadline(
        started_at=time.monotonic() - 600.0,
        max_request_seconds=900,
        max_job_seconds=900,
        soft_stop_margin_seconds=30,
    )

    with pytest.raises(AvatarGenerationRetryableError) as caught:
        _ensure_azure_round_deadline_budget(
            deadline,
            candidate_count=2,
            stage="extra",
        )

    assert str(caught.value) == "avatar_worker_deadline_deferred_extra"
