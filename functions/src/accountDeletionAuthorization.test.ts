import assert from "node:assert/strict";
import test from "node:test";
import { HttpsError } from "firebase-functions/v2/https";

import { resolveAccountDeletionOwner } from "./accountDeletionAuthorization";
import {
  CLEANUP_AVATAR_MEDIA_CALLABLE_OPTIONS,
  handleCleanupAvatarMediaRequest,
  type CleanupDocs,
  type CleanupExecutor,
  type CleanupOperation,
  accountDeletionDocsFromParts,
} from "./avatarCleanup";
import { FakeFirestore, type Db } from "./testing/fakeFirestore";

/**
 * Withdrawal authorization contract (owner lifecycle, not feature access):
 *   1 fully verified user                      -> can withdraw
 *   2 authenticated, student verification not  -> can withdraw own account
 *     finished (users doc, isStudentVerified=false)
 *   3 users doc missing, auth uid proves       -> safe own cleanup path
 *     ownership                                   (skip_if_missing policy)
 *   4 payload uid is ignored                   -> caller can only delete self
 *   5 unauthenticated                          -> deny, no executor created
 *   6 App Check                                -> enforced by callable options
 *   7 rerun with same client request id        -> idempotent (duplicate short-circuit)
 *   8 Auth already deleted                     -> served by the deleted-account purge
 *     (accountDeletionAvatarMediaPurge.test.ts), not by the callable
 *   9 consent_withdrawal keeps the feature resolver (verified account required)
 */

const VERIFIED = "kakao_verified_owner";
const UNVERIFIED = "kakao_unverified_owner";
const NO_DOC = "AaBbCcDdEeFfGgHhIiJjKkLlMmNn";

function seededDb(): Db {
  const db: Db = new Map();
  db.set(`users/${VERIFIED}`, { isStudentVerified: true, studentEmail: "owner@yonsei.ac.kr", onboarding: { nickname: "n" } });
  db.set(`users/${UNVERIFIED}`, { isStudentVerified: false, kakaoUserId: UNVERIFIED });
  for (const uid of [VERIFIED, UNVERIFIED, NO_DOC]) {
    db.set(`userPrivateMedia/${uid}`, {
      sourcePhotos: [{ photoId: "src_1", status: "active", gcsUri: `gs://seolleyeon-final-private-source-photos/users/${uid}/source/src_1.jpg` }],
    });
  }
  return db;
}

type Recorded = { uid: string; authUid: string | null; policy: string | undefined; ops: string[] };

function recordingFactory(db: Db, completedRequests: Set<string>) {
  const created: Recorded[] = [];
  const factory = (_firestore: unknown, uid: string, authUid: string | null, options: { userDocPolicy?: string }) => {
    const record: Recorded = { uid, authUid, policy: options.userDocPolicy, ops: [] };
    created.push(record);
    const executor: CleanupExecutor = {
      async load(loadUid, requestId): Promise<CleanupDocs> {
        return {
          userData: db.get(`users/${loadUid}`) ?? {},
          privateMediaData: db.get(`userPrivateMedia/${loadUid}`) ?? {},
          candidateDocs: [],
          jobDocs: [],
          existingRequest: completedRequests.has(requestId) ? { status: "completed", reason: "account_deletion", response: { counts: {} } } : null,
          accountDeletionDocs: accountDeletionDocsFromParts(),
        } as unknown as CleanupDocs;
      },
      async apply(operation: CleanupOperation) {
        record.ops.push(operation.kind);
        if (operation.kind === "markCompleted") completedRequests.add(operation.requestId);
      },
    };
    return executor;
  };
  return { created, factory };
}

const featureResolver = async (auth: { uid?: string } | null | undefined) => {
  if (!auth?.uid) throw new HttpsError("unauthenticated", "로그인이 필요해요.");
  if (auth.uid !== VERIFIED) throw new HttpsError("failed-precondition", "학생 인증이 완료된 계정으로 다시 로그인해주세요.");
  return { userId: auth.uid, email: "owner@yonsei.ac.kr", data: {} };
};

function handler(db: Db, completed = new Set<string>()) {
  const fs = new FakeFirestore(db);
  const { created, factory } = recordingFactory(db, completed);
  return {
    created,
    run: (auth: { uid?: string } | null, data: Record<string, unknown>) =>
      handleCleanupAvatarMediaRequest(
        { firestore: fs as never, resolveUser: featureResolver, executorFactory: factory as never },
        { auth: auth as never, data },
      ),
  };
}

