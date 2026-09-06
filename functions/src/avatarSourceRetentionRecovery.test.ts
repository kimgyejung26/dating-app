import assert from "node:assert/strict";
import test from "node:test";
import { Timestamp } from "firebase-admin/firestore";

import {
  avatarSourceRetentionStateId,
  executeAvatarSourceRetention,
  recoverAvatarSourceRetentionDeletions,
} from "./avatarSourceRetention";
import { FakeFirestore, type Db, type Doc } from "./testing/fakeFirestore";

/**
 * Recovery-loop contract for `recoverAvatarSourceRetention` (the scheduled
 * function). Every fixture drives the real claim -> revalidate -> delete ->
 * mark path with an in-memory Firestore and an injected object deleter, so the
 * assertions are about production semantics, not about mocks:
 *
 *   A canonical terminal + eligible      -> exactly one delete, state deleted
 *   B approval-protected user            -> retained, state stale, no delete
 *   C legacy clip map missing, no consent -> claim + delete
 *   D legacy clip map missing, consent    -> retained (fail closed)
 *   E canonical CLIP pending/processing   -> retained
 *   F deleted user (private doc missing)  -> explicit skip, no mutation
 *   G superseded non-current historical   -> no mutation
 *   H selection generation mismatch       -> no delete
 *   I active/current generation           -> retained
 *   J rerun                               -> idempotent (one delete total)
 *   K already deleted                     -> not scanned, no-op
 *   L expired lease / retry schedule      -> exactly-once convergence
 */

const UID = "uid_recovery_user";
const JOB = "avatar_job_recovery_0001";
const PHOTO = "src_recovery_photo";
const BUCKET = "seolleyeon-final-private-source-photos";
const PATH = `users/${UID}/source/${PHOTO}.jpg`;
const STATE_ID = avatarSourceRetentionStateId(UID, PHOTO);
const STATES = "avatarSourceRetentionStates";

type Fixture = {
  job?: Partial<Doc> | null;
  privateDoc?: Partial<Doc> | null;
  user?: Doc | null;
  clip?: Doc | null;
  state?: Partial<Doc> | null;
  consent?: Doc;
};

function build(fixture: Fixture = {}): { db: Db; fs: FakeFirestore; deleted: string[] } {
  const consent = fixture.consent ?? {
    avatarGeneration: true,
    clipRecommendation: false,
    sourcePhotoRetention: false,
  };
  const db: Db = new Map();
  if (fixture.job !== null) {
    db.set(`avatarJobs/${JOB}`, {
      uid: UID,
      status: "terminal_failed",
      sourcePhotoIds: [PHOTO],
      sourcePhotoRefs: [`gs://${BUCKET}/${PATH}`],
      avatarSourceSelectionVersion: 1,
      consentPurposes: consent,
      ...(fixture.job ?? {}),
    });
  }
  if (fixture.privateDoc !== null) {
    db.set(`userPrivateMedia/${UID}`, {
      currentAvatarJobId: JOB,
      currentAvatarSourcePhotoId: PHOTO,
      avatarSourceSelectionVersion: 1,
      photoConsent: { purposes: consent },
      sourcePhotos: [
        {
          photoId: PHOTO,
          status: "active",
          avatarGenerationState: "current",
          gcsUri: `gs://${BUCKET}/${PATH}`,
          storageBucket: BUCKET,
          storagePath: PATH,
        },
      ],
      ...(fixture.privateDoc ?? {}),
    });
  }
  if (fixture.user !== null) {
    db.set(`users/${UID}`, fixture.user ?? { avatar: { status: "terminal_failed" } });
  }
  if (fixture.clip) db.set(`clipEmbeddings/${UID}`, fixture.clip);
  if (fixture.state !== null) {
    db.set(`${STATES}/${STATE_ID}`, {
      uid: UID,
      jobId: JOB,
      photoId: PHOTO,
      sourceSelectionVersion: 1,
      status: "stale",
      attempts: 1,
      trigger: "avatar_job",
      ...(fixture.state ?? {}),
    });
  }
  const fs = new FakeFirestore(db);
  const deleted: string[] = [];
  return { db, fs, deleted };
}

