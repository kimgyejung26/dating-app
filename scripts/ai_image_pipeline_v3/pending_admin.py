from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .codex_imagegen import pending_path, read_pending, write_pending
from .config import now_utc, pipeline_paths, read_jsonl, to_portable_path, write_jsonl
from .pending_state import (
    pending_is_resolved,
    pending_is_unresolved,
    pending_requires_recovery,
    pending_status,
    pending_unresolved_reason,
)


PENDING_RESOLUTION_FILENAME = "pending_resolution_manifest.jsonl"
CANCELLED_PENDING_PREFIX = "cancelled"


def pending_resolution_path(root: Path | str | None = None) -> Path:
    return pipeline_paths(root).manifests / PENDING_RESOLUTION_FILENAME


def _safe_path(value: Any) -> Path | None:
    if not value:
        return None
    try:
        return Path(str(value)).resolve()
    except OSError:
        return None


def _path_report(value: Any) -> dict[str, Any]:
    path = _safe_path(value)
    if path is None:
        return {"path": str(value or ""), "exists": False, "size": 0}
    try:
        return {"path": to_portable_path(path), "exists": path.exists(), "size": path.stat().st_size if path.exists() else 0}
    except OSError:
        return {"path": to_portable_path(path), "exists": False, "size": 0}


def pending_status_report(*, root: Path | str | None = None, pending: Path | str | None = None) -> dict[str, Any]:
    pending_file = Path(pending).resolve() if pending else pending_path(root)
    payload = read_pending(pending_file)
    if not payload:
        return {
            "exists": pending_file.exists(),
            "pendingPath": to_portable_path(pending_file),
            "status": "",
            "resolved": True,
            "unresolved": False,
            "requiresRecovery": False,
            "reason": "",
            "assetId": "",
            "expectedRawPath": _path_report(""),
            "expectedFinalPath": _path_report(""),
        }
    return {
        "exists": True,
        "pendingPath": to_portable_path(pending_file),
        "status": pending_status(payload),
        "resolved": pending_is_resolved(payload),
        "unresolved": pending_is_unresolved(payload),
        "requiresRecovery": pending_requires_recovery(payload),
        "reason": pending_unresolved_reason(payload) if pending_is_unresolved(payload) else "",
        "assetId": str(payload.get("assetId") or ""),
        "profileId": str(payload.get("profileId") or ""),
        "shotType": str(payload.get("shotType") or ""),
        "attempt": int(payload.get("attempt") or 0),
        "expectedRawPath": _path_report(payload.get("expectedRawPath")),
        "expectedFinalPath": _path_report(payload.get("expectedFinalPath")),
    }


def _append_resolution(root: Path | str | None, row: Mapping[str, Any]) -> None:
    path = pending_resolution_path(root)
    rows = read_jsonl(path)
    rows.append(dict(row))
    write_jsonl(path, rows)


def _resolve_pending(
    *,
    root: Path | str | None,
    pending: Path | str | None,
    reason: str,
    action: str,
    require_cancelled: bool,
) -> dict[str, Any]:
    pending_file = Path(pending).resolve() if pending else pending_path(root)
    payload = read_pending(pending_file)
    if not payload:
        raise FileNotFoundError(f"No pending-imagegen checkpoint found: {pending_file}")
    if pending_is_resolved(payload):
        report = pending_status_report(root=root, pending=pending_file)
        report["action"] = "already_resolved"
        return report
    if pending_requires_recovery(payload):
        raise RuntimeError(
            "Active pending imagegen checkpoints must be recovered, not manually cleared. "
            f"Run recover first for assetId={payload.get('assetId') or ''}."
        )
    status = pending_status(payload)
    if require_cancelled and not status.startswith(CANCELLED_PENDING_PREFIX):
        raise RuntimeError(f"Refusing to clear non-cancelled pending checkpoint with status={status!r}.")

    before = pending_status_report(root=root, pending=pending_file)
    resolved = dict(payload)
    resolved.update(
        {
            "status": "cleared" if require_cancelled else "resolved",
            "resolved": True,
            "resolvedAt": now_utc(),
            "resolveReason": reason,
            "resolutionMode": action,
        }
    )
    write_pending(pending_file, resolved)
    after = pending_status_report(root=root, pending=pending_file)
    _append_resolution(
        root,
        {
            "assetId": str(payload.get("assetId") or ""),
            "profileId": str(payload.get("profileId") or ""),
            "shotType": str(payload.get("shotType") or ""),
            "attempt": int(payload.get("attempt") or 0),
            "beforeStatus": before["status"],
            "afterStatus": after["status"],
            "reason": reason,
            "action": action,
            "expectedRawExists": bool(before["expectedRawPath"]["exists"]),
            "expectedFinalExists": bool(before["expectedFinalPath"]["exists"]),
            "resolvedAt": resolved["resolvedAt"],
        },
    )
    after["action"] = action
    return after


def resolve_pending(
    *,
    root: Path | str | None = None,
    pending: Path | str | None = None,
    reason: str = "manual_resolution",
) -> dict[str, Any]:
    return _resolve_pending(root=root, pending=pending, reason=reason, action="manual_resolve", require_cancelled=False)


def clear_cancelled_pending(
    *,
    root: Path | str | None = None,
    pending: Path | str | None = None,
    reason: str = "cancelled_pending_clear",
) -> dict[str, Any]:
    return _resolve_pending(root=root, pending=pending, reason=reason, action="clear_cancelled", require_cancelled=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or manually resolve safe pending-imagegen checkpoint states.")
    parser.add_argument("command", choices=["status", "resolve", "clear-cancelled"])
    parser.add_argument("--root", default=None)
    parser.add_argument("--pending", default=None)
    parser.add_argument("--reason", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        result = pending_status_report(root=args.root, pending=args.pending)
    elif args.command == "resolve":
        result = resolve_pending(root=args.root, pending=args.pending, reason=args.reason or "manual_resolution")
    elif args.command == "clear-cancelled":
        result = clear_cancelled_pending(root=args.root, pending=args.pending, reason=args.reason or "cancelled_pending_clear")
    else:
        raise AssertionError(f"Unhandled command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
