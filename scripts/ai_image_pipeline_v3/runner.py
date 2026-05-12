from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .config import (
    DEFAULT_CONCURRENCY,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_QUALITY,
    DEFAULT_SIZE,
    MAX_ATTEMPTS,
    RESERVE_FEMALE_COUNT,
    RESERVE_MALE_COUNT,
    TARGET_APPROVED_ASSETS,
    TARGET_APPROVED_IDENTITIES,
    pipeline_paths,
)
from .contact_sheet import generate_grouped_contact_sheets
from .duplicate_audit import audit_duplicates
from .generate import generate_images
from .identity_consistency import run_identity_consistency_qa
from .manifest import load_generation_manifest
from .prepare import prepare_assets
from .qa import promote_approved_assets, qa_images
from .run_gates import assert_full_run_allowed, evaluate_run_gate_result, write_run_gate
from .shot_type_qa import run_shot_type_qa
from .summary import summarize_images
from .targeting import apply_reserve_policy, summarize_target_state, target_reached
from .vision_qa import run_vision_qa


PRESETS: dict[str, dict[str, Any]] = {
    "dry-run": {
        "female_count": 1,
        "male_count": 0,
        "limit": 3,
        "dry_run": True,
        "reserve_female_count": 0,
        "reserve_male_count": 0,
        "stage": "custom",
    },
    "smoke": {
        "female_count": 2,
        "male_count": 1,
        "limit": 9,
        "dry_run": False,
        "reserve_female_count": 0,
        "reserve_male_count": 0,
        "stage": "smoke",
    },
    "pilot": {
        "female_count": 12,
        "male_count": 12,
        "limit": 72,
        "dry_run": False,
        "reserve_female_count": 0,
        "reserve_male_count": 0,
        "stage": "pilot",
    },
    "full": {
        "female_count": 120,
        "male_count": 120,
        "limit": None,
        "dry_run": False,
        "reserve_female_count": RESERVE_FEMALE_COUNT,
        "reserve_male_count": RESERVE_MALE_COUNT,
        "stage": "full",
    },
}


def _sum_generation_counts(parts: list[dict[str, int]]) -> dict[str, int]:
    keys = {key for part in parts for key in part}
    return {key: sum(int(part.get(key, 0)) for part in parts) for key in sorted(keys)}


def run_target_approved_workflow(
    *,
    root: Path | str | None,
    dry_run: bool,
    force: bool,
    qa: bool,
    target_approved_identities: int,
    target_approved_assets: int,
    max_attempts: int,
    stop_when_target_reached: bool,
    concurrency: int,
    stage: str,
) -> dict[str, Any]:
    paths = pipeline_paths(root)
    before_state = summarize_target_state(root=root)
    if stop_when_target_reached and target_reached(
        load_generation_manifest(paths),
        target_identities=target_approved_identities,
        target_assets=target_approved_assets,
    ):
        summary = summarize_images(root=root)
        return {
            "dryRun": dry_run,
            "targetAlreadyReached": True,
            "targetState": before_state,
            "generation": {"selected": 0, "completed": 0, "skipped": 0, "failed": 0, "dry_run": 0, "waiting_reference": 0},
            "qa": {},
            "summary": summary,
        }

    reserve = apply_reserve_policy(root=root, max_attempts=max_attempts) if not dry_run else {"rejectedIdentities": 0, "activatedReserveIdentities": 0}

    if dry_run:
        generation = generate_images(
            root=root,
            dry_run=True,
            force=force,
            retry_only=False,
            active_only=True,
            max_attempts=max_attempts,
            concurrency=concurrency,
        )
        qa_result: dict[str, Any] = {}
        vision: dict[str, Any] = {}
        identity: dict[str, Any] = {}
    else:
        face_generation = generate_images(
            root=root,
            dry_run=False,
            force=force,
            retry_only=True,
            shot_type="face_card",
            active_only=True,
            max_attempts=max_attempts,
            concurrency=concurrency,
        )
        face_file_qa = (
            qa_images(root=root, shot_type="face_card", force=force, approve_integrity_only=True, copy_approved=False)
            if qa
            else {}
        )
        face_vision = run_vision_qa(root=root, shot_type="face_card", dry_run=False, append=False) if qa else {}
        face_promotion = promote_approved_assets(root=root, shot_type="face_card", force=force) if qa else {}
        dependent_generation = _sum_generation_counts(
            [
                generate_images(
                    root=root,
                    dry_run=False,
                    force=force,
                    retry_only=True,
                    shot_type=shot,
                    active_only=True,
                    approved_face_reference=True,
                    max_attempts=max_attempts,
                    concurrency=concurrency,
                )
                for shot in ("silhouette_card", "vibe_card")
            ]
        )
        file_qa = qa_images(root=root, force=force, approve_integrity_only=True, copy_approved=False) if qa else {}
        vision = run_vision_qa(
            root=root,
            shot_types=("silhouette_card", "vibe_card"),
            dry_run=False,
            append=True,
        ) if qa else {}
        promotion = promote_approved_assets(root=root, force=force) if qa else {}
        identity = run_identity_consistency_qa(root=root, max_attempts=max_attempts) if qa else {}
        shot_type_qa = run_shot_type_qa(root=root) if qa else {}
        qa_result = {
            "faceFileQA": face_file_qa,
            "faceVisionQA": face_vision,
            "facePromotion": face_promotion,
            "fileQA": file_qa,
            "visionQA": vision,
            "promotion": promotion,
            "shotTypeQA": shot_type_qa,
            "identityQA": identity,
        }
        generation = _sum_generation_counts([face_generation, dependent_generation])
        apply_reserve_policy(root=root, max_attempts=max_attempts)

    duplicate = audit_duplicates(root=root)
    contact_sheets = generate_grouped_contact_sheets(root=root, stage=stage if stage in {"pilot", "full"} else "pilot")
    summary = summarize_images(root=root)
    target_state = summarize_target_state(root=root)
    return {
        "dryRun": dry_run,
        "targetApprovedIdentities": target_approved_identities,
        "targetApprovedAssets": target_approved_assets,
        "stopWhenTargetReached": stop_when_target_reached,
        "targetReached": int(target_state.get("approvedIdentities", 0)) >= target_approved_identities
        and int(target_state.get("approvedAssets", 0)) >= target_approved_assets,
        "targetStateBefore": before_state,
        "targetState": target_state,
        "reservePolicy": reserve,
        "generation": generation,
        "qa": qa_result,
        "visionQA": vision,
        "duplicateAudit": duplicate,
        "contactSheets": [str(result.output_path) for result in contact_sheets],
        "summary": summary,
    }


