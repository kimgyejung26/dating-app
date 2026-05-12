from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .distribution_targets import (
    FACE_TYPES,
    LOOKS_LEVEL_BANDS,
    load_distribution_targets,
    looks_level_band,
    normalize_face_type,
)
from .prompt_source import build_asset_records_from_specs, load_prompt_module


def _expanded_items(targets: Mapping[str, int], order: tuple[str, ...]) -> list[str]:
    items: list[str] = []
    for key in order:
        items.extend([key] * int(targets.get(key, 0)))
    return items


def pair_plan(face_targets: Mapping[str, int], looks_targets: Mapping[str, int]) -> list[tuple[str, str]]:
    faces = _expanded_items(face_targets, FACE_TYPES)
    looks = _expanded_items(looks_targets, LOOKS_LEVEL_BANDS)
    if len(faces) != len(looks):
        raise ValueError(f"Face target count {len(faces)} does not match looks target count {len(looks)}.")
    if not faces:
        return []
    # A coprime-ish stride spreads looks bands across face types while preserving exact marginal counts.
    stride = 37 if len(looks) % 37 else 31
    return [(face, looks[(index * stride) % len(looks)]) for index, face in enumerate(faces)]


def scaled_targets(targets: Mapping[str, int], *, count: int, order: tuple[str, ...]) -> dict[str, int]:
    total = sum(int(value) for value in targets.values())
    if total <= 0 or count <= 0:
        return {key: 0 for key in order}
    raw = {key: int(targets.get(key, 0)) * int(count) / total for key in order}
    base = {key: int(raw[key]) for key in order}
    remaining = int(count) - sum(base.values())
    ranked = sorted(order, key=lambda key: (raw[key] - base[key], int(targets.get(key, 0))), reverse=True)
    for key in ranked[:remaining]:
        base[key] += 1
    return base


def _spec_bucket(spec: Mapping[str, Any]) -> tuple[str, str]:
    face = spec.get("face") if isinstance(spec.get("face"), Mapping) else {}
    face_type = normalize_face_type(face.get("faceType") if isinstance(face, Mapping) else "")
    looks_band = looks_level_band(face.get("looksLevel") if isinstance(face, Mapping) else None)
    return face_type, looks_band


def _annotate_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(spec)
    face = out.get("face") if isinstance(out.get("face"), Mapping) else {}
    target_face = normalize_face_type(face.get("faceType") if isinstance(face, Mapping) else "")
    target_looks = float(face.get("looksLevel")) if isinstance(face, Mapping) and face.get("looksLevel") is not None else 0.0
    out["targetFaceType"] = target_face
    out["targetLooksLevel"] = target_looks
    out["targetLooksLevelBand"] = looks_level_band(target_looks)
    return out


def sample_matching_spec(
    *,
    module: Any,
    gender: str,
    numeric_id: int,
    desired_face_type: str,
    desired_looks_band: str,
    seed: int,
    id_width: int,
    max_search: int = 50000,
) -> dict[str, Any]:
    for offset in range(max_search):
        candidate_seed = int(seed) + int(numeric_id) + offset * 104729
        if gender == "male":
            candidate_seed += 100000
        spec = module.sample_spec(gender, int(numeric_id), seed=candidate_seed, id_width=id_width)
        if _spec_bucket(spec) == (desired_face_type, desired_looks_band):
            return _annotate_spec(spec)
    raise RuntimeError(
        f"Could not sample {gender}_{numeric_id:0{id_width}d} for "
        f"{desired_face_type}/{desired_looks_band} after {max_search} attempts."
    )


def build_controlled_specs(
    *,
    root: Path | str | None,
    gender: str,
    count: int,
    start: int,
    seed: int,
    id_width: int,
    face_targets: Mapping[str, int],
    looks_targets: Mapping[str, int],
) -> list[dict[str, Any]]:
    _ = root
    module = load_prompt_module()
    plan = pair_plan(face_targets, looks_targets)
    if len(plan) != int(count):
        raise ValueError(f"Controlled plan for {gender} produced {len(plan)} specs, expected {count}.")
    return [
        sample_matching_spec(
            module=module,
            gender=gender,
            numeric_id=int(start) + index,
            desired_face_type=face_type,
            desired_looks_band=looks_band,
            seed=int(seed) + index * 17,
            id_width=id_width,
        )
        for index, (face_type, looks_band) in enumerate(plan)
    ]


def build_distribution_controlled_asset_records(
    *,
    root: Path | str | None,
    female_count: int,
    male_count: int,
    reserve_female_count: int,
    reserve_male_count: int,
    start_female: int,
    start_male: int,
    start_reserve_female: int,
    start_reserve_male: int,
    seed: int,
    id_width: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    targets = load_distribution_targets(root)
    face_targets = targets["faceTypeTargets"]
    looks_targets = targets["looksLevelBandTargets"]
    specs: list[dict[str, Any]] = []
    specs.extend(
        build_controlled_specs(
            root=root,
            gender="female",
            count=female_count,
            start=start_female,
            seed=seed,
            id_width=id_width,
            face_targets=face_targets["female"],
            looks_targets=looks_targets["female"],
        )
    )
    specs.extend(
        build_controlled_specs(
            root=root,
            gender="male",
            count=male_count,
            start=start_male,
            seed=seed + 100000,
            id_width=id_width,
            face_targets=face_targets["male"],
            looks_targets=looks_targets["male"],
        )
    )
    reserve_specs: list[dict[str, Any]] = []
    if reserve_female_count:
        reserve_specs.extend(
            build_controlled_specs(
                root=root,
                gender="female",
                count=reserve_female_count,
                start=start_reserve_female,
                seed=seed + 500000,
                id_width=id_width,
                face_targets=scaled_targets(face_targets["female"], count=reserve_female_count, order=FACE_TYPES),
                looks_targets=scaled_targets(looks_targets["female"], count=reserve_female_count, order=LOOKS_LEVEL_BANDS),
            )
        )
    if reserve_male_count:
        reserve_specs.extend(
            build_controlled_specs(
                root=root,
                gender="male",
                count=reserve_male_count,
                start=start_reserve_male,
                seed=seed + 600000,
                id_width=id_width,
                face_targets=scaled_targets(face_targets["male"], count=reserve_male_count, order=FACE_TYPES),
                looks_targets=scaled_targets(looks_targets["male"], count=reserve_male_count, order=LOOKS_LEVEL_BANDS),
            )
        )
    for spec in reserve_specs:
        spec["identityScope"] = "reserve"
        spec["isReserve"] = True
    all_specs = [*specs, *reserve_specs]
    assets = [dict(asset) for asset in build_asset_records_from_specs(all_specs)]
    reserve_ids = {str(spec["profileId"]) for spec in reserve_specs}
    for asset in assets:
        if str(asset.get("profileId")) in reserve_ids:
            asset["identityScope"] = "reserve"
            asset["isReserve"] = True
            asset["reserveStatus"] = "standby"
            asset["activeForTarget"] = False
            asset["identityDecision"] = ""
    return all_specs, assets


def distribution_counts(specs: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    face_counts: Counter[str] = Counter()
    looks_counts: Counter[str] = Counter()
    for spec in specs:
        if bool(spec.get("isReserve")):
            continue
        face_counts[str(spec.get("targetFaceType") or "")] += 1
        looks_counts[str(spec.get("targetLooksLevelBand") or "")] += 1
    return {"faceType": dict(face_counts), "looksLevelBand": dict(looks_counts)}
