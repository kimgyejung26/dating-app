from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

from .config import repo_root_from_here


PROMPT_SOURCE_RELATIVE = Path(
    "lib/ai_recommend_model/seolleyeon_ai_profile_prompt_v3_package/seolleyeon_ai_profile_prompt_v3.py"
)


def prompt_source_path(repo_root: Path | None = None) -> Path:
    root = repo_root_from_here() if repo_root is None else Path(repo_root).resolve()
    return root / PROMPT_SOURCE_RELATIVE


def load_prompt_module(repo_root: Path | None = None) -> ModuleType:
    path = prompt_source_path(repo_root)
    if not path.exists():
        raise FileNotFoundError(f"Prompt builder not found: {path}")
    spec = importlib.util.spec_from_file_location("seolleyeon_ai_profile_prompt_v3", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import prompt builder from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generate_asset_records(
    *,
    female_count: int,
    male_count: int,
    start_female: int,
    start_male: int,
    seed: int,
    id_width: int,
    repo_root: Path | None = None,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    module = load_prompt_module(repo_root)
    specs = module.generate_specs(
        female_count=female_count,
        male_count=male_count,
        start_female=start_female,
        start_male=start_male,
        seed=seed,
        id_width=id_width,
    )
    assets: list[Mapping[str, Any]] = []
    for spec in specs:
        assets.extend(module.build_asset_records(spec))
    return specs, assets


def build_asset_records_from_specs(
    specs: list[Mapping[str, Any]],
    *,
    repo_root: Path | None = None,
) -> list[Mapping[str, Any]]:
    module = load_prompt_module(repo_root)
    assets: list[Mapping[str, Any]] = []
    for spec in specs:
        assets.extend(module.build_asset_records(spec))
    return assets
