from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .config import SHOT_ORDER, ensure_base_dirs, pipeline_paths, read_csv, read_jsonl
from .manifest import manifest_path, status_path
from .targeting import approved_identity_report


def summarize_images(*, root: Path | str | None = None) -> dict[str, object]:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    manifest_rows = read_jsonl(manifest_path(paths))
    identity_rows = read_jsonl(paths.manifests / "identity_manifest.jsonl")
    status_rows = read_csv(status_path(paths))
    status_counts = Counter(str(row.get("status", "")) for row in status_rows)
    gender_counts = Counter(str(row.get("gender", "")) for row in manifest_rows)
    shot_counts = Counter(str(row.get("shotType", "")) for row in manifest_rows)
    scope_counts = Counter(str(row.get("identityScope", "production")) for row in manifest_rows)
    reserve_status_counts = Counter(str(row.get("reserveStatus", "")) for row in manifest_rows)
    active_counts = Counter("active" if bool(row.get("activeForTarget", True)) else "inactive" for row in manifest_rows)
    approved_state = approved_identity_report(manifest_rows)
    missing = [
        row.get("assetId", "")
        for row in manifest_rows
        if row.get("status") not in {"completed", "qa_approved", "vision_approved", "dry_run"}
        and not Path(str(row.get("localPath", ""))).exists()
    ]
    summary = {
        "manifestCount": len(manifest_rows),
        "identityManifestCount": len(identity_rows),
        "statusCount": len(status_rows),
        "statusCounts": dict(status_counts),
        "genderCounts": dict(gender_counts),
        "shotCounts": dict(shot_counts),
        "identityScopeCounts": dict(scope_counts),
        "reserveStatusCounts": dict(reserve_status_counts),
        "activeForTargetCounts": dict(active_counts),
        **approved_state,
        "completeIdentityTarget": 240,
        "approvedAssetTarget": 720,
        "requiredShotsPerIdentity": list(SHOT_ORDER),
        "missingCount": len(missing),
        "missingAssetIds": missing,
    }
    summary_json = paths.reports / "summary.json"
    summary_md = paths.reports / "summary.md"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md.write_text(render_markdown_summary(summary), encoding="utf-8")
    return summary


def render_markdown_summary(summary: dict[str, object]) -> str:
    lines = [
        "# AI Image Pipeline Summary",
        "",
        f"- manifestCount: {summary['manifestCount']}",
        f"- statusCount: {summary['statusCount']}",
        f"- missingCount: {summary['missingCount']}",
        f"- approvedIdentities: {summary.get('approvedIdentities', 0)}",
        f"- approvedAssets: {summary.get('approvedAssets', 0)}",
        "",
        "## Status Counts",
    ]
    for key, value in sorted(dict(summary["statusCounts"]).items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Shot Counts"])
    for key, value in sorted(dict(summary["shotCounts"]).items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Identity Scope Counts"])
    for key, value in sorted(dict(summary.get("identityScopeCounts", {})).items()):
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize Seolleyeon AI image generation status.")
    parser.add_argument("--root", default=None, help="Workspace root. Defaults to the repository root.")
    parser.add_argument("--manifest", default=None, help="Compatibility option; generation_manifest.jsonl remains the source of truth.")
    parser.add_argument("--identity_manifest", default=None, help="Compatibility option.")
    parser.add_argument("--qa_manifest", default=None, help="Compatibility option.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = summarize_images(root=args.root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0
