import assert from "node:assert/strict";
import test from "node:test";

import { replaceAvatarGenerationCore } from "./avatarGenerationRecovery";
import { readCurrentAvatarContract } from "./avatarMedia";
import { FakeFirestore, type Db } from "./testing/fakeFirestore";

const UID = "uid_recover_1";
const JOB = "avatar_job_recover_000001";

function db(jobStatus: string, extra: Record<string, unknown> = {}): Db {
  return new Map<string, Record<string, unknown>>([
    [`users/${UID}`, { avatar: { status: jobStatus }, onboarding: { avatarGenerationJobId: JOB } }],
    [
      `userPrivateMedia/${UID}`,
      {
        currentAvatarJobId: JOB,
        currentAvatarSourcePhotoId: "src_old",
        avatarSourceSelectionVersion: 1,
        avatarSourceSelection: { status: "selected" },
        sourcePhotos: [
          { photoId: "src_old", status: "active", avatarGenerationState: "current" },
          { photoId: "src_other", status: "active", avatarGenerationState: "selection_not_selected" },
        ],
      },
    ],
    [`avatarJobs/${JOB}`, { uid: UID, jobId: JOB, status: jobStatus, ...extra }],
  ]);
}

test("needs_review replacement ends the job, releases the lock, and re-admits a new source set", async () => {
  const store = db("needs_review", { errorCode: "qa_requires_review" });
  const firestore = new FakeFirestore(store);

  const result = await replaceAvatarGenerationCore({
    firestore: firestore as never,
    uid: UID,
    clientRequestId: "replace-0001",
  });

  assert.equal(result.replaced, true);
  assert.equal(result.duplicate, false);
  assert.equal(result.previousJobId, JOB);

  const job = store.get(`avatarJobs/${JOB}`) ?? {};
  assert.equal(job.status, "cancelled");
  assert.equal(job.errorCode, "avatar_generation_replaced_by_user");

  const priv = store.get(`userPrivateMedia/${UID}`) ?? {};
  assert.equal("currentAvatarJobId" in priv, false, "job pointer must be released");
  assert.equal("currentAvatarSourcePhotoId" in priv, false, "source pointer must be released");
  // The contract reader must now see an unlocked, consistent state.
  const contract = readCurrentAvatarContract(priv);
  assert.equal(contract.sourceLocked, false);

  const user = store.get(`users/${UID}`) ?? {};
  assert.equal((user.avatar as Record<string, unknown>).status, "none");
  assert.equal((user.avatar as Record<string, unknown>).generationReplacementCount, 1);
  assert.equal("avatarGenerationJobId" in (user.onboarding as Record<string, unknown>), false);
});

test("replacement is idempotent for the same clientRequestId", async () => {
  const store = db("terminal_failed");
  const firestore = new FakeFirestore(store);
  const first = await replaceAvatarGenerationCore({
    firestore: firestore as never,
    uid: UID,
    clientRequestId: "replace-0002",
  });
  const second = await replaceAvatarGenerationCore({
    firestore: firestore as never,
    uid: UID,
    clientRequestId: "replace-0002",
  });
  assert.equal(first.duplicate, false);
  assert.equal(second.duplicate, true);
  assert.equal(second.generationAttemptCount, first.generationAttemptCount);
});

test("provider-ambiguous, active, and approved generations are refused", async () => {
  for (const [status, extra] of [
    ["needs_review", { errorCode: "azure_unknown_post_send_outcome", generationClaim: { state: "active" } }],
    ["provider_inflight", {}],
    ["queued", {}],
    ["approved", {}],
  ] as const) {
    const firestore = new FakeFirestore(db(status, extra));
    await assert.rejects(
      replaceAvatarGenerationCore({
        firestore: firestore as never,
        uid: UID,
        clientRequestId: "replace-0003",
      }),
      (error: unknown) => error instanceof Error && !error.message.includes("replaced"),
      `${status} must be refused`,
    );
  }
});

