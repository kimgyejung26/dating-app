"""An intentional config change is declared one key and one operation at a time.

`--allow-removal KEY` used to switch off *every* check for that key: declaring
a removal also let a value change through unnoticed. And a single declaration
never justifies whatever else the diff happens to contain - the 2026-09-08
deploy dropped nineteen variables at once, so one approved removal must not
become a door the other eighteen walk through.

The contract these tests hold:

  * `--allow-remove-key K`  authorises the removal of K, nothing else
  * `--allow-add-key K`     authorises the addition of K, nothing else
  * `--allow-change-key K`  authorises a value change of K, nothing else
  * exact, case-sensitive key names - no globs, prefixes or regexes
  * a declaration that matches nothing in the diff is itself a failure
  * platform-injected variables cannot be declared at all
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import functions_env_regression_guard as guard  # noqa: E402

LIVE = {
    "ENVIRONMENT": "production",
    "JOB_QUEUE_MODE": "cloud_tasks",
    "AVATAR_UPLOAD_ALLOWED_UIDS": "uid_a,uid_b",
    "AVATAR_UPLOAD_ALLOWED_UIDS_OLD": "uid_legacy",
    "RESEND_API_KEY": "re_live_do_not_print",
    "K_SERVICE": "replaceavatargeneration",
}
FUNCTION = "replaceAvatarGeneration"


def candidate_without(*keys):
    return {
        k: v for k, v in LIVE.items()
        if k not in guard.PLATFORM_MANAGED_KEYS and k not in keys
    }


def check(candidate, **authorizations):
    return guard.plan_functions_env_check(
        deployed={FUNCTION: LIVE}, candidate=candidate, **authorizations
    )


def kinds(result):
    return sorted((f.kind, f.key) for f in result.findings)


# ---------------------------------------------------------------------------
# The baseline that must never need a flag
# ---------------------------------------------------------------------------

def test_a_code_only_deploy_needs_no_authorization():
    """LIVE == CANDIDATE 인 배포에 새 플래그가 필요하면 안 된다."""
    result = check(candidate_without())

    assert result.ok, [f.render() for f in result.findings]


def test_an_undeclared_removal_is_refused():
    result = check(candidate_without("AVATAR_UPLOAD_ALLOWED_UIDS"))

    assert not result.ok
    assert ("removed", "AVATAR_UPLOAD_ALLOWED_UIDS") in kinds(result)


# ---------------------------------------------------------------------------
# remove / add / change, each scoped to its own operation
# ---------------------------------------------------------------------------

def test_a_declared_removal_of_exactly_that_key_passes():
    result = check(
        candidate_without("AVATAR_UPLOAD_ALLOWED_UIDS"),
        allowed_removals=["AVATAR_UPLOAD_ALLOWED_UIDS"],
    )

    assert result.ok, [f.render() for f in result.findings]


def test_a_declared_addition_of_exactly_that_key_passes():
    candidate = candidate_without()
    candidate["AVATAR_SOFT_REVIEW_ENABLED"] = "true"

    result = check(candidate, allowed_additions=["AVATAR_SOFT_REVIEW_ENABLED"])

    assert result.ok, [f.render() for f in result.findings]


def test_a_declared_value_change_of_exactly_that_key_passes():
    candidate = candidate_without()
    candidate["JOB_QUEUE_MODE"] = "inline"

    result = check(candidate, allowed_changes=["JOB_QUEUE_MODE"])

    assert result.ok, [f.render() for f in result.findings]


def test_authorising_a_removal_does_not_authorise_a_change_of_the_same_key():
    """이게 기존 --allow-removal 의 실제 결함이다."""
    candidate = candidate_without()
    candidate["AVATAR_UPLOAD_ALLOWED_UIDS"] = "uid_c"

    result = check(candidate, allowed_removals=["AVATAR_UPLOAD_ALLOWED_UIDS"])

    assert not result.ok
    assert ("changed", "AVATAR_UPLOAD_ALLOWED_UIDS") in kinds(result)


def test_authorising_a_change_does_not_authorise_a_removal_of_the_same_key():
    result = check(
        candidate_without("JOB_QUEUE_MODE"),
        allowed_changes=["JOB_QUEUE_MODE"],
    )

    assert not result.ok
    assert ("removed", "JOB_QUEUE_MODE") in kinds(result)


def test_authorising_an_addition_does_not_authorise_a_removal_of_the_same_key():
    result = check(
        candidate_without("JOB_QUEUE_MODE"),
        allowed_additions=["JOB_QUEUE_MODE"],
    )

    assert not result.ok
    assert ("removed", "JOB_QUEUE_MODE") in kinds(result)


# ---------------------------------------------------------------------------
# One declaration never covers the rest of the diff
# ---------------------------------------------------------------------------

def test_a_second_undeclared_removal_still_fails():
    result = check(
        candidate_without("AVATAR_UPLOAD_ALLOWED_UIDS", "JOB_QUEUE_MODE"),
        allowed_removals=["AVATAR_UPLOAD_ALLOWED_UIDS"],
    )

    assert not result.ok
    assert ("removed", "JOB_QUEUE_MODE") in kinds(result)
    assert ("removed", "AVATAR_UPLOAD_ALLOWED_UIDS") not in kinds(result)


def test_an_undeclared_change_alongside_a_declared_removal_still_fails():
    candidate = candidate_without("AVATAR_UPLOAD_ALLOWED_UIDS")
    candidate["JOB_QUEUE_MODE"] = "inline"

    result = check(candidate, allowed_removals=["AVATAR_UPLOAD_ALLOWED_UIDS"])

    assert not result.ok
    assert ("changed", "JOB_QUEUE_MODE") in kinds(result)


def test_the_2026_09_08_incident_is_not_unlocked_by_one_declaration():
    """하나를 허용해도 나머지 삭제 때문에 계속 막혀야 한다."""
    incomplete = {"ENVIRONMENT": "production"}

    result = check(incomplete, allowed_removals=["AVATAR_UPLOAD_ALLOWED_UIDS"])

    assert not result.ok
    removed = {key for kind, key in kinds(result) if kind == "removed"}
    assert "JOB_QUEUE_MODE" in removed
    assert "RESEND_API_KEY" in removed


# ---------------------------------------------------------------------------
# Exact means exact
# ---------------------------------------------------------------------------

def test_a_differently_cased_key_authorises_nothing():
    result = check(
        candidate_without("AVATAR_UPLOAD_ALLOWED_UIDS"),
        allowed_removals=["avatar_upload_allowed_uids"],
    )

    assert not result.ok


def test_a_declaration_does_not_reach_a_key_that_merely_shares_a_prefix():
    """AVATAR_UPLOAD_ALLOWED_UIDS 허용이 ..._OLD 까지 열어주면 안 된다."""
    result = check(
        candidate_without("AVATAR_UPLOAD_ALLOWED_UIDS", "AVATAR_UPLOAD_ALLOWED_UIDS_OLD"),
        allowed_removals=["AVATAR_UPLOAD_ALLOWED_UIDS"],
    )

    assert not result.ok
    assert ("removed", "AVATAR_UPLOAD_ALLOWED_UIDS_OLD") in kinds(result)


@pytest.mark.parametrize("pattern", ["AVATAR_*", "AVATAR_UPLOAD_ALLOWED_UID?", "*", ".*"])
def test_wildcards_are_rejected_rather_than_quietly_matching_nothing(pattern):
    with pytest.raises(guard.GuardError):
        check(candidate_without("AVATAR_UPLOAD_ALLOWED_UIDS"), allowed_removals=[pattern])


# ---------------------------------------------------------------------------
# A declaration that matches nothing is an operator error
# ---------------------------------------------------------------------------

def test_a_declaration_that_matches_nothing_fails():
    """오타나 잘못된 함수 지정을 배포 전에 잡는다."""
    result = check(candidate_without(), allowed_removals=["AVATAR_UPLOAD_ALLOWED_UIDS"])

    assert not result.ok
    assert [f.kind for f in result.findings] == ["unused_authorization"]


def test_a_declaration_observed_on_any_checked_function_counts_as_used():
    other = {k: v for k, v in LIVE.items() if k != "AVATAR_UPLOAD_ALLOWED_UIDS"}

    result = guard.plan_functions_env_check(
        deployed={"first": LIVE, "second": other},
        candidate=candidate_without("AVATAR_UPLOAD_ALLOWED_UIDS"),
        allowed_removals=["AVATAR_UPLOAD_ALLOWED_UIDS"],
    )

    assert result.ok, [f.render() for f in result.findings]


# ---------------------------------------------------------------------------
# Malformed declarations fail fast
# ---------------------------------------------------------------------------

def test_the_same_key_cannot_be_declared_for_two_operations():
    with pytest.raises(guard.GuardError) as excinfo:
        check(
            candidate_without("JOB_QUEUE_MODE"),
            allowed_removals=["JOB_QUEUE_MODE"],
            allowed_changes=["JOB_QUEUE_MODE"],
        )

    assert "JOB_QUEUE_MODE" in str(excinfo.value)


def test_a_duplicated_declaration_is_rejected():
    with pytest.raises(guard.GuardError):
        check(
            candidate_without("JOB_QUEUE_MODE"),
            allowed_removals=["JOB_QUEUE_MODE", "JOB_QUEUE_MODE"],
        )


@pytest.mark.parametrize("key", ["", "   ", "JOB QUEUE MODE", "JOB=QUEUE"])
def test_a_key_that_cannot_name_a_variable_is_rejected(key):
    with pytest.raises(guard.GuardError):
        check(candidate_without(), allowed_removals=[key])


def test_a_platform_injected_variable_cannot_be_declared():
    """K_SERVICE 같은 값은 env 파일이 소유하지 않는다. 허용 대상이 아니다."""
    with pytest.raises(guard.GuardError) as excinfo:
        check(candidate_without(), allowed_removals=["K_SERVICE"])

    assert "K_SERVICE" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Secrets stay redacted through every operation
# ---------------------------------------------------------------------------

SECRET_VALUES = ("re_live_do_not_print", "re_live_replacement", "re_live_new")


def _rendered(result):
    return " ".join(f.render() for f in result.findings)


def test_a_changed_secret_fails_without_printing_either_value():
    candidate = candidate_without()
    candidate["RESEND_API_KEY"] = "re_live_replacement"

    result = check(candidate)
    rendered = _rendered(result)

    assert ("changed", "RESEND_API_KEY") in kinds(result)
    assert not any(secret in rendered for secret in SECRET_VALUES)
    assert "sha256:" in rendered


def test_a_removed_secret_fails_without_printing_its_value():
    result = check(candidate_without("RESEND_API_KEY"))

    assert ("removed", "RESEND_API_KEY") in kinds(result)
    assert not any(secret in _rendered(result) for secret in SECRET_VALUES)


def test_a_changed_uid_allowlist_does_not_print_the_uids():
    """실계정 식별자가 배포 로그에 남으면 안 된다."""
    candidate = candidate_without()
    candidate["AVATAR_UPLOAD_ALLOWED_UIDS"] = "uid_a,uid_b,uid_c"

    result = check(candidate)
    rendered = _rendered(result)

    assert ("changed", "AVATAR_UPLOAD_ALLOWED_UIDS") in kinds(result)
    assert "uid_a" not in rendered and "uid_c" not in rendered
    assert "sha256:" in rendered


def test_an_added_secret_fails_without_printing_its_value():
    candidate = candidate_without()
    candidate["STRIPE_API_KEY"] = "sk_live_never_print"

    result = check(candidate)

    assert ("added", "STRIPE_API_KEY") in kinds(result)
    assert "sk_live_never_print" not in _rendered(result)


def test_a_declared_secret_change_still_prints_no_value(capsys):
    candidate = candidate_without()
    candidate["RESEND_API_KEY"] = "re_live_new"

    result = check(candidate, allowed_changes=["RESEND_API_KEY"])
    guard.print_report(result, {FUNCTION: LIVE})
    printed = capsys.readouterr()

    assert result.ok
    assert not any(secret in printed.out + printed.err for secret in SECRET_VALUES)


def test_the_full_report_of_a_failing_run_prints_no_secret_value(capsys):
    candidate = candidate_without("RESEND_API_KEY")
    candidate["JOB_QUEUE_MODE"] = "inline"

    result = check(candidate)
    guard.print_report(result, {FUNCTION: LIVE})
    printed = capsys.readouterr()

    assert not result.ok
    assert not any(secret in printed.out + printed.err for secret in SECRET_VALUES)


# ---------------------------------------------------------------------------
# The CLI surface
# ---------------------------------------------------------------------------

@pytest.fixture
def cli(tmp_path, monkeypatch):
    monkeypatch.setattr(
        guard, "deployed_env_for", lambda function, project, region: LIVE
    )

    def run(env_text, *flags):
        env_file = tmp_path / ".env.seolleyeon-final"
        env_file.write_text(env_text, encoding="utf-8")
        return guard.main([
            "--project", "seolleyeon-final",
            "--region", "asia-northeast3",
            "--env-file", str(env_file),
            "--function", FUNCTION,
            "--source-dir", str(tmp_path / "no-source"),
            *flags,
        ])

    return run


COMPLETE_ENV = "".join(
    f"{k}={v}\n" for k, v in LIVE.items() if k not in guard.PLATFORM_MANAGED_KEYS
)
WITHOUT_ALLOWLIST = "".join(
    line + "\n" for line in COMPLETE_ENV.splitlines()
    if not line.startswith("AVATAR_UPLOAD_ALLOWED_UIDS=")
)


def test_cli_passes_a_code_only_deploy_with_no_flags(cli):
    assert cli(COMPLETE_ENV) == 0


def test_cli_refuses_an_undeclared_removal(cli):
    assert cli(WITHOUT_ALLOWLIST) == 1


def test_cli_accepts_an_exact_remove_key_declaration(cli):
    """Phase 4 가 실제로 실행할 명령 그대로."""
    assert cli(WITHOUT_ALLOWLIST, "--allow-remove-key", "AVATAR_UPLOAD_ALLOWED_UIDS") == 0


def test_cli_still_refuses_the_removal_that_rode_along(cli):
    without_both = "".join(
        line + "\n" for line in COMPLETE_ENV.splitlines()
        if not line.startswith("AVATAR_UPLOAD_ALLOWED_UIDS")
    )

    assert cli(without_both, "--allow-remove-key", "AVATAR_UPLOAD_ALLOWED_UIDS") == 1
    assert cli(
        without_both,
        "--allow-remove-key", "AVATAR_UPLOAD_ALLOWED_UIDS",
        "--allow-remove-key", "AVATAR_UPLOAD_ALLOWED_UIDS_OLD",
    ) == 0


def test_cli_accepts_add_and_change_declarations(cli):
    added = COMPLETE_ENV + "AVATAR_SOFT_REVIEW_ENABLED=true\n"
    assert cli(added) == 1
    assert cli(added, "--allow-add-key", "AVATAR_SOFT_REVIEW_ENABLED") == 0

    changed = COMPLETE_ENV.replace("JOB_QUEUE_MODE=cloud_tasks", "JOB_QUEUE_MODE=inline")
    assert cli(changed) == 1
    assert cli(changed, "--allow-change-key", "JOB_QUEUE_MODE") == 0


def test_cli_rejects_the_old_broad_flags_by_name(cli, capsys):
    """--allow-removal 은 같은 키의 값 변경까지 통과시켰다. 조용히 사라지면 안 된다."""
    with pytest.raises(SystemExit) as excinfo:
        cli(WITHOUT_ALLOWLIST, "--allow-removal", "AVATAR_UPLOAD_ALLOWED_UIDS")

    assert excinfo.value.code != 0
    assert "--allow-remove-key" in capsys.readouterr().err


def test_cli_reports_a_declaration_failure_without_a_traceback(cli, capsys):
    assert cli(COMPLETE_ENV, "--allow-remove-key", "K_SERVICE") == 1
    assert "K_SERVICE" in capsys.readouterr().out
