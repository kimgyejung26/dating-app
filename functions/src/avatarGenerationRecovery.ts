/**
 * needs_review / terminal 실패에서 사용자가 빠져나오는 유일한 안전 경로.
 *
 * 제품 결정(2026-09-05):
 *   같은 logical generation 을 다시 시도하지 않는다.
 *   사용자가 명시적으로 "사진을 바꾸고 다시 만들기"를 선택하면
 *   현재 generation 을 종료하고 source lock 을 풀어 새 generation 을 연다.
 *
 * provider post-send unknown 은 이 경로에서 완전히 제외된다. 이미 과금된
 * 생성이 존재할 수 있으므로 재조정이 끝나기 전에는 새 generation 도 막는다.
 *
 * 순수 함수다. Firestore 를 읽거나 쓰지 않는다.
 */

import {
  FieldValue,
  type Firestore,
} from "firebase-admin/firestore";
import { createHash } from "node:crypto";

import {
  HttpsError,
  onCall,
  type CallableOptions,
  type CallableRequest,
} from "firebase-functions/v2/https";
import * as logger from "firebase-functions/logger";

import {
  rejectAvatarRetryRequestWithImageBytes,
  type ResolvedAvatarUploadUser,
} from "./avatarMedia";

type RecordData = Record<string, unknown>;

function readMap(value: unknown): RecordData {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as RecordData)
    : {};
}

function asString(value: unknown): string {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}

/** 사용자가 스스로 시작할 수 있는 총 generation 횟수 상한. */
export const MAX_USER_GENERATION_ATTEMPTS = 3;

/** 새 generation 으로 교체 가능한 종료 상태. */
// 아래 두 집합은 "교체 자격" 전용이다. polling / status normalization /
// resume planning 이 쓰는 전역 상태 집합과 섞지 마라. 여기서의 in-flight 는
// "새로 만들기를 막아야 하는가"라는 뜻이지 "작업이 끝났는가"가 아니다.
const REPLACEABLE_STATUSES = new Set([
  "needs_review",
  "terminal_failed",
  "retryable_failed",
  "no_previewable",
  "no_previewable_candidates",
  "failed",
  "cancelled",
  // 후보는 나왔지만 사용자가 아직 고르지 않았다. 선택 화면이 제공하는
  // "사진을 바꾸고 다시 만들기" 가 바로 이 상태에서 눌리므로 허용해야 한다.
  "preview_ready",
]);

// 새 generation 을 시작하면 진행 중인 작업과 충돌하는 상태들.
const RECONCILIATION_REQUIRED_STATUSES = new Set(["reconciliation_required"]);

/** 아직 워커/승인이 붙들고 있는 상태. 교체 금지. */
const REPLACE_BLOCKING_IN_FLIGHT_STATUSES = new Set([
  "queued",
  "running",
  "generating",
  "provider_inflight",
  "generated",
  "persisted",
  "qa_pending",
  "approval_copying",
]);

const PROVIDER_OUTCOME_UNKNOWN_ERROR_CODES = new Set([
  "azure_unknown_post_send_outcome",
]);

export type NewGenerationRecoveryDecision =
  | { allowed: false; reasonCode: string }
  | {
      allowed: true;
      releasesSourceLock: true;
      jobUpdate: RecordData;
      privateMediaClearFields: readonly string[];
      userAvatarStatus: string;
    };