test("the generation attempt limit is enforced across replacements", async () => {
  const store = db("terminal_failed");
  const user = store.get(`users/${UID}`) ?? {};
  (user.avatar as Record<string, unknown>).generationReplacementCount = 2;
  const firestore = new FakeFirestore(store);
  await assert.rejects(
    replaceAvatarGenerationCore({
      firestore: firestore as never,
      uid: UID,
      clientRequestId: "replace-0004",
    }),
    (error: unknown) =>
      error instanceof Error && error.message.includes("avatar_generation_limit_reached"),
  );
});

// ---------------------------------------------------------------------------
// Stage reporting (2026-09-09)
//
// A 400 whose stage we cannot name is what left the production rejection
// unexplained. These assert the core reports where it actually stopped.
// ---------------------------------------------------------------------------

import {
  buildReplaceRejectionLog,
  type ReplaceRejectionStage,
} from "./avatarGenerationRecovery";

async function runStages(
  store: Db,
  clientRequestId = "replace-stage-0001",
): Promise<{ stages: ReplaceRejectionStage[]; error: unknown }> {
  const stages: ReplaceRejectionStage[] = [];
  let error: unknown = null;
  try {
    await replaceAvatarGenerationCore({
      firestore: new FakeFirestore(store) as never,
      uid: UID,
      clientRequestId,
      onStage: (stage) => stages.push(stage),
    });
  } catch (caught) {
    error = caught;
  }
  return { stages, error };
}

test("a successful replacement walks every stage up to the commit", async () => {
  const { stages, error } = await runStages(db("needs_review"));
  assert.equal(error, null);
  assert.deepEqual(stages, [
    "client_request_id_validation",
    "user_document_lookup",
    "job_ownership_validation",
    "replacement_policy",
    "transaction_commit",
  ]);
});

test("an invalid clientRequestId stops at its own stage", async () => {
  const { stages, error } = await runStages(db("needs_review"), "not a safe segment!");
  assert.notEqual(error, null);
  assert.equal(stages.at(-1), "client_request_id_validation");
  const entry = buildReplaceRejectionLog({
    stage: stages.at(-1) as ReplaceRejectionStage,
    error,
    uidHash: "",
  });
  assert.equal(entry.httpsCode, "invalid-argument");
  assert.equal(entry.stage, "client_request_id_validation");
});

test("a missing user document stops at the lookup stage", async () => {
  const store = db("needs_review");
  store.delete(`users/${UID}`);
  const { stages, error } = await runStages(store);
  assert.notEqual(error, null);
  assert.equal(stages.at(-1), "user_document_lookup");
});

test("a job owned by someone else stops at ownership validation", async () => {
  const store = db("needs_review");
  store.set(`avatarJobs/${JOB}`, { uid: "someone_else", jobId: JOB, status: "needs_review" });
  const { stages, error } = await runStages(store);
  assert.notEqual(error, null);
  assert.equal(stages.at(-1), "job_ownership_validation");
  const entry = buildReplaceRejectionLog({
    stage: stages.at(-1) as ReplaceRejectionStage,
    error,
    uidHash: "",
  });
  assert.equal(entry.reasonCode, "avatar_job_not_current");
});

test("a blocked status stops at the policy stage with its reason", async () => {
  const { stages, error } = await runStages(db("queued"));
  assert.notEqual(error, null);
  assert.equal(stages.at(-1), "replacement_policy");
  const entry = buildReplaceRejectionLog({
    stage: stages.at(-1) as ReplaceRejectionStage,
    error,
    uidHash: "",
  });
  assert.equal(entry.reasonCode, "avatar_generation_in_progress");
  assert.equal(entry.httpsCode, "failed-precondition");
});

