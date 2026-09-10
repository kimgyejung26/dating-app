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

    An explicit report always wins over this default and is preserved verbatim
    in the record. Whether it *gates* is a separate question, answered by
    ``blocking_signal_failure_codes``.
    """

    key = str(signal_key or "").strip().lower()
    return STATUS_UNAVAILABLE if key in _REQUIRED_SIGNAL_KEYS else STATUS_NOT_REQUIRED


def blocking_signal_failure_codes(availability: Mapping[str, Any]) -> tuple[str, ...]:
    """Which reported failures may withhold a candidate or suppress generation.

    This is the same rule ``qa_preflight.QARuntimeReadiness.blocking_components``
    already applies -- ``critical and status != available`` -- restated for the
    per-candidate availability map so the two authorities cannot disagree.

    They did disagree. ``preview_policy`` and ``adaptive_generation`` scanned
    *every* key in the flat map and treated any "unavailable" as a systemic
    outage, while the readiness contract declares ``dino`` with
    ``critical=False, status=not_required, reason="not_in_active_qa_contract"``
    and ``signalCoverage`` maps every QA decision to a *required* component
    (``dinoRerank -> not_required_in_active_qa_contract``). A signal that no
    decision consults cannot make a decision less trustworthy by failing, so
    withholding a candidate over it is a fabricated outage rather than
    fail-closed behaviour.

    ``mediapipe`` is narrower still: it is a provider of the ``faceDetector``
    capability, not a capability of its own. When the OpenCV Haar fallback
    answers, ``faceDetector`` is available and the capability is intact
    whatever mediapipe reports.

    Required capabilities are unchanged: absent, unavailable or uncalibrated,
    they all still block.
    """

    return required_signal_failure_codes(availability)


def candidate_availability(qa_doc: Mapping[str, Any]) -> Mapping[str, Any]:
    """Where a candidate's availability map actually lives.

    ``_qa_debug_document`` writes it to ``qa["debug"]["modelAvailability"]``.
    ``worker._qa_critical_models_unavailable`` read ``qa["modelAvailability"]``
    instead and so scanned an empty dict on every candidate production has ever
    stored -- 0 of 298. The gate it guards is not decoration: it authorises the
    extra round's provider calls. It was inert by accident of shape, not by
    design, and a consumer that reads the wrong key fails open silently.

    The top-level form is still accepted because ``calibration_evaluator``
    reads that shape.
    """

    debug = qa_doc.get("debug")
    if isinstance(debug, Mapping):
        availability = debug.get("modelAvailability")
        if isinstance(availability, Mapping):
            return availability
    availability = qa_doc.get("modelAvailability")
    return availability if isinstance(availability, Mapping) else {}


def candidate_blocking_failures(qa_doc: Mapping[str, Any]) -> tuple[str, ...]:
    """Required-capability failures for one candidate QA document.

    The single entry point for every consumer that asks "may this candidate's
    availability state withhold something?" -- the preview gate, the generation
    planner, and the worker's provider-call gate. They differ in how they
    *aggregate* across candidates (any vs uniform), which is a scope decision;
    what counts as a blocking failure is decided here, once.
    """

    return blocking_signal_failure_codes(candidate_availability(qa_doc))


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
    "blocking_signal_failure_codes",
    "candidate_availability",
    "candidate_blocking_failures",
    "STATUS_NOT_REQUIRED",
    "STATUS_UNAVAILABLE",
    "required_signal_failure_codes",
    "unreported_signal_status",
]