def run_pipeline(
    *,
    mode: str,
    root: Path | str | None = None,
    dry_run: bool | None = None,
    force: bool = False,
    qa: bool = True,
    allow_full_without_pilot_gate: bool = False,
    target_approved_identity: str | None = None,
    target_approved_identities: int = TARGET_APPROVED_IDENTITIES,
    target_approved_assets: int = TARGET_APPROVED_ASSETS,
    reserve_female_count: int | None = None,
    reserve_male_count: int | None = None,
    max_attempts: int = MAX_ATTEMPTS,
    stop_when_target_reached: bool = False,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict[str, object]:
    if mode == "target-approved-identity":
        if not target_approved_identity:
            raise ValueError("target_approved_identity is required for target-approved-identity mode.")
        effective_dry_run = bool(dry_run)
        generation = generate_images(
            root=root,
            limit=3,
            dry_run=effective_dry_run,
            force=force,
            target_approved_identity=target_approved_identity,
            max_attempts=max_attempts,
            approved_face_reference=True,
            concurrency=concurrency,
        )
        qa_result = qa_images(root=root, limit=3) if qa and not effective_dry_run else {}
        summary = summarize_images(root=root)
        return {
            "mode": mode,
            "dryRun": effective_dry_run,
            "targetApprovedIdentity": target_approved_identity,
            "generation": generation,
            "qa": qa_result,
            "summary": summary,
        }

    if mode == "target-approved":
        effective_dry_run = bool(dry_run)
        result = run_target_approved_workflow(
            root=root,
            dry_run=effective_dry_run,
            force=force,
            qa=qa,
            target_approved_identities=target_approved_identities,
            target_approved_assets=target_approved_assets,
            max_attempts=max_attempts,
            stop_when_target_reached=stop_when_target_reached,
            concurrency=concurrency,
            stage="full",
        )
        result["mode"] = mode
        return result

    preset = dict(PRESETS[mode])
    effective_dry_run = bool(preset["dry_run"] if dry_run is None else dry_run)
    paths = pipeline_paths(root)
    if mode == "full" and not allow_full_without_pilot_gate:
        assert_full_run_allowed(paths)
    effective_reserve_female = int(preset["reserve_female_count"] if reserve_female_count is None else reserve_female_count)
    effective_reserve_male = int(preset["reserve_male_count"] if reserve_male_count is None else reserve_male_count)
    prepare_result = prepare_assets(
        root=root,
        female_count=int(preset["female_count"]),
        male_count=int(preset["male_count"]),
        reserve_female_count=effective_reserve_female,
        reserve_male_count=effective_reserve_male,
        limit=preset["limit"],
        dry_run=effective_dry_run,
        force=force,
        replace_manifest=effective_dry_run or mode in {"smoke", "pilot"},
        model=DEFAULT_MODEL,
        size=DEFAULT_SIZE,
        quality=DEFAULT_QUALITY,
        output_format=DEFAULT_OUTPUT_FORMAT,
    )

    if effective_dry_run:
        generation = generate_images(
            root=root,
            limit=preset["limit"],
            dry_run=True,
            force=force,
            active_only=True,
            max_attempts=max_attempts,
            concurrency=concurrency,
        )
        qa_result: dict[str, Any] = {}
        duplicate: dict[str, Any] = audit_duplicates(root=root)
        contact_sheets: list[str] = []
    else:
        result = run_target_approved_workflow(
            root=root,
            dry_run=False,
            force=force,
            qa=qa,
            target_approved_identities=target_approved_identities if mode == "full" else int(preset["female_count"]) + int(preset["male_count"]),
            target_approved_assets=target_approved_assets if mode == "full" else int(preset["female_count"] + preset["male_count"]) * 3,
            max_attempts=max_attempts,
            stop_when_target_reached=stop_when_target_reached,
            concurrency=concurrency,
            stage=str(preset["stage"]),
        )
        generation = result["generation"]
        qa_result = result["qa"]
        duplicate = result["duplicateAudit"]
        contact_sheets = list(result["contactSheets"])

    summary = summarize_images(root=root)
    result = {
        "mode": mode,
        "dryRun": effective_dry_run,
        "preparedAssets": prepare_result.asset_count,
        "preparedSpecs": prepare_result.specs_count,
        "reserveFemaleCount": effective_reserve_female,
        "reserveMaleCount": effective_reserve_male,
        "generation": generation,
        "qa": qa_result,
        "duplicateAudit": duplicate,
        "contactSheets": contact_sheets,
        "targetState": summarize_target_state(root=root),
        "summary": summary,
    }
    if mode in {"smoke", "pilot", "full"}:
        gate_passed, gate_reasons = evaluate_run_gate_result(result)
        write_run_gate(
            paths,
            mode=mode,
            dry_run=effective_dry_run,
            passed=gate_passed,
            result=result,
            reasons=gate_reasons,
        )
        if mode in {"smoke", "pilot"} and not effective_dry_run and not gate_passed:
            raise RuntimeError(f"{mode} run gate failed: {', '.join(gate_reasons)}")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Seolleyeon AI image pipeline presets.")
    parser.add_argument("--root", default=None, help="Workspace root. Defaults to the repository root.")
    parser.add_argument("--mode", choices=sorted([*PRESETS, "target-approved", "target-approved-identity"]), default="dry-run")
    parser.add_argument("--dry_run", action="store_true", help="Override selected mode and avoid Codex $imagegen prompts.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing/generated files only when explicitly passed.")
    parser.add_argument("--skip_qa", action="store_true")
    parser.add_argument("--target_approved_identity", default=None)
    parser.add_argument("--target_approved_identities", type=int, default=TARGET_APPROVED_IDENTITIES)
    parser.add_argument("--target_approved_assets", type=int, default=TARGET_APPROVED_ASSETS)
    parser.add_argument("--reserve_female_count", type=int, default=None)
    parser.add_argument("--reserve_male_count", type=int, default=None)
    parser.add_argument("--max_attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--stop_when_target_reached", action="store_true")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument(
        "--allow_full_without_pilot_gate",
        action="store_true",
        help="Emergency override for full run gate. Do not use in normal operations.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_pipeline(
        mode=args.mode,
        root=args.root,
        dry_run=True if args.dry_run else None,
        force=args.force,
        qa=not args.skip_qa,
        allow_full_without_pilot_gate=args.allow_full_without_pilot_gate,
        target_approved_identity=args.target_approved_identity,
        target_approved_identities=args.target_approved_identities,
        target_approved_assets=args.target_approved_assets,
        reserve_female_count=args.reserve_female_count,
        reserve_male_count=args.reserve_male_count,
        max_attempts=args.max_attempts,
        stop_when_target_reached=args.stop_when_target_reached,
        concurrency=args.concurrency,
    )
    print(result)
    return 0
