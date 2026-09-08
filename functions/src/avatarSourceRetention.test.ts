import assert from "node:assert/strict";
import test from "node:test";

import {
  avatarSourceRetentionStateId,
  hasAvatarApprovalProtectedState,
  nextSourceDeletionRetryAt,
  planAvatarSourceRetention,
  redactSourcePhotosAfterDeletion,
  shouldEvaluateAvatarJobSourceRetentionTransition,
  shouldEvaluateClipEmbeddingSourceRetentionTransition,
} from "./avatarSourceRetention";
import { mapTerminalJobStatus } from "./avatarGenerationStateSync";

const uid = "u1";
const jobId = "avatar_u1_photo1";
const privateSourceRef =
  "gs://seolleyeon-final-private-source-photos/users/u1/source/photo1.jpg";

function privateMedia(overrides: Record<string, unknown> = {}) {
  return {
    currentAvatarJobId: jobId,
    currentAvatarSourcePhotoId: "photo1",
    avatarSourceSelectionVersion: 3,
    photoConsent: {
      purposes: {
        avatarGeneration: true,
        clipRecommendation: false,
        sourcePhotoRetention: false,
      },
    },
    clip: { embeddingStatus: "not_requested" },
    sourcePhotos: [
      {
        photoId: "photo1",
        status: "active",
        avatarGenerationState: "current",
        gcsUri: privateSourceRef,
        storageBucket: "seolleyeon-final-private-source-photos",
        storagePath: "users/u1/source/photo1.jpg",
        sha256: "audit-hash",
      },
    ],
    ...overrides,
  };
}

const NOW_MS = Date.parse("2026-09-08T06:00:00.000Z");
const TERMINAL_AT = "2026-09-08T05:39:26.406Z";
const GRACE_MS = 72 * 60 * 60 * 1000;

/**
 * 기본 fixture 는 "콘텐츠 사유로 확실히 종료됐고 공개 상태도 수렴한" job 이다.
 * 원본 삭제가 허용되는 유일한 형태이므로 명시적으로 적는다.
 */
function avatarJob(overrides: Record<string, unknown> = {}) {
  return {
    uid,
    jobId,
    status: "terminal_failed",
    failureClass: "content_terminal",
    failedAt: TERMINAL_AT,
    sourcePhotoIds: ["photo1"],
    sourcePhotoRefs: [privateSourceRef],
    avatarSourceSelectionVersion: 3,
    ...overrides,
  };
}

/** state-sync 가 이미 공개 상태를 이 job 으로 수렴시킨 사용자 문서. */
function convergedUser(jobData: Record<string, unknown>) {
  const mapped = mapTerminalJobStatus(
    String(jobData.status ?? "").toLowerCase(),
    String(jobData.errorCode ?? "").toLowerCase(),
  );
  return { avatar: { status: mapped?.avatarStatus ?? "unknown", jobId } };
}

function plan(
  jobOverrides: Record<string, unknown> = {},
  nowMs = NOW_MS,
  userData?: Record<string, unknown> | null,
) {
  const jobData = avatarJob(jobOverrides);
  return planAvatarSourceRetention({
    uid,
    jobId,
    privateData: privateMedia(),
    jobData,
    userData: userData === undefined ? convergedUser(jobData) : userData,
    userExists: userData !== null,
    nowMs,
  });
}

test("plans source deletion only after irreversible terminal outcome when retention is false", () => {
  const decision = plan();

  assert.equal(decision.action, "claim");
  assert.equal(decision.sourceSelectionVersion, 3);
  assert.deepEqual(decision.refs, [
    {
      bucket: "seolleyeon-final-private-source-photos",
      path: "users/u1/source/photo1.jpg",
    },
  ]);
});

test("non-irreversible avatar statuses are not source deletion terminal", () => {
  for (const status of [
    "preview_ready",
    "needs_review",
    "retryable_failed",
    "no_previewable",
    "no_previewable_candidates",
  ]) {
    assert.deepEqual(plan({ status }), {
      action: "skip",
      reason: "avatar_not_terminal",
    });
  }
  for (const status of ["completed", "approved"]) {
    assert.deepEqual(plan({ status }), {
      action: "skip",
      reason: "approval_without_irreversible_contract",
    });
  }
});

test("completed and approved jobs require an explicit irreversible deletion contract", () => {
  for (const status of ["completed", "approved"]) {
    const decision = plan({
      status,
      sourceDeletionIrreversible: true,
    });

    assert.equal(decision.action, "claim");
  }
});

