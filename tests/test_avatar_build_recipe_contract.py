"""The avatar-worker build recipe, enforced instead of remembered.

2026-09-10: a production worker image was built with the correct execution
region (asia-southeast1) and pushed to the correct registry (asia-southeast1),
but its source was staged in the US multi-region bucket
``seolleyeon-final_cloudbuild``. The currently-serving image's own build had used
``seolleyeon-final_asia-southeast1_cloudbuild``.

The flag that decides this is ``--default-buckets-behavior=REGIONAL_USER_OWNED_BUCKET``.
It was already in ``scripts/staging_avatar_live_setup.ps1``. The failing build
reconstructed its command from ``cloudbuild.avatar-worker.yaml`` plus a previous
build's metadata, and the flag is expressible in neither -- the YAML has no
options stanza for source staging, and ``gcloud builds describe`` reports the
bucket that resulted, not the flag that chose it. gcloud fell back silently.

So the guard is not a docs note. It is:
  * one machine-checkable contract (scripts/avatar_build_contract.py)
  * one sanctioned entrypoint that asks the contract for its argv
  * this test, which fails if anything else submits an avatar-worker build

`test_incident_recipe_is_rejected` is the incident itself: correct region,
correct registry, correct YAML, missing regional staging flag.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from avatar_build_contract import (  # noqa: E402
    BUCKET_BEHAVIOR,
    BUCKET_BEHAVIOR_FLAG,
    BUILD_REGION,
    CONFIG_PATH,
    PROJECT,
    REGISTRY_HOST,
    BuildRecipeError,
    build_submit_argv,
    image_uri,
    validate_submit_argv,
)

GOOD_SHA = "46485a05e592d6a09d0f29d90673a958829a75c6"
GOOD_TAG = "qa-107-46485a05"

# The single sanctioned callsite. Anything else in scripts/ that submits an
# avatar-worker build is a bypass.
SANCTIONED_BUILD_SCRIPTS = {
    "build_avatar_worker.ps1",
    "staging_avatar_live_setup.ps1",
}


def _argv(**overrides):
    argv = build_submit_argv(sha=GOOD_SHA, tag=GOOD_TAG)
    for flag, value in overrides.items():
        prefix = f"--{flag.replace('_', '-')}="
        argv = [a for a in argv if not a.startswith(prefix)]
        if value is not None:
            argv.append(f"{prefix}{value}")
    return argv


# ---------------------------------------------------------------------------
# The recipe
# ---------------------------------------------------------------------------


def test_sanctioned_recipe_passes():
    validate_submit_argv(build_submit_argv(sha=GOOD_SHA, tag=GOOD_TAG))


def test_sanctioned_recipe_pins_every_invariant():
    argv = build_submit_argv(sha=GOOD_SHA, tag=GOOD_TAG)
    joined = " ".join(argv)
    assert f"--project={PROJECT}" in joined
    assert f"--region={BUILD_REGION}" in joined
    assert f"{BUCKET_BEHAVIOR_FLAG}={BUCKET_BEHAVIOR}" in joined
    assert f"--config={CONFIG_PATH}" in joined
    assert image_uri(GOOD_TAG).startswith(f"{REGISTRY_HOST}/")


def test_incident_recipe_is_rejected():
    """2026-09-10, exactly: everything right except regional source staging."""

    argv = [a for a in build_submit_argv(sha=GOOD_SHA, tag=GOOD_TAG)
            if not a.startswith(f"{BUCKET_BEHAVIOR_FLAG}=")]
    with pytest.raises(BuildRecipeError) as exc:
        validate_submit_argv(argv)
    assert str(exc.value) == "regional_source_staging_missing"


@pytest.mark.parametrize(
    "argv,code",
    [
        ([a for a in build_submit_argv(sha=GOOD_SHA, tag=GOOD_TAG)
          if not a.startswith("--region=")], "build_region_missing"),
        (_argv(region="us-central1"), "build_region_mismatch"),
        (_argv(region="asia-northeast3"), "build_region_mismatch"),
        (_argv(**{"default_buckets_behavior": "DEFAULT_BUCKET"}),
         "regional_source_staging_mismatch"),
        ([a for a in build_submit_argv(sha=GOOD_SHA, tag=GOOD_TAG)
          if not a.startswith("--project=")], "project_missing"),
        (_argv(project="seolleyeon"), "historical_project_forbidden"),
        (_argv(config="cloudbuild.yaml"), "config_mismatch"),
    ],
    ids=[
        "missing --region",
        "wrong region (us)",
        "seoul region",
        "non-regional bucket behavior",
        "missing --project",
        "historical project seolleyeon",
        "wrong cloudbuild config",
    ],
)
def test_broken_recipes_are_rejected(argv, code):
    with pytest.raises(BuildRecipeError) as exc:
        validate_submit_argv(argv)
    assert str(exc.value) == code


def test_wrong_registry_region_is_rejected():
    argv = _argv(substitutions="_IMAGE=asia-northeast3-docker.pkg.dev/seolleyeon-final/r/i:t")
    with pytest.raises(BuildRecipeError):
        validate_submit_argv(argv)


def test_a_correct_yaml_does_not_make_a_correct_command():
    """The YAML cannot express source staging, so it can never be the authority."""

    yaml_text = (REPO_ROOT / CONFIG_PATH).read_text(encoding="utf-8")
    assert "default-buckets-behavior" not in yaml_text
    assert "gcs-source-staging-dir" not in yaml_text
    assert "bucket" not in yaml_text.lower()


def test_sha_and_tag_are_validated_before_any_call():
    for bad_sha in ("", "HEAD", "46485a05", "z" * 40):
        with pytest.raises(BuildRecipeError):
            build_submit_argv(sha=bad_sha, tag=GOOD_TAG)
    for bad_tag in ("", "bad tag", "-leading", "x" * 200):
        with pytest.raises(BuildRecipeError):
            build_submit_argv(sha=GOOD_SHA, tag=bad_tag)


# ---------------------------------------------------------------------------
# No bypasses
# ---------------------------------------------------------------------------

_SUBMIT_RE = re.compile(r"gcloud\s+builds\s+submit", re.IGNORECASE)


def _executable_scripts():
    for path in SCRIPTS.rglob("*"):
        if path.suffix.lower() in {".ps1", ".sh", ".bash", ".py"} and path.is_file():
            yield path


def test_no_unsanctioned_avatar_worker_build_submit_in_scripts():
    """Docs may show examples; executable scripts may not invent a recipe."""

    offenders = []
    for path in _executable_scripts():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not _SUBMIT_RE.search(text):
            continue
        if "cloudbuild.avatar-worker.yaml" not in text:
            continue
        if path.name not in SANCTIONED_BUILD_SCRIPTS:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], (
        "avatar-worker Cloud Build submitted outside the sanctioned entrypoint: "
        f"{offenders}. Call scripts/build_avatar_worker.ps1 instead."
    )


@pytest.mark.parametrize("script_name", sorted(SANCTIONED_BUILD_SCRIPTS))
def test_sanctioned_scripts_carry_the_regional_flag(script_name):
    """A sanctioned callsite that spells the command out must still be correct."""

    text = (SCRIPTS / script_name).read_text(encoding="utf-8", errors="ignore")
    if not _SUBMIT_RE.search(text):
        # build_avatar_worker.ps1 delegates argv construction to the contract.
        assert "avatar_build_contract" in text, script_name
        return
    assert f"{BUCKET_BEHAVIOR_FLAG}={BUCKET_BEHAVIOR}" in text, script_name
    assert "--region=" in text or "--region " in text, script_name


def test_sanctioned_entrypoint_refuses_before_calling_gcloud():
    """Preflight ordering matters: a wrong SHA must not reach Cloud Build."""

    text = (SCRIPTS / "build_avatar_worker.ps1").read_text(encoding="utf-8")
    head_check = text.index("head_sha_mismatch")
    dirty_check = text.index("worktree_dirty")
    invocation = text.rindex("& $argv[0]")
    assert head_check < invocation
    assert dirty_check < invocation
