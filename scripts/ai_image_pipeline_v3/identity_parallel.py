from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .codex_imagegen import build_pending_payload, queue_path, read_pending
from .config import SHOT_ORDER, now_utc, pipeline_paths, read_jsonl, to_portable_path, write_jsonl
from .manifest import load_generation_manifest, manifest_path, write_generation_outputs
from .one_asset_transaction import FORBIDDEN_CHILD_RELATIVE_PATHS


IDENTITY_RECEIPT_SCHEMA_VERSION = "seolleyeon_identity_transaction_v1"
IDENTITY_ASSET_RECEIPT_SCHEMA_VERSION = "seolleyeon_identity_asset_transaction_v1"
IDENTITY_LEASE_SCHEMA_VERSION = "seolleyeon_identity_lease_v1"
PENDING_ASSET_SCHEMA_VERSION = "seolleyeon_per_asset_pending_imagegen_v1"
PARENT_RUN_SCHEMA_VERSION = "seolleyeon_identity_parallel_run_v1"

DEPENDENT_SHOTS = {"silhouette_card", "vibe_card"}
DEFAULT_WORKERS = 3
DEFAULT_LEASE_TTL_SEC = 30 * 60
ASSET_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

FORBIDDEN_GLOBAL_RELATIVE_PATHS = tuple(
    dict.fromkeys(
        (
            "ai_image/manifests/generation_manifest.jsonl",
            "ai_image/manifests/imagegen_queue.jsonl",
            "ai_image/manifests/current_chunk_state.json",
            "ai_image/manifests/current_chunk_plan.json",
            "ai_image/manifests/approved_identity_manifest.jsonl",
            "ai_image/manifests/asset_qa_manifest.jsonl",
            "ai_image/manifests/identity_qa_manifest.jsonl",
            "ai_image/reports/latest_distribution_audit.json",
            "ai_image/reports/distribution_audit.json",
            *FORBIDDEN_CHILD_RELATIVE_PATHS,
        )
    )
)


class IdentityParallelError(RuntimeError):
    pass


class IdentityLeaseError(IdentityParallelError):
    pass


@dataclass(frozen=True)
class IdentityWorkerConfig:
    root: Path
    identity_id: str
    run_id: str
    worker_id: str
    fixture: bool = False
    fixture_fail_shot: str = ""
    max_attempts: int = 1
    lease_ttl_sec: int = DEFAULT_LEASE_TTL_SEC
    require_existing_lease: bool = False


@dataclass(frozen=True)
class IdentityParallelConfig:
    root: Path
    run_id: str
    workers: int = DEFAULT_WORKERS
    fixture: bool = False
    fixture_fail_shot: str = ""
    max_identities: int = 0
    max_attempts: int = 1
    lease_ttl_sec: int = DEFAULT_LEASE_TTL_SEC


def _root(root: Path | str | None = None) -> Path:
    return pipeline_paths(root).root


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    tmp.replace(path)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n")


def per_asset_pending_dir(root: Path | str | None = None) -> Path:
    return pipeline_paths(root).manifests / "pending"


def per_asset_pending_path(root: Path | str | None, asset_id: str) -> Path:
    value = str(asset_id or "")
    if not value or not ASSET_ID_PATTERN.fullmatch(value) or ".." in value:
        raise IdentityParallelError(f"Invalid asset_id for per-asset pending path: {asset_id!r}")
    pending_dir = per_asset_pending_dir(root).resolve()
    path = (pending_dir / f"{value}.json").resolve()
    try:
        path.relative_to(pending_dir)
    except ValueError as exc:
        raise IdentityParallelError(f"Per-asset pending path escaped pending directory: {asset_id!r}") from exc
    return path


def identity_lease_dir(root: Path | str | None = None) -> Path:
    return pipeline_paths(root).manifests / "leases"


def identity_lease_path(root: Path | str | None, identity_id: str) -> Path:
    return identity_lease_dir(root) / f"{identity_id}.json"


