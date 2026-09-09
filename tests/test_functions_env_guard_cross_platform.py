"""The deploy guard must read gcloud the same way on Windows and on Linux.

2026-09-09: the guard reported `RESEND_FROM_EMAIL` as *changed* on a Windows
operator machine while the live value and the candidate value were byte for
byte identical. Nothing had changed; the value simply contains Hangul.

The corruption is in the child, not in the parent. gcloud is itself a Python
program: when its stdout is a pipe it encodes with the Windows console code
page, and characters that code page cannot represent become `?`.

    live value seen by the guard:  '??? <noreply@seolleyeon.com>'
    candidate value from the file: '설레연 <noreply@seolleyeon.com>'

Both of those decode as clean ASCII, so `encoding="utf-8"` on the parent never
notices - the guard simply compares two different strings and refuses a deploy
that changes nothing. Exporting `PYTHONIOENCODING=utf-8` before running the
guard made it pass, which is the workaround this module exists to retire: the
guard now sets the child's output encoding itself.

These tests drive the real subprocess boundary. A fake `gcloud` is placed on
PATH and reproduces the observed behaviour exactly - UTF-8 out when the child
is told which encoding to use, lossy code-page replacement when it is not.
"""

from __future__ import annotations

import io
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import functions_env_regression_guard as guard  # noqa: E402

KOREAN_FROM_EMAIL = "설레연 <noreply@seolleyeon.com>"

FAKE_GCLOUD = '''
"""Stand-in for the real gcloud CLI, matching its observed output behaviour."""
import json
import os
import sys

mode = os.environ.get("FAKE_GCLOUD_MODE", "ok")

if mode == "exit-nonzero":
    sys.stderr.buffer.write(b"ERROR: (gcloud.run.services.describe) NOT_FOUND\\n")
    sys.exit(2)

if mode == "invalid-utf8":
    # A byte sequence no UTF-8 decoder can accept.
    sys.stdout.buffer.write(b'{"spec": "\\xff\\xfe not utf-8"}')
    sys.exit(0)

if mode == "malformed-json":
    sys.stdout.buffer.write(b'{"spec": {"template": ')
    sys.exit(0)

with open(os.environ["FAKE_GCLOUD_PAYLOAD"], encoding="utf-8") as handle:
    payload = json.load(handle)
text = json.dumps(payload, ensure_ascii=False, indent=2)

# The real gcloud writes through Python's stdout wrapper. PYTHONIOENCODING
# decides the encoding; without it Windows falls back to the console code page
# and substitutes "?" for every character it cannot represent.
requested = os.environ.get("PYTHONIOENCODING")
if requested:
    sys.stdout.buffer.write(text.encode(requested.split(":")[0], errors="strict"))
else:
    sys.stdout.buffer.write(text.encode("cp437", errors="replace"))
'''


def _service_payload(env: dict) -> dict:
    return {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {"env": [{"name": k, "value": v} for k, v in env.items()]}
                    ]
                }
            }
        }
    }


@pytest.fixture
def fake_gcloud(tmp_path, monkeypatch):
    """Put a fake `gcloud` on PATH and return a setter for its response."""
    script = tmp_path / "fake_gcloud.py"
    script.write_text(FAKE_GCLOUD, encoding="utf-8")

    bindir = tmp_path / "bin"
    bindir.mkdir()
    if os.name == "nt":
        launcher = bindir / "gcloud.cmd"
        launcher.write_text(
            '@echo off\r\n"{exe}" "{script}" %*\r\n'.format(
                exe=sys.executable, script=script
            ),
            encoding="utf-8",
        )
    else:
        launcher = bindir / "gcloud"
        launcher.write_text(
            '#!/bin/sh\nexec "{exe}" "{script}" "$@"\n'.format(
                exe=sys.executable, script=script
            ),
            encoding="utf-8",
        )
        launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ.get("PATH", ""))

    def respond(env=None, *, mode="ok"):
        monkeypatch.setenv("FAKE_GCLOUD_MODE", mode)
        if env is not None:
            payload = tmp_path / "payload.json"
            payload.write_text(
                json.dumps(_service_payload(env), ensure_ascii=False), encoding="utf-8"
            )
            monkeypatch.setenv("FAKE_GCLOUD_PAYLOAD", str(payload))

    return respond


