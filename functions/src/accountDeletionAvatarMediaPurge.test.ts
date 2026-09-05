import assert from "node:assert/strict";
import test from "node:test";

import {
  purgeAvatarPrivateMediaForDeletedAccounts,
  type DeletedAccountAvatarPurgeDeps,
} from "./accountDeletionAvatarMediaPurge";
import {
  accountDeletionDocsFromParts,
  createAvatarCleanupFirestoreExecutor,
  deleteStorageObjectWithGenerationMatch,
  executeAvatarCleanup,
  planAvatarCleanup,
  type CleanupExecutor,
  type CleanupOperation,
} from "./avatarCleanup";
import { FakeFirestore, type Db } from "./testing/fakeFirestore";

/**
 * Account-deletion avatar purge contract:
 *   1 normal app withdrawal       -> existing cleanup plan (avatarCleanup.test.ts) still holds
 *   2 Auth already missing        -> recovery purge runs the same contract
 *   3 private doc missing         -> nothing listed, safe no-op
 *   4 Storage object missing      -> no fatal inconsistency
 *   5 partial cleanup             -> retry converges (request stays pending)
 *   6 generation mismatch         -> no wrong-object delete, error retried
 *   7 approved/legal-retained     -> audit record kept, policy respected
 *   8 rerun                       -> idempotent (completed request short-circuits)
 */

type Fake = {
  uids: string[];
  auth: Set<string>;
  completed: Set<string>;
  runs: string[];
  plans: string[];
  failFor?: string;
};

function deps(fake: Fake): DeletedAccountAvatarPurgeDeps {
  return {
    async listPrivateMediaOwnerUids(limit) {
      return fake.uids.slice(0, limit);
    },
    async authUserExists(uid) {
      return fake.auth.has(uid);
    },
    async cleanupAlreadyCompleted(uid) {
      return fake.completed.has(uid);
    },
    async planCleanup(uid) {
      fake.plans.push(uid);
      return [
        { kind: "deleteStorage", ref: { bucket: "b", path: `users/${uid}/source/p.jpg` } },
        { kind: "sanitizePrivateMedia", reason: "account_deletion" },
        { kind: "writeAudit", reason: "account_deletion", counts: {} as never },
      ] as CleanupOperation[];
    },
    async runCleanup(uid) {
      if (fake.failFor === uid) throw new Error("storage unavailable");
      fake.runs.push(uid);
      fake.completed.add(uid);
      return { status: "completed", counts: {} as never };
    },
  };
}

test("2: owners whose Auth account is missing are purged; active owners are left alone", async () => {
  const fake: Fake = { uids: ["alive", "gone"], auth: new Set(["alive"]), completed: new Set(), runs: [], plans: [] };
  const summary = await purgeAvatarPrivateMediaForDeletedAccounts(deps(fake), { limit: 25 });
  assert.equal(summary.scanned, 2);
  assert.equal(summary.authPresent, 1);
  assert.equal(summary.authMissing, 1);
  assert.equal(summary.purged, 1);
  assert.deepEqual(fake.runs, ["gone"]);
  assert.equal(summary.candidates[0].plannedOperations.deleteStorage, 1);
  assert.ok(!JSON.stringify(summary).includes("gone"), "raw uid must not appear in the summary");
});

test("3: nothing listed (private doc missing) is a safe no-op", async () => {
  const fake: Fake = { uids: [], auth: new Set(), completed: new Set(), runs: [], plans: [] };
  const summary = await purgeAvatarPrivateMediaForDeletedAccounts(deps(fake));
  assert.deepEqual({ ...summary, candidates: [] }, {
    scanned: 0, authPresent: 0, authMissing: 0, alreadyCompleted: 0, purged: 0, errors: 0, dryRun: false, candidates: [],
  });
});

test("dry run plans but never applies, and reports the planned operation shape", async () => {
  const fake: Fake = { uids: ["gone"], auth: new Set(), completed: new Set(), runs: [], plans: [] };
  const summary = await purgeAvatarPrivateMediaForDeletedAccounts(deps(fake), { dryRun: true });
  assert.equal(summary.dryRun, true);
  assert.equal(summary.authMissing, 1);
  assert.equal(summary.purged, 0);
  assert.deepEqual(fake.runs, []);
  assert.deepEqual(fake.plans, ["gone"]);
  assert.deepEqual(summary.candidates[0].plannedOperations, { deleteStorage: 1, sanitizePrivateMedia: 1, writeAudit: 1 });
});

test("5: a failing owner is counted as an error, does not stop the batch, and is retried on the next run", async () => {
  const fake: Fake = { uids: ["gone_a", "gone_b"], auth: new Set(), completed: new Set(), runs: [], plans: [], failFor: "gone_a" };
  const first = await purgeAvatarPrivateMediaForDeletedAccounts(deps(fake));
  assert.equal(first.errors, 1);
  assert.equal(first.purged, 1);
  assert.deepEqual(fake.runs, ["gone_b"]);
  fake.failFor = undefined;
  const second = await purgeAvatarPrivateMediaForDeletedAccounts(deps(fake));
  assert.equal(second.alreadyCompleted, 1);
  assert.equal(second.purged, 1);
  assert.deepEqual(fake.runs, ["gone_b", "gone_a"]);
});

