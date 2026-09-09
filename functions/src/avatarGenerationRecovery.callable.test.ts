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

// ---------------------------------------------------------------------------
// Nested write shape (2026-09-09)
//
// set(merge) reads keys as field names. Dotted keys wrote literal
// "avatar.status" fields beside the real map while users.avatar.status stayed
// queued, so the callable returned 200 and the user stayed stuck.
// ---------------------------------------------------------------------------

const NESTED_UID = "TestMixedCaseUid_9Xk2";
const NESTED_JOB = "avatar_job_nested_shape_01";

function nestedDb(): Db {
  return new Map<string, Record<string, unknown>>([
    [
      `users/${NESTED_UID}`,
      {
        avatar: { status: "needs_review", errorCode: "qa_requires_review", jobId: NESTED_JOB },
        onboarding: { avatarGenerationJobId: NESTED_JOB, sourcePhotoUploadStatus: "queued" },
      },
    ],
    [
      `userPrivateMedia/${NESTED_UID}`,
      { currentAvatarJobId: NESTED_JOB, currentAvatarSourcePhotoId: "src_x", sourcePhotos: [] },
    ],
    [`avatarJobs/${NESTED_JOB}`, { uid: NESTED_UID, jobId: NESTED_JOB, status: "needs_review" }],
  ]);
}

test("replacement writes the nested avatar map, not literal dotted fields", async () => {
  const store = nestedDb();
  await replaceAvatarGenerationCore({
    firestore: new FakeFirestore(store) as never,
    uid: NESTED_UID,
    clientRequestId: "replace-nested-0001",
  });
  const user = store.get(`users/${NESTED_UID}`) as Record<string, unknown>;

  const literal = Object.keys(user).filter((k) => k.startsWith("avatar.") || k.startsWith("onboarding."));
  assert.deepEqual(literal, [], `literal dotted fields must not be created: ${literal.join(", ")}`);

  const avatar = user.avatar as Record<string, unknown>;
  assert.equal(avatar.status, "none", "the nested status must actually leave its old value");
  assert.equal(avatar.generationReplacementCount, 1);
  assert.equal(avatar.replacedByClientRequestId, "replace-nested-0001");
  assert.equal(avatar.replacedJobId, NESTED_JOB);
  // delete sentinels must reach the nested leaves
  assert.equal("errorCode" in avatar, false);
  assert.equal("jobId" in avatar, false);

  const onboarding = user.onboarding as Record<string, unknown>;
  assert.equal(onboarding.sourcePhotoUploadStatus, "avatar_generation_replaced");
  assert.equal("avatarGenerationJobId" in onboarding, false);
});

test("a replayed replacement stays idempotent through the nested map", async () => {
  const store = nestedDb();
  const firestore = new FakeFirestore(store) as never;
  const first = await replaceAvatarGenerationCore({
    firestore,
    uid: NESTED_UID,
    clientRequestId: "replace-nested-0002",
  });
  const replay = await replaceAvatarGenerationCore({
    firestore,
    uid: NESTED_UID,
    clientRequestId: "replace-nested-0002",
  });
  assert.equal(first.duplicate, false);
  assert.equal(replay.duplicate, true);
  assert.equal(replay.generationAttemptCount, first.generationAttemptCount);
});

// ---------------------------------------------------------------------------
// No current job + stale denormalized status (2026-09-09)
//
// users.avatar.status is denormalised UI state. It is NOT the authority on
// whether a generation is running; currentAvatarJobId is. A job document and
// that pointer are written in one transaction, and every clearer removes the
// pointer and the source pointer together, so "no pointer" means "no canonical
// active generation".
//
// The replace policy fabricated a job out of the stale user status when the
// pointer was gone, so a leftover "queued" string blocked recovery forever.
// ---------------------------------------------------------------------------

const STALE_UID = "TestStaleUid_7Qm4";

function staleDb(avatarStatus: string, extraAvatar: Record<string, unknown> = {}): Db {
  return new Map<string, Record<string, unknown>>([
    // A historical job may still exist; it is simply not current any more.
    ["users/" + STALE_UID, { avatar: { status: avatarStatus, ...extraAvatar } }],
    ["userPrivateMedia/" + STALE_UID, { sourcePhotos: [] }],
    ["avatarJobs/avatar_job_history_01", { uid: STALE_UID, status: "failed" }],
  ]);
}

