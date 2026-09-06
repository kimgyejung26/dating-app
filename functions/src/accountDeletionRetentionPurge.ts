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
      const [messages, teams] = await Promise.all([
        purgeExpiredDeletedAuthorMessages(firestore, { limit: 300 }),
        purgeEmptyEventTeams(firestore, { limit: 100 }),
      ]);
      // Owner-lifecycle authority for avatar private media: an identity whose
      // Firebase Auth account is gone is purged through the same idempotent
      // cleanup contract the app withdrawal path uses (reason=account_deletion).
      const avatarMedia = await purgeAvatarPrivateMediaForDeletedAccounts(
        createDeletedAccountAvatarPurgeDeps(firestore),
        { limit: 25 },
      );
      logger.info("accountDeletionRetentionPurge completed", {
        messages,
        teams,
        avatarMedia: { ...avatarMedia, candidates: undefined },
      });
    }
  );
}
