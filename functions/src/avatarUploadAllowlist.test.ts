import assert from "node:assert/strict";
import { test } from "node:test";

import { evaluateAvatarUploadAllowlist } from "./avatarMedia";

// Production finding (2026-09-07): AVATAR_UPLOAD_ALLOWED_UIDS still carried ten
// canary uids on the deployed admission callable, so every normal user was
// rejected with avatar_generation_not_allowed. These tests pin the env source
// semantics that the production config change relies on.

const ALLOWLIST_ENV_NAMES = [
  "AVATAR_UPLOAD_ALLOWED_UIDS",
  "AVATAR_GENERATION_ALLOWED_UIDS",
  "AVATAR_INTERNAL_SMOKE_ALLOWED_UIDS",
] as const;

function envWithout(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {};
  return env;
}

test("allowlist env absent means the gate is disabled and every uid is admitted", () => {
  const decision = evaluateAvatarUploadAllowlist("normal_user", envWithout());
  assert.deepEqual(decision, { enabled: false, allowed: true });
});

test("allowlist env present but empty is equivalent to absent", () => {
  for (const name of ALLOWLIST_ENV_NAMES) {
    for (const raw of ["", "   ", ",", " , ; "]) {
      const env: NodeJS.ProcessEnv = { [name]: raw };
      assert.deepEqual(
        evaluateAvatarUploadAllowlist("normal_user", env),
        { enabled: false, allowed: true },
        `${name}=${JSON.stringify(raw)}`,
      );
    }
  }
});

test("any non-empty allowlist enables the gate and rejects unlisted uids", () => {
  for (const name of ALLOWLIST_ENV_NAMES) {
    const env: NodeJS.ProcessEnv = { [name]: "canary_a, canary_b" };
    assert.deepEqual(evaluateAvatarUploadAllowlist("canary_a", env), { enabled: true, allowed: true });
    assert.deepEqual(evaluateAvatarUploadAllowlist("canary_b", env), { enabled: true, allowed: true });
    assert.deepEqual(evaluateAvatarUploadAllowlist("normal_user", env), { enabled: true, allowed: false });
  }
});

test("allowlist sources are unioned; clearing one variable is not enough while another lists uids", () => {
  const env: NodeJS.ProcessEnv = {
    AVATAR_UPLOAD_ALLOWED_UIDS: "",
    AVATAR_GENERATION_ALLOWED_UIDS: "canary_a",
  };
  assert.deepEqual(evaluateAvatarUploadAllowlist("normal_user", env), { enabled: true, allowed: false });
  assert.deepEqual(evaluateAvatarUploadAllowlist("canary_a", env), { enabled: true, allowed: true });
});
