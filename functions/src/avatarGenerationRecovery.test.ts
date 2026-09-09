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
