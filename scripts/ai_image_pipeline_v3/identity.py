from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import PipelinePaths, local_image_path, profile_number, to_portable_path
from .prompt_source import load_prompt_module


PROFILE_ID_RE = re.compile(r"^(female|male)_(\d+)$")


@dataclass(frozen=True)
class ReservedIdentity:
    profile_id: str
    gender: str
    numeric_id: int
    numeric_token: str


def parse_profile_id(profile_id: str) -> ReservedIdentity:
    match = PROFILE_ID_RE.match(str(profile_id or ""))
    if not match:
        raise ValueError(f"Invalid reserved identity '{profile_id}'. Expected female_001 or male_001.")
    return ReservedIdentity(
        profile_id=f"{match.group(1)}_{match.group(2)}",
        gender=match.group(1),
        numeric_id=int(match.group(2)),
        numeric_token=match.group(2),
    )


def build_reserved_specs(
    reserve_identities: Iterable[str],
    *,
    seed: int,
    id_width: int,
    repo_root: Path | None = None,
) -> list[Mapping[str, Any]]:
    module = load_prompt_module(repo_root)
    specs: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for profile_id in reserve_identities:
        identity = parse_profile_id(profile_id)
        if identity.profile_id in seen:
            continue
        seen.add(identity.profile_id)
        identity_seed = seed + identity.numeric_id
        if identity.gender == "male":
            identity_seed += 100_000
        specs.append(
            module.sample_spec(
                identity.gender,
                identity.numeric_id,
                seed=identity_seed,
                id_width=max(int(id_width), len(identity.numeric_token)),
            )
        )
    return specs


def build_counted_reserved_specs(
    *,
    female_count: int,
    male_count: int,
    start_female: int,
    start_male: int,
    seed: int,
    id_width: int,
    repo_root: Path | None = None,
) -> list[Mapping[str, Any]]:
    identities = [
        *(f"female_{str(start_female + index).zfill(id_width)}" for index in range(max(0, int(female_count)))),
        *(f"male_{str(start_male + index).zfill(id_width)}" for index in range(max(0, int(male_count)))),
    ]
    return build_reserved_specs(identities, seed=seed + 500_000, id_width=id_width, repo_root=repo_root)


def group_profile_ids_by_gender(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {"female": [], "male": []}
    seen: set[str] = set()
    for row in rows:
        profile_id = str(row.get("profileId", ""))
        if profile_id in seen:
            continue
        seen.add(profile_id)
        gender = str(row.get("gender", ""))
        if gender in grouped:
            grouped[gender].append(profile_id)
    return grouped


def filter_rows_for_profile(rows: Iterable[Mapping[str, Any]], profile_id: str | None) -> list[dict[str, Any]]:
    if not profile_id:
        return [dict(row) for row in rows]
    target = parse_profile_id(profile_id).profile_id
    return [dict(row) for row in rows if str(row.get("profileId")) == target]


def face_reference_candidates(
    paths: PipelinePaths,
    asset: Mapping[str, Any],
    *,
    prefer_approved: bool,
) -> list[Path]:
    face_asset = dict(asset)
    face_asset["shotType"] = "face_card"
    face_asset["assetId"] = f"{asset['profileId']}__face_card__v001"
    raw_face = local_image_path(paths, face_asset, root_key="raw")
    approved_face = local_image_path(paths, face_asset, root_key="approved")
    final_face = local_image_path(paths, face_asset, root_key="final")
    if prefer_approved:
        return [final_face, approved_face, raw_face]
    return [raw_face, final_face, approved_face]


def resolve_face_reference_path(
    paths: PipelinePaths,
    asset: Mapping[str, Any],
    *,
    prefer_approved: bool = False,
) -> Path:
    candidates = face_reference_candidates(paths, asset, prefer_approved=prefer_approved)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def attach_resolved_reference(
    paths: PipelinePaths,
    row: Mapping[str, Any],
    *,
    prefer_approved: bool = False,
) -> dict[str, Any]:
    out = dict(row)
    if str(out.get("shotType")) == "face_card":
        out["resolvedReferencePath"] = ""
        return out
    out["resolvedReferencePath"] = to_portable_path(
        resolve_face_reference_path(paths, out, prefer_approved=prefer_approved)
    )
    return out


def public_identity_number(profile_id: str) -> str:
    return profile_number(parse_profile_id(profile_id).profile_id)
