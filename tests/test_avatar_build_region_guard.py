"""Cross-region avatar build guard.

The avatar worker runs on Cloud Run in ``asia-southeast1`` because that is the
only region where this project holds L4 GPU quota. When a build config pushes
the (multi-GB) worker image to the Seoul Artifact Registry instead, every
Cloud Run cold start pulls it back across regions and the transfer is billed.

``tests/test_avatar_retired_generation_paths.py`` already pins the canonical
root config. This module widens that to *every* tracked Cloud Build config, so
a stale copy cannot reintroduce a Seoul destination for the avatar worker.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CANONICAL_REGISTRY_REGION = "asia-southeast1"
CANONICAL_REPOSITORY = "seolleyeon-avatar-repo"
CANONICAL_IMAGE_PREFIX = (
    f"{CANONICAL_REGISTRY_REGION}-docker.pkg.dev/seolleyeon-final/"
    f"{CANONICAL_REPOSITORY}/seolleyeon-avatar-worker"
)

# Only avatar worker destinations are in scope. recs-pipeline and other
# non-avatar artifacts legitimately live in the Seoul repository.
AVATAR_WORKER_IMAGE = re.compile(
    r"(?P<region>[a-z0-9-]+)-docker\.pkg\.dev/"
    r"(?P<project>[a-z0-9-]+)/"
    r"(?P<repository>[a-z0-9-]+)/"
    r"seolleyeon-avatar-worker"
)


def _tracked_cloudbuild_configs() -> list[Path]:
    return sorted(REPO_ROOT.glob("**/cloudbuild*.yaml"))


def _avatar_worker_destinations() -> list[tuple[Path, re.Match[str]]]:
    found: list[tuple[Path, re.Match[str]]] = []
    for config in _tracked_cloudbuild_configs():
        text = config.read_text(encoding="utf-8")
        for match in AVATAR_WORKER_IMAGE.finditer(text):
            found.append((config, match))
    return found


def test_at_least_one_avatar_worker_build_config_is_discovered():
    """Guard the guard: a rename must not silently make this test vacuous."""
    destinations = _avatar_worker_destinations()
    assert destinations, "no avatar worker Cloud Build destination found"
    configs = {config.name for config, _ in destinations}
    assert "cloudbuild.avatar-worker.yaml" in configs


def test_no_cloud_build_config_pushes_the_avatar_worker_outside_singapore():
    violations = []
    for config, match in _avatar_worker_destinations():
        if match.group("region") != CANONICAL_REGISTRY_REGION:
            violations.append(
                f"{config.relative_to(REPO_ROOT).as_posix()}: region "
                f"{match.group('region')!r} != {CANONICAL_REGISTRY_REGION!r}"
            )
        if match.group("repository") != CANONICAL_REPOSITORY:
            violations.append(
                f"{config.relative_to(REPO_ROOT).as_posix()}: repository "
                f"{match.group('repository')!r} != {CANONICAL_REPOSITORY!r}"
            )
    assert not violations, (
        "avatar worker image would be pushed outside the Cloud Run region, "
        "which bills a cross-region pull on every cold start:\n  "
        + "\n  ".join(violations)
    )


def test_canonical_root_config_uses_the_canonical_destination():
    text = (REPO_ROOT / "cloudbuild.avatar-worker.yaml").read_text(encoding="utf-8")
    assert CANONICAL_IMAGE_PREFIX in text


def test_operator_setup_script_defaults_to_the_canonical_registry():
    """The PowerShell entrypoint must not rely on the operator passing -Repository."""
    text = (REPO_ROOT / "scripts" / "staging_avatar_live_setup.ps1").read_text(
        encoding="utf-8"
    )
    assert f'$ArtifactRegistryRegion = "{CANONICAL_REGISTRY_REGION}"' in text
    assert f'$Repository = "{CANONICAL_REPOSITORY}"' in text
    assert f'$WorkerRegion = "{CANONICAL_REGISTRY_REGION}"' in text


def test_operator_setup_script_pins_the_build_to_the_canonical_region():
    """A global Cloud Build runs in the US and ships ~5GB across continents.

    Build execution, source staging, registry and runtime must all sit in
    ``asia-southeast1``; relying on the operator to remember ``--region`` is
    exactly how the cross-region bill came back last time.
    """
    text = (REPO_ROOT / "scripts" / "staging_avatar_live_setup.ps1").read_text(
        encoding="utf-8"
    )
    assert f'$BuildRegion = "{CANONICAL_REGISTRY_REGION}"' in text
    assert "--region=$BuildRegion" in text
    # Regional execution alone still stages source in the US multi-region
    # bucket; this is the supported flag that moves staging into the region.
    assert "--default-buckets-behavior=REGIONAL_USER_OWNED_BUCKET" in text
