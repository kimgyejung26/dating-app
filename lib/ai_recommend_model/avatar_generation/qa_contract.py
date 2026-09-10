"""Shared required/optional QA signal contract and coarse failure codes."""

from __future__ import annotations

from typing import Any, Mapping


REQUIRED_SIGNAL_ALIASES: dict[str, tuple[str, ...]] = {
    "face_detector": ("faceDetector",),
    "visual_risk": ("visualRisk",),
    "clip_safety": ("clipSafety", "localSafetyRisk", "clip"),
    "face_similarity": ("faceSimilarity",),
}
OPTIONAL_SIGNAL_NAMES = ("dino",)

STATUS_NOT_REQUIRED = "not_required"
STATUS_UNAVAILABLE = "unavailable"

_REQUIRED_SIGNAL_KEYS = frozenset(
    alias.lower() for aliases in REQUIRED_SIGNAL_ALIASES.values() for alias in aliases
)


def unreported_signal_status(signal_key: str) -> str:
    """What it means that nobody reported this signal.

    Silence is only an outage for a signal the contract requires: there, absence
    has to fail closed, because "the detector never answered" and "the detector
    answered badly" are equally unusable. For every other key silence means the
    run did not involve it, and writing that down as ``"unavailable"`` fabricates
    an outage that ``preview_policy`` and ``adaptive_generation`` then read as
    fact -- both scan the whole flat availability map. ``dino`` was fixed this
    way on 2026-09-07 with a literal; ``mediapipe`` is the same shape and kept
    the bug, so the rule lives here instead of being restated per key.

    An explicit report always wins over this default. A caller that genuinely
    saw a signal fail still records ``"unavailable"`` and still gates.
    """

    key = str(signal_key or "").strip().lower()
    return STATUS_UNAVAILABLE if key in _REQUIRED_SIGNAL_KEYS else STATUS_NOT_REQUIRED


def required_signal_failure_codes(availability: Mapping[str, Any]) -> tuple[str, ...]:
    """Return stable typed failures without retaining adapter exceptions."""

    normalized = {
        str(key).strip().lower(): str(value or "").strip().lower()
        for key, value in availability.items()
    }
    failures: list[str] = []
    for signal_name, aliases in REQUIRED_SIGNAL_ALIASES.items():
        status = _first_status(normalized, aliases)
        if status == "available":
            continue
        suffix = "uncalibrated" if status == "uncalibrated" else "unavailable"
        failures.append(f"{signal_name}_{suffix}")
    return tuple(failures)


def _first_status(normalized: Mapping[str, str], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        value = normalized.get(alias.lower())
        if value:
            return value
    return "unavailable"


__all__ = [
    "OPTIONAL_SIGNAL_NAMES",
    "REQUIRED_SIGNAL_ALIASES",
    "STATUS_NOT_REQUIRED",
    "STATUS_UNAVAILABLE",
    "required_signal_failure_codes",
    "unreported_signal_status",
]
