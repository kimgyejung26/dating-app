from __future__ import annotations

from dataclasses import dataclass
import math
import os
from typing import Mapping, Optional


@dataclass(frozen=True)
class AzureDeadlineBudget:
    provider_timeout_seconds: float = 90.0
    max_reservation_wait_seconds: float = 20.0
    artifact_seconds_per_candidate: float = 10.0
    qa_seconds_per_candidate: float = 30.0
    firestore_seconds_per_candidate: float = 5.0
    finalization_seconds: float = 30.0
    deadline_guard_seconds: float = 10.0
    cold_start_seconds: float = 60.0

    def remaining_round_seconds(self, candidate_count: int) -> float:
        count = max(0, int(candidate_count))
        per_candidate = (
            self.max_reservation_wait_seconds
            + self.provider_timeout_seconds
            + self.artifact_seconds_per_candidate
            + self.qa_seconds_per_candidate
            + self.firestore_seconds_per_candidate
        )
        return (
            count * per_candidate
            + self.finalization_seconds
            + self.deadline_guard_seconds
        )

    def worst_safe_job_seconds(self, provider_call_count: int) -> float:
        return self.cold_start_seconds + self.remaining_round_seconds(
            provider_call_count
        )


def deadline_budget_from_env(
    env: Optional[Mapping[str, str]] = None,
) -> AzureDeadlineBudget:
    source = os.environ if env is None else env
    return AzureDeadlineBudget(
        provider_timeout_seconds=_bounded_float(
            source, "AZURE_OPENAI_TIMEOUT_SECONDS", 90.0, 5.0, 300.0
        ),
        max_reservation_wait_seconds=_bounded_float(
            source,
            "AZURE_OPENAI_MAX_BOUNDED_WAIT_SECONDS",
            20.0,
            0.0,
            120.0,
        ),
        artifact_seconds_per_candidate=_bounded_float(
            source,
            "AVATAR_ARTIFACT_BUDGET_SECONDS_PER_CANDIDATE",
            10.0,
            0.0,
            300.0,
        ),
        qa_seconds_per_candidate=_bounded_float(
            source,
            "AVATAR_QA_BUDGET_SECONDS_PER_CANDIDATE",
            30.0,
            0.0,
            600.0,
        ),
        firestore_seconds_per_candidate=_bounded_float(
            source,
            "AVATAR_FIRESTORE_BUDGET_SECONDS_PER_CANDIDATE",
            5.0,
            0.0,
            120.0,
        ),
        finalization_seconds=_bounded_float(
            source, "AVATAR_FINALIZATION_BUDGET_SECONDS", 30.0, 0.0, 300.0
        ),
        deadline_guard_seconds=_bounded_float(
            source, "AZURE_OPENAI_DEADLINE_GUARD_SECONDS", 10.0, 1.0, 120.0
        ),
        cold_start_seconds=_bounded_float(
            source, "AVATAR_COLD_START_BUDGET_SECONDS", 60.0, 0.0, 600.0
        ),
    )


def _bounded_float(
    source: Mapping[str, str],
    name: str,
    fallback: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = str(source.get(name, "") or "").strip()
    if not raw:
        return fallback
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(value) or value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum:g} and {maximum:g}")
    return value


__all__ = [
    "AzureDeadlineBudget",
    "deadline_budget_from_env",
]