def identity_parallel_report_dir(root: Path | str | None, run_id: str) -> Path:
    return pipeline_paths(root).reports / "identity_parallel" / run_id


def asset_receipt_path(root: Path | str | None, run_id: str, asset_id: str, attempt: int) -> Path:
    return identity_parallel_report_dir(root, run_id) / "receipts" / "assets" / f"{asset_id}_attempt{attempt}.json"


def identity_receipt_path(root: Path | str | None, run_id: str, identity_id: str) -> Path:
    return identity_parallel_report_dir(root, run_id) / "receipts" / "identities" / f"{identity_id}.json"


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_forbidden_globals(root: Path | str | None = None) -> dict[str, dict[str, Any]]:
    base = _root(root)
    snapshot: dict[str, dict[str, Any]] = {}
    for relative in FORBIDDEN_GLOBAL_RELATIVE_PATHS:
        path = base / relative
        key = to_portable_path(path)
        snapshot[key] = {
            "exists": path.exists(),
            "sha256": _sha256(path),
            "size": path.stat().st_size if path.exists() and path.is_file() else None,
            "content": path.read_bytes() if path.exists() and path.is_file() else None,
        }
    return snapshot


def detect_forbidden_global_mutations(snapshot: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for path_text, before in snapshot.items():
        path = Path(path_text)
        after_exists = path.exists()
        after_sha = _sha256(path)
        if bool(before.get("exists")) != after_exists or before.get("sha256") != after_sha:
            violations.append(
                {
                    "path": path_text,
                    "beforeExists": bool(before.get("exists")),
                    "afterExists": after_exists,
                    "beforeSha256": before.get("sha256"),
                    "afterSha256": after_sha,
                }
            )
    return violations


def restore_forbidden_globals(snapshot: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    restored: list[dict[str, Any]] = []
    for path_text, before in snapshot.items():
        path = Path(path_text)
        before_exists = bool(before.get("exists"))
        before_content = before.get("content")
        if before_exists:
            if not isinstance(before_content, bytes):
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f"{path.name}.{os.getpid()}.restore.tmp")
            tmp.write_bytes(before_content)
            tmp.replace(path)
            restored.append({"path": path_text, "action": "restored"})
        elif path.exists():
            if not path.is_file():
                raise IdentityParallelError(f"Refusing to remove non-file forbidden path created by child: {path}")
            path.unlink()
            restored.append({"path": path_text, "action": "removed"})
    return restored


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def lease_is_stale(lease: Mapping[str, Any], *, now: datetime | None = None) -> bool:
    if not lease:
        return False
    if str(lease.get("status") or "") not in {"active", "heartbeat"}:
        return False
    expires = _parse_time(lease.get("expires_at") or lease.get("expiresAt"))
    return bool(expires and expires <= (now or _utc_now()))


def acquire_identity_lease(
    *,
    root: Path | str | None,
    identity_id: str,
    run_id: str,
    worker_id: str,
    ttl_sec: int = DEFAULT_LEASE_TTL_SEC,
    reclaim_stale: bool = False,
) -> dict[str, Any]:
    path = identity_lease_path(root, identity_id)
    existing = _read_json(path)
    if existing and str(existing.get("status") or "") in {"active", "heartbeat"}:
        if not (reclaim_stale and lease_is_stale(existing)):
            raise IdentityLeaseError(f"identity lease already active: {identity_id}")
    now = _utc_now()
    payload = {
        "schemaVersion": IDENTITY_LEASE_SCHEMA_VERSION,
        "identity_id": identity_id,
        "identityId": identity_id,
        "run_id": run_id,
        "runId": run_id,
        "worker_id": worker_id,
        "workerId": worker_id,
        "acquired_at": now.isoformat(),
        "acquiredAt": now.isoformat(),
        "heartbeat_at": now.isoformat(),
        "heartbeatAt": now.isoformat(),
        "status": "active",
        "expires_at": (now + timedelta(seconds=max(1, ttl_sec))).isoformat(),
        "expiresAt": (now + timedelta(seconds=max(1, ttl_sec))).isoformat(),
        "owner_command": "bounded-identity-worker",
        "ownerCommand": "bounded-identity-worker",
    }
    _atomic_write_json(path, payload)
    return payload


def verify_identity_lease(root: Path | str | None, identity_id: str, run_id: str, worker_id: str) -> dict[str, Any]:
    lease = _read_json(identity_lease_path(root, identity_id))
    if not lease:
        raise IdentityLeaseError(f"identity lease missing: {identity_id}")
    if str(lease.get("run_id") or lease.get("runId") or "") != run_id:
        raise IdentityLeaseError("identity lease run_id mismatch")
    if str(lease.get("worker_id") or lease.get("workerId") or "") != worker_id:
        raise IdentityLeaseError("identity lease worker_id mismatch")
    if lease_is_stale(lease):
        raise IdentityLeaseError("identity lease is stale")
    return lease


def heartbeat_identity_lease(root: Path | str | None, identity_id: str, run_id: str, worker_id: str, ttl_sec: int) -> dict[str, Any]:
    lease = verify_identity_lease(root, identity_id, run_id, worker_id)
    now = _utc_now()
    lease.update(
        {
            "status": "heartbeat",
            "heartbeat_at": now.isoformat(),
            "heartbeatAt": now.isoformat(),
            "expires_at": (now + timedelta(seconds=max(1, ttl_sec))).isoformat(),
            "expiresAt": (now + timedelta(seconds=max(1, ttl_sec))).isoformat(),
        }
    )
    _atomic_write_json(identity_lease_path(root, identity_id), lease)
    return lease


def mark_identity_lease(root: Path | str | None, identity_id: str, *, status: str, reason: str = "") -> dict[str, Any]:
    path = identity_lease_path(root, identity_id)
    lease = _read_json(path)
    if not lease:
        return {}
    lease.update({"status": status, "finished_at": now_utc(), "finishedAt": now_utc(), "reason": reason})
    _atomic_write_json(path, lease)
    return lease


def reclaim_stale_leases(root: Path | str | None = None) -> list[dict[str, Any]]:
    reclaimed: list[dict[str, Any]] = []
    for path in sorted(identity_lease_dir(root).glob("*.json")):
        lease = _read_json(path)
        if lease_is_stale(lease):
            lease.update({"status": "stale_reclaimed", "reclaimed_at": now_utc(), "reclaimedAt": now_utc()})
            _atomic_write_json(path, lease)
            reclaimed.append(lease)
    return reclaimed


def _profile_rows(root: Path | str | None, identity_id: str) -> list[dict[str, Any]]:
    rows = [row for row in load_generation_manifest(pipeline_paths(root)) if str(row.get("profileId") or "") == identity_id]
    by_shot = {str(row.get("shotType") or ""): dict(row) for row in rows}
    ordered = [by_shot[shot] for shot in SHOT_ORDER if shot in by_shot]
    if not ordered:
        raise IdentityParallelError(f"No generation manifest rows found for identity: {identity_id}")
    return ordered


def planned_identity_ids(root: Path | str | None = None, *, limit: int = 0) -> list[str]:
    plan_path = pipeline_paths(root).manifests / "current_chunk_plan.json"
    ids: list[str] = []
    if plan_path.exists():
        plan = _read_json(plan_path)
        for identity in plan.get("identities", []) or []:
            if isinstance(identity, Mapping) and identity.get("profileId"):
                ids.append(str(identity["profileId"]))
    if not ids:
        for row in load_generation_manifest(pipeline_paths(root)):
            profile_id = str(row.get("profileId") or "")
            if profile_id and profile_id not in ids:
                ids.append(profile_id)
    return ids[:limit] if limit and limit > 0 else ids


def _fixture_png_bytes() -> bytes:
    try:
        from PIL import Image
        from io import BytesIO
    except ImportError as exc:  # pragma: no cover - project tests already require Pillow.
        raise IdentityParallelError("Pillow is required for identity fixture image creation.") from exc
    buffer = BytesIO()
    Image.new("RGB", (512, 768), (36, 64, 92)).save(buffer, format="PNG")
    return buffer.getvalue()


def _write_fixture_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise IdentityParallelError(f"Refusing to overwrite existing fixture image without explicit cleanup: {path}")
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_bytes(_fixture_png_bytes())
    tmp.replace(path)


def _asset_receipt(
    *,
    config: IdentityWorkerConfig,
    row: Mapping[str, Any],
    pending_path_value: Path,
    status: str,
    attempt: int,
    raw_path: Path | None = None,
    final_path: Path | None = None,
    reference_image_path: str = "",
    error: str = "",
) -> dict[str, Any]:
    asset_id = str(row.get("assetId") or f"{config.identity_id}__{row.get('shotType')}__v001")
    return {
        "schemaVersion": IDENTITY_ASSET_RECEIPT_SCHEMA_VERSION,
        "run_id": config.run_id,
        "runId": config.run_id,
        "identity_id": config.identity_id,
        "identityId": config.identity_id,
        "profileId": config.identity_id,
        "worker_id": config.worker_id,
        "workerId": config.worker_id,
        "assetId": asset_id,
        "shotType": str(row.get("shotType") or ""),
        "attempt": int(attempt),
        "status": status,
        "pendingPath": to_portable_path(pending_path_value) if pending_path_value else "",
        "rawPath": to_portable_path(raw_path) if raw_path else "",
        "finalPath": to_portable_path(final_path) if final_path else "",
        "referenceAssetId": str(row.get("referenceAssetId") or ""),
        "referenceImagePath": reference_image_path,
        "startedAt": now_utc(),
        "finishedAt": now_utc(),
        "fixture": bool(config.fixture),
        "error": error,
    }


def _write_asset_receipt(root: Path | str | None, receipt: Mapping[str, Any]) -> Path:
    path = asset_receipt_path(root, str(receipt["run_id"]), str(receipt["assetId"]), int(receipt["attempt"]))
    _atomic_write_json(path, receipt)
    return path


def _write_identity_receipt(root: Path | str | None, config: IdentityWorkerConfig, assets: Sequence[Mapping[str, Any]], status: str, error: str = "") -> Path:
    payload = {
        "schemaVersion": IDENTITY_RECEIPT_SCHEMA_VERSION,
        "run_id": config.run_id,
        "runId": config.run_id,
        "identity_id": config.identity_id,
        "identityId": config.identity_id,
        "profileId": config.identity_id,
        "worker_id": config.worker_id,
        "workerId": config.worker_id,
        "status": status,
        "assetReceipts": [dict(item) for item in assets],
        "assetStatus": {str(item.get("assetId")): str(item.get("status")) for item in assets},
        "startedAt": assets[0].get("startedAt") if assets else now_utc(),
        "finishedAt": now_utc(),
        "error": error,
    }
    path = identity_receipt_path(root, config.run_id, config.identity_id)
    _atomic_write_json(path, payload)
    return path


def _pending_for_asset(config: IdentityWorkerConfig, row: Mapping[str, Any], attempt: int, out_pending: Path, reference_path: str = "") -> dict[str, Any]:
    paths = pipeline_paths(config.root)
    payload = build_pending_payload(
        paths_root=config.root,
        row=row,
        attempt=attempt,
        queue_file=queue_path(config.root),
        manifest_file=manifest_path(paths),
        out_pending=out_pending,
    )
    payload.update(
        {
            "schemaVersion": PENDING_ASSET_SCHEMA_VERSION,
            "runId": config.run_id,
            "identityId": config.identity_id,
            "workerId": config.worker_id,
            "perAssetPending": True,
        }
    )
    if reference_path:
        payload["referenceImagePath"] = reference_path
    return payload


def run_identity_worker(config: IdentityWorkerConfig) -> dict[str, Any]:
    if not config.fixture:
        raise IdentityParallelError("bounded-identity-worker currently supports fixture/mock mode only.")
    if not config.require_existing_lease:
        try:
            acquire_identity_lease(
                root=config.root,
                identity_id=config.identity_id,
                run_id=config.run_id,
                worker_id=config.worker_id,
                ttl_sec=config.lease_ttl_sec,
                reclaim_stale=False,
            )
        except IdentityLeaseError:
            verify_identity_lease(config.root, config.identity_id, config.run_id, config.worker_id)
    else:
        verify_identity_lease(config.root, config.identity_id, config.run_id, config.worker_id)

    rows_by_shot = {str(row.get("shotType") or ""): row for row in _profile_rows(config.root, config.identity_id)}
    receipts: list[dict[str, Any]] = []
    face_final_path = ""
    identity_status = "complete"
    identity_error = ""

    for shot in SHOT_ORDER:
        row = dict(rows_by_shot.get(shot) or {})
        if not row:
            continue
        heartbeat_identity_lease(config.root, config.identity_id, config.run_id, config.worker_id, config.lease_ttl_sec)
        asset_id = str(row["assetId"])
        pending_file = per_asset_pending_path(config.root, asset_id)
        attempt = 1
        if shot in DEPENDENT_SHOTS and not face_final_path:
            receipt = _asset_receipt(
                config=config,
                row=row,
                pending_path_value=pending_file,
                status="skipped",
                attempt=attempt,
                reference_image_path="",
                error="blocked_by_face_card_failure",
            )
            _write_asset_receipt(config.root, receipt)
            receipts.append(receipt)
            identity_status = "failed"
            continue

        pending_payload = _pending_for_asset(config, row, attempt, pending_file, reference_path=face_final_path if shot in DEPENDENT_SHOTS else "")
        _atomic_write_json(pending_file, pending_payload)
        if config.fixture_fail_shot == shot:
            pending_payload.update({"status": "failed", "resolved": True, "error": "fixture_failure", "resolvedAt": now_utc()})
            _atomic_write_json(pending_file, pending_payload)
            receipt = _asset_receipt(
                config=config,
                row=row,
                pending_path_value=pending_file,
                status="failed",
                attempt=attempt,
                reference_image_path=face_final_path if shot in DEPENDENT_SHOTS else "",
                error="fixture_failure",
            )
            _write_asset_receipt(config.root, receipt)
            receipts.append(receipt)
            identity_status = "failed"
            identity_error = f"{shot}_fixture_failure"
            if shot == "face_card":
                continue
            continue

        raw_path = Path(str(pending_payload["expectedRawPath"]))
        final_path = Path(str(pending_payload["expectedFinalPath"]))
        try:
            _write_fixture_image(raw_path)
            _write_fixture_image(final_path)
        except IdentityParallelError as exc:
            pending_payload.update({"status": "failed", "resolved": True, "error": str(exc), "resolvedAt": now_utc()})
            _atomic_write_json(pending_file, pending_payload)
            receipt = _asset_receipt(
                config=config,
                row=row,
                pending_path_value=pending_file,
                status="failed",
                attempt=attempt,
                reference_image_path=face_final_path if shot in DEPENDENT_SHOTS else "",
                error=str(exc),
            )
            _write_asset_receipt(config.root, receipt)
            receipts.append(receipt)
            identity_status = "failed"
            identity_error = str(exc)
            if shot == "face_card":
                continue
            continue
        pending_payload.update(
            {
                "status": "resolved",
                "resolved": True,
                "recoveryStatus": "fixture_generated",
                "rawPath": to_portable_path(raw_path),
                "finalPath": to_portable_path(final_path),
                "resolvedAt": now_utc(),
                "resolvedBy": "bounded_identity_worker_fixture",
            }
        )
        _atomic_write_json(pending_file, pending_payload)
        if shot == "face_card":
            face_final_path = to_portable_path(final_path)
        receipt = _asset_receipt(
            config=config,
            row=row,
            pending_path_value=pending_file,
            status="succeeded",
            attempt=attempt,
            raw_path=raw_path,
            final_path=final_path,
            reference_image_path=face_final_path if shot in DEPENDENT_SHOTS else "",
        )
        _write_asset_receipt(config.root, receipt)
        receipts.append(receipt)

    if not receipts or any(str(item.get("status")) == "failed" for item in receipts):
        identity_status = "failed"
    elif any(str(item.get("status")) == "skipped" for item in receipts):
        identity_status = "partial"
    identity_receipt = _write_identity_receipt(config.root, config, receipts, identity_status, identity_error)
    return {
        "status": identity_status,
        "identityId": config.identity_id,
        "runId": config.run_id,
        "assetReceipts": receipts,
        "identityReceiptPath": to_portable_path(identity_receipt),
    }


def _state_path(root: Path | str | None) -> Path:
    return pipeline_paths(root).manifests / "current_chunk_state.json"


def apply_identity_receipts_to_global_state(root: Path | str | None, identity_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    paths = pipeline_paths(root)
    rows = load_generation_manifest(paths)
    rows_by_asset = {str(row.get("assetId") or ""): dict(row) for row in rows}
    state_path = _state_path(root)
    state = _read_json(state_path) if state_path.exists() else {
        "schemaVersion": "seolleyeon_identity_parallel_state_v1",
        "status": "identity_parallel_running",
        "assetStates": {},
        "identityStates": {},
    }
    asset_states = dict(state.get("assetStates") or {})
    identity_states = dict(state.get("identityStates") or {})
    applied_assets = 0
    for result in identity_results:
        identity_id = str(result.get("identityId") or result.get("identity_id") or "")
        result_status = str(result.get("status") or "")
        identity_states[identity_id] = result_status
        for receipt in result.get("assetReceipts", []) or []:
            if not isinstance(receipt, Mapping):
                continue
            asset_id = str(receipt.get("assetId") or "")
            status = str(receipt.get("status") or "")
            mapped = {"succeeded": "file_qa_passed", "failed": "failed", "skipped": "skipped"}.get(status, status)
            asset_states[asset_id] = mapped
            if asset_id in rows_by_asset:
                row = rows_by_asset[asset_id]
                row.update(
                    {
                        "status": "file_needs_review" if status == "succeeded" else mapped,
                        "attempt": int(receipt.get("attempt") or row.get("attempt") or 0),
                        "attemptCount": int(receipt.get("attempt") or row.get("attemptCount") or 0),
                        "pendingPath": str(receipt.get("pendingPath") or row.get("pendingPath") or ""),
                        "localPath": str(receipt.get("rawPath") or row.get("localPath") or ""),
                        "rawPath": str(receipt.get("rawPath") or row.get("rawPath") or ""),
                        "finalPath": str(receipt.get("finalPath") or row.get("finalPath") or ""),
                        "resolvedReferencePath": str(receipt.get("referenceImagePath") or row.get("resolvedReferencePath") or ""),
                        "updatedAt": now_utc(),
                        "error": str(receipt.get("error") or ""),
                    }
                )
                rows_by_asset[asset_id] = row
                applied_assets += 1
    if rows_by_asset:
        write_generation_outputs(paths, list(rows_by_asset.values()))
    state.update(
        {
            "status": "identity_parallel_complete",
            "assetStates": asset_states,
            "identityStates": identity_states,
            "updatedAt": now_utc(),
        }
    )
    _atomic_write_json(state_path, state)
    return {"updatedAssets": applied_assets, "statePath": to_portable_path(state_path)}


def run_identity_parallel(
    config: IdentityParallelConfig,
    *,
    worker_func: Callable[[IdentityWorkerConfig], Mapping[str, Any]] = run_identity_worker,
) -> dict[str, Any]:
    if not config.fixture:
        raise IdentityParallelError("bounded-identity-parallel-run currently supports fixture/mock mode only.")
    paths = pipeline_paths(config.root)
    identities = planned_identity_ids(config.root, limit=config.max_identities)
    selected: list[str] = []
    reclaimed = reclaim_stale_leases(config.root)
    for identity_id in identities:
        worker_id = f"{config.run_id}-{identity_id}-{os.getpid()}"
        try:
            acquire_identity_lease(
                root=config.root,
                identity_id=identity_id,
                run_id=config.run_id,
                worker_id=worker_id,
                ttl_sec=config.lease_ttl_sec,
                reclaim_stale=True,
            )
        except IdentityLeaseError:
            continue
        selected.append(identity_id)
    results: list[dict[str, Any]] = []
    violations_by_identity: dict[str, list[dict[str, Any]]] = {}
    restored_forbidden_globals: dict[str, list[dict[str, Any]]] = {}

    def run_one(identity_id: str) -> dict[str, Any]:
        worker_id = f"{config.run_id}-{identity_id}-{os.getpid()}"
        lease = _read_json(identity_lease_path(config.root, identity_id))
        worker = IdentityWorkerConfig(
            root=config.root,
            identity_id=identity_id,
            run_id=config.run_id,
            worker_id=str(lease.get("worker_id") or lease.get("workerId") or worker_id),
            fixture=True,
            fixture_fail_shot=config.fixture_fail_shot,
            max_attempts=config.max_attempts,
            lease_ttl_sec=config.lease_ttl_sec,
            require_existing_lease=True,
        )
        before = snapshot_forbidden_globals(config.root)
        try:
            result = dict(worker_func(worker))
        except Exception as exc:  # noqa: BLE001 - parent must preserve failed worker evidence.
            error = f"{type(exc).__name__}: {exc}"
            identity_receipt = _write_identity_receipt(config.root, worker, [], "failed", error)
            mark_identity_lease(config.root, identity_id, status="failed", reason="child_worker_exception")
            return {
                "status": "failed",
                "identityId": identity_id,
                "assetReceipts": [],
                "identityReceiptPath": to_portable_path(identity_receipt),
                "error": error,
            }
        violations = detect_forbidden_global_mutations(before)
        if violations:
            violations_by_identity[identity_id] = violations
            restored_forbidden_globals[identity_id] = restore_forbidden_globals(before)
            mark_identity_lease(config.root, identity_id, status="failed", reason="child_forbidden_global_mutation")
            return {"status": "failed", "identityId": identity_id, "assetReceipts": [], "error": "child_forbidden_global_mutation"}
        mark_identity_lease(config.root, identity_id, status=str(result.get("status") or "complete"))
        return result

    with ThreadPoolExecutor(max_workers=max(1, int(config.workers))) as executor:
        futures = {executor.submit(run_one, identity_id): identity_id for identity_id in selected}
        for future in as_completed(futures):
            identity_id = futures[future]
            try:
                results.append(dict(future.result()))
            except Exception as exc:  # noqa: BLE001 - keep parent report resumable even after coordinator bugs.
                error = f"{type(exc).__name__}: {exc}"
                mark_identity_lease(config.root, identity_id, status="failed", reason="parent_future_exception")
                results.append({"status": "failed", "identityId": identity_id, "assetReceipts": [], "error": error})

    parent_update = (
        {"updatedAssets": 0, "skipped": "forbidden_global_mutation"}
        if violations_by_identity
        else apply_identity_receipts_to_global_state(config.root, results) if results else {"updatedAssets": 0}
    )
    run_report = {
        "schemaVersion": PARENT_RUN_SCHEMA_VERSION,
        "runId": config.run_id,
        "status": "failed" if violations_by_identity or any(str(result.get("status") or "") == "failed" for result in results) else "complete",
        "workers": int(config.workers),
        "selectedIdentities": selected,
        "identityResults": results,
        "reclaimedStaleLeases": reclaimed,
        "forbiddenGlobalMutations": violations_by_identity,
        "restoredForbiddenGlobals": restored_forbidden_globals,
        "parentUpdate": parent_update,
        "pendingDir": to_portable_path(per_asset_pending_dir(config.root)),
        "leaseDir": to_portable_path(identity_lease_dir(config.root)),
        "updatedAt": now_utc(),
    }
    report_path = identity_parallel_report_dir(config.root, config.run_id) / "run.json"
    _atomic_write_json(report_path, run_report)
    run_report["reportPath"] = to_portable_path(report_path)
    return run_report


def identity_parallel_status(root: Path | str | None = None, *, asset_id: str = "") -> dict[str, Any]:
    pending_files = sorted(per_asset_pending_dir(root).glob("*.json"))
    leases = [_read_json(path) for path in sorted(identity_lease_dir(root).glob("*.json"))]
    if asset_id:
        path = per_asset_pending_path(root, asset_id)
        payload = read_pending(path)
        return {
            "assetId": asset_id,
            "pendingPath": to_portable_path(path),
            "exists": path.exists(),
            "pending": payload or {},
            "legacy": False,
        }
    unresolved = []
    resolved = []
    for path in pending_files:
        payload = read_pending(path) or {}
        if payload.get("resolved") or str(payload.get("status") or "") in {"resolved", "cleared"}:
            resolved.append(to_portable_path(path))
        else:
            unresolved.append(to_portable_path(path))
    return {
        "schemaVersion": "seolleyeon_identity_parallel_status_v1",
        "pendingDir": to_portable_path(per_asset_pending_dir(root)),
        "perAssetPendingCount": len(pending_files),
        "unresolvedPendingFiles": unresolved,
        "resolvedPendingFiles": resolved,
        "activeLeases": [lease for lease in leases if str(lease.get("status") or "") in {"active", "heartbeat"}],
        "staleLeases": [lease for lease in leases if lease_is_stale(lease)],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fixture-safe identity-level parallel image pipeline helpers.")
    parser.add_argument("command", choices=["worker", "parallel-run", "status"])
    parser.add_argument("--root", default=None)
    parser.add_argument("--identity-id", "--identity_id", dest="identity_id", default="")
    parser.add_argument("--run-id", "--run_id", dest="run_id", default="")
    parser.add_argument("--worker-id", "--worker_id", dest="worker_id", default="")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--max-identities", "--max_identities", dest="max_identities", type=int, default=0)
    parser.add_argument("--fixture", action="store_true", default=False)
    parser.add_argument("--fixture-fail-shot", "--fixture_fail_shot", dest="fixture_fail_shot", default="")
    parser.add_argument("--asset-id", "--asset_id", dest="asset_id", default="")
    return parser


def _default_run_id() -> str:
    return "identity_parallel_" + now_utc().replace(":", "").replace("+", "Z")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    run_id = args.run_id or _default_run_id()
    if args.command in {"worker", "parallel-run"} and not args.fixture:
        raise SystemExit("--fixture is required; identity parallel execution is currently fixture/mock only.")
    if args.command == "worker":
        if not args.identity_id:
            raise SystemExit("--identity-id is required")
        result = run_identity_worker(
            IdentityWorkerConfig(
                root=root,
                identity_id=args.identity_id,
                run_id=run_id,
                worker_id=args.worker_id or f"{run_id}-{args.identity_id}-{os.getpid()}",
                fixture=True,
                fixture_fail_shot=args.fixture_fail_shot,
            )
        )
    elif args.command == "parallel-run":
        result = run_identity_parallel(
            IdentityParallelConfig(
                root=root,
                run_id=run_id,
                workers=max(1, int(args.workers)),
                fixture=True,
                max_identities=max(0, int(args.max_identities)),
                fixture_fail_shot=args.fixture_fail_shot,
            )
        )
    else:
        result = identity_parallel_status(root, asset_id=args.asset_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status") or "") not in {"failed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
