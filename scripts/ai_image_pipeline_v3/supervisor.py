from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .completion import completion_check
from .config import ensure_base_dirs, now_utc, pipeline_paths, read_jsonl


VALID_MODES = ("auto", "chunk", "identity", "asset")
STOP_PATTERNS = (
    "manual review",
    "approval required",
    "awaiting user",
    "please confirm",
    "image gen unavailable",
    "imagegen unavailable",
    "quota",
    "usage limit",
    "rate limit",
    "cannot continue",
    "fatal",
    "permission denied",
)


@dataclass(frozen=True)
class SupervisorConfig:
    mode: Literal["auto", "chunk", "identity", "asset"]
    max_chunks: int
    required_unattended_chunks: int
    max_identity_ticks: int
    max_asset_ticks: int
    allow_promote_back_to_chunk: bool
    promote_after_identity_success_ticks: int
    min_deficit_identities_for_chunk: int
    active_visual_qa: bool


def parse_config(env: dict[str, str] | None = None, *, mode: str | None = None) -> SupervisorConfig:
    values = env or os.environ
    selected_mode = str(mode or values.get("MODE") or "auto").strip()
    if selected_mode not in VALID_MODES:
        raise ValueError(f"Unsupported supervisor MODE: {selected_mode}")
    return SupervisorConfig(
        mode=selected_mode,  # type: ignore[arg-type]
        max_chunks=int(values.get("MAX_CHUNKS", "30")),
        required_unattended_chunks=int(values.get("REQUIRED_UNATTENDED_CHUNKS", "10")),
        max_identity_ticks=int(values.get("MAX_IDENTITY_TICKS", "240")),
        max_asset_ticks=int(values.get("MAX_ASSET_TICKS", "720")),
        allow_promote_back_to_chunk=str(values.get("ALLOW_PROMOTE_BACK_TO_CHUNK", "0")) == "1",
        promote_after_identity_success_ticks=int(values.get("PROMOTE_AFTER_IDENTITY_SUCCESS_TICKS", "8")),
        min_deficit_identities_for_chunk=int(values.get("MIN_DEFICIT_IDENTITIES_FOR_CHUNK", "24")),
        active_visual_qa=str(values.get("ACTIVE_VISUAL_QA", "1")) != "0",
    )


def progress_snapshot(root: Path | str | None = None) -> dict[str, int]:
    paths = pipeline_paths(root)
    audit_path = paths.reports / "latest_distribution_audit.json"
    audit: dict[str, Any] = {}
    if audit_path.exists():
        try:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            audit = {}
    asset_rows = read_jsonl(paths.manifests / "asset_qa_manifest.jsonl")
    identity_rows = read_jsonl(paths.manifests / "identity_qa_manifest.jsonl")
    completed_pending = read_jsonl(paths.manifests / "completed_pending_imagegen.jsonl")
    rejected_rows = read_jsonl(paths.manifests / "rejected_identity_manifest.jsonl")
    return {
        "approvedIdentityCount": int(audit.get("approvedCompleteIdentityCount") or audit.get("approvedCompleteIdentities") or 0),
        "approvedAssetCount": int(audit.get("approvedImageCount") or audit.get("approvedImages") or 0),
        "assetQaCount": len(asset_rows),
        "identityQaCount": len(identity_rows),
        "resolvedPendingCount": len(completed_pending),
        "rejectedIdentityCount": len(rejected_rows),
    }


def log_mode_transition(
    *,
    root: Path | str | None = None,
    from_mode: str,
    to_mode: str,
    reason: str,
    before: dict[str, int] | None = None,
    after: dict[str, int] | None = None,
) -> Path:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    log_dir = paths.reports / "autopilot_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    before = before or {}
    after = after or {}
    row = {
        "timestamp": now_utc(),
        "from_mode": from_mode,
        "to_mode": to_mode,
        "reason": reason,
        "approvedIdentityCountBefore": int(before.get("approvedIdentityCount", 0)),
        "approvedIdentityCountAfter": int(after.get("approvedIdentityCount", 0)),
        "approvedAssetCountBefore": int(before.get("approvedAssetCount", 0)),
        "approvedAssetCountAfter": int(after.get("approvedAssetCount", 0)),
    }
    path = log_dir / "mode_transitions.log"
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def should_promote_to_chunk(
    *,
    config: SupervisorConfig,
    consecutive_identity_success_ticks: int,
    remaining_deficit_identities: int,
    promotion_already_attempted: bool = False,
) -> bool:
    return (
        config.allow_promote_back_to_chunk
        and not promotion_already_attempted
        and consecutive_identity_success_ticks >= config.promote_after_identity_success_ticks
        and remaining_deficit_identities >= config.min_deficit_identities_for_chunk
    )


