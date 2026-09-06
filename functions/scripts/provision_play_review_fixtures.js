/**
 * Idempotently provisions the fixed Google Play review data partition.
 * Dry-run is the default and performs no network writes.
 *
 * Apply (operator-owned ADC/service account required):
 *   node scripts/provision_play_review_fixtures.js \
 *     --project seolleyeon-final --database '(default)' \
 *     --images ./play-review-images.json --apply
 *
 * The JSON file must map all nine fixed UIDs to permanent HTTPS image URLs.
 * Never use signed URLs, real member photos, or URLs containing credentials.
 */
const fs = require("fs");
const admin = require("firebase-admin");

const REVIEWER_UID = "play-reviewer-v1";
const FIXTURES = [
  { uid: "play-fixture-a-02", gender: "male", nickname: "리뷰 민준", major: "경영학" },
  { uid: "play-fixture-a-03", gender: "male", nickname: "리뷰 현우", major: "경제학" },
  { uid: "play-fixture-b-01", gender: "female", nickname: "리뷰 서연", major: "심리학" },
  { uid: "play-fixture-b-02", gender: "female", nickname: "리뷰 지우", major: "국문학" },
  { uid: "play-fixture-b-03", gender: "female", nickname: "리뷰 하린", major: "언론홍보" },
  { uid: "play-fixture-b-04", gender: "female", nickname: "리뷰 수아", major: "사회학" },
  { uid: "play-fixture-b-05", gender: "female", nickname: "리뷰 유나", major: "교육학" },
  { uid: "play-fixture-b-06", gender: "female", nickname: "리뷰 다은", major: "컴퓨터과학" },
];
const ALL = [
  { uid: REVIEWER_UID, gender: "male", nickname: "Play 리뷰어", major: "테스트 전공" },
  ...FIXTURES,
];

const args = process.argv.slice(2);
const option = (name) => {
  const index = args.indexOf("--" + name);
  return index >= 0 ? String(args[index + 1] || "").trim() : "";
};
const apply = args.includes("--apply");
const projectId = option("project");
const databaseId = option("database") || "(default)";
const imageFile = option("images");

if (projectId !== "seolleyeon-final" || databaseId !== "(default)") {
  console.error("Refusing: target must be seolleyeon-final/(default).");
  process.exit(2);
}

function readImages() {
  if (!imageFile) return {};
  const value = JSON.parse(fs.readFileSync(imageFile, "utf8"));
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("--images must be a JSON object keyed by fixed UID.");
  }
  return value;
}

function validateImageUrl(value, uid) {
  if (typeof value !== "string" || !value.startsWith("https://")) {
    throw new Error(`A permanent HTTPS image URL is required for ${uid}.`);
  }
  const lower = value.toLowerCase();
  if (/x-goog-|signature=|expires=|token=|googleaccessid/.test(lower)) {
    throw new Error(`Signed/credentialed image URL is forbidden for ${uid}.`);
  }
  return value;
}

function userPayload(profile, imageUrl) {
  const reviewFixture = profile.uid !== REVIEWER_UID;
  return {
    uid: profile.uid,
    nickname: profile.nickname,
    accountType: reviewFixture ? "google_play_fixture" : "google_play_review",
    dataPartition: "play_review",
    reviewAccess: !reviewFixture,
    reviewProfileReady: !reviewFixture,
    reviewFixtureEnabled: reviewFixture,
    isStudentVerified: false,
    adultVerified: false,
    realNameVerified: false,
    isActive: true,
    status: "active",
    loginDisabled: reviewFixture,
    profileVisible: reviewFixture,
    initialSetupComplete: true,
    hasSeenTutorial: true,
    heartBalance: reviewFixture ? 0 : 100,
    recommendationPrivacyReady: true,
    onboarding: {
      nickname: profile.nickname,
      gender: profile.gender,
      birthYear: 2002,
      age: 24,
      university: "연세대학교",
      major: profile.major,
      department: profile.major,
      bio: "Google Play 앱 심사를 위한 합성 프로필입니다.",
      selfIntroduction: "실제 사용자가 아닌 앱 심사용 테스트 프로필입니다.",
      mbti: "ENFP",
      height: profile.gender === "male" ? 177 : 164,
      lifestyle: {
        drinking: "sometimes",
        smoking: "nonSmoker",
      },
      interests: ["카페", "산책", "영화"],
      keywords: ["대화", "배려", "웃음"],
      profileQa: [{ question: "주말에는?", answer: "친구들과 카페에 가요." }],
      campusLifeZones: ["sinchon"],
      photoUrls: [imageUrl],
      avatarUrls: [imageUrl],
    },
    profileImageUrl: imageUrl,
    avatar: { status: "approved", approvedAvatarUrl: imageUrl },
  };
}