function deleter(deleted: string[]) {
  return async (ref: { bucket: string; path: string }) => {
    deleted.push(`gs://${ref.bucket}/${ref.path}`);
  };
}

function state(db: Db): Doc {
  return db.get(`${STATES}/${STATE_ID}`) ?? {};
}

async function recover(fs: FakeFirestore, deleted: string[]) {
  return recoverAvatarSourceRetentionDeletions({
    firestore: fs as never,
    deleteObject: deleter(deleted),
  });
}

test("A: canonical terminal job with eligible source is deleted exactly once and state converges", async () => {
  const { db, fs, deleted } = build({
    job: { sourceSelection: { status: "selected", selectedPhotoId: PHOTO } },
  });
  const summary = await recover(fs, deleted);
  assert.deepEqual(summary, { scanned: 1, due: 1, claimed: 1, skipped: 0 });
  assert.deepEqual(deleted, [`gs://${BUCKET}/${PATH}`]);
  assert.equal(state(db).status, "deleted");
  const job = db.get(`avatarJobs/${JOB}`) ?? {};
  assert.deepEqual(job.sourcePhotoRefs, []);
  assert.ok(job.sourceRefRedactedAt);
  const priv = db.get(`userPrivateMedia/${UID}`) ?? {};
  const entries = priv.sourcePhotos as Doc[];
  assert.equal(entries[0].status, "source_deleted");
  assert.equal(entries[0].gcsUri, undefined);
  assert.equal(
    Array.from(db.keys()).filter((key) => key.startsWith("avatarSourceRetentionEvents/")).length,
    1,
  );
});

test("B: approval-protected user is retained (state stale, no delete)", async () => {
  const { db, fs, deleted } = build({ user: { avatar: { status: "approved" } } });
  const summary = await recover(fs, deleted);
  assert.equal(summary.claimed, 0);
  assert.deepEqual(deleted, []);
  assert.equal(state(db).status, "stale");
  assert.ok((db.get(`avatarJobs/${JOB}`)?.sourcePhotoRefs as string[]).length === 1);
});

test("C: legacy job with clip map missing and clip never requested is eligible", async () => {
  const { db, fs, deleted } = build({
    privateDoc: { clip: undefined },
    job: { model: { provider: "local_cloud_run" } },
  });
  const summary = await recover(fs, deleted);
  assert.equal(summary.claimed, 1);
  assert.equal(deleted.length, 1);
  assert.equal(state(db).status, "deleted");
});

test("D: legacy job with clip map missing but clip consent/request evidence is retained (fail closed)", async () => {
  const { db, fs, deleted } = build({
    consent: { avatarGeneration: true, clipRecommendation: true, sourcePhotoRetention: false },
    job: { model: { provider: "local_cloud_run" } },
  });
  const summary = await recover(fs, deleted);
  assert.equal(summary.claimed, 0);
  assert.deepEqual(deleted, []);
  assert.equal(state(db).status, "stale");
});

for (const clipStatus of ["pending", "processing"]) {
  test(`E: canonical CLIP ${clipStatus} is retained`, async () => {
    const { db, fs, deleted } = build({
      consent: { avatarGeneration: true, clipRecommendation: true, sourcePhotoRetention: false },
      privateDoc: { clip: { embeddingStatus: clipStatus } },
    });
    const summary = await recover(fs, deleted);
    assert.equal(summary.claimed, 0);
    assert.deepEqual(deleted, []);
    assert.equal(state(db).status, "stale");
  });
}

test("F: deleted user (private doc missing) is an explicit skip with no mutation", async () => {
  const { db, fs, deleted } = build({ privateDoc: null, user: null });
  const before = JSON.stringify(Array.from(db.entries()));
  const summary = await recover(fs, deleted);
  assert.deepEqual(summary, { scanned: 1, due: 1, claimed: 0, skipped: 1 });
  assert.deepEqual(deleted, []);
  assert.equal(JSON.stringify(Array.from(db.entries())), before);
  assert.deepEqual(fs.writes, []);
});

