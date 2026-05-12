from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .config import PipelinePaths, now_utc


REQUIRED_BEFORE_FULL = ("smoke", "pilot")


def gate_path(paths: PipelinePaths, mode: str) -> Path:
    return paths.reports / f"{mode}_run_gate.json"


def write_run_gate(
    paths: PipelinePaths,
    *,
    mode: str,
    dry_run: bool,
    passed: bool,
    result: Mapping[str, Any],
    reasons: list[str] | None = None,
) -> Path:
    path = gate_path(paths, mode)
    payload = {
        "mode": mode,
        "dryRun": bool(dry_run),
        "passed": bool(passed),
        "reasons": list(reasons or []),
        "updatedAt": now_utc(),
        "result": dict(result),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_run_gate(paths: PipelinePaths, mode: str) -> dict[str, Any] | None:
    path = gate_path(paths, mode)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def missing_full_run_gates(paths: PipelinePaths) -> list[str]:
    missing: list[str] = []
    for mode in REQUIRED_BEFORE_FULL:
        gate = read_run_gate(paths, mode)
        if not gate or not gate.get("passed") or gate.get("dryRun"):
            missing.append(mode)
    return missing


def assert_full_run_allowed(paths: PipelinePaths) -> None:
    missing = missing_full_run_gates(paths)
    if missing:
        raise RuntimeError(
            "Refusing full 720-image run until real smoke and pilot run gates pass. "
            f"Missing or dry-run gates: {', '.join(missing)}."
        )


def _count(mapping: Mapping[str, Any], key: str) -> int:
    try:
        return int(mapping.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _nested_count(value: Any, key: str) -> int:
    if isinstance(value, Mapping):
        total = _count(value, key)
        for child in value.values():
            total += _nested_count(child, key)
        return total
    if isinstance(value, list):
        return sum(_nested_count(child, key) for child in value)
    return 0


def evaluate_run_gate_result(result: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if bool(result.get("dryRun")):
        reasons.append("dry_run_gate")

    generation = result.get("generation") if isinstance(result.get("generation"), Mapping) else {}
    selected = _count(generation, "selected")
    completed = _count(generation, "completed")
    skipped = _count(generation, "skipped")
    if selected <= 0:
        reasons.append("generation_selected_zero")
    if _count(generation, "failed") > 0:
        reasons.append("generation_failed")
    if _count(generation, "waiting_reference") > 0:
        reasons.append("generation_waiting_reference")
    if _count(generation, "dry_run") > 0 and not bool(result.get("dryRun")):
        reasons.append("generation_dry_run_assets")
    if selected > 0 and completed + skipped < selected and not bool(result.get("dryRun")):
        reasons.append("generation_incomplete")

    qa = result.get("qa") if isinstance(result.get("qa"), Mapping) else {}
    if not qa:
        reasons.append("qa_skipped")
    else:
        if _nested_count(qa, "missing") > 0:
            reasons.append("qa_missing")
        if _nested_count(qa, "rejected") > 0:
            reasons.append("qa_rejected")
        if _nested_count(qa, "needs_manual_review") > 0 or _nested_count(qa, "needs_review") > 0:
            reasons.append("qa_needs_manual_review")

    summary = result.get("summary") if isinstance(result.get("summary"), Mapping) else {}
    if _count(summary, "missingCount") > 0:
        reasons.append("summary_missing_assets")

    return not reasons, reasons