test("resolver: owner is always the auth uid; users doc state is reported, never required", async () => {
  const fs = new FakeFirestore(seededDb());
  assert.deepEqual(await resolveAccountDeletionOwner(fs as never, { uid: VERIFIED } as never), { uid: VERIFIED, usersDocExists: true, isStudentVerified: true });
  assert.deepEqual(await resolveAccountDeletionOwner(fs as never, { uid: UNVERIFIED } as never), { uid: UNVERIFIED, usersDocExists: true, isStudentVerified: false });
  assert.deepEqual(await resolveAccountDeletionOwner(fs as never, { uid: NO_DOC } as never), { uid: NO_DOC, usersDocExists: false, isStudentVerified: false });
  await assert.rejects(resolveAccountDeletionOwner(fs as never, undefined), (e: HttpsError) => e.code === "unauthenticated");
  await assert.rejects(resolveAccountDeletionOwner(fs as never, { uid: "../users" } as never), (e: HttpsError) => e.code === "invalid-argument");
});

test("1: fully verified user can withdraw (owner = auth uid, users doc required policy)", async () => {
  const h = handler(seededDb());
  const response = await h.run({ uid: VERIFIED }, { reason: "account_deletion", clientRequestId: "account_deletion_1700000000000" });
  assert.equal(response.status, "completed");
  assert.equal(h.created.length, 1);
  assert.equal(h.created[0].uid, VERIFIED);
  assert.equal(h.created[0].authUid, VERIFIED);
  assert.equal(h.created[0].policy, "require");
  assert.ok(h.created[0].ops.includes("deleteAuthUser"));
});

test("2: authenticated account that never finished student verification can withdraw its own account", async () => {
  const h = handler(seededDb());
  const response = await h.run({ uid: UNVERIFIED }, { reason: "account_deletion", clientRequestId: "account_deletion_1700000000001" });
  assert.equal(response.status, "completed");
  assert.equal(h.created[0].uid, UNVERIFIED);
  assert.equal(h.created[0].policy, "require");
  assert.ok(h.created[0].ops.includes("deleteStorage") && h.created[0].ops.includes("deleteAuthUser"));
});

test("3: users doc missing but auth uid proves ownership -> own cleanup runs with skip_if_missing (no users stub)", async () => {
  const h = handler(seededDb());
  const response = await h.run({ uid: NO_DOC }, { reason: "account_deletion", clientRequestId: "account_deletion_1700000000002" });
  assert.equal(response.status, "completed");
  assert.equal(h.created[0].uid, NO_DOC);
  assert.equal(h.created[0].policy, "skip_if_missing");
});

test("4: a uid in the payload is ignored - the caller can only delete itself", async () => {
  const h = handler(seededDb());
  await h.run({ uid: UNVERIFIED }, { reason: "account_deletion", clientRequestId: "account_deletion_1700000000003", uid: VERIFIED, userId: VERIFIED });
  assert.equal(h.created.length, 1);
  assert.equal(h.created[0].uid, UNVERIFIED);
  assert.notEqual(h.created[0].uid, VERIFIED);
});

test("5: unauthenticated callers are denied before any executor is created", async () => {
  const h = handler(seededDb());
  await assert.rejects(h.run(null, { reason: "account_deletion", clientRequestId: "account_deletion_1700000000004" }), (e: HttpsError) => e.code === "unauthenticated");
  await assert.rejects(h.run({}, { reason: "account_deletion", clientRequestId: "account_deletion_1700000000004" }), (e: HttpsError) => e.code === "unauthenticated");
  assert.equal(h.created.length, 0);
});

test("6: App Check stays enforced on the callable and it is public-invoker only through App Check + Auth", () => {
  assert.equal(CLEANUP_AVATAR_MEDIA_CALLABLE_OPTIONS.enforceAppCheck, true);
  assert.equal(CLEANUP_AVATAR_MEDIA_CALLABLE_OPTIONS.invoker, "public");
});

test("7: rerun with the same client request id after completion is idempotent (no second delete)", async () => {
  const completed = new Set<string>();
  const h = handler(seededDb(), completed);
  const first = await h.run({ uid: UNVERIFIED }, { reason: "account_deletion", clientRequestId: "account_deletion_1700000000005" });
  const second = await h.run({ uid: UNVERIFIED }, { reason: "account_deletion", clientRequestId: "account_deletion_1700000000005" });
  assert.equal(first.status, "completed");
  assert.equal(second.status, "completed");
  assert.equal(h.created.length, 2);
  assert.ok(h.created[0].ops.includes("deleteStorage"));
  assert.deepEqual(h.created[1].ops, [], "duplicate request performs no operation");
});

test("9: consent_withdrawal still requires the feature-authorized (student-verified) account", async () => {
  const h = handler(seededDb());
  await assert.rejects(h.run({ uid: UNVERIFIED }, { reason: "consent_withdrawal", clientRequestId: "consent_1700000000006" }), (e: HttpsError) => e.code === "failed-precondition");
  assert.equal(h.created.length, 0);
  const ok = await h.run({ uid: VERIFIED }, { reason: "consent_withdrawal", clientRequestId: "consent_1700000000007" });
  assert.equal(ok.status, "completed");
  assert.ok(!h.created[0].ops.includes("deleteAuthUser"));
});
