"""Chat-profile bucket IAM contract.

The production incident was a mismatch between two things that were never
checked against each other: the principal that writes chat-profile objects in
code (the avatar worker) and the principal the provisioning script grants
(the Functions runtime). The write path failed with GCS 403 and, because the
copy ran inside the generation pipeline, the whole avatar generation died.

These checks are static: they read the source of truth in the repository, not
live GCP state, so they fail in CI before a deploy repeats the mistake.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER = REPO_ROOT / "lib" / "ai_recommend_model" / "avatar_generation" / "worker.py"
APPLY_SCRIPT = REPO_ROOT / "scripts" / "p1_apply_chat_profile_bucket_staging.sh"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "p1_verify_chat_profile_bucket_iam.sh"
COMMON_SCRIPT = REPO_ROOT / "scripts" / "p1_chat_real_photo_common.sh"

WORKER_SERVICE_ACCOUNT_VAR = "AVATAR_WORKER_SERVICE_ACCOUNT"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_worker_is_the_chat_profile_writer():
    """이 테스트의 전제. 쓰기 주체가 바뀌면 아래 검사도 함께 바뀌어야 한다."""
    worker = _read(WORKER)

    assert "def _persist_chat_real_photo_if_consented(" in worker
    assert "chat_profile_photo_bucket()" in worker
    assert 'storage_path = f"users/{payload.uid}/chat-profile/{photo_id}.jpg"' in worker


def test_provisioning_grants_the_worker_a_scoped_write_role():
    apply_script = _read(APPLY_SCRIPT)

    binding = re.search(
        r'add-iam-policy-binding "gs://\$CHAT_PROFILE_PHOTO_BUCKET" \\\n'
        r'\s+--member="serviceAccount:\$' + WORKER_SERVICE_ACCOUNT_VAR + r'" \\\n'
        r'\s+--role="(?P<role>[^"]+)"',
        apply_script,
    )

    assert binding is not None, (
        "chat-profile 버킷에 아바타 워커 바인딩이 없다. 코드가 쓰는 주체와"
        " IAM 을 받는 주체가 어긋나면 프로덕션에서 403 이 난다."
    )
    assert binding.group("role") in {
        "roles/storage.objectCreator",
        "roles/storage.objectUser",
    }, "워커에게 project 수준이나 광범위한 Storage 권한을 주지 않는다."


def test_the_worker_service_account_has_a_source_controlled_default():
    common = _read(COMMON_SCRIPT)

    assert f'"${{{WORKER_SERVICE_ACCOUNT_VAR}:=' in common


def test_the_verifier_checks_the_worker_binding_too():
    verify = _read(VERIFY_SCRIPT)

    assert f'"${WORKER_SERVICE_ACCOUNT_VAR}"' in verify
    assert "roles/storage.objectCreator" in verify


def test_the_worker_only_creates_objects_in_the_chat_profile_bucket():
    """objectCreator 로 충분하다는 근거를 코드로 고정한다.

    업로드 뒤 metadata 를 다시 쓰면 storage.objects.update 가 필요해지고, 최소
    권한이 한 단계 넓어진다.
    """
    worker = _read(WORKER)
    start = worker.index("def _persist_chat_real_photo_if_consented(")
    end = worker.index("def _write_fixture_file(", start)
    body = worker[start:end]

    assert "upload_from_string(" in body
    assert "blob.patch()" not in body
    assert "download_as_bytes" not in body
    assert ".delete(" not in body
