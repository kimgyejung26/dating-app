import test from "node:test";
import {
  assertFails,
  assertSucceeds,
  getTestEnv,
  kakaoSession,
  withClearedDb,
} from "./helpers.mjs";
import { doc, setDoc, updateDoc } from "firebase/firestore";

// ---------------------------------------------------------------------------
// users/{uid}.avatar is server-owned.
//
// Regression lock for the 2026-09-02 false-approved incident: a client wrote
// users/{uid}.avatar = {status: "approved"} without the canonical approval
// write set (approvedAvatarUrl, approvedAvatarStoragePath, selectedCandidateId,
// sourceJobId), which locked the user out of every avatar flow. Only the
// approveAvatarCandidate transaction (Admin SDK) may produce an approved avatar
// state; clients may not create, replace, or edit any field of the avatar map.
// ---------------------------------------------------------------------------

const USER = "kakao_avatar_status_user_1";

function verifiedUserDoc(uid, avatar) {
  return {
    kakaoUserId: uid,
    isStudentVerified: true,
    studentEmail: "student@yonsei.ac.kr",
    nickname: "테스트",
    onboarding: { nickname: "테스트", birthYear: "2003", major: "컴퓨터과학" },
    ...(avatar ? { avatar } : {}),
  };
}

async function seedUser(avatar) {
  return withClearedDb(async (db) => {
    await setDoc(doc(db, "users", USER), verifiedUserDoc(USER, avatar));
  });
}

test.after(async () => {
  const env = await getTestEnv();
  await env.cleanup();
});

test("client cannot set users.avatar.status = approved (status-only false approval)", async () => {
  await seedUser({ status: "queued" });
  const db = await kakaoSession(USER);
  await assertFails(updateDoc(doc(db, "users", USER), { "avatar.status": "approved" }));
});

test("client cannot set users.avatar.status = terminal_failed", async () => {
  await seedUser({ status: "queued" });
  const db = await kakaoSession(USER);
  await assertFails(updateDoc(doc(db, "users", USER), { "avatar.status": "terminal_failed" }));
});

test("client cannot create the avatar map on a user document that has none", async () => {
  await seedUser(undefined);
  const db = await kakaoSession(USER);
  await assertFails(updateDoc(doc(db, "users", USER), { avatar: { status: "approved" } }));
});

test("client cannot replace the avatar map wholesale", async () => {
  await seedUser({ status: "queued", sourceJobId: "avatar_job_real_0001" });
  const db = await kakaoSession(USER);
  await assertFails(
    updateDoc(doc(db, "users", USER), {
      avatar: { status: "approved", approvedAvatarUrl: "https://cdn.example/forged.png" },
    }),
  );
});

test("client cannot update a nested avatar field", async () => {
  await seedUser({ status: "queued", sourceJobId: "avatar_job_real_0001" });
  const db = await kakaoSession(USER);
  await assertFails(updateDoc(doc(db, "users", USER), { "avatar.sourceJobId": "avatar_job_forged" }));
});

test("client cannot seed an avatar map on create", async () => {
  await withClearedDb();
  const db = await kakaoSession(USER);
  await assertFails(
    setDoc(doc(db, "users", USER), {
      ...verifiedUserDoc(USER, undefined),
      isStudentVerified: false,
      avatar: { status: "approved" },
    }),
  );
});

test("ordinary profile updates still succeed while the avatar map stays untouched", async () => {
  await seedUser({ status: "queued" });
  const db = await kakaoSession(USER);
  await assertSucceeds(updateDoc(doc(db, "users", USER), { "onboarding.selfIntroduction": "안녕하세요" }));
});
