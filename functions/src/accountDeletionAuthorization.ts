import { type Firestore } from "firebase-admin/firestore";
import { HttpsError, type CallableRequest } from "firebase-functions/v2/https";

/**
 * Account-deletion authorization.
 *
 * Deleting one's own account is an owner-lifecycle action, not a product
 * feature: it must be available to every authenticated identity, including
 * accounts that never finished student verification or never got a
 * `users/{uid}` document. The feature resolver (`resolveAuthedAppUser`)
 * requires a student-verified users doc and therefore locked those accounts
 * out of withdrawal (`failed-precondition`).
 *
 * Authority model (unchanged from the feature callables where it matters):
 *   - Firebase Auth is required; the owner is ALWAYS `request.auth.uid`.
 *     Nothing in the request payload can select another identity.
 *   - App Check stays enforced by the callable options.
 *   - Kakao tokens are never an account-deletion authority.
 *   - The identity contract guarantees `FirebaseAuth.currentUser.uid ==
 *     appUserId` for canonical sessions (legacy Kakao numeric ids included),
 *     so `users/{auth.uid}` is the caller's own document when it exists.
 */
export type AccountDeletionOwner = {
  uid: string;
  usersDocExists: boolean;
  isStudentVerified: boolean;
};

const UID_SEGMENT = /^[A-Za-z0-9_-]{1,128}$/;

export async function resolveAccountDeletionOwner(
  firestore: Firestore,
  auth: CallableRequest<unknown>["auth"],
): Promise<AccountDeletionOwner> {
  const uid = typeof auth?.uid === "string" ? auth.uid.trim() : "";
  if (!uid) {
    throw new HttpsError("unauthenticated", "로그인이 필요해요.");
  }
  if (!UID_SEGMENT.test(uid) || uid === "." || uid === "..") {
    throw new HttpsError("invalid-argument", "account_deletion_owner_invalid");
  }
  const snap = await firestore.collection("users").doc(uid).get();
  const data = (snap.exists ? snap.data() : undefined) ?? {};
  return {
    uid,
    usersDocExists: snap.exists,
    isStudentVerified: data.isStudentVerified === true,
  };
}
