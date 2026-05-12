from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .active_visual_verdict_runner import ActiveVisualConfig, discover_command_forms, run_active_visual_qa_all
from .bounded_batch_executor import (
    BoundedExecutorConfig,
    build_agent_args,
    build_one_asset_prompt,
    chunk_report_dir,
    current_plan_path,
    current_state_path,
    file_qa_single_asset,
    finalize_bounded_chunk,
    validate_chunk_plan,
    _append_event,
    _transition_asset,
    _transition_chunk,
    _transition_identity,
    _write_plan_and_state,
)
from .codex_imagegen import build_pending_payload, pending_path, recover_pending_imagegen, write_identity_manifest, write_imagegen_queue, write_pending
from .config import DEFAULT_CODEX_GENERATED_IMAGES_DIR, SHOT_ORDER, ensure_base_dirs, now_utc, pipeline_paths, prompt_hash, read_jsonl, to_portable_path, write_jsonl
from .contact_sheet import generate_chunk_contact_sheets, generate_grouped_contact_sheets, generate_identity_contact_sheets
from .distribution_audit import audit_distribution
from .manifest import enrich_asset, load_generation_manifest, manifest_path, write_generation_outputs
from .prompt_source import load_prompt_module


E2E_SCHEMA_VERSION = "seolleyeon_bounded_imagegen_e2e_smoke_v3"
E2E_ASSERTION = "This E2E validates one bounded chunk only and does not validate full dataset completion."
E2E_ENV_GUARD = "SEOLLEYEON_ALLOW_REAL_IMAGEGEN_E2E"
DEFAULT_LOGICAL_IDENTITY_ID = "e2e_identity_001"
DEFAULT_PROFILE_ID = "female_997"
DEFAULT_FACE_TYPE = "deer_like"
DEFAULT_LOOKS_LEVEL = 3.0
DEFAULT_LOOKS_BAND = "2.5-3.2"
DEPENDENT_SHOTS = {"silhouette_card", "vibe_card"}
REFERENCE_IMAGE_ARGS = {"image": "--image", "short_i": "-i"}

PROTECTED_RECOMMENDER_FILENAMES = (
    "seolleyeon_run_all.py",
    "seolleyeon_svd_train_export.py",
    "seolleyeon_knn_train_export.py",
    "seolleyeon_clip_train_export.py",
    "seolleyeon_clip_embedder.py",
    "seolleyeon_rrf_export.py",
    "seolleyeon_rec_common_v3.py",
)
PROTECTED_RECOMMENDER_DIRS = ("", "lib/ai_recommend_model")

STATEFUL_FILES = (
    "ai_image/manifests/generation_manifest.jsonl",
    "ai_image/manifests/imagegen_queue.jsonl",
    "ai_image/manifests/ai_profile_assets_v3.jsonl",
    "ai_image/manifests/ai_profile_specs_v3.jsonl",
    "ai_image/manifests/identity_manifest.jsonl",
    "ai_image/manifests/current_chunk_plan.json",
    "ai_image/manifests/current_chunk_state.json",
    "ai_image/manifests/pending-imagegen.json",
    "ai_image/manifests/completed_pending_imagegen.jsonl",
    "ai_image/manifests/asset_qa_manifest.jsonl",
    "ai_image/manifests/identity_qa_manifest.jsonl",
    "ai_image/manifests/approved_identity_manifest.jsonl",
    "ai_image/manifests/rejected_identity_manifest.jsonl",
    "ai_image/manifests/needs_review_identity_manifest.jsonl",
    "ai_image/manifests/manual_review_required.flag",
    "ai_image/reports/generation_status.csv",
    "ai_image/reports/distribution_report.csv",
    "ai_image/reports/distribution_audit.json",
    "ai_image/reports/latest_distribution_audit.json",
    "ai_image/reports/visual_verdict/asset_qa_latest.json",
    "ai_image/reports/visual_verdict/identity_qa_latest.json",
    "ai_image/reports/visual_verdict/distribution_audit_latest.json",
)


class E2EBoundedSmokeError(RuntimeError):
    def __init__(self, reason: str, message: str | None = None, details: Mapping[str, Any] | None = None):
        super().__init__(message or reason)
        self.reason = reason
        self.details = dict(details or {})


@dataclass(frozen=True)
class AgentReferenceForm:
    image_arg_mode: str


@dataclass
class E2EConfig:
    root: Path
    chunk_id: str
    agent_cmd: str | None = None
    identity_id: str = DEFAULT_LOGICAL_IDENTITY_ID
    profile_id: str = DEFAULT_PROFILE_ID
    keep_artifacts: bool = False
    no_restore: bool = False
    preflight_only: bool = False
    max_assets: int = 3

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "E2EConfig":
        root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
        return cls(
            root=root,
            chunk_id=args.chunk_id or default_e2e_chunk_id(),
            agent_cmd=args.agent_cmd,
            identity_id=args.identity_id or DEFAULT_LOGICAL_IDENTITY_ID,
            keep_artifacts=bool(args.keep_artifacts),
            no_restore=bool(args.no_restore),
            preflight_only=bool(args.preflight_only),
        )


