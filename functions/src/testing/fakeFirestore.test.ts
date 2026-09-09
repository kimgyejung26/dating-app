import assert from "node:assert/strict";
import test from "node:test";

import { FieldValue } from "firebase-admin/firestore";

import { FakeFirestore, type Db } from "./fakeFirestore";

// ---------------------------------------------------------------------------
// Firestore write-semantics contract (2026-09-09)
//
// Verified against real Firestore on 2026-09-09. A dotted string key means
// different things per write API, and the difference is why production wrote
// literal "avatar.status" fields while the nested map kept its old value:
//
//   set(merge) + "a.b"        -> a literal top-level field named "a.b"
//   update()   + "a.b"        -> the nested field path a -> b
//   delete via set(merge)     -> does NOT remove the nested field
//   delete via update()       -> removes the nested field
//   set(merge) nested object  -> merges into the map, siblings kept
//
// The double must reproduce this, otherwise incorrect production writes look
// correct in tests.
// ---------------------------------------------------------------------------

function seeded(): { store: Db; fs: FakeFirestore } {
  const store: Db = new Map<string, Record<string, unknown>>([
    ["users/u1", { avatar: { status: "queued", errorCode: "boom" } }],
  ]);
  return { store, fs: new FakeFirestore(store) };
}

test("set(merge) treats a dotted key as a literal field name", async () => {
  const { store, fs } = seeded();
  await fs.collection("users").doc("u1").set({ "avatar.status": "none" }, { merge: true });
  const doc = store.get("users/u1") as Record<string, unknown>;
  assert.equal(
    Object.keys(doc).includes("avatar.status"),
    true,
    "real Firestore creates a literal top-level field",
  );
  assert.equal(
    (doc.avatar as Record<string, unknown>).status,
    "queued",
    "the nested map must be left untouched",
  );
});

test("update() treats a dotted key as a nested field path", async () => {
  const { store, fs } = seeded();
  await fs.collection("users").doc("u1").update({ "avatar.status": "none" });
  const doc = store.get("users/u1") as Record<string, unknown>;
  assert.equal(Object.keys(doc).includes("avatar.status"), false, "no literal field");
  const avatar = doc.avatar as Record<string, unknown>;
  assert.equal(avatar.status, "none");
  assert.equal(avatar.errorCode, "boom", "siblings survive a field-path update");
});

test("FieldValue.delete() removes a nested field only through update()", async () => {
  const viaSet = seeded();
  await viaSet.fs
    .collection("users")
    .doc("u1")
    .set({ "avatar.errorCode": FieldValue.delete() }, { merge: true });
  assert.equal(
    "errorCode" in ((viaSet.store.get("users/u1") as Record<string, unknown>).avatar as Record<string, unknown>),
    true,
    "set(merge) cannot delete a nested field through a dotted key",
  );

  const viaUpdate = seeded();
  await viaUpdate.fs
    .collection("users")
    .doc("u1")
    .update({ "avatar.errorCode": FieldValue.delete() });
  assert.equal(
    "errorCode" in ((viaUpdate.store.get("users/u1") as Record<string, unknown>).avatar as Record<string, unknown>),
    false,
    "update() deletes the nested field",
  );
});

test("set(merge) with a nested object merges into the map and keeps siblings", async () => {
  const { store, fs } = seeded();
  await fs.collection("users").doc("u1").set({ avatar: { status: "none" } }, { merge: true });
  const avatar = (store.get("users/u1") as Record<string, unknown>).avatar as Record<string, unknown>;
  assert.equal(avatar.status, "none");
  assert.equal(avatar.errorCode, "boom");
});

test("transaction writes follow the same per-API semantics", async () => {
  const { store, fs } = seeded();
  await fs.runTransaction(async (tx) => {
    tx.set(fs.collection("users").doc("u1") as never, { "avatar.status": "none" }, { merge: true });
  });
  const doc = store.get("users/u1") as Record<string, unknown>;
  assert.equal(Object.keys(doc).includes("avatar.status"), true);
  assert.equal((doc.avatar as Record<string, unknown>).status, "queued");
});