export function planNewGenerationRecovery(params: {
  currentJobData: unknown;
  userAvatar: unknown;
  generationAttemptCount: number;
}): NewGenerationRecoveryDecision {
  const job = readMap(params.currentJobData);
  const avatar = readMap(params.userAvatar);
  const status = asString(job.status) || asString(avatar.status);
  const errorCode = asString(job.errorCode);
  const claimState = asString(readMap(job.generationClaim).state);

  if (status === "approved" || asString(avatar.status) === "approved") {
    return { allowed: false, reasonCode: "avatar_already_approved" };
  }

  // provider 결과 미확인은 그 어떤 새 생성보다 우선해서 막는다.
  if (
    PROVIDER_OUTCOME_UNKNOWN_ERROR_CODES.has(errorCode) ||
    claimState === "active"
  ) {
    return { allowed: false, reasonCode: "avatar_provider_outcome_unknown" };
  }

  if (REPLACE_BLOCKING_IN_FLIGHT_STATUSES.has(status)) {
    return { allowed: false, reasonCode: "avatar_generation_in_progress" };
  }

  // provider 결과나 상태가 어긋났다는 뜻이므로 새 generation 이 이전 상태와
  // 충돌할 수 있다. generic not_replaceable 로 흘려보내면 이 의도가 사라진다.
  if (RECONCILIATION_REQUIRED_STATUSES.has(status)) {
    return { allowed: false, reasonCode: "avatar_reconciliation_required" };
  }

  if (!REPLACEABLE_STATUSES.has(status)) {
    return { allowed: false, reasonCode: "avatar_generation_not_replaceable" };
  }

  if (params.generationAttemptCount >= MAX_USER_GENERATION_ATTEMPTS) {
    return { allowed: false, reasonCode: "avatar_generation_limit_reached" };
  }

  return {
    allowed: true,
    releasesSourceLock: true,
    jobUpdate: {
      status: "cancelled",
      errorCode: "avatar_generation_replaced_by_user",
      retryable: false,
    },
    // 이 필드들을 지워야 새 source set 이 admission 을 통과할 수 있다.
    privateMediaClearFields: [
      "currentAvatarSourcePhotoId",
      "currentAvatarJobId",
    ],
    userAvatarStatus: "none",
  };
}

// ---------------------------------------------------------------------------
// Rejection observability
//
// The callable hands the reason back to the client in the response body, which
// Cloud Run never logs. When production rejected a replacement that a
// source-level replay said was allowed, there was nothing on the server to
// classify. These emit one sanitized line per outcome: enough to name the
// stage and reason, never enough to identify the person.
// ---------------------------------------------------------------------------

export const REPLACE_REJECTION_STAGES = [
  "app_user_resolution",
  "uid_validation",
  "request_argument_validation",
  "client_request_id_validation",
  "user_document_lookup",
  "job_ownership_validation",
  "replacement_policy",
  "transaction_commit",
  "unexpected",
] as const;

export type ReplaceRejectionStage = (typeof REPLACE_REJECTION_STAGES)[number];

/** Irreversible short fingerprint. Correlates lines without naming anyone. */
export function shortHash(value: string): string {
  if (!value) return "";
  return createHash("sha256").update(value).digest("hex").slice(0, 12);
}

/** Internal codes are safe to log verbatim; human sentences never are. */
const CANONICAL_REASON = /^[a-z][a-z0-9_]*$/;

function readHttpsCode(error: unknown): string {
  const code = (error as { code?: unknown } | null)?.code;
  return typeof code === "string" && code ? code : "internal";
}

function readMessage(error: unknown): string {
  const message = (error as { message?: unknown } | null)?.message;
  return typeof message === "string" ? message : "";
}

export type ReplaceRejectionLog = {
  event: "avatar_replace_rejected";
  stage: ReplaceRejectionStage;
  httpsCode: string;
  reasonCode: string;
  messageHash: string;
  uidHash: string;
};

export function buildReplaceRejectionLog(params: {
  stage: ReplaceRejectionStage;
  error: unknown;
  uidHash: string;
}): ReplaceRejectionLog {
  const message = readMessage(params.error);
  // A user-facing sentence can carry anything the thrower interpolated into
  // it, so it is fingerprinted rather than copied.
  const canonical = CANONICAL_REASON.test(message);
  return {
    event: "avatar_replace_rejected",
    stage: params.stage,
    httpsCode: readHttpsCode(params.error),
    reasonCode: canonical ? message : "non_canonical_message",
    messageHash: canonical ? "" : shortHash(message),
    uidHash: params.uidHash,
  };
}

