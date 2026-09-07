import assert from "node:assert/strict";
import { scryptSync } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

import {
  PLAY_REVIEW_ACCOUNT_TYPE,
  PLAY_REVIEW_FIXTURE_ACCOUNT_TYPE,
  PLAY_REVIEW_PARTITION,
  assertSameDataPartition,
  canPlayReviewUserOpenDirectChatWithFixture,
  dataPartitionOf,
  isPlayReviewFixtureData,
  isPlayReviewUserData,
  verifyPlayReviewPassword,
} from "./playReviewAccess";

const playReviewSource = readFileSync(
  resolve(__dirname, "../src/playReviewAccess.ts"),
  "utf8",
) as string;

test("review password verifier accepts only the scrypt-v1 derived key", () => {
  const salt = Buffer.from("0123456789abcdef", "utf8");
  const password = "a-review-password-with-24-characters";
  const key = scryptSync(password, salt, 32, {
    N: 16384,
    r: 8,
    p: 1,
    maxmem: 64 * 1024 * 1024,
  });
  const encoded = `scrypt-v1:${salt.toString("base64")}:${key.toString("base64")}`;

  assert.equal(verifyPlayReviewPassword(password, encoded), true);
  assert.equal(verifyPlayReviewPassword(`${password}!`, encoded), false);
  assert.equal(verifyPlayReviewPassword(password, "not-a-valid-secret"), false);
});

test("reviewer authority requires every server-owned marker", () => {
  const complete = {
    accountType: PLAY_REVIEW_ACCOUNT_TYPE,
    dataPartition: PLAY_REVIEW_PARTITION,
    reviewAccess: true,
    reviewProfileReady: true,
  };
  assert.equal(isPlayReviewUserData(complete), true);
  for (const key of Object.keys(complete)) {
    assert.equal(isPlayReviewUserData({ ...complete, [key]: null }), false);
  }
});

test("fixture eligibility cannot be asserted by a normal account", () => {
  assert.equal(isPlayReviewFixtureData({
    accountType: PLAY_REVIEW_FIXTURE_ACCOUNT_TYPE,
    dataPartition: PLAY_REVIEW_PARTITION,
    reviewFixtureEnabled: true,
  }), true);
  assert.equal(isPlayReviewFixtureData({
    accountType: "member",
    dataPartition: PLAY_REVIEW_PARTITION,
    reviewFixtureEnabled: true,
  }), false);
});

test("only the fixed review user may open a direct chat with a fixture", () => {
  const reviewer = {
    accountType: PLAY_REVIEW_ACCOUNT_TYPE,
    dataPartition: PLAY_REVIEW_PARTITION,
    reviewAccess: true,
    reviewProfileReady: true,
  };
  const fixture = {
    accountType: PLAY_REVIEW_FIXTURE_ACCOUNT_TYPE,
    dataPartition: PLAY_REVIEW_PARTITION,
    reviewFixtureEnabled: true,
    loginDisabled: true,
  };
  assert.equal(canPlayReviewUserOpenDirectChatWithFixture(reviewer, fixture), true);
  assert.equal(canPlayReviewUserOpenDirectChatWithFixture({}, fixture), false);
  assert.equal(canPlayReviewUserOpenDirectChatWithFixture(reviewer, {}), false);
});

test("missing legacy partition remains production and mixed pairs fail", () => {
  assert.equal(dataPartitionOf({}), "production");
  assert.equal(dataPartitionOf({ dataPartition: "production" }), "production");
  assert.equal(dataPartitionOf({ dataPartition: PLAY_REVIEW_PARTITION }), "play_review");
  assert.equal(dataPartitionOf({ dataPartition: "unknown" }), "invalid");
  assert.equal(assertSameDataPartition({}, { dataPartition: "production" }), "production");
  assert.throws(() => assertSameDataPartition({}, {
    dataPartition: PLAY_REVIEW_PARTITION,
  }));
});

test("review session reset and seed use only the isolated Bamboo roots", () => {
  for (const collection of [
    "playReviewBambooPosts",
    "playReviewBambooPostAuthors",
    "playReviewBambooCommentAuthors",
  ]) {
    assert.match(playReviewSource, new RegExp(collection));
  }
  assert.match(playReviewSource, /resetReviewBambooArtifacts\(firestore\)/);
  assert.match(playReviewSource, /resetReviewDirectChatHeartTransactions\(firestore\)/);
  assert.match(playReviewSource, /collection\("heartTransactions"\)/);
  assert.match(playReviewSource, /dataPartition: PLAY_REVIEW_PARTITION/);
});
