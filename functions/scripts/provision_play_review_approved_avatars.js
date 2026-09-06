/**
 * Moves the fixed Google Play review fixtures onto the same approved-avatar
 * storage contract used by normal member accounts.
 *
 * Default is dry-run. Apply only writes these fixed review UIDs:
 *   - Storage: gs://seolleyeon-final-approved-avatars/users/{uid}/avatar/play_review_v1.png
 *   - Firestore: users/{uid}, publicProfiles/{uid}
 *
 * Usage:
 *   node scripts/provision_play_review_approved_avatars.js \
 *     --project seolleyeon-final --database '(default)' \
 *     --images ../../tmp/play_review_fixture_images.json --apply
 */
const crypto = require("crypto");
const fs = require("fs");
const admin = require("firebase-admin");

const PROJECT_ID = "seolleyeon-final";
const DATABASE_ID = "(default)";
const APPROVED_AVATAR_BUCKET = "seolleyeon-final-approved-avatars";
const REVIEWER_UID = "play-reviewer-v1";
const FIXTURE_UIDS = [
  REVIEWER_UID,
  "play-fixture-a-02",
  "play-fixture-a-03",
  "play-fixture-b-01",
  "play-fixture-b-02",
  "play-fixture-b-03",
  "play-fixture-b-04",
  "play-fixture-b-05",
  "play-fixture-b-06",
];
const AVATAR_ID = "play_review_v1";

const args = process.argv.slice(2);
const option = (name) => {
  const index = args.indexOf(`--${name}`);
  return index >= 0 ? String(args[index + 1] || "").trim() : "";
};
const apply = args.includes("--apply");
const projectId = option("project");
const databaseId = option("database") || DATABASE_ID;
const imageFile = option("images");

if (projectId !== PROJECT_ID || databaseId !== DATABASE_ID) {
  console.error(`Refusing: target must be ${PROJECT_ID}/${DATABASE_ID}.`);
  process.exit(2);
}
if (!imageFile) {
  console.error("Refusing: --images is required.");
  process.exit(2);
}

function readImages() {
  const images = JSON.parse(fs.readFileSync(imageFile, "utf8"));
  if (!images || typeof images !== "object" || Array.isArray(images)) {
    throw new Error("--images must be a JSON object keyed by the fixed review UIDs.");
  }
  for (const uid of FIXTURE_UIDS) {
    const url = images[uid];
    if (typeof url !== "string" || !url.startsWith("https://")) {
      throw new Error(`A permanent HTTPS source image is required for ${uid}.`);
    }
    if (/x-goog-|signature=|expires=|token=|googleaccessid/i.test(url)) {
      throw new Error(`Credentialed source URLs are forbidden for ${uid}.`);
    }
  }
  return images;
}

function objectPath(uid) {
  return `users/${uid}/avatar/${AVATAR_ID}.png`;
}

function storagePath(uid) {
  return `gs://${APPROVED_AVATAR_BUCKET}/${objectPath(uid)}`;
}

function publicUrl(uid, downloadToken) {
  return `https://firebasestorage.googleapis.com/v0/b/${encodeURIComponent(
    APPROVED_AVATAR_BUCKET,
  )}/o/${encodeURIComponent(objectPath(uid))}?alt=media&token=${encodeURIComponent(downloadToken)}`;
}

async function downloadPng(url, uid) {
  const response = await fetch(url, { redirect: "error" });
  if (!response.ok) {
    throw new Error(`Source image download failed for ${uid}: ${response.status}.`);
  }
  const contentType = String(response.headers.get("content-type") || "").toLowerCase();
  if (!contentType.startsWith("image/")) {
    throw new Error(`Source image for ${uid} is not an image.`);
  }
  const bytes = Buffer.from(await response.arrayBuffer());
  if (bytes.length === 0 || bytes.length > 5 * 1024 * 1024) {
    throw new Error(`Source image size is invalid for ${uid}.`);
  }
  return bytes;
}

async function main() {
  const images = readImages();
  const plan = {
    projectId,
    databaseId,
    mode: apply ? "apply" : "dry-run",
    dataPartition: "play_review",
    approvedAvatarBucket: APPROVED_AVATAR_BUCKET,
    fixedReviewUids: FIXTURE_UIDS,
    objectPaths: FIXTURE_UIDS.map(objectPath),
    firestoreDocuments: FIXTURE_UIDS.flatMap((uid) => [
      `users/${uid}`,
      `publicProfiles/${uid}`,
    ]),
  };
  if (!apply) {
    console.log(JSON.stringify(plan, null, 2));
    return;
  }

  admin.initializeApp({ projectId, storageBucket: APPROVED_AVATAR_BUCKET });
  const db = admin.firestore();
  const bucket = admin.storage().bucket(APPROVED_AVATAR_BUCKET);
  const now = admin.firestore.FieldValue.serverTimestamp();

  for (const uid of FIXTURE_UIDS) {
    const sourceBytes = await downloadPng(images[uid], uid);
    const downloadToken = crypto.randomUUID();
    const url = publicUrl(uid, downloadToken);
    await bucket.file(objectPath(uid)).save(sourceBytes, {
      resumable: false,
      contentType: "image/png",
      metadata: {
        cacheControl: "public, max-age=3600",
        metadata: {
          firebaseStorageDownloadTokens: downloadToken,
          dataPartition: "play_review",
          fixtureUid: uid,
        },
      },
    });

    const avatar = {
      status: "approved",
      approvedAvatarUrl: url,
      approvedAvatarStoragePath: storagePath(uid),
      avatarId: AVATAR_ID,
      selectedCandidateId: "play_review_fixture",
      sourceJobId: "play_review_fixture",
      updatedAt: now,
    };
    const batch = db.batch();
    const userRef = db.collection("users").doc(uid);
    const publicRef = db.collection("publicProfiles").doc(uid);
    batch.update(userRef, {
      dataPartition: "play_review",
      profileImageMode: "avatar",
      profileImageUrl: url,
      avatar,
      "onboarding.avatarUrls": [url],
      "onboarding.photoUrls": [url],
      updatedAt: now,
    });
    batch.update(publicRef, {
      dataPartition: "play_review",
      profileImageUrl: url,
      avatar: { status: "approved", approvedAvatarUrl: url },
      "onboarding.avatarUrls": [url],
      "onboarding.photoUrls": [url],
      updatedAt: now,
    });
    await batch.commit();
  }

  console.log(JSON.stringify({ ...plan, provisioned: true }, null, 2));
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : "Provision failed.");
  process.exit(1);
});