test("retryable failed jobs keep source available for retry", () => {
  const retryable = plan({
    status: "failed",
    retryable: true,
  });

  assert.equal(retryable.action, "defer");
  assert.equal(
    retryable.action === "defer" ? retryable.reason : "",
    "retryable_failure_source_preserved",
  );
  assert.equal(
    retryable.action === "defer" ? retryable.eligibleAtMs : 0,
    Date.parse(TERMINAL_AT) + GRACE_MS,
  );
});

test("content-terminal failures still delete the source", () => {
  const decision = plan({
    status: "failed",
    retryable: false,
    failureClass: "content_terminal",
  });

  assert.equal(decision.action, "claim");
});

/**
 * 이번 인시던트의 회귀 테스트. Storage 403 은 인프라 실패이고, 인프라 실패가
 * 사용자의 원본 사진을 지워서는 안 된다.
 */
test("infrastructure failures never delete the source inside the recovery window", () => {
  for (const failureClass of [
    "infrastructure_recoverable",
    "provider_ambiguous",
    "reconciliation_required",
  ]) {
    const decision = plan({
      status: "failed",
      failureClass,
      errorCode: "avatar_generation_worker_error",
    });

    assert.equal(decision.action, "defer", failureClass);
    assert.equal(
      decision.action === "defer" ? decision.reason : "",
      "unproven_terminal_source_preserved",
    );
  }
});

/**
 * 분류가 없는 실패는 과거 계약에서 곧바로 삭제로 떨어졌다. 미분류는 증명이
 * 아니므로 파괴적 기본값이 되어서는 안 된다.
 */
test("unclassified failures are not a destructive default", () => {
  for (const status of ["failed", "terminal_failed"]) {
    const decision = plan({ status, failureClass: undefined });
    assert.equal(decision.action, "defer", status);
  }
});

/**
 * 유예는 무기한이 아니다. 동의 없는 원본을 영구 보관하지 않는다.
 */
test("deferred sources converge to deletion once the recovery window expires", () => {
  const jobOverrides = {
    status: "failed",
    failureClass: "infrastructure_recoverable",
  };
  const beforeDeadline = plan(jobOverrides, Date.parse(TERMINAL_AT) + GRACE_MS - 1);
  const afterDeadline = plan(jobOverrides, Date.parse(TERMINAL_AT) + GRACE_MS);

  assert.equal(beforeDeadline.action, "defer");
  assert.equal(afterDeadline.action, "claim");
});

/**
 * 트리거 순서에 의존하지 않는다. 공개 상태 수렴 증거가 없으면 삭제하지 않고
 * 짧은 창으로 유예한다.
 */
test("destructive retention waits for public state convergence evidence", () => {
  // 인시던트 실제 상태: job 은 종료됐는데 공개 문서는 queued 로 남아 있었다.
  const stalePublicState = plan({}, NOW_MS, { avatar: { status: "queued", jobId } });
  const missingAvatarMap = plan({}, NOW_MS, {});

  for (const decision of [stalePublicState, missingAvatarMap]) {
    assert.equal(decision.action, "defer");
    assert.equal(
      decision.action === "defer" ? decision.reason : "",
      "awaiting_public_state_convergence",
    );
    assert.equal(
      decision.action === "defer" ? decision.eligibleAtMs : 0,
      NOW_MS + 15 * 60 * 1000,
    );
  }
});

test("cancelled generations delete the source once public state converged", () => {
  assert.equal(
    plan({
      status: "cancelled",
    }).action,
    "claim",
  );
});

test("approval and approval-in-progress public states protect source deletion unconditionally", () => {
  for (const status of ["approved", "approval_copying", "approval_copy_failed"]) {
    assert.equal(hasAvatarApprovalProtectedState({ avatar: { status } }), true);
  }
  assert.equal(hasAvatarApprovalProtectedState({ avatar: { status: "completed" } }), false);
});

test("retention consent prevents source deletion", () => {
  const decision = planAvatarSourceRetention({
    uid,
    jobId,
    privateData: privateMedia({
      photoConsent: {
        purposes: {
          avatarGeneration: true,
          clipRecommendation: false,
          sourcePhotoRetention: true,
        },
      },
    }),
    jobData: avatarJob(),
    userData: convergedUser(avatarJob()),
  });

  assert.deepEqual(decision, { action: "skip", reason: "retained_by_consent" });
});

test("running avatar status is never eligible", () => {
  assert.deepEqual(plan({ status: "running" }), {
    action: "skip",
    reason: "avatar_not_terminal",
  });
});

