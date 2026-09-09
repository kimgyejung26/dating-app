import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_USER_GENERATION_ATTEMPTS,
  planNewGenerationRecovery,
} from "./avatarGenerationRecovery";

function decide(status: string, extra: Record<string, unknown> = {}, attempts = 1) {
  return planNewGenerationRecovery({
    currentJobData: { status, ...extra },
    userAvatar: { status },
    generationAttemptCount: attempts,
  });
}

test("QA needs_review lets the user start a new generation with new photos", () => {
  const decision = decide("needs_review", { errorCode: "qa_requires_review" });
  assert.equal(decision.allowed, true);
  if (!decision.allowed) return;
  // 같은 generation 재시도가 아니라 현재 generation 을 끝내고 lock 을 푼다.
  assert.equal(decision.jobUpdate.status, "cancelled");
  assert.equal(decision.jobUpdate.errorCode, "avatar_generation_replaced_by_user");
  assert.equal(decision.releasesSourceLock, true);
});

test("terminal failure and no previewable candidates also allow a new generation", () => {
  for (const status of ["terminal_failed", "no_previewable_candidates", "failed"]) {
    assert.equal(decide(status).allowed, true, `${status} should allow restart`);
  }
});

test("provider outcome unknown blocks a new generation until reconciled", () => {
  // 이미 과금된 생성이 존재할 수 있다. 재조정 전에는 새 generation 도 막는다.
  const decision = decide("needs_review", {
    errorCode: "azure_unknown_post_send_outcome",
  });
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.equal(decision.reasonCode, "avatar_provider_outcome_unknown");
});

test("an active generation cannot be replaced", () => {
  // preview_ready 는 2026-09-09 에 이 목록에서 빠졌다. 후보가 나온 뒤에도
  // 사용자는 사진을 바꿔 다시 만들 수 있어야 하고, 선택 화면이 그 버튼을
  // 제공한다. 나머지 상태는 여전히 교체를 막는다.
  for (const status of [
    "queued",
    "running",
    "provider_inflight",
    "qa_pending",
    "approval_copying",
  ]) {
    const decision = decide(status);
    assert.equal(decision.allowed, false, `${status} must not be replaceable`);
    if (decision.allowed) continue;
    assert.equal(decision.reasonCode, "avatar_generation_in_progress");
  }
});

test("an approved avatar is never replaced by this path", () => {
  const decision = decide("approved");
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.equal(decision.reasonCode, "avatar_already_approved");
});

test("the generation attempt limit is enforced", () => {
  const decision = decide("terminal_failed", {}, MAX_USER_GENERATION_ATTEMPTS);
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.equal(decision.reasonCode, "avatar_generation_limit_reached");
});

test("an active generation claim blocks replacement even on a terminal status", () => {
  const decision = decide("terminal_failed", {
    generationClaim: { state: "active" },
  });
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.equal(decision.reasonCode, "avatar_provider_outcome_unknown");
});

// ---------------------------------------------------------------------------
// Replace eligibility contract (P0, 2026-09-09)
//
// The avatar select screen offers "사진을 바꾸고 다시 만들기" while the job is
// preview_ready. Treating preview_ready as in-progress made the server reject
// the one action the UI offers, so the button failed every time it was pressed.
// ---------------------------------------------------------------------------

test("preview_ready lets the user start over with new photos", () => {
  // 후보는 생성됐지만 사용자가 아직 approve 하지 않았다. 선택 화면의 canonical
  // action 이므로 서버가 허용해야 한다.
  const decision = decide("preview_ready");
  assert.equal(decision.allowed, true);
  if (!decision.allowed) return;
  // 기존 replacement 계약을 그대로 따른다: 옛 job 은 취소되고 source lock 이 풀린다.
  assert.equal(decision.jobUpdate.status, "cancelled");
  assert.equal(decision.jobUpdate.errorCode, "avatar_generation_replaced_by_user");
  assert.equal(decision.releasesSourceLock, true);
  assert.equal(decision.userAvatarStatus, "none");
  // 옛 후보가 나중에 approve 되지 않도록 current job pointer 를 지운다.
  assert.ok(decision.privateMediaClearFields.includes("currentAvatarJobId"));
});

