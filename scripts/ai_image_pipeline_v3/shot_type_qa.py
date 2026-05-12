from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import SHOT_ORDER, ensure_base_dirs, now_utc, pipeline_paths, write_csv, write_jsonl
from .manifest import load_generation_manifest

SHOT_TYPE_QA_FIELDS = (
    "assetId",
    "profileId",
    "shotType",
    "shotTypeValid",
    "imageExists",
    "decision",
    "reasons",
    "updatedAt",
)


def run_shot_type_qa(*, root: Path | str | None = None, limit: int | None = None) -> dict[str, int]:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    rows = load_generation_manifest(paths)
    selected = rows[:limit] if limit else rows
    report: list[dict[str, Any]] = []
    counts = {"checked": 0, "approved": 0, "needs_review": 0, "rejected": 0}
    for row in selected:
        counts["checked"] += 1
        shot_type = str(row.get("shotType") or "")
        valid = shot_type in SHOT_ORDER
        image_path = Path(str(row.get("localPath") or row.get("finalPath") or ""))
        image_exists = image_path.exists() and image_path.stat().st_size > 0
        reasons: list[str] = []
        if not valid:
            reasons.append("invalid_shot_type")
        if not image_exists:
            reasons.append("missing_image_for_shot_type_review")
        if not valid:
            decision = "rejected"
        elif image_exists:
            decision = "needs_review"
            reasons.append("visual_shot_type_readability_checked_by_vision_qa")
        else:
            decision = "needs_review"
        counts[decision] += 1
        report.append(
            {
                "assetId": row.get("assetId", ""),
                "profileId": row.get("profileId", ""),
                "shotType": shot_type,
                "shotTypeValid": valid,
                "imageExists": image_exists,
                "decision": decision,
                "reasons": reasons,
                "updatedAt": now_utc(),
            }
        )
    write_jsonl(paths.reports / "shot_type_qa_report.jsonl", report)
    write_csv(
        paths.reports / "shot_type_qa_report.csv",
        [{**row, "reasons": json.dumps(row["reasons"], ensure_ascii=False)} for row in report],
        SHOT_TYPE_QA_FIELDS,
    )
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run shotType structural QA for Seolleyeon AI images.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(run_shot_type_qa(root=args.root, limit=args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
