import assert from "node:assert/strict";
import test from "node:test";
import { FieldValue } from "firebase-admin/firestore";

import {
  buildDeletedMessagePurgePatch,
  purgeExpiredDeletedAuthorMessages,
  shouldPurgeDeletedAuthorMessage,
} from "./accountDeletionChatLifecycle";

/**
 * Deleted-author message purge: candidate-set invariant.
 *
 * The purge query is
 *   collectionGroup("messages")
 *     .where("authorDeleted", "==", true)
 *     .where("legalHold", "==", false)
 *     .where("purgeAfter", "<=", now)
 *     .limit(300)
 * (ordered by purgeAfter ascending, i.e. oldest first). A message that has
 * been purged must leave that candidate set; otherwise, once 300 purged
 * messages exist, every run returns only already-purged rows and newer
 * eligible messages are never purged (starvation).
 */

type Doc = Record<string, unknown>;

/** Minimal in-memory Firestore surface for the purge query and batch writes. */
function fakeMessagesFirestore(seed: Array<{ id: string; data: Doc }>) {
  const docs = new Map(seed.map((d) => [d.id, { ...d.data }]));
  const writes: Array<{ id: string; patch: Doc }> = [];
  const toMs = (v: unknown) => (v instanceof Date ? v.getTime() : typeof v === "number" ? v : NaN);
  const firestore = {
    collectionGroup(name: string) {
      assert.equal(name, "messages");
      const filters: Array<(d: Doc) => boolean> = [];
      let max = Infinity;
      const q = {
        where(field: string, op: string, value: unknown) {
          if (op === "==") filters.push((d) => d[field] === value);
          else if (op === "<=") filters.push((d) => field in d && toMs(d[field]) <= toMs(value));
          else throw new Error(`unsupported op ${op}`);
          return q;
        },
        limit(n: number) {
          max = n;
          return q;
        },
        async get() {
          const rows = [...docs.entries()]
            .filter(([, d]) => filters.every((f) => f(d)))
            .sort((a, b) => toMs(a[1].purgeAfter) - toMs(b[1].purgeAfter))
            .slice(0, max)
            .map(([id, d]) => ({ id, ref: { id }, data: () => ({ ...d }) }));
          return { size: rows.length, docs: rows };
        },
      };
      return q;
    },
    batch() {
      const pending: Array<{ id: string; patch: Doc }> = [];
      return {
        set(ref: { id: string }, patch: Doc, options?: { merge?: boolean }) {
          assert.equal(options?.merge, true, "purge must merge, never replace the message");
          pending.push({ id: ref.id, patch });
        },
        async commit() {
          for (const { id, patch } of pending) {
            const current = docs.get(id) ?? {};
            for (const [k, v] of Object.entries(patch)) {
              if (v !== null && typeof v === "object" && (v as { constructor?: { name?: string } }).constructor?.name === "DeleteTransform") delete current[k];
              else if (v === FieldValue.delete()) delete current[k];
              else current[k] = v;
            }
            docs.set(id, current);
            writes.push({ id, patch });
          }
        },
      };
    },
  };
  return { firestore, docs, writes };
}

const NOW = new Date("2026-09-06T04:00:00Z");
const day = 24 * 60 * 60 * 1000;

function anonymizedMessage(purgeAfterDaysAgo: number, purged: boolean): Doc {
  return {
    authorDeleted: true,
    legalHold: false,
    purgeAfter: new Date(NOW.getTime() - purgeAfterDaysAgo * day),
    text: purged ? "[삭제된 메시지]" : "original body",
    ...(purged ? { purgedAt: new Date(NOW.getTime() - purgeAfterDaysAgo * day + day), purgedReason: "retention_elapsed" } : {}),
  };
}