test("reconciliation_required is nameable from the log alone", async () => {
  const { stages, error } = await runStages(db("reconciliation_required"));
  const entry = buildReplaceRejectionLog({
    stage: stages.at(-1) as ReplaceRejectionStage,
    error,
    uidHash: "",
  });
  assert.equal(entry.stage, "replacement_policy");
  assert.equal(entry.reasonCode, "avatar_reconciliation_required");
});

// ---------------------------------------------------------------------------
// Identifier case sensitivity (2026-09-09, production organic evidence)
//
// asString() normalises status tokens with trim().toLowerCase(). Applied to an
// identifier it destroys case, and requireSegment() only trims, so the two
// sides of an identifier comparison disagree. Firebase UIDs are mixed case, so
// ownership validation rejected every real user:
//   stage=job_ownership_validation reason=avatar_job_not_current
// The fixtures above all use lowercase ids, which is why nothing caught it.
// ---------------------------------------------------------------------------

const MIXED_CASE_UID = "ZqXvT7MixedCaseUidFixture001";
const MIXED_CASE_JOB = "avatar_job_MixedCase000001";

function mixedCaseDb(uid: string, jobId: string, jobStatus = "failed"): Db {
  return new Map<string, Record<string, unknown>>([
    [`users/${uid}`, { avatar: { status: jobStatus } }],
    [
      `userPrivateMedia/${uid}`,
      {
        currentAvatarJobId: jobId,
        currentAvatarSourcePhotoId: "src_old",
        sourcePhotos: [{ photoId: "src_old", avatarGenerationState: "current" }],
      },
    ],
    [`avatarJobs/${jobId}`, { uid, jobId, status: jobStatus }],
  ]);
}

test("a mixed-case Firebase uid owns its own job", async () => {
  // job.uid and the caller uid are byte-identical; only normalisation differed.
  const store = mixedCaseDb(MIXED_CASE_UID, "avatar_job_ownership_0001");
  const result = await replaceAvatarGenerationCore({
    firestore: new FakeFirestore(store) as never,
    uid: MIXED_CASE_UID,
    clientRequestId: "replace-mixed-0001",
  });
  assert.equal(result.replaced, true);
  assert.equal(result.duplicate, false);
});

test("a mixed-case job id resolves to the job it names", async () => {
  const store = mixedCaseDb(MIXED_CASE_UID, MIXED_CASE_JOB);
  const result = await replaceAvatarGenerationCore({
    firestore: new FakeFirestore(store) as never,
    uid: MIXED_CASE_UID,
    clientRequestId: "replace-mixed-0002",
  });
  assert.equal(result.replaced, true);
  assert.equal(result.previousJobId, MIXED_CASE_JOB, "job id must survive verbatim");
  const job = store.get(`avatarJobs/${MIXED_CASE_JOB}`) ?? {};
  assert.equal(job.status, "cancelled", "the named job must be the one cancelled");
});

test("an uppercase clientRequestId is still recognised as a replay", async () => {
  const requestId = "Replace-UPPER-0003";
  const store = mixedCaseDb(MIXED_CASE_UID, "avatar_job_idem_0003");
  const firestore = new FakeFirestore(store) as never;
  const first = await replaceAvatarGenerationCore({
    firestore,
    uid: MIXED_CASE_UID,
    clientRequestId: requestId,
  });
  const replay = await replaceAvatarGenerationCore({
    firestore,
    uid: MIXED_CASE_UID,
    clientRequestId: requestId,
  });
  assert.equal(first.duplicate, false);
  assert.equal(replay.duplicate, true, "same request id must not start a second replacement");
  assert.equal(replay.generationAttemptCount, first.generationAttemptCount);
});

test("lowercase fixtures keep behaving exactly as before", async () => {
  const store = db("needs_review", { errorCode: "qa_requires_review" });
  const result = await replaceAvatarGenerationCore({
    firestore: new FakeFirestore(store) as never,
    uid: UID,
    clientRequestId: "replace-lower-0004",
  });
  assert.equal(result.replaced, true);
  assert.equal(result.previousJobId, JOB);
});
