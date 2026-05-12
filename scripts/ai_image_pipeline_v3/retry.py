from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .codex_imagegen import retry_manifest_path
from .config import MAX_ATTEMPTS, ensure_base_dirs, now_utc, pipeline_paths, write_jsonl
from .manifest import load_generation_manifest, write_generation_outputs
from .retry_plan import APPROVED_STATUSES, attempt_count
from .targeting import apply_reserve_policy


RETRY_SOURCE_STATUSES = {"missing", "qa_rejected", "vision_rejected", "failed"}


def plan_retries(
    *,
    root: Path | str | None = None,
    max_attempts: int = MAX_ATTEMPTS,
    force: bool = False,
) -> dict[str, Any]:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    rows = load_generation_manifest(paths)
    retry_rows: list[dict[str, Any]] = []
    exhausted_rows: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []

    for row in rows:
        out = dict(row)
        status = str(out.get("status") or "")
        attempts = attempt_count(out)
        if status in APPROVED_STATUSES and not force:
            updated.append(out)
            continue
        if force and bool(out.get("activeForTarget", True)):
            out["status"] = "retry_queued"
            out["updatedAt"] = now_utc()
            out["error"] = ""
            retry_rows.append(dict(out))
        elif status in RETRY_SOURCE_STATUSES:
            if attempts < max_attempts:
                out["status"] = "retry_queued"
                out["updatedAt"] = now_utc()
                out["error"] = ""
                retry_rows.append(dict(out))
            else:
                out["status"] = "attempts_exhausted"
                out["updatedAt"] = now_utc()
                exhausted_rows.append(dict(out))
        updated.append(out)

    write_generation_outputs(paths, updated)
    reserve_counts = apply_reserve_policy(root=root, max_attempts=max_attempts)
    write_jsonl(
        retry_manifest_path(root),
        [
            {
                "assetId": row.get("assetId", ""),
                "profileId": row.get("profileId", ""),
                "shotType": row.get("shotType", ""),
                "attemptCount": row.get("attemptCount", 0),
                "retryStatus": "retry_queued",
                "updatedAt": now_utc(),
            }
            for row in retry_rows
        ],
    )
    return {
        "retryQueued": len(retry_rows),
        "attemptsExhausted": len(exhausted_rows),
        **reserve_counts,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan retries for Codex $imagegen Seolleyeon assets.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--max_attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = plan_retries(root=args.root, max_attempts=args.max_attempts, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