@pytest.fixture
def windows_operator_shell(monkeypatch):
    """The environment the false positive was actually reported from."""
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)
    monkeypatch.delenv("PYTHONUTF8", raising=False)


def _fetch(function="replaceAvatarGeneration"):
    return guard.deployed_env_for(function, "seolleyeon-final", "asia-northeast3")


# ---------------------------------------------------------------------------
# The reported defect
# ---------------------------------------------------------------------------

def test_hangul_value_survives_a_windows_shell_without_pythonioencoding(
    fake_gcloud, windows_operator_shell
):
    """RESEND_FROM_EMAIL 은 손상되지 않고 그대로 읽혀야 한다."""
    fake_gcloud({"RESEND_FROM_EMAIL": KOREAN_FROM_EMAIL})

    live = _fetch()

    assert live["RESEND_FROM_EMAIL"] == KOREAN_FROM_EMAIL


def test_the_phase1_false_positive_does_not_recur(fake_gcloud, windows_operator_shell):
    """같은 값을 changed 로 보고하면 이유 없이 배포가 막힌다."""
    fake_gcloud({
        "JOB_QUEUE_MODE": "cloud_tasks",
        "RESEND_FROM_EMAIL": KOREAN_FROM_EMAIL,
    })
    candidate = guard.parse_env_file(
        "JOB_QUEUE_MODE=cloud_tasks\n"
        "RESEND_FROM_EMAIL=" + KOREAN_FROM_EMAIL + "\n"
    )

    result = guard.plan_functions_env_check(
        deployed={"replaceAvatarGeneration": _fetch()}, candidate=candidate
    )

    assert result.ok, [f.render() for f in result.findings]


def test_pythonioencoding_is_not_a_correctness_requirement(
    fake_gcloud, windows_operator_shell
):
    """운영자가 환경변수를 export 하지 않아도 결과가 같아야 한다."""
    fake_gcloud({"RESEND_FROM_EMAIL": KOREAN_FROM_EMAIL})
    without_override = _fetch()

    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        with_override = _fetch()
    finally:
        del os.environ["PYTHONIOENCODING"]

    assert without_override == with_override == {"RESEND_FROM_EMAIL": KOREAN_FROM_EMAIL}


def test_a_real_unicode_change_is_still_reported(fake_gcloud, windows_operator_shell):
    """인코딩을 고쳤다고 진짜 변경까지 통과시키면 안 된다."""
    fake_gcloud({"RESEND_FROM_EMAIL": KOREAN_FROM_EMAIL})
    candidate = {"RESEND_FROM_EMAIL": "설레연 <hello@seolleyeon.com>"}

    result = guard.plan_functions_env_check(
        deployed={"replaceAvatarGeneration": _fetch()}, candidate=candidate
    )

    changed = [f for f in result.findings if f.kind == "changed"]
    assert [f.key for f in changed] == ["RESEND_FROM_EMAIL"]


# ---------------------------------------------------------------------------
# Fail-closed on anything the guard cannot read
# ---------------------------------------------------------------------------

def test_undecodable_stdout_fails_loudly(fake_gcloud, windows_operator_shell):
    """깨진 바이트를 조용히 무시(errors='replace')하면 안 된다."""
    fake_gcloud(mode="invalid-utf8")

    with pytest.raises(guard.GuardError) as excinfo:
        _fetch()

    assert "utf-8" in str(excinfo.value).lower()


def test_malformed_json_fails_loudly(fake_gcloud, windows_operator_shell):
    fake_gcloud(mode="malformed-json")

    with pytest.raises(guard.GuardError):
        _fetch()


def test_a_failing_gcloud_call_fails_closed(fake_gcloud, windows_operator_shell):
    fake_gcloud(mode="exit-nonzero")

    with pytest.raises(guard.GuardError) as excinfo:
        _fetch()

    assert "replaceavatargeneration" in str(excinfo.value).lower()


def test_a_service_with_no_environment_reads_as_empty(
    fake_gcloud, windows_operator_shell
):
    fake_gcloud({})

    assert _fetch() == {}