test("selection version mismatch blocks stale deletion claims", () => {
  const decision = planAvatarSourceRetention({
    uid,
    jobId,
    privateData: privateMedia({ avatarSourceSelectionVersion: 4 }),
    jobData: avatarJob({ avatarSourceSelectionVersion: 3 }),
    userData: convergedUser(avatarJob({ avatarSourceSelectionVersion: 3 })),
  });

  assert.deepEqual(decision, {
    action: "skip",
    reason: "selection_version_mismatch",
  });
});

test("clip recommendation consent waits for terminal clip state", () => {
  const decision = planAvatarSourceRetention({
    uid,
    jobId,
    privateData: privateMedia({
      photoConsent: {
        purposes: {
          avatarGeneration: true,
          clipRecommendation: true,
          sourcePhotoRetention: false,
        },
      },
      clip: { embeddingStatus: "pending" },
    }),
    jobData: avatarJob(),
    clipData: { status: "running", sourcePhotoRefs: [privateSourceRef] },
  });

  assert.deepEqual(decision, { action: "skip", reason: "clip_not_terminal" });
});

test("terminal clip document allows deletion after irreversible avatar terminal", () => {
  const decision = planAvatarSourceRetention({
    uid,
    jobId,
    privateData: privateMedia({
      photoConsent: {
        purposes: {
          avatarGeneration: true,
          clipRecommendation: true,
          sourcePhotoRetention: false,
        },
      },
      clip: { embeddingStatus: "pending" },
    }),
    jobData: avatarJob(),
    clipData: { status: "completed", sourcePhotoRefs: [privateSourceRef] },
  });

  assert.equal(decision.action, "claim");
});

test("already deleted state is represented outside sourcePhotos", () => {
  const sourcePhotos = redactSourcePhotosAfterDeletion(
    privateMedia().sourcePhotos,
    "photo1",
  );
  const redacted = sourcePhotos[0];

  assert.equal(redacted.status, "source_deleted");
  assert.equal(redacted.sourceDeleted, true);
  assert.equal("gcsUri" in redacted, false);
  assert.equal("storageBucket" in redacted, false);
  assert.equal("storagePath" in redacted, false);
  assert.equal("sourceDeletion" in redacted, false);
  assert.equal("updatedAt" in redacted, false);
});

test("only UID-bound private source refs are eligible", () => {
  const decision = planAvatarSourceRetention({
    uid,
    jobId,
    privateData: privateMedia({
      sourcePhotos: [
        {
          photoId: "photo1",
          status: "active",
          avatarGenerationState: "current",
          gcsUri: "gs://seolleyeon-final-avatar-temp/users/u1/jobs/job1/source.png",
        },
      ],
    }),
    jobData: avatarJob(),
    userData: convergedUser(avatarJob()),
  });

  assert.deepEqual(decision, {
    action: "skip",
    reason: "missing_uid_bound_source_ref",
  });
});

test("state ids and retry schedule are deterministic and bounded", () => {
  assert.equal(
    avatarSourceRetentionStateId("u1", "photo1"),
    avatarSourceRetentionStateId("u1", "photo1"),
  );
  assert.equal(
    nextSourceDeletionRetryAt({ attempts: 1, nowMs: 1_000 })?.getTime(),
    301_000,
  );
  assert.equal(nextSourceDeletionRetryAt({ attempts: 5, nowMs: 1_000 }), null);
});

test("avatar retention runs only when a job enters an irreversible terminal state", () => {
  assert.equal(
    shouldEvaluateAvatarJobSourceRetentionTransition({
      beforeData: { status: "running" },
      afterData: { status: "terminal_failed" },
    }),
    true,
  );
  assert.equal(
    shouldEvaluateAvatarJobSourceRetentionTransition({
      beforeData: { status: "terminal_failed", updatedAt: "old" },
      afterData: { status: "terminal_failed", updatedAt: "new" },
    }),
    false,
  );
  assert.equal(
    shouldEvaluateAvatarJobSourceRetentionTransition({
      beforeData: { status: "completed" },
      afterData: { status: "completed", sourceDeletionIrreversible: true },
    }),
    true,
  );
});

test("clip retention runs only when the clip enters a terminal state", () => {
  assert.equal(
    shouldEvaluateClipEmbeddingSourceRetentionTransition({
      beforeData: { status: "running" },
      afterData: { status: "completed" },
    }),
    true,
  );
  assert.equal(
    shouldEvaluateClipEmbeddingSourceRetentionTransition({
      beforeData: { status: "completed", updatedAt: "old" },
      afterData: { status: "completed", updatedAt: "new" },
    }),
    false,
  );
  assert.equal(
    shouldEvaluateClipEmbeddingSourceRetentionTransition({
      beforeData: { status: "pending" },
      afterData: { status: "running" },
    }),
    false,
  );
});
