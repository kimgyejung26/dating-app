/**
 * Scheduled retention purge for deleted-author chat messages, empty event
 * teams, and avatar private media whose owner identity no longer exists.
 */

import { type Firestore } from "firebase-admin/firestore";
import * as logger from "firebase-functions/logger";
import { onSchedule } from "firebase-functions/v2/scheduler";

import { purgeExpiredDeletedAuthorMessages } from "./accountDeletionChatLifecycle";
import { purgeEmptyEventTeams } from "./accountDeletionEventTeamCleanup";
import {
  createDeletedAccountAvatarPurgeDeps,
  purgeAvatarPrivateMediaForDeletedAccounts,
} from "./accountDeletionAvatarMediaPurge";

export type RetentionPurgeStageName = "messages" | "teams" | "avatarMedia";

export type RetentionPurgeStages = {
  [K in RetentionPurgeStageName]: () => Promise<unknown>;
};

export type RetentionPurgeStageOutcome =
  | { stage: RetentionPurgeStageName; status: "ok"; result: unknown }
  | { stage: RetentionPurgeStageName; status: "error"; error: unknown };

export type RetentionPurgeRunSummary = {
  outcomes: RetentionPurgeStageOutcome[];
  failedStages: RetentionPurgeStageName[];
};

export class RetentionPurgeStageError extends Error {
  readonly failedStages: RetentionPurgeStageName[];

  constructor(failedStages: RetentionPurgeStageName[]) {
    super(`account_deletion_retention_purge_stage_failed:${failedStages.join(",")}`);
    this.name = "RetentionPurgeStageError";
    this.failedStages = failedStages;
  }
}

export const RETENTION_PURGE_STAGE_ORDER: readonly RetentionPurgeStageName[] = [
  "messages",
  "teams",
  "avatarMedia",
];

/**
 * Runs every purge stage to completion regardless of the others (per-stage
 * isolation). A stage that throws is recorded and the caller still fails the
 * run at the end so the scheduler keeps reporting the failure; a failing stage
 * never prevents the remaining stages from running.
 *
 * Rationale: the three stages own different data (chat messages, event teams,
 * avatar private media) and have independent failure modes (e.g. a missing
 * composite index on one query). Sequencing them behind a fail-fast
 * `Promise.all` silently starved the avatar purge for as long as the messages
 * query failed.
 */
export async function runAccountDeletionRetentionPurgeStages(
  stages: RetentionPurgeStages,
): Promise<RetentionPurgeRunSummary> {
  const outcomes: RetentionPurgeStageOutcome[] = [];
  for (const stage of RETENTION_PURGE_STAGE_ORDER) {
    try {
      outcomes.push({ stage, status: "ok", result: await stages[stage]() });
    } catch (error) {
      outcomes.push({ stage, status: "error", error });
    }
  }
  return {
    outcomes,
    failedStages: outcomes
      .filter((outcome) => outcome.status === "error")
      .map((outcome) => outcome.stage),
  };
}

function loggableError(error: unknown): {
  errorType: string;
  errorCode?: string | number;
  errorMessageHead: string;
} {
  const code =
    error && typeof error === "object" && "code" in error
      ? (error as { code?: unknown }).code
      : undefined;
  return {
    errorType: error instanceof Error ? error.name : typeof error,
    ...(typeof code === "string" || typeof code === "number" ? { errorCode: code } : {}),
    errorMessageHead: (error instanceof Error ? error.message : String(error)).slice(0, 120),
  };
}

export function createAccountDeletionRetentionPurgeSchedule(
  firestore: Firestore
) {
  return onSchedule(
    {
      schedule: "30 4 * * *",
      timeZone: "Asia/Seoul",
      region: "asia-northeast3",
      cpu: "gcf_gen1",
      concurrency: 1,
      maxInstances: 1,
    },
    async () => {
      const summary = await runAccountDeletionRetentionPurgeStages({
        messages: () => purgeExpiredDeletedAuthorMessages(firestore, { limit: 300 }),
        teams: () => purgeEmptyEventTeams(firestore, { limit: 100 }),
        // Owner-lifecycle authority for avatar private media: an identity whose
        // Firebase Auth account is gone is purged through the same idempotent
        // cleanup contract the app withdrawal path uses (reason=account_deletion).
        avatarMedia: async () => {
          const result = await purgeAvatarPrivateMediaForDeletedAccounts(
            createDeletedAccountAvatarPurgeDeps(firestore),
            { limit: 25 },
          );
          return { ...result, candidates: undefined };
        },
      });
      const logged: Record<string, unknown> = {};
      for (const outcome of summary.outcomes) {
        logged[outcome.stage] =
          outcome.status === "ok"
            ? outcome.result
            : { status: "error", ...loggableError(outcome.error) };
      }
      if (summary.failedStages.length > 0) {
        logger.error("accountDeletionRetentionPurge completed with stage failures", {
          failedStages: summary.failedStages,
          ...logged,
        });
        throw new RetentionPurgeStageError(summary.failedStages);
      }
      logger.info("accountDeletionRetentionPurge completed", logged);
    }
  );
}