test("statuses that are genuinely mid-flight still block a replacement", () => {
  for (const status of [
    "queued",
    "running",
    "generating",
    "provider_inflight",
    "generated",
    "persisted",
    "qa_pending",
  ]) {
    const decision = decide(status);
    assert.equal(decision.allowed, false, `${status} must block replacement`);
    if (decision.allowed) return;
    assert.equal(decision.reasonCode, "avatar_generation_in_progress", status);
  }
});

test("reconciliation_required blocks replacement with its own reason code", () => {
  // 이 상태는 provider outcome 이나 state 가 어긋났다는 뜻이라 새 generation 이
  // 이전 상태와 충돌할 수 있다. generic not_replaceable 로 흘러가면 의도가
  // 사라지므로 명시적으로 분류한다.
  const decision = decide("reconciliation_required");
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.equal(decision.reasonCode, "avatar_reconciliation_required");
});

test("reconciliation_required is not silently treated as replaceable or in-progress", () => {
  const decision = decide("reconciliation_required");
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.notEqual(decision.reasonCode, "avatar_generation_not_replaceable");
  assert.notEqual(decision.reasonCode, "avatar_generation_in_progress");
});

test("approved stays terminal and unchanged by the replace fix", () => {
  const decision = decide("approved");
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.equal(decision.reasonCode, "avatar_already_approved");
});

test("preview_ready with an unknown provider outcome still blocks", () => {
  // provider 결과 미확인은 preview_ready 여부보다 우선한다.
  const decision = decide("preview_ready", {
    errorCode: "azure_unknown_post_send_outcome",
  });
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.equal(decision.reasonCode, "avatar_provider_outcome_unknown");
});

test("preview_ready with an active generation claim still blocks", () => {
  const decision = decide("preview_ready", {
    generationClaim: { state: "active" },
  });
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.equal(decision.reasonCode, "avatar_provider_outcome_unknown");
});

test("preview_ready respects the per-user generation attempt limit", () => {
  const decision = decide("preview_ready", {}, MAX_USER_GENERATION_ATTEMPTS);
  assert.equal(decision.allowed, false);
  if (decision.allowed) return;
  assert.equal(decision.reasonCode, "avatar_generation_limit_reached");
});

// ---------------------------------------------------------------------------
// Rejection observability (2026-09-09)
//
// Production rejects replaceAvatarGeneration with 400 while a source-level
// replay of the same documents says the replacement is allowed. The callable
// returns the reason in the response body only, so the server logs nothing we
// can classify. These cover the sanitized log payload, not the transport.
// ---------------------------------------------------------------------------

import {
  REPLACE_REJECTION_STAGES,
  buildReplaceCompletionLog,
  buildReplaceRejectionLog,
  shortHash,
} from "./avatarGenerationRecovery";
import { HttpsError } from "firebase-functions/v2/https";

const SECRET_UID = "AlNkhWSecretUid0123456789QR22";
const SECRET_REQUEST_ID = "3f2504e0-4f89-11d3-9a0c-0305e82c3301";

test("every rejection stage is a canonical snake_case token", () => {
  for (const stage of REPLACE_REJECTION_STAGES) {
    assert.match(stage, /^[a-z][a-z0-9_]*$/, stage);
  }
  // The stages the audit enumerated must all exist.
  for (const required of [
    "app_user_resolution",
    "uid_validation",
    "request_argument_validation",
    "client_request_id_validation",
    "user_document_lookup",
    "job_ownership_validation",
    "replacement_policy",
    "transaction_commit",
    "unexpected",
  ]) {
    assert.ok(REPLACE_REJECTION_STAGES.includes(required as never), required);
  }
});