async function replaceStale(store: Db, requestId = "replace-stale-0001") {
  return replaceAvatarGenerationCore({
    firestore: new FakeFirestore(store) as never,
    uid: STALE_UID,
    clientRequestId: requestId,
  });
}

test("CASE A: no current job and a stale queued status recovers", async () => {
  const store = staleDb("queued");
  const result = await replaceStale(store);
  assert.equal(result.replaced, true);
  assert.equal(result.previousJobId, null, "there is no current job to report");
  const avatar = (store.get("users/" + STALE_UID) as Record<string, unknown>).avatar as Record<string, unknown>;
  assert.equal(avatar.status, "none");
  // A historical job must not be hunted down and cancelled.
  assert.equal((store.get("avatarJobs/avatar_job_history_01") as Record<string, unknown>).status, "failed");
});

test("CASE B: other stale in-flight strings recover the same way", async () => {
  for (const stale of ["running", "generating", "provider_inflight", "qa_pending"]) {
    const store = staleDb(stale);
    const result = await replaceStale(store, `replace-stale-${stale}`);
    assert.equal(result.replaced, true, `${stale} must be recoverable without a pointer`);
  }
});

test("CASE F/H: user-level ambiguity still blocks without a pointer", async () => {
  await assert.rejects(
    () => replaceStale(staleDb("reconciliation_required"), "replace-stale-recon"),
    /avatar_reconciliation_required/,
  );
  await assert.rejects(
    () => replaceStale(staleDb("queued", { errorCode: "azure_unknown_post_send_outcome" }), "replace-stale-amb"),
    /avatar_provider_outcome_unknown/,
  );
  await assert.rejects(
    () => replaceStale(staleDb("approved"), "replace-stale-approved"),
    /avatar_already_approved/,
  );
});

test("an idle user without a pointer is still not a replacement", async () => {
  // "none" is not a stale in-flight state; nothing to start over from.
  await assert.rejects(
    () => replaceStale(staleDb("none"), "replace-stale-idle"),
    /avatar_generation_not_replaceable/,
  );
});

test("CASE C: a real current job that is running still blocks", async () => {
  const store = new Map<string, Record<string, unknown>>([
    ["users/" + STALE_UID, { avatar: { status: "queued" } }],
    ["userPrivateMedia/" + STALE_UID, { currentAvatarJobId: "avatar_job_live_01", sourcePhotos: [] }],
    ["avatarJobs/avatar_job_live_01", { uid: STALE_UID, status: "running" }],
  ]);
  await assert.rejects(() => replaceStale(store, "replace-live"), /avatar_generation_in_progress/);
});

test("CASE G: a pointer whose job document is missing is inconsistent, not stale", async () => {
  const store = new Map<string, Record<string, unknown>>([
    ["users/" + STALE_UID, { avatar: { status: "queued" } }],
    ["userPrivateMedia/" + STALE_UID, { currentAvatarJobId: "avatar_job_ghost_01", sourcePhotos: [] }],
  ]);
  await assert.rejects(() => replaceStale(store, "replace-ghost"), /avatar_state_inconsistent/);
});

test("literal dotted garbage is never the authority", async () => {
  const store = staleDb("queued");
  // Fields the pre-#98 writer left behind must be ignored entirely.
  const user = store.get("users/" + STALE_UID) as Record<string, unknown>;
  user["avatar.status"] = "none";
  user["avatar.generationReplacementCount"] = 99;
  const result = await replaceStale(store, "replace-garbage");
  assert.equal(result.replaced, true);
  const avatar = (store.get("users/" + STALE_UID) as Record<string, unknown>).avatar as Record<string, unknown>;
  assert.equal(avatar.status, "none");
  assert.equal(avatar.generationReplacementCount, 1, "the literal count must not seed the canonical one");
});

test("stale recovery stays idempotent for one clientRequestId", async () => {
  const store = staleDb("queued");
  const firestore = new FakeFirestore(store) as never;
  const first = await replaceAvatarGenerationCore({ firestore, uid: STALE_UID, clientRequestId: "stale-idem-1" });
  const replay = await replaceAvatarGenerationCore({ firestore, uid: STALE_UID, clientRequestId: "stale-idem-1" });
  assert.equal(first.duplicate, false);
  assert.equal(replay.duplicate, true);
  assert.equal(replay.generationAttemptCount, first.generationAttemptCount);
});
