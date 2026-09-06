import { createHash } from "crypto";
import { getAuth } from "firebase-admin/auth";
import { FieldPath, type Firestore } from "firebase-admin/firestore";
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
  /** Owner ids that are not account identities (synthetic fixtures / smoke ids); never purged here. */
  unclassifiedIdentity: number;
  alreadyCompleted: number;
  purged: number;
  /** Auth-missing owners found beyond this run's purge cap; picked up next run. */
  deferred: number;
  errors: number;
  dryRun: boolean;
  candidates: DeletedAccountAvatarPurgeCandidate[];
  unclassified: string[];
};

/**
 * Account identities are Firebase Auth uids (28 url-safe chars) or numeric
 * Kakao ids. Anything else in userPrivateMedia (e.g. `avatar_live_fixture_*`,
 * `avatar_smoke_*`, `avatar_azure_stage_*`) was written by fixture/smoke
 * tooling, never had an Auth account, and is test-data lifecycle - not an
 * account deletion. Those ids are reported for the test-data cleanup plan and
 * are never run through the account-deletion contract.
 */
export function isAccountIdentityShape(uid: string): boolean {
  return /^[A-Za-z0-9_-]{28}$/.test(uid) || /^[0-9]{6,20}$/.test(uid);
}

/** Upper bound on owner ids examined per run (cheap id-only reads). */
export const DELETED_ACCOUNT_PURGE_SCAN_LIMIT = 5000;

export type DeletedAccountAvatarPurgeDeps = {
  /**
   * userPrivateMedia document ids (owner uids) in stable document-id order,
   * bounded by `scanLimit`. Every owner must be reachable by the scan: the
   * purge cap (`limit`) bounds how many cleanups are applied per run, never
   * how many owners are examined.
   */
  listPrivateMediaOwnerUids(scanLimit: number): Promise<string[]>;
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
  options: { limit?: number; scanLimit?: number; dryRun?: boolean } = {},
): Promise<DeletedAccountAvatarPurgeSummary> {
  const limit = Math.max(1, Math.min(options.limit ?? 25, 100));
  const scanLimit = Math.max(
    limit,
    Math.min(options.scanLimit ?? DELETED_ACCOUNT_PURGE_SCAN_LIMIT, DELETED_ACCOUNT_PURGE_SCAN_LIMIT),
  );
  const dryRun = options.dryRun === true;
  const summary: DeletedAccountAvatarPurgeSummary = {
    scanned: 0,
    authPresent: 0,
    authMissing: 0,
    unclassifiedIdentity: 0,
    alreadyCompleted: 0,
    purged: 0,
    deferred: 0,
    errors: 0,
    dryRun,
    candidates: [],
    unclassified: [],
  };
  // Every owner is examined (bounded by scanLimit); only the number of
  // cleanups applied per run is capped by `limit`. Owners beyond the cap are
  // reported as deferred and picked up by the next run, because completed
  // cleanups short-circuit and the scan order is stable.
  const uids = await deps.listPrivateMediaOwnerUids(scanLimit);
  for (const uid of uids) {
    summary.scanned += 1;
    try {
      if (!isAccountIdentityShape(uid)) {
        summary.unclassifiedIdentity += 1;
        summary.unclassified.push(uidHashForLog(uid));
        continue;
      }
      if (await deps.cleanupAlreadyCompleted(uid)) {
        summary.alreadyCompleted += 1;
        continue;
      }
      if (await deps.authUserExists(uid)) {
        summary.authPresent += 1;
        continue;
      }
      summary.authMissing += 1;
      if (summary.candidates.length >= limit) {
        summary.deferred += 1;
        continue;
      }
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
    async listPrivateMediaOwnerUids(scanLimit) {
      // Id-only pagination in document-id order so every owner is reachable
      // regardless of collection size; no document bodies are read here.
      const pageSize = 500;
      const uids: string[] = [];
      let cursor: string | null = null;
      while (uids.length < scanLimit) {
        const take = Math.min(pageSize, scanLimit - uids.length);
        let query = firestore
          .collection("userPrivateMedia")
          .orderBy(FieldPath.documentId())
          .select()
          .limit(take);
        if (cursor) query = query.startAfter(cursor);
        const snap = await query.get();
        for (const doc of snap.docs) uids.push(doc.id);
        if (snap.size < take) break;
        cursor = snap.docs[snap.docs.length - 1].id;
      }
      return uids;
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