function publicPayload(profile, imageUrl) {
  const user = userPayload(profile, imageUrl);
  return {
    uid: profile.uid,
    kakaoUserId: profile.uid,
    nickname: profile.nickname,
    profileImageUrl: imageUrl,
    status: "active",
    isWithdrawn: false,
    isActive: true,
    profileVisible: profile.uid !== REVIEWER_UID,
    isStudentVerified: false,
    initialSetupComplete: true,
    isProfileComplete: true,
    recommendationPrivacyReady: true,
    dataPartition: "play_review",
    accountType: user.accountType,
    reviewFixtureEnabled: profile.uid !== REVIEWER_UID,
    onboarding: user.onboarding,
    avatar: user.avatar,
    schemaVersion: 2,
  };
}

async function main() {
  const images = readImages();
  const plan = {
    projectId,
    databaseId,
    mode: apply ? "apply" : "dry-run",
    reviewerAuthUid: REVIEWER_UID,
    firestoreOnlyFixtureUids: FIXTURES.map((item) => item.uid),
    requiredImageUids: ALL.map((item) => item.uid),
  };
  if (!apply) {
    console.log(JSON.stringify(plan, null, 2));
    return;
  }

  for (const profile of ALL) validateImageUrl(images[profile.uid], profile.uid);
  admin.initializeApp({ projectId });
  const auth = admin.auth();
  const db = admin.firestore();

  let reviewer;
  try {
    reviewer = await auth.getUser(REVIEWER_UID);
  } catch (error) {
    if (error && error.code === "auth/user-not-found") {
      reviewer = await auth.createUser({ uid: REVIEWER_UID, disabled: false });
    } else {
      throw error;
    }
  }
  if (reviewer.email || reviewer.phoneNumber || reviewer.passwordHash) {
    throw new Error("Reviewer Auth user must not have email, phone, or password auth.");
  }
  for (const fixture of FIXTURES) {
    try {
      await auth.getUser(fixture.uid);
      throw new Error(`Fixture ${fixture.uid} must remain Firestore-only.`);
    } catch (error) {
      if (!error || error.code !== "auth/user-not-found") throw error;
    }
  }

  const batch = db.batch();
  const now = admin.firestore.FieldValue.serverTimestamp();
  for (const profile of ALL) {
    batch.set(db.collection("users").doc(profile.uid), {
      ...userPayload(profile, images[profile.uid]),
      createdAt: now,
      updatedAt: now,
    }, { merge: false });
    batch.set(db.collection("publicProfiles").doc(profile.uid), {
      ...publicPayload(profile, images[profile.uid]),
      updatedAt: now,
    }, { merge: false });
  }
  batch.set(db.collection("playReviewConfig").doc("current"), {
    accessControlledBySecret: true,
    fixtureVersion: 1,
    reviewerUid: REVIEWER_UID,
    fixtureUids: FIXTURES.map((item) => item.uid),
    dataPartition: "play_review",
    updatedAt: now,
  }, { merge: false });
  await batch.commit();
  console.log(JSON.stringify({ ...plan, provisioned: true }, null, 2));
}

main().catch((error) => {
  console.error(error && error.message ? error.message : "Provision failed.");
  process.exit(1);
});