def test_secret_backed_env_entries_are_not_read_as_values(
    fake_gcloud, windows_operator_shell, tmp_path, monkeypatch
):
    """valueFrom(secretRef) 항목에는 value 가 없다. 빈 문자열로 착각하면 안 된다."""
    fake_gcloud({})
    payload = _service_payload({"JOB_QUEUE_MODE": "cloud_tasks"})
    payload["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "RESEND_API_KEY", "valueFrom": {"secretKeyRef": {"name": "resend"}}}
    )
    path = tmp_path / "secretref.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("FAKE_GCLOUD_PAYLOAD", str(path))

    assert _fetch() == {"JOB_QUEUE_MODE": "cloud_tasks"}


def test_gcloud_is_invoked_without_a_shell(
    fake_gcloud, windows_operator_shell, monkeypatch
):
    """shell=True 는 로케일에 좌우되는 cmd.exe 를 사이에 끼워 넣는다."""
    seen = []
    real_run = subprocess.run

    def spy(*args, **kwargs):
        seen.append(kwargs)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(guard.subprocess, "run", spy)
    fake_gcloud({"JOB_QUEUE_MODE": "cloud_tasks"})

    _fetch()

    assert seen and all(not kwargs.get("shell") for kwargs in seen)


def test_the_report_prints_in_full_on_a_console_that_cannot_encode_a_value(
    tmp_path, monkeypatch
):
    """콘솔 코드페이지 때문에 리포트가 도중에 죽으면 findings 를 못 본다."""
    live = {"JOB_QUEUE_MODE": "cloud_tasks", "RESEND_FROM_EMAIL": KOREAN_FROM_EMAIL}
    monkeypatch.setattr(guard, "deployed_env_for", lambda *a, **k: live)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "JOB_QUEUE_MODE=inline\nRESEND_FROM_EMAIL=" + KOREAN_FROM_EMAIL + "\n",
        encoding="utf-8",
    )
    # cp437 cannot represent Hangul; a strict console is what crashed the run.
    console = io.TextIOWrapper(io.BytesIO(), encoding="cp437", errors="strict")
    monkeypatch.setattr(sys, "stdout", console)

    exit_code = guard.main([
        "--project", "seolleyeon-final",
        "--region", "asia-northeast3",
        "--env-file", str(env_file),
        "--function", "replaceAvatarGeneration",
        "--source-dir", str(tmp_path / "no-source"),
    ])
    console.flush()
    printed = console.buffer.getvalue().decode("cp437")

    assert exit_code == 1
    assert "ENV REGRESSION GUARD: FAIL" in printed
    assert "changed JOB_QUEUE_MODE" in printed


# ---------------------------------------------------------------------------
# Comparison semantics: exact, never normalised
# ---------------------------------------------------------------------------

def test_values_are_compared_exactly_and_never_unicode_normalised():
    """NFC/NFD 를 같다고 보면 토큰·서명 값의 변경을 놓친다."""
    composed = "설"                      # 설, precomposed
    decomposed = "설"        # 설, ᄉ + ᅥ + ᆯ
    assert composed != decomposed

    result = guard.plan_functions_env_check(
        deployed={"fn": {"DISPLAY_NAME": composed}},
        candidate={"DISPLAY_NAME": decomposed},
    )

    assert [f.kind for f in result.findings] == ["changed"]


def test_env_file_representation_differences_are_not_changes():
    """따옴표와 줄바꿈은 표현일 뿐 값이 아니다."""
    crlf_quoted = guard.parse_env_file(
        'JOB_QUEUE_MODE="cloud_tasks"\r\n'
        'RESEND_FROM_EMAIL="' + KOREAN_FROM_EMAIL + '"\r\n'
    )
    lf_bare = guard.parse_env_file(
        "JOB_QUEUE_MODE=cloud_tasks\n"
        "RESEND_FROM_EMAIL=" + KOREAN_FROM_EMAIL + "\n"
    )

    assert crlf_quoted == lf_bare

    result = guard.plan_functions_env_check(
        deployed={"fn": lf_bare}, candidate=crlf_quoted
    )
    assert result.ok, [f.render() for f in result.findings]