def no_progress(before: dict[str, int], after: dict[str, int]) -> bool:
    keys = (
        "approvedIdentityCount",
        "approvedAssetCount",
        "assetQaCount",
        "identityQaCount",
        "resolvedPendingCount",
        "rejectedIdentityCount",
    )
    return all(int(after.get(key, 0)) <= int(before.get(key, 0)) for key in keys)


def write_chunk_unattended_verification(
    *,
    root: Path | str | None = None,
    passed: bool,
    successful_chunks: int,
    required_chunks: int,
    reason: str,
    chunk_qa_complete: bool = False,
    chunk_distribution_updated: bool = False,
    chunk_new_approved_identities: int = 0,
    chunk_new_rejected_identities: int = 0,
    chunk_new_needs_review_identities: int = 0,
) -> Path:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    path = paths.reports / "chunk_unattended_verification.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"chunk_unattended_verification={'PASS' if passed else 'FAIL'}",
                "meaning=unattended_execution_only_not_final_QA_or_distribution_completion",
                f"successful_chunks={successful_chunks}",
                f"required_chunks={required_chunks}",
                f"chunk_qa_complete={str(chunk_qa_complete).lower()}",
                f"chunk_distribution_updated={str(chunk_distribution_updated).lower()}",
                f"chunk_new_approved_identities={chunk_new_approved_identities}",
                f"chunk_new_rejected_identities={chunk_new_rejected_identities}",
                f"chunk_new_needs_review_identities={chunk_new_needs_review_identities}",
                f"reason={reason}",
                f"updated_at={now_utc()}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def supervisor_status(*, root: Path | str | None = None, mode: str | None = None) -> dict[str, Any]:
    config = parse_config(mode=mode)
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    completion = completion_check(root=root)
    manual_flag = paths.manifests / "manual_review_required.flag"
    return {
        "schemaVersion": "seolleyeon_ai_image_supervisor_status_v3",
        "mode": config.mode,
        "dryRunStatusOnly": True,
        "completionPassed": bool(completion["passed"]),
        "manualReviewRequired": manual_flag.exists(),
        "progress": progress_snapshot(root=root),
        "allowPromoteBackToChunk": config.allow_promote_back_to_chunk,
        "activeVisualQa": config.active_visual_qa,
        "chunkExecutor": "bounded_batch_executor",
        "chunkCommand": "python scripts/run_ai_image_pipeline_v3.py bounded-chunk-run --root .",
        "strictChunkQaBehavior": "active_visual_qa_all_required_after_contact_sheets" if config.active_visual_qa else "manual_review_required_unless_dry_run_or_manual_mode",
        "modeTransitionsLog": str(paths.reports / "autopilot_logs" / "mode_transitions.log"),
        "updatedAt": now_utc(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform dry-run/status supervisor helpers for Seolleyeon imagegen automation.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--mode", choices=VALID_MODES, default=None)
    parser.add_argument("--simulate_transition", choices=["chunk_to_identity", "identity_to_asset"], default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.simulate_transition:
        before = progress_snapshot(root=args.root)
        after = dict(before)
        if args.simulate_transition == "chunk_to_identity":
            path = log_mode_transition(root=args.root, from_mode="chunk", to_mode="identity", reason="two_consecutive_chunks_no_approved_identity_progress", before=before, after=after)
        else:
            path = log_mode_transition(root=args.root, from_mode="identity", to_mode="asset", reason="three_identity_ticks_no_approved_identity_progress", before=before, after=after)
        print(json.dumps({"modeTransitionsLog": str(path)}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(supervisor_status(root=args.root, mode=args.mode), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