test("G: superseded non-current historical job is never mutated", async () => {
  const { db, fs, deleted } = build({
    job: { status: "superseded", errorCode: "avatar_job_superseded_old_contract" },
    privateDoc: { currentAvatarJobId: "avatar_job_other_current", currentAvatarSourcePhotoId: "src_other" },
  });
  const before = JSON.stringify(Array.from(db.entries()));
  const summary = await recover(fs, deleted);
  assert.equal(summary.claimed, 0);
  assert.deepEqual(deleted, []);
  assert.equal(JSON.stringify(Array.from(db.entries())), before);
});

test("H: selection generation mismatch blocks deletion", async () => {
  const { db, fs, deleted } = build({ privateDoc: { avatarSourceSelectionVersion: 2 } });
  const summary = await recover(fs, deleted);
  assert.equal(summary.claimed, 0);
  assert.deepEqual(deleted, []);
  assert.equal(state(db).status, "stale");
});

for (const status of ["queued", "running", "qa_pending", "preview_ready"]) {
  test(`I: active/current generation (${status}) is retained`, async () => {
    const { db, fs, deleted } = build({ job: { status } });
    const summary = await recover(fs, deleted);
    assert.equal(summary.claimed, 0);
    assert.deepEqual(deleted, []);
    assert.equal(state(db).status, "stale");
  });
}

test("J: rerunning recovery is idempotent (one delete total, second run finds nothing due)", async () => {
  const { db, fs, deleted } = build();
  const first = await recover(fs, deleted);
  const second = await recover(fs, deleted);
  assert.equal(first.claimed, 1);
  assert.deepEqual(second, { scanned: 0, due: 0, claimed: 0, skipped: 0 });
  assert.equal(deleted.length, 1);
  assert.equal(state(db).status, "deleted");
});

test("K: already deleted state is not scanned and a direct execute is a no-op", async () => {
  const { db, fs, deleted } = build({ state: { status: "deleted" } });
  const summary = await recover(fs, deleted);
  assert.deepEqual(summary, { scanned: 0, due: 0, claimed: 0, skipped: 0 });
  const direct = await executeAvatarSourceRetention({
    firestore: fs as never,
    uid: UID,
    jobId: JOB,
    trigger: "avatar_job",
    deleteObject: deleter(deleted),
  });
  assert.equal(direct, "skipped");
  assert.deepEqual(deleted, []);
  assert.equal(state(db).status, "deleted");
});

test("L: an expired 'deleting' lease is recovered exactly once; an unexpired one is left alone", async () => {
  const expired = build({
    state: {
      status: "deleting",
      claimToken: "old-token",
      leaseExpiresAt: Timestamp.fromMillis(Date.now() - 60_000),
    },
  });
  const summary = await recover(expired.fs, expired.deleted);
  assert.equal(summary.claimed, 1);
  assert.equal(expired.deleted.length, 1);
  assert.equal(state(expired.db).status, "deleted");
  assert.equal((await recover(expired.fs, expired.deleted)).claimed, 0);

  const held = build({
    state: {
      status: "deleting",
      claimToken: "live-token",
      leaseExpiresAt: Timestamp.fromMillis(Date.now() + 10 * 60_000),
    },
  });
  const heldSummary = await recover(held.fs, held.deleted);
  assert.equal(heldSummary.claimed, 0);
  assert.deepEqual(held.deleted, []);
  assert.equal(state(held.db).status, "deleting");

  const future = build({
    state: { status: "retryable_failed", nextRetryAt: Timestamp.fromMillis(Date.now() + 60 * 60_000) },
  });
  const futureSummary = await recover(future.fs, future.deleted);
  assert.deepEqual(futureSummary, { scanned: 1, due: 0, claimed: 0, skipped: 0 });
  assert.deepEqual(future.deleted, []);
});

test("M: a deleter failure is recorded as retryable_failed with a bounded retry schedule", async () => {
  const { db, fs } = build();
  const summary = await recoverAvatarSourceRetentionDeletions({
    firestore: fs as never,
    deleteObject: async () => {
      throw new Error("storage unavailable");
    },
  });
  assert.equal(summary.claimed, 1);
  const st = state(db);
  assert.equal(st.status, "retryable_failed");
  assert.ok(st.nextRetryAt instanceof Timestamp);
  assert.equal((db.get(`avatarJobs/${JOB}`)?.sourcePhotoRefs as string[]).length, 1);
});
