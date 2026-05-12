from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from .config import ensure_base_dirs, local_image_path, now_utc, pipeline_paths, write_csv
from .manifest import load_generation_manifest


UPLOAD_FIELDS = (
    "assetId",
    "profileId",
    "gender",
    "shotType",
    "sourcePath",
    "storagePath",
    "status",
    "updatedAt",
    "error",
)


def upload_images(
    *,
    root: Path | str | None = None,
    bucket: str | None = None,
    source: str = "final",
    limit: int | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, int]:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    rows = load_generation_manifest(paths)
    selected = rows[:limit] if limit else rows
    bucket_name = bucket or os.environ.get("FIREBASE_STORAGE_BUCKET")
    storage_bucket = None
    if not dry_run:
        if not bucket_name:
            raise RuntimeError("Set --bucket or FIREBASE_STORAGE_BUCKET before uploading.")
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError("Install google-cloud-storage before uploading.") from exc
        storage_bucket = storage.Client().bucket(bucket_name)

    counts = {"selected": len(selected), "uploaded": 0, "skipped": 0, "missing": 0, "failed": 0, "dry_run": 0}
    report: list[dict[str, Any]] = []
    for row in selected:
        source_path = local_image_path(paths, row, root_key=source)
        status = "pending"
        error = ""
        if not source_path.exists():
            status = "missing"
            counts["missing"] += 1
        elif dry_run:
            status = "dry_run"
            counts["dry_run"] += 1
        else:
            try:
                assert storage_bucket is not None
                blob = storage_bucket.blob(str(row["storagePath"]))
                if blob.exists() and not force:
                    status = "skipped_existing"
                    counts["skipped"] += 1
                else:
                    blob.upload_from_filename(str(source_path), content_type="image/png")
                    status = "uploaded"
                    counts["uploaded"] += 1
            except Exception as exc:  # noqa: BLE001 - upload report should stay resumable.
                status = "failed"
                error = str(exc)
                counts["failed"] += 1
        report.append(
            {
                "assetId": row["assetId"],
                "profileId": row["profileId"],
                "gender": row["gender"],
                "shotType": row["shotType"],
                "sourcePath": str(source_path),
                "storagePath": row["storagePath"],
                "status": status,
                "updatedAt": now_utc(),
                "error": error,
            }
        )
    write_csv(paths.reports / "upload_report.csv", report, UPLOAD_FIELDS)
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload approved Seolleyeon AI profile images to Firebase Storage.")
    parser.add_argument("--root", default=None, help="Workspace root. Defaults to the repository root.")
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--source", default="final", choices=["approved", "final", "raw"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    counts = upload_images(
        root=args.root,
        bucket=args.bucket,
        source=args.source,
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force,
    )
    print(counts)
    return 0