test("starvation: 300+ already-purged eligible messages must not shadow newer unpurged ones", async () => {
  const seed: Array<{ id: string; data: Doc }> = [];
  for (let i = 0; i < 320; i += 1) seed.push({ id: `old_purged_${i}`, data: anonymizedMessage(60 + i, true) });
  for (let i = 0; i < 5; i += 1) seed.push({ id: `new_${i}`, data: anonymizedMessage(1 + i, false) });
  const fake = fakeMessagesFirestore(seed);

  const result = await purgeExpiredDeletedAuthorMessages(fake.firestore as never, { limit: 300, now: NOW });

  assert.equal(result.purged, 5, "the 5 newer eligible messages are purged in this run");
  for (let i = 0; i < 5; i += 1) {
    const d = fake.docs.get(`new_${i}`) ?? {};
    assert.ok(d.purgedAt, `new_${i} carries purgedAt`);
    assert.equal(d.text, "[삭제된 메시지]");
  }
  assert.equal(result.released, 320, "historical purged rows are released from the candidate set");
  const releaseWrites = fake.writes.filter((w) => w.id.startsWith("old_purged_"));
  assert.equal(releaseWrites.length, 320);
  assert.ok(
    releaseWrites.every((w) => Object.keys(w.patch).length === 1 && "purgeAfter" in w.patch),
    "release touches only purgeAfter; already-purged bodies are never rewritten",
  );
  for (let i = 0; i < 320; i += 1) {
    const d = fake.docs.get(`old_purged_${i}`) ?? {};
    assert.equal("purgeAfter" in d, false);
    assert.ok(d.purgedAt, "audit marker retained");
  }
  // the next run finds nothing: released rows and purged rows are both out of the query
  const again = await purgeExpiredDeletedAuthorMessages(fake.firestore as never, { limit: 300, now: NOW });
  assert.deepEqual(again, { scanned: 0, purged: 0, skipped: 0, released: 0 });
});

test("dry run reports what a run would purge/release without writing, and never loops", async () => {
  const seed: Array<{ id: string; data: Doc }> = [];
  for (let i = 0; i < 300; i += 1) seed.push({ id: `old_purged_${i}`, data: anonymizedMessage(60 + i, true) });
  seed.push({ id: "new_0", data: anonymizedMessage(1, false) });
  const fake = fakeMessagesFirestore(seed);
  const result = await purgeExpiredDeletedAuthorMessages(fake.firestore as never, { limit: 300, now: NOW, dryRun: true });
  assert.deepEqual(result, { scanned: 300, purged: 0, skipped: 300, released: 300 });
  assert.equal(fake.writes.length, 0);
});

test("a purged message leaves the purge candidate set and a rerun is a no-op (idempotent)", async () => {
  const fake = fakeMessagesFirestore([
    { id: "m1", data: anonymizedMessage(3, false) },
    { id: "m2", data: anonymizedMessage(2, false) },
  ]);
  const first = await purgeExpiredDeletedAuthorMessages(fake.firestore as never, { limit: 300, now: NOW });
  assert.equal(first.purged, 2);
  const stillCandidates = await fake.firestore
    .collectionGroup("messages")
    .where("authorDeleted", "==", true)
    .where("legalHold", "==", false)
    .where("purgeAfter", "<=", NOW)
    .limit(300)
    .get();
  assert.equal(stillCandidates.size, 0, "purged messages are no longer query candidates");
  const second = await purgeExpiredDeletedAuthorMessages(fake.firestore as never, { limit: 300, now: NOW });
  assert.deepEqual(second, { scanned: 0, purged: 0, skipped: 0, released: 0 });
  assert.equal(fake.writes.length, 2, "no duplicate destructive write");
  assert.equal(fake.docs.get("m1")?.authorDeleted, true, "author-deleted marker is preserved for the anonymized body");
  assert.equal(fake.docs.get("m1")?.legalHold, false);
});

test("purge patch never re-processes: predicate rejects purged and purgeAfter-less docs", () => {
  const patch = buildDeletedMessagePurgePatch();
  assert.equal(patch.text, "[삭제된 메시지]");
  assert.ok(patch.purgedAt, "purgedAt is still recorded for audit");
  assert.equal(
    shouldPurgeDeletedAuthorMessage({ authorDeleted: true, legalHold: false, purgeAfter: null, purgedAt: undefined, now: NOW }),
    false,
  );
  assert.equal(
    shouldPurgeDeletedAuthorMessage({ authorDeleted: true, legalHold: false, purgeAfter: new Date(NOW.getTime() - day), purgedAt: new Date(), now: NOW }),
    false,
  );
});