@dataclass
class CommandRecord:
    args: list[str]
    cwd: str
    return_code: int | None
    shell: bool
    stdout_path: str = ""
    stderr_path: str = ""
    stdout_snippet: str = ""
    stderr_snippet: str = ""


@dataclass
class PathBackupRecord:
    relative_path: str
    existed: bool
    backup_path: str = ""


@dataclass
class E2EContext:
    config: E2EConfig
    report_dir: Path
    run_dir: Path
    backup_dir: Path
    started_at: str = field(default_factory=now_utc)
    commands: list[CommandRecord] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    asset_status: dict[str, dict[str, Any]] = field(default_factory=dict)
    failure_reason: str = ""
    failure_details: dict[str, Any] = field(default_factory=dict)
    git_status_before: str = ""
    git_status_after: str = ""
    protected_hashes_before: dict[str, str] = field(default_factory=dict)
    protected_hashes_after: dict[str, str] = field(default_factory=dict)
    backup_records: list[PathBackupRecord] = field(default_factory=list)
    selected_agent: str = ""
    reference_form: AgentReferenceForm | None = None
    visual_available: bool = False


def default_e2e_chunk_id() -> str:
    return "e2e_bounded_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _json_dump(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _snippet(text: str, limit: int = 2000) -> str:
    return text[:limit]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_status(root: Path, run_func: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> str:
    try:
        result = run_func(
            ["git", "status", "--short"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"git_status_unavailable: {exc}"
    return (result.stdout or result.stderr or "").strip()


def recommender_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for filename in PROTECTED_RECOMMENDER_FILENAMES:
        found = False
        for directory in PROTECTED_RECOMMENDER_DIRS:
            relative = str(Path(directory) / filename) if directory else filename
            path = root / relative
            if path.exists():
                result[Path(relative).as_posix()] = _sha256_file(path)
                found = True
        if not found:
            result[filename] = "<missing>"
    return result


class FileBackup:
    def __init__(self, root: Path, backup_dir: Path, relative_paths: Sequence[str | Path]):
        self.root = root
        self.backup_dir = backup_dir
        self.relative_paths = [Path(path) for path in relative_paths]
        self.records: list[PathBackupRecord] = []

    def backup(self) -> list[PathBackupRecord]:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.records = []
        for relative in self.relative_paths:
            source = self.root / relative
            backup = self.backup_dir / relative
            existed = source.exists()
            record = PathBackupRecord(relative_path=relative.as_posix(), existed=existed, backup_path=to_portable_path(backup) if existed else "")
            if existed:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, backup)
            self.records.append(record)
        return self.records

    def restore(self) -> None:
        for record in self.records:
            target = self.root / record.relative_path
            if record.existed:
                backup = Path(record.backup_path)
                if backup.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, target)
            elif target.exists():
                target.unlink()


def e2e_paths(config: E2EConfig) -> tuple[Path, Path, Path]:
    paths = pipeline_paths(config.root)
    report_dir = paths.reports / "e2e" / config.chunk_id
    run_dir = paths.ai_image / "e2e_runs" / config.chunk_id
    backup_dir = report_dir / "backup"
    return report_dir, run_dir, backup_dir


def build_context(config: E2EConfig) -> E2EContext:
    report_dir, run_dir, backup_dir = e2e_paths(config)
    report_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    return E2EContext(config=config, report_dir=report_dir, run_dir=run_dir, backup_dir=backup_dir)


def resolve_agent(
    *,
    config: E2EConfig,
    which_func: Callable[[str], str | None] = shutil.which,
) -> str | None:
    explicit = config.agent_cmd or os.environ.get("BOUNDED_EXECUTOR_AGENT_CMD")
    candidates = [explicit] if explicit else ["omx", "codex"]
    for candidate in candidates:
        if candidate and which_func(candidate):
            return candidate
    return None


def _agent_candidates(config: E2EConfig) -> list[str]:
    explicit = config.agent_cmd or os.environ.get("BOUNDED_EXECUTOR_AGENT_CMD")
    return [explicit] if explicit else ["omx", "codex"]


def _run_help(
    args: Sequence[str],
    *,
    root: Path,
    run_func: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[int, str]:
    try:
        result = run_func(
            list(args),
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return int(result.returncode), f"{result.stdout or ''}\n{result.stderr or ''}"


def probe_reference_image_form(
    agent_bin: str,
    *,
    root: Path,
    run_func: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> AgentReferenceForm | None:
    rc, help_text = _run_help([agent_bin, "exec", "--help"], root=root, run_func=run_func)
    if rc != 0:
        return None
    if "--image" in help_text:
        return AgentReferenceForm("image")
    if re.search(r"(^|\s)-i([,\s]|$)", help_text):
        return AgentReferenceForm("short_i")
    return None


def probe_visual_verdict(
    *,
    root: Path,
    run_func: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> bool:
    try:
        forms = discover_command_forms(root=root, config=ActiveVisualConfig.from_env(), run_func=run_func)
    except Exception:
        return False
    return bool(forms)


def preflight(
    context: E2EContext,
    *,
    run_func: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    which_func: Callable[[str], str | None] = shutil.which,
) -> dict[str, Any]:
    root = context.config.root
    first_available = resolve_agent(config=context.config, which_func=which_func)
    selected_agent = ""
    reference_form: AgentReferenceForm | None = None
    for candidate in _agent_candidates(context.config):
        if not candidate or not which_func(candidate):
            continue
        candidate_form = probe_reference_image_form(candidate, root=root, run_func=run_func)
        if candidate_form:
            selected_agent = candidate
            reference_form = candidate_form
            break
    if not selected_agent and first_available:
        selected_agent = first_available
    context.selected_agent = selected_agent
    visual_available = probe_visual_verdict(root=root, run_func=run_func)
    context.reference_form = reference_form
    context.visual_available = visual_available
    return {
        "agentAvailable": bool(first_available),
        "selectedAgent": selected_agent,
        "referenceImageInputAvailable": bool(reference_form),
        "referenceImageArgMode": reference_form.image_arg_mode if reference_form else "",
        "visualVerdictAvailable": visual_available,
    }


def _e2e_final_paths(root: Path, profile_id: str) -> list[Path]:
    gender, numeric = profile_id.split("_", 1)
    return [root / "ai_image" / gender / numeric / f"{shot}.png" for shot in SHOT_ORDER]


def _e2e_raw_paths(root: Path, profile_id: str) -> list[Path]:
    return [root / "ai_image" / "raw" / f"{profile_id}__{shot}__v001__attempt01.png" for shot in SHOT_ORDER]


def stateful_paths_for_backup(config: E2EConfig) -> list[Path]:
    paths: list[Path] = [Path(path) for path in STATEFUL_FILES]
    for path in _e2e_final_paths(config.root, config.profile_id):
        paths.append(path.relative_to(config.root))
    for path in _e2e_raw_paths(config.root, config.profile_id):
        paths.append(path.relative_to(config.root))
    return paths


def build_e2e_asset_rows(config: E2EConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gender, numeric = config.profile_id.split("_", 1)
    module = load_prompt_module(config.root)
    spec = module.sample_spec(gender, int(numeric), seed=20260510 + int(numeric), id_width=len(numeric))
    spec["face"]["faceType"] = DEFAULT_FACE_TYPE
    spec["face"]["looksLevel"] = DEFAULT_LOOKS_LEVEL
    spec["identityScope"] = "e2e"
    spec["isReserve"] = False
    spec["activeForTarget"] = True
    spec["e2eIdentityId"] = config.identity_id
    module.validate_spec(spec)
    raw_assets = module.build_asset_records(spec)
    paths = pipeline_paths(config.root)
    rows: list[dict[str, Any]] = []
    for asset in raw_assets:
        enriched = enrich_asset(
            {
                **dict(asset),
                "identityScope": "e2e",
                "isReserve": False,
                "activeForTarget": True,
                "e2eChunkId": config.chunk_id,
                "e2eIdentityId": config.identity_id,
            },
            paths,
            status="prepared",
            dry_run=False,
        )
        enriched.update(
            {
                "targetFaceType": DEFAULT_FACE_TYPE,
                "targetLooksLevel": DEFAULT_LOOKS_LEVEL,
                "targetLooksLevelBand": DEFAULT_LOOKS_BAND,
                "identityScope": "e2e",
                "activeForTarget": True,
                "e2eChunkId": config.chunk_id,
                "e2eIdentityId": config.identity_id,
            }
        )
        rows.append(enriched)
    rows = sorted(rows, key=lambda row: SHOT_ORDER.index(str(row["shotType"])))
    if len(rows) != 3 or [row["shotType"] for row in rows] != list(SHOT_ORDER):
        raise E2EBoundedSmokeError("e2e_plan_invalid", "E2E asset materialization did not produce exactly face/silhouette/vibe.")
    if any(row["targetLooksLevelBand"] == "4.4-5.0" for row in rows):
        raise E2EBoundedSmokeError("e2e_overlevel_bucket", "E2E plan must not use 4.4-5.0.")
    return [dict(spec)], rows


def write_e2e_manifests(context: E2EContext, specs: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]]) -> None:
    paths = pipeline_paths(context.config.root)
    ensure_base_dirs(paths)
    write_generation_outputs(paths, [dict(row) for row in rows])
    write_identity_manifest(context.config.root, specs)
    write_imagegen_queue(context.config.root, rows)
    write_jsonl(paths.manifests / "ai_profile_specs_v3.jsonl", specs)
    write_jsonl(paths.manifests / "ai_profile_assets_v3.jsonl", rows)


def build_e2e_chunk_plan(context: E2EContext, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_shot = {str(row["shotType"]): dict(row) for row in rows}
    assets = []
    for order, shot in enumerate(SHOT_ORDER, start=1):
        row = by_shot[shot]
        face_asset_id = f"{context.config.profile_id}__face_card__v001"
        assets.append(
            {
                "assetId": row["assetId"],
                "shotType": shot,
                "order": order,
                "status": "planned",
                "attempt": 0,
                "maxAttempts": 1,
                "prompt": row["prompt"],
                "promptHash": row["promptHash"],
                "finalPath": row["finalPath"],
                "rawPathPattern": to_portable_path(pipeline_paths(context.config.root).raw / f"{row['assetId']}__attemptXX.png"),
                "requiresReferenceAssetId": None if shot == "face_card" else face_asset_id,
            }
        )
    plan = {
        "schemaVersion": "seolleyeon_bounded_chunk_plan_v3",
        "chunkId": context.config.chunk_id,
        "createdAt": now_utc(),
        "status": "planned",
        "e2e": True,
        "e2eIdentityId": context.config.identity_id,
        "maxIdentities": 1,
        "maxAssets": 3,
        "selectedIdentityCount": 1,
        "selectedAssetCount": 3,
        "selectionSource": "e2e_forced_single_identity",
        "targetsJson": to_portable_path(pipeline_paths(context.config.root).ai_image / "config" / "AI_IMAGE_DISTRIBUTION_TARGETS_V3.json"),
        "distributionAuditJson": to_portable_path(pipeline_paths(context.config.root).reports / "latest_distribution_audit.json"),
        "allowedBuckets": [{"gender": "female", "faceType": DEFAULT_FACE_TYPE, "looksLevelBand": DEFAULT_LOOKS_BAND}],
        "forbiddenBuckets": [{"looksLevelBand": "4.4-5.0"}],
        "identities": [
            {
                "profileId": context.config.profile_id,
                "gender": "female",
                "numericId": context.config.profile_id.split("_", 1)[1],
                "targetFaceType": DEFAULT_FACE_TYPE,
                "targetLooksLevelBand": DEFAULT_LOOKS_BAND,
                "source": "e2e",
                "status": "planned",
                "assets": assets,
            }
        ],
        "initialProgress": {},
    }
    validate_chunk_plan(plan)
    _write_plan_and_state(context.config.root, plan)
    context.artifacts["chunkPlan"] = to_portable_path(current_plan_path(context.config.root))
    context.artifacts["chunkState"] = to_portable_path(current_state_path(context.config.root))
    return plan


def _write_command_logs(context: E2EContext, asset_id: str, attempt: int, result: subprocess.CompletedProcess[str], args: Sequence[str]) -> None:
    log_dir = context.report_dir / "commands"
    log_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{asset_id}_attempt{attempt}"
    stdout_path = log_dir / f"{stem}.stdout.txt"
    stderr_path = log_dir / f"{stem}.stderr.txt"
    command_path = log_dir / f"{stem}.command.json"
    stdout_path.write_text(result.stdout or "", encoding="utf-8")
    stderr_path.write_text(result.stderr or "", encoding="utf-8")
    command_path.write_text(json.dumps({"args": list(args), "shell": False}, ensure_ascii=False, indent=2), encoding="utf-8")
    context.commands.append(
        CommandRecord(
            args=list(args),
            cwd=str(context.config.root),
            return_code=int(result.returncode),
            shell=False,
            stdout_path=to_portable_path(stdout_path),
            stderr_path=to_portable_path(stderr_path),
            stdout_snippet=_snippet(result.stdout or ""),
            stderr_snippet=_snippet(result.stderr or ""),
        )
    )


def build_generation_args(
    *,
    context: E2EContext,
    prompt: str,
    reference_path: Path | None = None,
) -> list[str]:
    if not context.selected_agent:
        raise E2EBoundedSmokeError("agent_unavailable")
    if reference_path:
        if context.reference_form is None:
            raise E2EBoundedSmokeError("reference_image_input_unavailable")
        return build_agent_args(
            prompt,
            root=context.config.root,
            config=BoundedExecutorConfig.from_env(),
            agent_bin=context.selected_agent,
            image_paths=[reference_path],
            image_arg_mode=context.reference_form.image_arg_mode,
        )
    return build_agent_args(prompt, root=context.config.root, config=BoundedExecutorConfig.from_env(), agent_bin=context.selected_agent)


def _update_manifest_status(root: Path, asset_id: str, **updates: Any) -> None:
    paths = pipeline_paths(root)
    rows = []
    for row in load_generation_manifest(paths):
        out = dict(row)
        if str(out.get("assetId") or "") == asset_id:
            out.update(updates)
            out["updatedAt"] = now_utc()
        rows.append(out)
    write_generation_outputs(paths, rows)


def _copy_e2e_asset_outputs(context: E2EContext, asset_id: str) -> dict[str, str]:
    rows = {str(row.get("assetId") or ""): row for row in load_generation_manifest(pipeline_paths(context.config.root))}
    row = rows.get(asset_id, {})
    copied: dict[str, str] = {}
    for key in ("localPath", "rawPath", "finalPath"):
        value = str(row.get(key) or "")
        if not value:
            continue
        source = Path(value)
        if not source.exists():
            continue
        target = context.run_dir / "generated" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied[key] = to_portable_path(target)
    return copied


def _chunk_file_qa_rows(root: Path, chunk_id: str, asset_id: str) -> list[dict[str, Any]]:
    report_path = chunk_report_dir(root, chunk_id) / "file_qa.jsonl"
    return [dict(row) for row in read_jsonl(report_path) if str(row.get("assetId") or "") == asset_id]


def _generated_image_files(generated_root: Path) -> set[Path]:
    if not generated_root.exists():
        return set()
    suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    return {path.resolve() for path in generated_root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes}


def _new_generated_sources(before: set[Path], generated_root: Path) -> list[Path]:
    after = _generated_image_files(generated_root)
    return sorted(after - before, key=lambda path: path.stat().st_mtime, reverse=True)


def _pending_snapshot(context: E2EContext, asset_id: str, attempt: int) -> str:
    source = pending_path(context.config.root)
    target = context.report_dir / "pending_snapshots" / f"{asset_id}_attempt{attempt}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return to_portable_path(target)


def _face_reference_path(context: E2EContext) -> Path:
    rows = {str(row.get("assetId") or ""): row for row in load_generation_manifest(pipeline_paths(context.config.root))}
    face_id = f"{context.config.profile_id}__face_card__v001"
    face = rows.get(face_id, {})
    return Path(str(face.get("finalPath") or ""))


def assert_reference_ready(context: E2EContext, asset_row: Mapping[str, Any], face_file_qa_passed: bool) -> Path:
    if str(asset_row.get("shotType") or "") not in DEPENDENT_SHOTS:
        raise E2EBoundedSmokeError("reference_not_required")
    if not face_file_qa_passed:
        raise E2EBoundedSmokeError("face_card_not_file_qa_passed")
    reference_path = _face_reference_path(context)
    if not reference_path.exists() or reference_path.stat().st_size <= 0:
        raise E2EBoundedSmokeError("reference_image_missing", details={"referencePath": str(reference_path)})
    if context.reference_form is None:
        raise E2EBoundedSmokeError("reference_image_input_unavailable", details={"referencePath": str(reference_path)})
    return reference_path


def run_one_asset(
    context: E2EContext,
    asset_row: Mapping[str, Any],
    *,
    face_file_qa_passed: bool,
    run_func: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    recover_func: Callable[..., Any] = recover_pending_imagegen,
    file_qa_func: Callable[..., Mapping[str, int]] = file_qa_single_asset,
) -> bool:
    root = context.config.root
    paths = pipeline_paths(root)
    plan = json.loads(current_plan_path(root).read_text(encoding="utf-8"))
    state = json.loads(current_state_path(root).read_text(encoding="utf-8"))
    asset_id = str(asset_row["assetId"])
    shot_type = str(asset_row["shotType"])
    reference_path: Path | None = None
    if shot_type in DEPENDENT_SHOTS:
        reference_path = assert_reference_ready(context, asset_row, face_file_qa_passed)
    pending_file = pending_path(root)
    pending_payload = build_pending_payload(
        paths_root=root,
        row=asset_row,
        attempt=1,
        queue_file=paths.manifests / "imagegen_queue.jsonl",
        manifest_file=manifest_path(paths),
        out_pending=pending_file,
    )
    pending_payload.update({"chunkId": context.config.chunk_id, "e2eSmoke": True, "logicalIdentityId": context.config.identity_id})
    write_pending(pending_file, pending_payload)
    pending_snapshot = _pending_snapshot(context, asset_id, 1)
    _update_manifest_status(root, asset_id, status="pending_imagegen", attempt=1, attemptCount=1, finalPath=pending_payload["expectedFinalPath"])
    _transition_asset(root, plan, state, asset_id, "pending_imagegen", profile_id=str(asset_row["profileId"]), shot_type=shot_type, reason="e2e_pending_written")

    prompt = build_one_asset_prompt(asset_row, pending_payload)
    planned_asset_ids = [str(row.get("assetId") or "") for row in load_generation_manifest(paths)]
    allowed_asset_ids = {asset_id}
    if shot_type in DEPENDENT_SHOTS and pending_payload.get("referenceAssetId"):
        allowed_asset_ids.add(str(pending_payload["referenceAssetId"]))
    other_asset_ids = [planned for planned in planned_asset_ids if planned and planned not in allowed_asset_ids]
    if asset_id not in prompt or any(other_asset_id in prompt for other_asset_id in other_asset_ids):
        raise E2EBoundedSmokeError("prompt_asset_count_invalid", details={"assetId": asset_id, "otherAssetIds": other_asset_ids})
    args = build_generation_args(context=context, prompt=prompt, reference_path=reference_path)
    generated_root = Path(
        pending_payload.get("codexGeneratedImagesDir")
        or os.environ.get("CODEX_GENERATED_IMAGES_DIR")
        or DEFAULT_CODEX_GENERATED_IMAGES_DIR
    ).resolve()
    generated_before = _generated_image_files(generated_root)
    result = run_func(
        args,
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=int(os.environ.get("BOUNDED_EXECUTOR_TIMEOUT_SEC") or "1800"),
        shell=False,
    )
    _write_command_logs(context, asset_id, 1, result, args)
    state = json.loads(current_state_path(root).read_text(encoding="utf-8"))
    plan = json.loads(current_plan_path(root).read_text(encoding="utf-8"))
    _transition_asset(
        root,
        plan,
        state,
        asset_id,
        "imagegen_called",
        profile_id=str(asset_row["profileId"]),
        shot_type=shot_type,
        reason="e2e_agent_returned",
        command=args,
        return_code=int(result.returncode),
    )
    context.asset_status.setdefault(asset_id, {})["pendingSnapshot"] = pending_snapshot
    context.asset_status[asset_id]["referencePath"] = to_portable_path(reference_path) if reference_path else ""
    if int(result.returncode) != 0:
        raise E2EBoundedSmokeError("imagegen_command_failed", details={"assetId": asset_id, "returnCode": result.returncode})

    explicit_source: Path | None = None
    new_sources = _new_generated_sources(generated_before, generated_root)
    if new_sources:
        context.asset_status.setdefault(asset_id, {})["generatedSourceCandidates"] = [to_portable_path(path) for path in new_sources]
        if len(new_sources) > 1:
            raise E2EBoundedSmokeError(
                "imagegen_multiple_outputs",
                details={"assetId": asset_id, "generatedSourceCandidates": [to_portable_path(path) for path in new_sources]},
            )
        explicit_source = new_sources[0]

    try:
        recovered = recover_func(root=root, pending=pending_file, source=explicit_source, run_qa=False)
    except RuntimeError as exc:
        if "already resolved" not in str(exc).lower():
            raise
        recovered = recover_func(root=root, pending=pending_file, source=explicit_source, run_qa=False, force=True)
        context.asset_status.setdefault(asset_id, {})["recoveryNote"] = "pending was already resolved by child process; parent recovery was repeated with force=True"
    context.asset_status[asset_id]["recovery"] = "passed"
    context.asset_status[asset_id]["finalPath"] = to_portable_path(getattr(recovered, "final_path", Path(pending_payload["expectedFinalPath"])))
    context.asset_status[asset_id]["e2eCopies"] = _copy_e2e_asset_outputs(context, asset_id)
    state = json.loads(current_state_path(root).read_text(encoding="utf-8"))
    plan = json.loads(current_plan_path(root).read_text(encoding="utf-8"))
    _transition_asset(root, plan, state, asset_id, "recovered", profile_id=str(asset_row["profileId"]), shot_type=shot_type, reason="e2e_recovered")

    qa_counts = dict(file_qa_func(root=root, chunk_id=context.config.chunk_id, asset_id=asset_id, shot_type=shot_type, force=True))
    context.asset_status[asset_id]["fileQa"] = qa_counts
    file_qa_rows = _chunk_file_qa_rows(root, context.config.chunk_id, asset_id)
    context.asset_status[asset_id]["fileQaRows"] = file_qa_rows
    if int(qa_counts.get("checked", 0)) != 1 or int(qa_counts.get("rejected", 0)) or int(qa_counts.get("missing", 0)):
        raise E2EBoundedSmokeError("file_qa_failed", details={"assetId": asset_id, "fileQa": qa_counts, "fileQaRows": file_qa_rows})
    state = json.loads(current_state_path(root).read_text(encoding="utf-8"))
    plan = json.loads(current_plan_path(root).read_text(encoding="utf-8"))
    _transition_asset(root, plan, state, asset_id, "file_qa_passed", profile_id=str(asset_row["profileId"]), shot_type=shot_type, reason="e2e_file_qa_passed")
    return True


def generate_e2e_contact_sheets(context: E2EContext) -> list[str]:
    root = context.config.root
    results = []
    results.extend(generate_grouped_contact_sheets(root=root, stage=context.config.chunk_id, limit=3))
    results.extend(generate_identity_contact_sheets(root=root, limit_identities=1))
    results.extend(generate_chunk_contact_sheets(root=root, chunk_size=1))
    chunk_dir = chunk_report_dir(root, context.config.chunk_id) / "contact_sheets"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for result in results:
        if result.image_count <= 0 or not result.output_path.exists():
            continue
        target = chunk_dir / result.output_path.name
        shutil.copy2(result.output_path, target)
        copied.append(to_portable_path(target))
    if not copied:
        raise E2EBoundedSmokeError("contact_sheet_missing")
    context.artifacts["contactSheets"] = copied
    return copied


def run_visual_and_finalize(
    context: E2EContext,
    *,
    active_visual_func: Callable[..., Mapping[str, Any]] = run_active_visual_qa_all,
    audit_func: Callable[..., Mapping[str, Any]] = audit_distribution,
    finalize_func: Callable[..., Mapping[str, Any]] = finalize_bounded_chunk,
) -> dict[str, Any]:
    root = context.config.root
    plan = json.loads(current_plan_path(root).read_text(encoding="utf-8"))
    state = json.loads(current_state_path(root).read_text(encoding="utf-8"))
    _transition_identity(root, plan, state, context.config.profile_id, "assets_complete", reason="e2e_assets_complete")
    state = json.loads(current_state_path(root).read_text(encoding="utf-8"))
    plan = json.loads(current_plan_path(root).read_text(encoding="utf-8"))
    _transition_chunk(root, plan, state, "generation_complete", reason="e2e_generation_complete")
    state = json.loads(current_state_path(root).read_text(encoding="utf-8"))
    plan = json.loads(current_plan_path(root).read_text(encoding="utf-8"))
    _transition_chunk(root, plan, state, "file_qa_complete", reason="e2e_file_qa_complete")

    generate_e2e_contact_sheets(context)
    visual_result = active_visual_func(root=root, chunk_id=context.config.chunk_id)
    context.artifacts["activeVisualQA"] = dict(visual_result)
    state = json.loads(current_state_path(root).read_text(encoding="utf-8"))
    state["activeVisualQaComplete"] = True
    _json_dump(current_state_path(root), state)
    plan = json.loads(current_plan_path(root).read_text(encoding="utf-8"))
    _transition_chunk(root, plan, state, "active_visual_qa_complete", reason="e2e_active_visual_qa_complete")
    audit_before_finalize = audit_func(root=root)
    context.artifacts["numericAudit"] = {
        "passed": bool(audit_before_finalize.get("passed")),
        "finalDecision": audit_before_finalize.get("finalDecision"),
        "approvedCompleteIdentityCount": audit_before_finalize.get("approvedCompleteIdentityCount"),
        "approvedImageCount": audit_before_finalize.get("approvedImageCount"),
    }
    finalize_result = finalize_func(root=root, audit_func=audit_func)
    context.artifacts["finalize"] = dict(finalize_result)
    return {"visualQA": dict(visual_result), "audit": context.artifacts["numericAudit"], "finalize": dict(finalize_result)}


def _manual_flags(root: Path) -> list[str]:
    flag = root / "ai_image" / "manifests" / "manual_review_required.flag"
    return [to_portable_path(flag)] if flag.exists() else []


def report_payload(context: E2EContext, status: str) -> dict[str, Any]:
    config = context.config
    return {
        "schemaVersion": E2E_SCHEMA_VERSION,
        "chunkId": config.chunk_id,
        "status": status,
        "failureReason": context.failure_reason,
        "failureDetails": context.failure_details,
        "startTime": context.started_at,
        "endTime": now_utc(),
        "statement": E2E_ASSERTION,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "selectedAgent": context.selected_agent,
            "imagegenAvailability": bool(context.selected_agent),
            "referenceImageInputAvailable": context.reference_form is not None,
            "referenceImageArgMode": context.reference_form.image_arg_mode if context.reference_form else "",
            "visualVerdictAvailability": context.visual_available,
            "codexGeneratedImagesDir": os.environ.get("CODEX_GENERATED_IMAGES_DIR", DEFAULT_CODEX_GENERATED_IMAGES_DIR),
        },
        "commands": [record.__dict__ for record in context.commands],
        "shellFalseUsed": all(record.shell is False for record in context.commands),
        "identity": {
            "logicalIdentityId": config.identity_id,
            "profileId": config.profile_id,
            "targetFaceType": DEFAULT_FACE_TYPE,
            "targetLooksLevelBand": DEFAULT_LOOKS_BAND,
        },
        "assetStatus": context.asset_status,
        "artifacts": context.artifacts,
        "manualReviewFlags": _manual_flags(config.root),
        "gitStatusBefore": context.git_status_before,
        "gitStatusAfter": context.git_status_after,
        "protectedRecommenderHashesBefore": context.protected_hashes_before,
        "protectedRecommenderHashesAfter": context.protected_hashes_after,
        "protectedRecommenderUnchanged": context.protected_hashes_before == context.protected_hashes_after if context.protected_hashes_after else None,
        "backupRecords": [record.__dict__ for record in context.backup_records],
        "productionGenerationRun": False,
    }


def write_reports(context: E2EContext, status: str) -> dict[str, Any]:
    payload = report_payload(context, status)
    json_path = context.report_dir / "e2e_report.json"
    md_path = context.report_dir / "e2e_report.md"
    _json_dump(json_path, payload)
    lines = [
        f"# Seolleyeon Bounded Imagegen E2E Smoke - {payload['chunkId']}",
        "",
        f"- status: {payload['status']}",
        f"- failureReason: {payload['failureReason'] or 'none'}",
        f"- selectedAgent: {payload['environment']['selectedAgent'] or 'none'}",
        f"- referenceImageInputAvailable: {payload['environment']['referenceImageInputAvailable']}",
        f"- visualVerdictAvailability: {payload['environment']['visualVerdictAvailability']}",
        f"- shellFalseUsed: {payload['shellFalseUsed']}",
        f"- protectedRecommenderUnchanged: {payload['protectedRecommenderUnchanged']}",
        f"- reportJson: {to_portable_path(json_path)}",
        "",
        E2E_ASSERTION,
        "",
        "## Assets",
    ]
    for asset_id, status_row in payload["assetStatus"].items():
        lines.append(f"- {asset_id}: finalPath={status_row.get('finalPath', '')}, referencePath={status_row.get('referencePath', '')}")
    lines.extend(["", "## Artifacts", ""])
    for key, value in payload["artifacts"].items():
        lines.append(f"- {key}: {value}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload["reportJson"] = to_portable_path(json_path)
    payload["reportMarkdown"] = to_portable_path(md_path)
    return payload


def run_e2e_smoke(
    config: E2EConfig,
    *,
    run_func: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    which_func: Callable[[str], str | None] = shutil.which,
    recover_func: Callable[..., Any] = recover_pending_imagegen,
    file_qa_func: Callable[..., Mapping[str, int]] = file_qa_single_asset,
    active_visual_func: Callable[..., Mapping[str, Any]] = run_active_visual_qa_all,
    audit_func: Callable[..., Mapping[str, Any]] = audit_distribution,
    finalize_func: Callable[..., Mapping[str, Any]] = finalize_bounded_chunk,
) -> dict[str, Any]:
    context = build_context(config)
    paths = pipeline_paths(config.root)
    ensure_base_dirs(paths)
    context.git_status_before = _git_status(config.root, run_func=run_func)
    context.protected_hashes_before = recommender_hashes(config.root)
    backup = FileBackup(config.root, context.backup_dir, stateful_paths_for_backup(config))
    restored = False
    try:
        preflight_result = preflight(context, run_func=run_func, which_func=which_func)
        context.artifacts["preflight"] = preflight_result
        if config.preflight_only:
            status = "preflight_passed" if all(
                [
                    preflight_result["agentAvailable"],
                    preflight_result["referenceImageInputAvailable"],
                    preflight_result["visualVerdictAvailable"],
                ]
            ) else "preflight_failed"
            if status == "preflight_failed":
                context.failure_reason = "preflight_unavailable"
                context.failure_details = preflight_result
            context.protected_hashes_after = recommender_hashes(config.root)
            context.git_status_after = _git_status(config.root, run_func=run_func)
            return write_reports(context, status)

        if os.environ.get(E2E_ENV_GUARD) != "1":
            context.failure_reason = "real_e2e_guard_missing"
            context.failure_details = {"requiredEnv": E2E_ENV_GUARD}
            context.protected_hashes_after = recommender_hashes(config.root)
            context.git_status_after = _git_status(config.root, run_func=run_func)
            return write_reports(context, "blocked")

        if not preflight_result["agentAvailable"]:
            raise E2EBoundedSmokeError("agent_unavailable", details=preflight_result)
        if not preflight_result["referenceImageInputAvailable"]:
            raise E2EBoundedSmokeError("reference_image_input_unavailable", details=preflight_result)
        if not preflight_result["visualVerdictAvailable"]:
            raise E2EBoundedSmokeError("visual_verdict_unavailable", details=preflight_result)

        context.backup_records = backup.backup()
        specs, rows = build_e2e_asset_rows(config)
        write_e2e_manifests(context, specs, rows)
        plan = build_e2e_chunk_plan(context, rows)
        _append_event(config.root, config.chunk_id, event_type="e2e_started", to_status="running")
        state = json.loads(current_state_path(config.root).read_text(encoding="utf-8"))
        _transition_chunk(config.root, plan, state, "running", reason="e2e_real_smoke_started")
        face_file_qa_passed = False
        for row in rows:
            ok = run_one_asset(
                context,
                row,
                face_file_qa_passed=face_file_qa_passed,
                run_func=run_func,
                recover_func=recover_func,
                file_qa_func=file_qa_func,
            )
            if row["shotType"] == "face_card":
                face_file_qa_passed = ok
        run_visual_and_finalize(
            context,
            active_visual_func=active_visual_func,
            audit_func=audit_func,
            finalize_func=finalize_func,
        )
        status = "passed"
    except E2EBoundedSmokeError as exc:
        context.failure_reason = exc.reason
        context.failure_details = exc.details
        status = "failed"
    except Exception as exc:  # noqa: BLE001 - report unexpected failures instead of hiding them.
        context.failure_reason = "unexpected_error"
        context.failure_details = {"error": str(exc), "type": type(exc).__name__}
        status = "failed"
    finally:
        if context.backup_records and not config.no_restore:
            backup.restore()
            restored = True
        context.artifacts["productionStateRestored"] = restored
        context.protected_hashes_after = recommender_hashes(config.root)
        context.git_status_after = _git_status(config.root, run_func=run_func)
    return write_reports(context, status)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a real, bounded 1-identity Seolleyeon imagegen E2E smoke.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--agent-cmd", "--agent_cmd", dest="agent_cmd", default=None)
    parser.add_argument("--chunk-id", "--chunk_id", dest="chunk_id", default=None)
    parser.add_argument("--identity-id", "--identity_id", dest="identity_id", default=DEFAULT_LOGICAL_IDENTITY_ID)
    parser.add_argument("--keep-artifacts", "--keep_artifacts", dest="keep_artifacts", action="store_true")
    parser.add_argument("--no-restore", "--no_restore", dest="no_restore", action="store_true")
    parser.add_argument("--preflight-only", "--preflight_only", dest="preflight_only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_e2e_smoke(E2EConfig.from_args(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] in {"passed", "preflight_passed"}:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