export function buildReplaceCompletionLog(params: {
  uidHash: string;
  result: ReplaceAvatarGenerationResult;
}): {
  event: "avatar_replace_succeeded";
  stage: "complete";
  duplicate: boolean;
  generationAttemptCount: number;
  previousJobHash: string;
  uidHash: string;
} {
  return {
    event: "avatar_replace_succeeded",
    stage: "complete",
    duplicate: params.result.duplicate,
    generationAttemptCount: params.result.generationAttemptCount,
    previousJobHash: shortHash(params.result.previousJobId ?? ""),
    uidHash: params.uidHash,
  };
}

// ---------------------------------------------------------------------------
// Callable boundary
// ---------------------------------------------------------------------------

export const REPLACE_AVATAR_GENERATION_CALLABLE_OPTIONS: CallableOptions = {
  timeoutSeconds: 60,
  memory: "512MiB",
  invoker: "public",
  enforceAppCheck: true,
};

type ResolveUploadUser = (
  auth: CallableRequest<unknown>["auth"],
) => Promise<ResolvedAvatarUploadUser>;

const SAFE_SEGMENT = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;

function requireSegment(value: unknown, field: string): string {
  const normalized = typeof value === "string" ? value.trim() : "";
  if (!SAFE_SEGMENT.test(normalized)) {
    throw new HttpsError("invalid-argument", `${field} is invalid.`);
  }
  return normalized;
}

export type ReplaceAvatarGenerationResult = {
  replaced: boolean;
  duplicate: boolean;
  previousJobId: string | null;
  generationAttemptCount: number;
};

/// Ends the current logical generation and releases the source lock so the
/// user can pick new photos and start a NEW generation (new source selection,
/// new job id). This is NOT a retry of the same generation.
///
/// Refused for provider-ambiguous outcomes, active generations and approved
/// avatars — see planNewGenerationRecovery. Idempotent per clientRequestId.
export async function replaceAvatarGenerationCore(params: {
  firestore: Firestore;
  uid: string;
  clientRequestId: string;
  /** Optional so existing callers and tests keep working unchanged. */
  onStage?: (stage: ReplaceRejectionStage) => void;
}): Promise<ReplaceAvatarGenerationResult> {
  const { firestore, uid } = params;
  const reportStage = params.onStage ?? (() => {});
  reportStage("client_request_id_validation");
  const clientRequestId = requireSegment(params.clientRequestId, "clientRequestId");
  const userRef = firestore.collection("users").doc(uid);
  const privateRef = firestore.collection("userPrivateMedia").doc(uid);

  return firestore.runTransaction(async (tx) => {
    const [userSnap, privateSnap] = await Promise.all([
      tx.get(userRef),
      tx.get(privateRef),
    ]);
    reportStage("user_document_lookup");
    if (!userSnap.exists) {
      throw new HttpsError("failed-precondition", "User profile was not found.");
    }
    const userData = readMap(userSnap.data());
    const privateData = readMap(privateSnap.data());
    const userAvatar = readMap(userData.avatar);
    const currentJobId = asString(privateData.currentAvatarJobId);

    let jobData: RecordData = {};
    let jobRef: ReturnType<Firestore["collection"]> extends infer C
      ? C extends { doc(id: string): infer D }
        ? D
        : never
      : never;
    jobRef = firestore.collection("avatarJobs").doc(currentJobId || "__none__");
    if (currentJobId) {
      reportStage("job_ownership_validation");
      const jobSnap = await tx.get(jobRef);
      jobData = jobSnap.exists ? readMap(jobSnap.data()) : {};
      if (jobSnap.exists && asString(jobData.uid) && asString(jobData.uid) !== uid) {
        throw new HttpsError("failed-precondition", "avatar_job_not_current");
      }
    }

    const previousReplacements = Math.max(
      0,
      Math.floor(Number(userAvatar.generationReplacementCount ?? 0) || 0),
    );

    // Idempotent replay: the same request already released this generation.
    if (
      currentJobId === "" &&
      asString(userAvatar.replacedByClientRequestId) === clientRequestId
    ) {
      // The counter was already advanced by the original request.
      return {
        replaced: true,
        duplicate: true,
        previousJobId: asString(userAvatar.replacedJobId) || null,
        generationAttemptCount: previousReplacements,
      };
    }

    reportStage("replacement_policy");
    const decision = planNewGenerationRecovery({
      currentJobData: currentJobId ? jobData : { status: asString(userAvatar.status) },
      userAvatar,
      generationAttemptCount: previousReplacements + 1,
    });
    if (!decision.allowed) {
      const code =
        decision.reasonCode === "avatar_generation_limit_reached"
          ? "resource-exhausted"
          : "failed-precondition";
      throw new HttpsError(code, decision.reasonCode);
    }

    reportStage("transaction_commit");
    if (currentJobId) {
      tx.set(
        jobRef,
        {
          ...decision.jobUpdate,
          replacedByClientRequestId: clientRequestId,
          replacedAt: FieldValue.serverTimestamp(),
          updatedAt: FieldValue.serverTimestamp(),
        },
        { merge: true },
      );
    }

    // Release every source that belonged to the replaced generation so the
    // contract reader sees no dangling "current" entry.
    const sourcePhotos = Array.isArray(privateData.sourcePhotos)
      ? privateData.sourcePhotos.filter(
          (entry): entry is RecordData => entry !== null && typeof entry === "object",
        )
      : [];
    const releasedSources = sourcePhotos.map((entry) => {
      const state = asString(entry.avatarGenerationState);
      if (state === "current" || state === "selection_candidate") {
        return { ...entry, avatarGenerationState: "replaced" };
      }
      return entry;
    });
    tx.set(
      privateRef,
      {
        ...Object.fromEntries(
          decision.privateMediaClearFields.map((field) => [field, FieldValue.delete()]),
        ),
        avatarSourceSelection: FieldValue.delete(),
        sourcePhotos: releasedSources,
        updatedAt: FieldValue.serverTimestamp(),
      },
      { merge: true },
    );
    tx.set(
      userRef,
      {
        "avatar.status": decision.userAvatarStatus,
        "avatar.errorCode": FieldValue.delete(),
        "avatar.reasonCode": FieldValue.delete(),
        "avatar.sourceJobId": FieldValue.delete(),
        "avatar.jobId": FieldValue.delete(),
        "avatar.sourcePhotoId": FieldValue.delete(),
        "avatar.generationReplacementCount": previousReplacements + 1,
        "avatar.replacedByClientRequestId": clientRequestId,
        "avatar.replacedJobId": currentJobId || FieldValue.delete(),
        "avatar.updatedAt": FieldValue.serverTimestamp(),
        "onboarding.avatarGenerationJobId": FieldValue.delete(),
        "onboarding.sourcePhotoUploadStatus": "avatar_generation_replaced",
        updatedAt: FieldValue.serverTimestamp(),
      },
      { merge: true },
    );

    return {
      replaced: true,
      duplicate: false,
      previousJobId: currentJobId || null,
      generationAttemptCount: previousReplacements + 1,
    };
  });
}

