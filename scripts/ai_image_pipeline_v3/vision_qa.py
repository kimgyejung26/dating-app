from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .config import ensure_base_dirs, now_utc, pipeline_paths, read_jsonl, write_csv, write_jsonl
from .manifest import load_generation_manifest, write_generation_outputs


VISION_QA_JSONL_FIELDS = (
    "assetId",
    "profileId",
    "shotType",
    "adultVisual",
    "photoRealism",
    "campusRealism",
    "brandFit",
    "influencerRisk",
    "childlikeRisk",
    "schoolUniformRisk",
    "sexualizationRisk",
    "artifactRisk",
    "shotTypeReadable",
    "decision",
    "reasons",
)

CONTRACT_SUMMARY = (
    "Realistic adult Korean university student profile photo; calm sincere campus trust tone; "
    "hard reject childlike/teenager look, school uniform, idol styling, influencer photoshoot, "
    "sexualized or revealing styling, nightlife/club/neon scene, readable school name, logo/watermark, "
    "distorted face/hands/body, plastic skin, or heavy beauty filter."
)


def vision_prompt(asset: Mapping[str, Any]) -> str:
    return (
        "You are strict QA for Seolleyeon, a university-only trust-based relationship platform. "
        "Return ONLY one compact JSON object with exactly these keys: "
        + ", ".join(VISION_QA_JSONL_FIELDS)
        + ". Risk fields and realism fields are integers 0-5. decision is approved, needs_review, or rejected. "
        "Hard reject if adultVisual is false, childlikeRisk >= 2, schoolUniformRisk >= 1, "
        "sexualizationRisk >= 1, artifactRisk >= 3, photoRealism < 4, brandFit < 4, or shotTypeReadable is false. "
        f"assetId={asset.get('assetId')} profileId={asset.get('profileId')} shotType={asset.get('shotType')}. "
        f"Contract: {CONTRACT_SUMMARY}"
    )


class OpenAIVisionQAClient:
    def __init__(self, *, model: str) -> None:
        raise RuntimeError(
            "OpenAI Vision/API QA is disabled. This workflow uses Codex built-in $imagegen only; "
            "run local file QA plus strict manual/Codex-assisted JSONL review instead."
        )

    def review(self, *, asset: Mapping[str, Any], image_path: Path) -> dict[str, Any]:
        raise RuntimeError("OpenAI Vision/API QA is disabled in Codex built-in $imagegen mode.")


def _bounded_score(value: Any, *, default: int) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = default
    return max(0, min(5, score))