test("8: rerun is idempotent - completed owners short-circuit before any Auth lookup or plan", async () => {
  const fake: Fake = { uids: ["gone"], auth: new Set(), completed: new Set(["gone"]), runs: [], plans: [] };
  const summary = await purgeAvatarPrivateMediaForDeletedAccounts(deps(fake));
  assert.equal(summary.alreadyCompleted, 1);
  assert.equal(summary.purged, 0);
  assert.deepEqual(fake.plans, []);
});

test("limit is bounded to at most 100 per run and at least 1", async () => {
  const fake: Fake = { uids: Array.from({ length: 150 }, (_, i) => `u${i}`), auth: new Set(), completed: new Set(), runs: [], plans: [] };
  const summary = await purgeAvatarPrivateMediaForDeletedAccounts(deps(fake), { limit: 500, dryRun: true });
  assert.equal(summary.scanned, 100);
});

// ---------------------------------------------------------------------------
// Generation-aware storage delete (shared by app withdrawal and the purge).

type FakeFileState = { exists: boolean; generation: string; deletedWith?: unknown; conflict?: boolean };

function fakeFile(state: FakeFileState) {
  return {
    async exists(): Promise<[boolean, ...unknown[]]> {
      return [state.exists];
    },
    async getMetadata(): Promise<[{ generation?: string }, ...unknown[]]> {
      return [{ generation: state.generation }];
    },
    async delete(options?: { ifGenerationMatch?: number }) {
      if (state.conflict) {
        const error = new Error("precondition failed") as Error & { code?: number };
        error.code = 412;
        throw error;
      }
      state.deletedWith = options;
      state.exists = false;
    },
  };
}

test("4: a missing object is a no-op, not a fatal inconsistency", async () => {
  const state: FakeFileState = { exists: false, generation: "1" };
  assert.equal(await deleteStorageObjectWithGenerationMatch(fakeFile(state)), "missing");
  assert.equal(state.deletedWith, undefined);
});

test("6: deletion targets exactly the observed generation and a mismatch is surfaced, never swallowed", async () => {
  const ok: FakeFileState = { exists: true, generation: "1788000000000001" };
  assert.equal(await deleteStorageObjectWithGenerationMatch(fakeFile(ok)), "deleted");
  assert.deepEqual(ok.deletedWith, { ifGenerationMatch: 1788000000000001 });
  const conflict: FakeFileState = { exists: true, generation: "42", conflict: true };
  await assert.rejects(deleteStorageObjectWithGenerationMatch(fakeFile(conflict)), /precondition failed/);
  assert.equal(conflict.exists, true);
});

// ---------------------------------------------------------------------------
// Executor policy for identities that no longer have a users document.

const UID = "uid_gone_owner";

function seededDb(): Db {
  const db: Db = new Map();
  db.set(`userPrivateMedia/${UID}`, {
    currentAvatarJobId: "avatar_job_gone_1",
    currentAvatarSourcePhotoId: "src_gone",
    sourcePhotos: [
      {
        photoId: "src_gone",
        status: "active",
        gcsUri: `gs://seolleyeon-final-private-source-photos/users/${UID}/source/src_gone.jpg`,
      },
    ],
    clip: { embeddingStatus: "pending" },
  });
  db.set("avatarJobs/avatar_job_gone_1", { uid: UID, status: "superseded", sourcePhotoRefs: [] });
  return db;
}

test("7: the account-deletion plan for a deleted owner keeps the audit record and sanitizes private media; user-doc operations are skipped when the users doc is gone", async () => {
  const db = seededDb();
  const fs = new FakeFirestore(db);
  const applied: string[] = [];
  const real = createAvatarCleanupFirestoreExecutor(fs as never, UID, null, { userDocPolicy: "skip_if_missing" });
  const executor: CleanupExecutor = {
    load: (uid, requestId) =>
      Promise.resolve({
        userData: {},
        privateMediaData: db.get(`userPrivateMedia/${UID}`) ?? {},
        candidateDocs: [],
        jobDocs: [{ id: "avatar_job_gone_1", data: db.get("avatarJobs/avatar_job_gone_1") ?? {} }],
        existingRequest: null,
        accountDeletionDocs: accountDeletionDocsFromParts(),
      } as never).then((docs) => (void requestId, void uid, docs)),
    async apply(operation) {
      applied.push(operation.kind);
      if (operation.kind === "lockAccountForDeletion" || operation.kind === "sanitizeUser") {
        await real.apply(operation);
      }
    },
  };
  const plan = planAvatarCleanup({
    uid: UID,
    requestId: "req_test",
    reason: "account_deletion",
    docs: await executor.load(UID, "req_test"),
  });
  const kinds = plan.operations.map((operation) => operation.kind);
  assert.ok(kinds.includes("writeAudit"), "audit record is part of the policy");
  assert.ok(kinds.includes("deleteStorage"), "private source object is purged");
  assert.ok(kinds.includes("sanitizePrivateMedia"));
  await executeAvatarCleanup({ uid: UID, clientRequestId: "account_deletion_auth_missing_v1", reason: "account_deletion", executor });
  assert.ok(applied.includes("lockAccountForDeletion") && applied.includes("sanitizeUser"));
  assert.equal(db.has(`users/${UID}`), false, "no users stub may be created for a deleted identity");
});
