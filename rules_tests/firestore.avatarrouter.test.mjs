import test from "node:test";

import {
  anon,
  assertFails,
  getTestEnv,
  kakaoSession,
  withClearedDb,
} from "./helpers.mjs";

import {
  deleteDoc,
  doc,
  getDoc,
  setDoc,
  Timestamp,
  updateDoc,
} from "firebase/firestore";

const STATE_PATH = ["avatarProviderRouterState", "gpt-image-2"];

async function seedRouterState() {
  return withClearedDb(async (db) => {
    await setDoc(doc(db, ...STATE_PATH), {
      schemaVersion: "azure_router_state_v1",
      sequence: 1,
      endpoints: {
        ep1: {
          rpmLimit: 2,
          lastReservedAt: Timestamp.now(),
          nextAvailableAt: Timestamp.now(),
        },
      },
      updatedAt: Timestamp.now(),
    });
  });
}

test.after(async () => {
  const env = await getTestEnv();
  await env.cleanup();
});

for (const [sessionName, session] of [
  ["anonymous", anon],
  ["authenticated", () => kakaoSession("router_attacker")],
]) {
  test(`SEC-AVATAR-ROUTER: ${sessionName} client cannot read router state`, async () => {
    await seedRouterState();
    const db = await session();
    await assertFails(getDoc(doc(db, ...STATE_PATH)));
  });

  test(`SEC-AVATAR-ROUTER: ${sessionName} client cannot create router state`, async () => {
    await withClearedDb();
    const db = await session();
    await assertFails(
      setDoc(doc(db, ...STATE_PATH), {
        schemaVersion: "attacker",
        sequence: 999,
      })
    );
  });

  test(`SEC-AVATAR-ROUTER: ${sessionName} client cannot update router state`, async () => {
    await seedRouterState();
    const db = await session();
    await assertFails(updateDoc(doc(db, ...STATE_PATH), { sequence: 999 }));
  });

  test(`SEC-AVATAR-ROUTER: ${sessionName} client cannot delete router state`, async () => {
    await seedRouterState();
    const db = await session();
    await assertFails(deleteDoc(doc(db, ...STATE_PATH)));
  });
}