def normalize_review(asset: Mapping[str, Any], review: Mapping[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    reasons_raw = review.get("reasons", [])
    if isinstance(reasons_raw, str):
        reasons = [reasons_raw]
    elif isinstance(reasons_raw, list):
        reasons = [str(reason) for reason in reasons_raw]
    else:
        reasons = [str(reasons_raw)] if reasons_raw else []

    row = {
        "assetId": str(review.get("assetId") or asset.get("assetId") or ""),
        "profileId": str(review.get("profileId") or asset.get("profileId") or ""),
        "shotType": str(review.get("shotType") or asset.get("shotType") or ""),
        "adultVisual": bool(review.get("adultVisual", True)),
        "photoRealism": _bounded_score(review.get("photoRealism"), default=4 if dry_run else 0),
        "campusRealism": _bounded_score(review.get("campusRealism"), default=4 if dry_run else 0),
        "brandFit": _bounded_score(review.get("brandFit"), default=4 if dry_run else 0),
        "influencerRisk": _bounded_score(review.get("influencerRisk"), default=0),
        "childlikeRisk": _bounded_score(review.get("childlikeRisk"), default=0),
        "schoolUniformRisk": _bounded_score(review.get("schoolUniformRisk"), default=0),
        "sexualizationRisk": _bounded_score(review.get("sexualizationRisk"), default=0),
        "artifactRisk": _bounded_score(review.get("artifactRisk"), default=0 if dry_run else 5),
        "shotTypeReadable": bool(review.get("shotTypeReadable", True)),
        "decision": str(review.get("decision") or ("needs_review" if dry_run else "rejected")),
        "reasons": reasons,
    }
    return apply_hard_reject_rules(row, dry_run=dry_run)


def apply_hard_reject_rules(row: Mapping[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    out = dict(row)
    reasons = list(out.get("reasons") or [])
    hard_reasons: list[str] = []
    if out["adultVisual"] is False:
        hard_reasons.append("adultVisual_false")
    if int(out["childlikeRisk"]) >= 2:
        hard_reasons.append("childlikeRisk>=2")
    if int(out["schoolUniformRisk"]) >= 1:
        hard_reasons.append("schoolUniformRisk>=1")
    if int(out["sexualizationRisk"]) >= 1:
        hard_reasons.append("sexualizationRisk>=1")
    if int(out["artifactRisk"]) >= 3:
        hard_reasons.append("artifactRisk>=3")
    if int(out["photoRealism"]) < 4:
        hard_reasons.append("photoRealism<4")
    if int(out["brandFit"]) < 4:
        hard_reasons.append("brandFit<4")
    if out["shotTypeReadable"] is False:
        hard_reasons.append("shotTypeReadable_false")

    if dry_run and not hard_reasons:
        out["decision"] = "needs_review"
        reasons.append("dry_run_no_api_call")
    elif hard_reasons:
        out["decision"] = "rejected"
        reasons.extend(hard_reasons)
    elif out["decision"] not in {"approved", "needs_review", "rejected"}:
        out["decision"] = "needs_review"
        reasons.append("invalid_decision_normalized")
    out["reasons"] = sorted(set(map(str, reasons)))
    return out


def status_from_decision(decision: str) -> str:
    if decision == "approved":
        return "vision_approved"
    if decision == "needs_review":
        return "needs_review"
    return "vision_rejected"


def run_vision_qa(
    *,
    root: Path | str | None = None,
    limit: int | None = None,
    shot_type: str | None = None,
    shot_types: tuple[str, ...] | list[str] | set[str] | None = None,
    dry_run: bool = False,
    model: str | None = None,
    update_manifest: bool = True,
    append: bool = False,
) -> dict[str, int]:
    paths = pipeline_paths(root)
    ensure_base_dirs(paths)
    rows = load_generation_manifest(paths)
    allowed_shots = set(shot_types or [])
    if shot_type:
        allowed_shots.add(str(shot_type))
    candidates = [row for row in rows if not allowed_shots or str(row.get("shotType")) in allowed_shots]
    selected = candidates[:limit] if limit else candidates
    selected_ids = {str(row["assetId"]) for row in selected}
    report: list[dict[str, Any]] = []
    counts = {"checked": 0, "approved": 0, "needs_review": 0, "rejected": 0, "missing": 0, "dry_run": 0}
    _ = model  # Compatibility only; no model/API call is made in Codex built-in imagegen mode.

    for row in rows:
        if str(row.get("assetId")) not in selected_ids:
            continue
        counts["checked"] += 1
        local_path = Path(str(row.get("localPath") or ""))
        missing_local_image = False
        if dry_run:
            review = normalize_review(row, {}, dry_run=True)
            counts["dry_run"] += 1
        elif not local_path.exists():
            missing_local_image = True
            review = normalize_review(
                row,
                {
                    "adultVisual": False,
                    "photoRealism": 0,
                    "campusRealism": 0,
                    "brandFit": 0,
                    "artifactRisk": 5,
                    "shotTypeReadable": False,
                    "decision": "rejected",
                    "reasons": ["missing_image"],
                },
            )
            counts["missing"] += 1
        else:
            review = normalize_review(
                row,
                {
                    "adultVisual": True,
                    "photoRealism": 4,
                    "campusRealism": 4,
                    "brandFit": 4,
                    "artifactRisk": 0,
                    "shotTypeReadable": True,
                    "decision": "needs_review",
                    "reasons": ["codex_imagegen_mode_manual_visual_review_required"],
                },
            )

        decision = str(review["decision"])
        if decision == "approved":
            counts["approved"] += 1
        elif decision == "needs_review":
            counts["needs_review"] += 1
        else:
            counts["rejected"] += 1
        row["status"] = "missing" if missing_local_image else (status_from_decision(decision) if not dry_run else "vision_dry_run")
        row["error"] = "; ".join(map(str, review.get("reasons", [])))
        row["updatedAt"] = now_utc()
        report.append({field: review[field] for field in VISION_QA_JSONL_FIELDS})

    jsonl_path = paths.reports / "vision_qa_report.jsonl"
    if append and jsonl_path.exists():
        selected_asset_ids = {str(row.get("assetId")) for row in report}
        report = [row for row in read_jsonl(jsonl_path) if str(row.get("assetId")) not in selected_asset_ids] + report
    write_jsonl(jsonl_path, report)
    csv_rows = [{**row, "reasons": json.dumps(row.get("reasons", []), ensure_ascii=False)} for row in report]
    write_csv(paths.reports / "vision_qa_report.csv", csv_rows, VISION_QA_JSONL_FIELDS)
    if update_manifest and not dry_run:
        write_generation_outputs(paths, rows)
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Seolleyeon AI image vision QA.")
    parser.add_argument("--root", default=None, help="Workspace root. Defaults to the repository root.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--shot_type", choices=["face_card", "silhouette_card", "vibe_card"], default=None)
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--no_update_manifest", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    counts = run_vision_qa(
        root=args.root,
        limit=args.limit,
        shot_type=args.shot_type,
        dry_run=args.dry_run,
        model=args.model,
        update_manifest=not args.no_update_manifest,
        append=args.append,
    )
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