export function createReplaceAvatarGenerationFunction(
  firestore: Firestore,
  resolveUploadUser: ResolveUploadUser,
) {
  return onCall(REPLACE_AVATAR_GENERATION_CALLABLE_OPTIONS, async (request) => {
    // Tracks how far the request got, so a rejection names its own stage.
    let stage: ReplaceRejectionStage = "app_user_resolution";
    let uidHash = "";
    try {
      const user = await resolveUploadUser(request.auth);
      stage = "uid_validation";
      const uid = requireSegment(user.userId, "uid");
      uidHash = shortHash(uid);
      stage = "request_argument_validation";
      const data = readMap(request.data);
      // This endpoint never accepts image bytes or source refs.
      rejectAvatarRetryRequestWithImageBytes(data);
      const result = await replaceAvatarGenerationCore({
        firestore,
        uid,
        clientRequestId: asString(data.clientRequestId),
        onStage: (next) => {
          stage = next;
        },
      });
      logger.info(
        "avatar_replace_succeeded",
        buildReplaceCompletionLog({ uidHash, result }),
      );
      return result;
    } catch (error) {
      // The response contract is unchanged: the client still receives the same
      // HttpsError. This only makes the rejection visible server side.
      logger.warn(
        "avatar_replace_rejected",
        buildReplaceRejectionLog({ stage, error, uidHash }),
      );
      throw error;
    }
  });
}
