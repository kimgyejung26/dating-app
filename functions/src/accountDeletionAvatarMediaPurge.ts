import { createHash } from "crypto";
import { getAuth } from "firebase-admin/auth";
import { type Firestore } from "firebase-admin/firestore";
import * as logger from "firebase-functions/logger";

import {
  createAvatarCleanupFirestoreExecutor,
  executeAvatarCleanup,
  planAvatarCleanup,
  type AvatarCleanupResponse,
  type CleanupOperation,
} from "./avatarCleanup";

/**
 * Deleted-account avatar private media purge.
 *
 * Ownership authority split (kept deliberately separate):
 *   - ACCOUNT DELETION (owner lifecycle)  -> this module, run from the daily
 *     accountDeletionRetentionPurge schedule.
 *   - GENERATION TERMINAL (source lifecycle) -> avatarSourceRetention
 *     (trigger + recoverAvatarSourceRetention).
 *
 * The app withdrawal path (UserService.withdrawAccount -> cleanupAvatarMedia
 * callable) is the primary purge. Identities removed from Firebase Auth by any
 * other path (console, tooling) never invoke it, so their userPrivateMedia,
 * candidates and private source objects were left behind. This pass reuses the
 * exact same cleanup plan (reason=account_deletion, same request idempotency,
 * same audit record) for owners whose Auth account no longer exists.
 */

export const DELETED_ACCOUNT_PURGE_REQUEST_ID = "account_deletion_auth_missing_v1";
export const DELETED_ACCOUNT_PURGE_REASON = "account_deletion" as const;

export type DeletedAccountAvatarPurgeCandidate = {
  uidHash: string;
  /** Operation kinds the cleanup plan would apply (dry-run evidence). */
  plannedOperations: Record<string, number>;
};

export type DeletedAccountAvatarPurgeSummary = {
  scanned: number;
  authPresent: number;
  authMissing: number;
  alreadyCompleted: number;
  purged: number;
  errors: number;
  dryRun: boolean;
  candidates: DeletedAccountAvatarPurgeCandidate[];
};

export type DeletedAccountAvatarPurgeDeps = {
  /** userPrivateMedia document ids (owner uids), bounded by `limit`. */
  listPrivateMediaOwnerUids(limit: number): Promise<string[]>;
  /** True when the Firebase Auth account still exists (active or disabled). */
  authUserExists(uid: string): Promise<boolean>;
  /** True when the idempotent cleanup request for this uid already completed. */
  cleanupAlreadyCompleted(uid: string): Promise<boolean>;
  /** Plans the cleanup without applying (dry-run evidence). */
  planCleanup(uid: string): Promise<CleanupOperation[]>;
  /** Applies the full idempotent cleanup contract for this uid. */
  runCleanup(uid: string): Promise<AvatarCleanupResponse>;
};

export function uidHashForLog(uid: string): string {
  return createHash("sha256").update(uid).digest("hex").slice(0, 12);
}

function countOperations(operations: CleanupOperation[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const operation of operations) {
    counts[operation.kind] = (counts[operation.kind] ?? 0) + 1;
  }
  return counts;
}

export async function purgeAvatarPrivateMediaForDeletedAccounts(
  deps: DeletedAccountAvatarPurgeDeps,
  options: { limit?: number; dryRun?: boolean } = {},
): Promise<DeletedAccountAvatarPurgeSummary> {
  const limit = Math.max(1, Math.min(options.limit ?? 25, 100));
  const dryRun = options.dryRun === true;
  const summary: DeletedAccountAvatarPurgeSummary = {
    scanned: 0,
    authPresent: 0,
    authMissing: 0,
    alreadyCompleted: 0,
    purged: 0,
    errors: 0,
    dryRun,
    candidates: [],
  };
  const uids = await deps.listPrivateMediaOwnerUids(limit);
  for (const uid of uids) {
    summary.scanned += 1;
    try {
      if (await deps.cleanupAlreadyCompleted(uid)) {
        summary.alreadyCompleted += 1;
        continue;
      }
      if (await deps.authUserExists(uid)) {
        summary.authPresent += 1;
        continue;
      }
      summary.authMissing += 1;
      const plannedOperations = countOperations(await deps.planCleanup(uid));
      summary.candidates.push({ uidHash: uidHashForLog(uid), plannedOperations });
      if (dryRun) continue;
      await deps.runCleanup(uid);
      summary.purged += 1;
    } catch (error) {
      summary.errors += 1;
      logger.warn("deleted-account avatar media purge failed for one owner", {
        uidHash: uidHashForLog(uid),
        errorHash: createHash("sha256")
          .update(error instanceof Error ? error.message : String(error))
          .digest("hex")
          .slice(0, 16),
      });
    }
  }
  return summary;
}

export function createDeletedAccountAvatarPurgeDeps(
  firestore: Firestore,
): DeletedAccountAvatarPurgeDeps {
  const executorFor = (uid: string) =>
    createAvatarCleanupFirestoreExecutor(firestore, uid, null, {
      userDocPolicy: "skip_if_missing",
    });
  const requestIdFor = (uid: string) =>
    createHash("sha256")
      .update(`${uid}:${DELETED_ACCOUNT_PURGE_REQUEST_ID}:avatar_cleanup_v1`)
      .digest("hex")
      .slice(0, 32);
  return {
    async listPrivateMediaOwnerUids(limit) {
      const snap = await firestore.collection("userPrivateMedia").limit(limit).get();
      return snap.docs.map((doc) => doc.id);
    },
    async authUserExists(uid) {
      try {
        await getAuth().getUser(uid);
        return true;
      } catch (error) {
        const code =
          error && typeof error === "object" && "code" in error
            ? String((error as { code?: unknown }).code ?? "")
            : "";
        if (code === "auth/user-not-found") return false;
        throw error;
      }
    },
    async cleanupAlreadyCompleted(uid) {
      const snap = await firestore
        .collection("avatarMediaCleanupRequests")
        .doc(requestIdFor(uid))
        .get();
      return snap.exists && String(snap.get("status") ?? "") === "completed";
    },
    async planCleanup(uid) {
      const executor = executorFor(uid);
      const docs = await executor.load(uid, requestIdFor(uid));
      return planAvatarCleanup({
        uid,
        requestId: requestIdFor(uid),
        reason: DELETED_ACCOUNT_PURGE_REASON,
        docs,
      }).operations;
    },
    async runCleanup(uid) {
      return executeAvatarCleanup({
        uid,
        clientRequestId: DELETED_ACCOUNT_PURGE_REQUEST_ID,
        reason: DELETED_ACCOUNT_PURGE_REASON,
        executor: executorFor(uid),
      });
    },
  };
}
