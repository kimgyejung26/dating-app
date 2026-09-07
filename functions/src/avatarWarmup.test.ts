import assert from "node:assert/strict";
import { test } from "node:test";

import {
  AVATAR_WARMUP_BUCKET_SECONDS,
  AVATAR_WARMUP_DISPATCH_DEADLINE_SECONDS,
  avatarWarmupBucket,
  avatarWarmupQueuePath,
  avatarWarmupTargetUrl,
  enqueueAvatarWorkerWarmup,
} from "./avatarWarmup";

const PROD_LIKE_ENV: NodeJS.ProcessEnv = {
  JOB_QUEUE_MODE: "cloud_tasks",
  CLOUD_TASKS_PROJECT: "example-project",
  GCP_LOCATION: "asia-northeast3",
  AVATAR_GENERATION_QUEUE_NAME: "avatar-generation",
  AVATAR_GENERATION_TASK_URL: "https://worker.example.run.app/tasks/avatar-generation",
  TASK_INVOKER_SERVICE_ACCOUNT: "task-invoker@example-project.iam.gserviceaccount.com",
};

function fakeClient(behaviour: "ok" | "already_exists" | "boom" = "ok") {
  const calls: Array<{ parent: string; task: Record<string, unknown> }> = [];
  return {
    calls,
    tasksClient: () => ({
      async createTask(request: { parent: string; task: Record<string, unknown> }) {
        calls.push(request);
        if (behaviour === "already_exists") {
          throw Object.assign(new Error("exists"), { code: 6 });
        }
        if (behaviour === "boom") {
          throw new Error("network down");
        }
        return [request.task] as [Record<string, unknown>];
      },
    }),
  };
}

test("warmup targets the worker /warmup path derived from the generation task url", () => {
  assert.equal(
    avatarWarmupTargetUrl(PROD_LIKE_ENV),
    "https://worker.example.run.app/warmup",
  );
  assert.equal(
    avatarWarmupQueuePath(PROD_LIKE_ENV),
    "projects/example-project/locations/asia-northeast3/queues/avatar-generation",
  );
});

test("clients within one bucket collapse into a single deterministic task", async () => {
  const client = fakeClient();
  // Align to a bucket start so the second call is still inside the same bucket.
  const base = Math.floor(1_700_000_000_000 / (AVATAR_WARMUP_BUCKET_SECONDS * 1000)) * AVATAR_WARMUP_BUCKET_SECONDS * 1000;
  const first = await enqueueAvatarWorkerWarmup({ env: PROD_LIKE_ENV, now: () => base, tasksClient: client.tasksClient });
  const second = await enqueueAvatarWorkerWarmup({
    env: PROD_LIKE_ENV,
    now: () => base + (AVATAR_WARMUP_BUCKET_SECONDS - 1) * 1000,
    tasksClient: client.tasksClient,
  });
  assert.equal(first.status, "enqueued");
  assert.equal(second.taskName, first.taskName);
  assert.equal(first.bucket, avatarWarmupBucket(base));
  assert.equal(client.calls.length, 2);
  const task = client.calls[0].task as {
    name: string;
    dispatchDeadline: { seconds: number };
    httpRequest: { url: string; oidcToken: { serviceAccountEmail: string; audience: string }; body: Buffer };
  };
  assert.equal(task.name, `projects/example-project/locations/asia-northeast3/queues/avatar-generation/tasks/avatar-warmup-${first.bucket}`);
  assert.equal(task.dispatchDeadline.seconds, AVATAR_WARMUP_DISPATCH_DEADLINE_SECONDS);
  assert.equal(task.httpRequest.url, "https://worker.example.run.app/warmup");
  assert.equal(task.httpRequest.oidcToken.serviceAccountEmail, PROD_LIKE_ENV.TASK_INVOKER_SERVICE_ACCOUNT);
  assert.equal(task.httpRequest.oidcToken.audience, "https://worker.example.run.app/warmup");
  assert.deepEqual(JSON.parse(task.httpRequest.body.toString("utf8")), { kind: "avatar_warmup", bucket: first.bucket });
});

test("a duplicate task in the same bucket is reported as already_exists, not an error", async () => {
  const client = fakeClient("already_exists");
  const result = await enqueueAvatarWorkerWarmup({ env: PROD_LIKE_ENV, now: () => 1, tasksClient: client.tasksClient });
  assert.equal(result.status, "already_exists");
});

test("warmup is skipped outside cloud_tasks mode, when disabled, or without an invoker identity", async () => {
  const client = fakeClient();
  assert.deepEqual(
    await enqueueAvatarWorkerWarmup({ env: { ...PROD_LIKE_ENV, JOB_QUEUE_MODE: "dry_run" }, now: () => 1, tasksClient: client.tasksClient }),
    { status: "skipped", reason: "queue_mode_not_cloud_tasks" },
  );
  assert.deepEqual(
    await enqueueAvatarWorkerWarmup({ env: { ...PROD_LIKE_ENV, AVATAR_PREWARM_ENABLED: "false" }, now: () => 1, tasksClient: client.tasksClient }),
    { status: "skipped", reason: "prewarm_disabled" },
  );
  assert.deepEqual(
    await enqueueAvatarWorkerWarmup({ env: { ...PROD_LIKE_ENV, TASK_INVOKER_SERVICE_ACCOUNT: "" }, now: () => 1, tasksClient: client.tasksClient }),
    { status: "skipped", reason: "task_invoker_service_account_missing" },
  );
  assert.equal(client.calls.length, 0);
});

test("transport failures propagate to the caller (the callable downgrades them)", async () => {
  const client = fakeClient("boom");
  await assert.rejects(
    enqueueAvatarWorkerWarmup({ env: PROD_LIKE_ENV, now: () => 1, tasksClient: client.tasksClient }),
    /network down/,
  );
});
