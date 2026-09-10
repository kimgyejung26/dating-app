"""The avatar-worker Cloud Build recipe, as data rather than as a habit.

On 2026-09-10 a production worker image was built with the right execution
region and the right registry, but its source was staged in the US multi-region
bucket. The canonical recipe in ``scripts/staging_avatar_live_setup.ps1`` already
carried ``--default-buckets-behavior=REGIONAL_USER_OWNED_BUCKET``, which is what
puts source in ``<project>_<region>_cloudbuild``. The command was reconstructed
from ``cloudbuild.avatar-worker.yaml`` plus a previous build's metadata instead,
and that flag is expressible in neither: the YAML has no options stanza for
source staging, and ``gcloud builds describe`` reports the resulting bucket, not
the flag that chose it. gcloud then fell back to the global bucket silently.

The repository already knew this. ``tests/test_avatar_build_region_guard.py``
asserted the flag's presence, with a docstring saying regional execution alone
still stages source in the US bucket -- and it was passing throughout, because it
guards the *script* and the operator never ran the script. That is the real gap:
a guard on a file cannot cover an ad-hoc invocation.

So the lesson is not "remember the flag". This module is the one definition; the
PowerShell entrypoint asks it for the argv rather than spelling a command out,
and a CI test asserts nothing else in the repository submits an avatar-worker
build behind its back.
"""

from __future__ import annotations

import re
from typing import Sequence

PROJECT = "seolleyeon-final"
BUILD_REGION = "asia-southeast1"
REGISTRY_HOST = "asia-southeast1-docker.pkg.dev"
REPOSITORY = "seolleyeon-avatar-repo"
IMAGE_NAME = "seolleyeon-avatar-worker"
CONFIG_PATH = "cloudbuild.avatar-worker.yaml"

# The flag that decides where source is staged. Kept as the single authority
# rather than adding --gcs-source-staging-dir beside it: this one is what the
# currently-serving image's build used, and two flags aiming at the same bucket
# is how they drift apart.
BUCKET_BEHAVIOR_FLAG = "--default-buckets-behavior"
BUCKET_BEHAVIOR = "REGIONAL_USER_OWNED_BUCKET"

# The project was renamed; builds must never target the historical one, and the
# Seoul region hosts other services but never this image.
FORBIDDEN_TOKENS = ("asia-northeast3", "seoul")
FORBIDDEN_PROJECTS = ("seolleyeon",)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class BuildRecipeError(ValueError):
    """Raised with a stable code so a preflight can refuse before calling gcloud."""


def image_uri(tag: str) -> str:
    return f"{REGISTRY_HOST}/{PROJECT}/{REPOSITORY}/{IMAGE_NAME}:{tag}"


def build_submit_argv(*, sha: str, tag: str, source: str = ".") -> list[str]:
    """The only sanctioned avatar-worker Cloud Build invocation."""

    if not _SHA_RE.fullmatch(str(sha or "").strip().lower()):
        raise BuildRecipeError("build_sha_invalid")
    if not _TAG_RE.fullmatch(str(tag or "").strip()):
        raise BuildRecipeError("build_tag_invalid")
    return [
        "gcloud", "builds", "submit", source,
        f"--project={PROJECT}",
        f"--region={BUILD_REGION}",
        f"{BUCKET_BEHAVIOR_FLAG}={BUCKET_BEHAVIOR}",
        f"--config={CONFIG_PATH}",
        f"--substitutions=_IMAGE={image_uri(tag)}",
    ]


def validate_submit_argv(argv: Sequence[str]) -> None:
    """Refuse a command that would repeat any known regional-provenance failure.

    Raises BuildRecipeError; returns None when the command is sanctioned.
    """

    tokens = [str(token) for token in argv]
    joined = " ".join(tokens).lower()

    if tokens[:3] != ["gcloud", "builds", "submit"]:
        raise BuildRecipeError("not_a_builds_submit")

    def value_of(flag: str) -> str | None:
        for index, token in enumerate(tokens):
            if token.startswith(f"{flag}="):
                return token.split("=", 1)[1]
            if token == flag and index + 1 < len(tokens):
                return tokens[index + 1]
        return None

    project = value_of("--project")
    if project is None:
        raise BuildRecipeError("project_missing")
    if project in FORBIDDEN_PROJECTS:
        raise BuildRecipeError("historical_project_forbidden")
    if project != PROJECT:
        raise BuildRecipeError("project_mismatch")

    region = value_of("--region")
    if region is None:
        raise BuildRecipeError("build_region_missing")
    if region != BUILD_REGION:
        raise BuildRecipeError("build_region_mismatch")

    behavior = value_of(BUCKET_BEHAVIOR_FLAG)
    if behavior is None:
        # The 2026-09-10 incident, exactly: correct region, correct registry,
        # correct YAML, and source staged in the US multi-region bucket.
        raise BuildRecipeError("regional_source_staging_missing")
    if behavior != BUCKET_BEHAVIOR:
        raise BuildRecipeError("regional_source_staging_mismatch")

    config = value_of("--config")
    if config != CONFIG_PATH:
        raise BuildRecipeError("config_mismatch")

    substitutions = value_of("--substitutions")
    if not substitutions or "_IMAGE=" not in substitutions:
        raise BuildRecipeError("image_substitution_missing")
    image = substitutions.split("_IMAGE=", 1)[1].split(",")[0]
    if not image.startswith(f"{REGISTRY_HOST}/"):
        raise BuildRecipeError("registry_region_mismatch")
    if f"/{PROJECT}/{REPOSITORY}/{IMAGE_NAME}:" not in image:
        raise BuildRecipeError("image_path_mismatch")

    for token in FORBIDDEN_TOKENS:
        if token in joined:
            raise BuildRecipeError("forbidden_region_reference")


__all__ = [
    "BUCKET_BEHAVIOR",
    "BUCKET_BEHAVIOR_FLAG",
    "BUILD_REGION",
    "CONFIG_PATH",
    "IMAGE_NAME",
    "PROJECT",
    "REGISTRY_HOST",
    "REPOSITORY",
    "BuildRecipeError",
    "build_submit_argv",
    "image_uri",
    "validate_submit_argv",
]