test("a policy rejection reports its stage, https code and internal reason", () => {
  const entry = buildReplaceRejectionLog({
    stage: "replacement_policy",
    error: new HttpsError("failed-precondition", "avatar_generation_in_progress"),
    uidHash: shortHash(SECRET_UID),
  });
  assert.equal(entry.event, "avatar_replace_rejected");
  assert.equal(entry.stage, "replacement_policy");
  assert.equal(entry.httpsCode, "failed-precondition");
  assert.equal(entry.reasonCode, "avatar_generation_in_progress");
});

test("the attempt limit keeps its distinct resource-exhausted code", () => {
  const entry = buildReplaceRejectionLog({
    stage: "replacement_policy",
    error: new HttpsError("resource-exhausted", "avatar_generation_limit_reached"),
    uidHash: "",
  });
  assert.equal(entry.httpsCode, "resource-exhausted");
  assert.equal(entry.reasonCode, "avatar_generation_limit_reached");
});

test("a user-facing message is never logged verbatim, only fingerprinted", () => {
  // resolveAuthedAppUser throws human sentences. Those are not internal codes,
  // so they must not be copied into the log line.
  const message = "학생 인증이 완료된 계정으로 다시 로그인해주세요.";
  const entry = buildReplaceRejectionLog({
    stage: "app_user_resolution",
    error: new HttpsError("failed-precondition", message),
    uidHash: "",
  });
  assert.equal(entry.reasonCode, "non_canonical_message");
  assert.notEqual(entry.messageHash, "");
  assert.ok(!JSON.stringify(entry).includes(message));
  // The fingerprint must be stable so the operator can identify which message.
  assert.equal(
    entry.messageHash,
    buildReplaceRejectionLog({
      stage: "app_user_resolution",
      error: new HttpsError("failed-precondition", message),
      uidHash: "",
    }).messageHash,
  );
});

test("a non-HttpsError is classified as unexpected without leaking its text", () => {
  const entry = buildReplaceRejectionLog({
    stage: "transaction_commit",
    error: new Error(`firestore write failed for ${SECRET_UID}`),
    uidHash: "",
  });
  assert.equal(entry.httpsCode, "internal");
  assert.equal(entry.reasonCode, "non_canonical_message");
  assert.ok(!JSON.stringify(entry).includes(SECRET_UID));
});

test("no rejection log carries a raw uid, email, request id or token", () => {
  const entry = buildReplaceRejectionLog({
    stage: "client_request_id_validation",
    error: new HttpsError(
      "invalid-argument",
      `clientRequestId is invalid. ${SECRET_REQUEST_ID} test-user@example.invalid`,
    ),
    uidHash: shortHash(SECRET_UID),
  });
  const serialized = JSON.stringify(entry);
  for (const secret of [SECRET_UID, SECRET_REQUEST_ID, "test-user@example.invalid", "example.invalid"]) {
    assert.ok(!serialized.includes(secret), `${secret} leaked into ${serialized}`);
  }
});

test("shortHash is irreversible-looking, stable and not the input", () => {
  const hashed = shortHash(SECRET_UID);
  assert.equal(hashed, shortHash(SECRET_UID));
  assert.notEqual(hashed, SECRET_UID);
  assert.ok(!SECRET_UID.includes(hashed));
  assert.match(hashed, /^[0-9a-f]{12}$/);
  assert.equal(shortHash(""), "");
});

test("a completion log records the outcome without dumping user state", () => {
  const entry = buildReplaceCompletionLog({
    uidHash: shortHash(SECRET_UID),
    result: {
      replaced: true,
      duplicate: false,
      previousJobId: "avatar_job_2276bSECRET",
      generationAttemptCount: 1,
    },
  });
  assert.equal(entry.event, "avatar_replace_succeeded");
  assert.equal(entry.stage, "complete");
  assert.equal(entry.duplicate, false);
  assert.equal(entry.generationAttemptCount, 1);
  // The job id identifies a user's generation; only its fingerprint may ship.
  assert.ok(!JSON.stringify(entry).includes("avatar_job_2276bSECRET"));
});
