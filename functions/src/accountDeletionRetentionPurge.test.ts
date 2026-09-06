import assert from "node:assert/strict";
import test from "node:test";

import {
  RETENTION_PURGE_STAGE_ORDER,
  RetentionPurgeStageError,
  runAccountDeletionRetentionPurgeStages,
} from "./accountDeletionRetentionPurge";

/**
 * Stage isolation contract for the daily accountDeletionRetentionPurge run.
 *
 * Production evidence (2026-08-07 .. 2026-09-05): the messages stage threw
 * FAILED_PRECONDITION (missing composite index) on every run, and because the
 * stages were chained fail-fast the avatar private media purge never executed.
 */

test("a failing messages stage does not prevent the teams and avatar media stages from running", async () => {
  const ran: string[] = [];
  const summary = await runAccountDeletionRetentionPurgeStages({
    messages: async () => {
      ran.push("messages");
      const error = new Error("9 FAILED_PRECONDITION: The query requires an index") as Error & { code?: number };
      error.code = 9;
      throw error;
    },
    teams: async () => {
      ran.push("teams");
      return { scanned: 0, purged: 0 };
    },
    avatarMedia: async () => {
      ran.push("avatarMedia");
      return { scanned: 3, authMissing: 0, purged: 0, errors: 0 };
    },
  });
  assert.deepEqual(ran, ["messages", "teams", "avatarMedia"]);
  assert.deepEqual(summary.failedStages, ["messages"]);
  assert.equal(summary.outcomes.length, 3);
  assert.equal(summary.outcomes[2].status, "ok");
});

test("every stage runs in the documented order and a clean run reports no failed stages", async () => {
  const ran: string[] = [];
  const summary = await runAccountDeletionRetentionPurgeStages({
    messages: async () => (ran.push("messages"), { purged: 1 }),
    teams: async () => (ran.push("teams"), { purged: 2 }),
    avatarMedia: async () => (ran.push("avatarMedia"), { purged: 0 }),
  });
  assert.deepEqual(ran, [...RETENTION_PURGE_STAGE_ORDER]);
  assert.deepEqual(summary.failedStages, []);
  assert.deepEqual(
    summary.outcomes.map((outcome) => outcome.status),
    ["ok", "ok", "ok"],
  );
});

test("multiple failing stages are all recorded and the avatar stage still runs last", async () => {
  const summary = await runAccountDeletionRetentionPurgeStages({
    messages: async () => {
      throw new Error("messages down");
    },
    teams: async () => {
      throw new Error("teams down");
    },
    avatarMedia: async () => ({ purged: 0 }),
  });
  assert.deepEqual(summary.failedStages, ["messages", "teams"]);
  const error = new RetentionPurgeStageError(summary.failedStages);
  assert.match(error.message, /stage_failed:messages,teams/);
  assert.deepEqual(error.failedStages, ["messages", "teams"]);
});

test("an avatar media stage failure is isolated to that stage and surfaced", async () => {
  const summary = await runAccountDeletionRetentionPurgeStages({
    messages: async () => ({ purged: 0 }),
    teams: async () => ({ purged: 0 }),
    avatarMedia: async () => {
      throw new Error("storage unavailable");
    },
  });
  assert.deepEqual(summary.failedStages, ["avatarMedia"]);
  assert.equal(summary.outcomes[0].status, "ok");
  assert.equal(summary.outcomes[1].status, "ok");
});
