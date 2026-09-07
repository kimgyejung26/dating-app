import { CloudTasksClient, protos } from "@google-cloud/tasks";
import { HttpsError, onCall, type CallableOptions } from "firebase-functions/v2/https";
import { logger } from "firebase-functions/v2";

/// Pre-warm the avatar worker while the user is still picking photos.
///
/// The worker scales to zero and pays ~60-90s of instance start + QA model
/// load on the first job. The client calls this callable when the photo
/// upload screen opens; we enqueue one `/warmup` task on the production
/// avatar queue. The task name is bucketed by time so any number of clients
/// collapse into one warmup per bucket (Cloud Tasks rejects duplicates).
/// No Azure request is ever sent by a warmup.

export const PREWARM_AVATAR_WORKER_CALLABLE_OPTIONS: CallableOptions = {
  timeoutSeconds: 30,
  memory: "256MiB",
  invoker: "public",
  enforceAppCheck: true,
};

export const AVATAR_WARMUP_BUCKET_SECONDS = 300;
export const AVATAR_WARMUP_DISPATCH_DEADLINE_SECONDS = 600;
const ALREADY_EXISTS_GRPC_CODE = 6;

export type AvatarWarmupEnqueueResult = {
  status: "enqueued" | "already_exists" | "skipped";
  reason?: string;
  bucket?: number;
  taskName?: string;
};

type TasksClientLike = {
  createTask(request: {
    parent: string;
    task: protos.google.cloud.tasks.v2.ITask;
  }): Promise<[protos.google.cloud.tasks.v2.ITask, ...unknown[]]>;
};

export type AvatarWarmupDeps = {
  env: NodeJS.ProcessEnv;
  now: () => number;
  tasksClient: () => TasksClientLike;
};

function defaultDeps(): AvatarWarmupDeps {
  return {
    env: process.env,
    now: () => Date.now(),
    tasksClient: () => new CloudTasksClient(),
  };
}

function trimmed(value: string | undefined): string {
  return (value ?? "").trim();
}

export function avatarWarmupBucket(nowMs: number, bucketSeconds = AVATAR_WARMUP_BUCKET_SECONDS): number {
  return Math.floor(nowMs / 1000 / bucketSeconds);
}

/// Derive the worker `/warmup` URL from the configured generation task URL so
/// the warmup always targets the same service (and revision routing) as jobs.
export function avatarWarmupTargetUrl(env: NodeJS.ProcessEnv): string {
  const taskUrl = trimmed(env.AVATAR_GENERATION_TASK_URL);
  if (!taskUrl) {
    throw new HttpsError("failed-precondition", "avatar_warmup_task_url_missing");
  }
  const url = new URL(taskUrl);
  url.pathname = "/warmup";
  url.search = "";
  url.hash = "";
  return url.toString();
}

export function avatarWarmupQueuePath(env: NodeJS.ProcessEnv): string {
  const project = trimmed(env.CLOUD_TASKS_PROJECT) || trimmed(env.GCLOUD_PROJECT) || trimmed(env.GCP_PROJECT);
  const location = trimmed(env.GCP_LOCATION);
  const queue = trimmed(env.AVATAR_GENERATION_QUEUE_NAME) || "avatar-generation";
  if (!project || !location) {
    throw new HttpsError("failed-precondition", "avatar_warmup_queue_config_missing");
  }
  if (queue.startsWith("projects/")) return queue;
  return `projects/${project}/locations/${location}/queues/${queue}`;
}

function isAlreadyExists(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const code = (error as { code?: unknown }).code;
  return code === ALREADY_EXISTS_GRPC_CODE || code === "ALREADY_EXISTS";
}

export async function enqueueAvatarWorkerWarmup(
  deps: AvatarWarmupDeps = defaultDeps(),
): Promise<AvatarWarmupEnqueueResult> {
  const { env } = deps;
  if (trimmed(env.JOB_QUEUE_MODE).toLowerCase() !== "cloud_tasks") {
    return { status: "skipped", reason: "queue_mode_not_cloud_tasks" };
  }
  if (trimmed(env.AVATAR_PREWARM_ENABLED).toLowerCase() === "false") {
    return { status: "skipped", reason: "prewarm_disabled" };
  }
  const serviceAccountEmail = trimmed(env.TASK_INVOKER_SERVICE_ACCOUNT);
  if (!serviceAccountEmail) {
    // Never enqueue an unauthenticated worker call.
    return { status: "skipped", reason: "task_invoker_service_account_missing" };
  }
  const url = avatarWarmupTargetUrl(env);
  const parent = avatarWarmupQueuePath(env);
  const bucket = avatarWarmupBucket(deps.now());
  const taskName = `${parent}/tasks/avatar-warmup-${bucket}`;
  const task: protos.google.cloud.tasks.v2.ITask = {
    name: taskName,
    dispatchDeadline: { seconds: AVATAR_WARMUP_DISPATCH_DEADLINE_SECONDS },
    httpRequest: {
      httpMethod: protos.google.cloud.tasks.v2.HttpMethod.POST,
      url,
      headers: { "Content-Type": "application/json" },
      body: Buffer.from(JSON.stringify({ kind: "avatar_warmup", bucket })),
      oidcToken: {
        serviceAccountEmail,
        audience: trimmed(env.TASK_OIDC_AUDIENCE) || url,
      },
    },
  };
  try {
    await deps.tasksClient().createTask({ parent, task });
    return { status: "enqueued", bucket, taskName };
  } catch (error) {
    if (isAlreadyExists(error)) {
      return { status: "already_exists", bucket, taskName };
    }
    throw error;
  }
}

type ResolveWarmupUser = (
  auth: { uid?: string; token?: Record<string, unknown> } | null | undefined,
) => Promise<{ userId: string }>;

export function createPrewarmAvatarWorkerFunction(
  resolveUser: ResolveWarmupUser,
  deps: AvatarWarmupDeps = defaultDeps(),
) {
  return onCall(PREWARM_AVATAR_WORKER_CALLABLE_OPTIONS, async (request) => {
    // Same admission prelude as the generation callables (Auth + App Check +
    // canonical app user). The warmup itself carries no user data.
    await resolveUser(request.auth);
    try {
      const result = await enqueueAvatarWorkerWarmup(deps);
      return { status: result.status, reason: result.reason ?? null };
    } catch (error) {
      if (error instanceof HttpsError) throw error;
      logger.warn("avatar worker prewarm enqueue failed", {
        errorType: error instanceof Error ? error.name : typeof error,
      });
      // Pre-warm is best effort; never surface a failure to the client flow.
      return { status: "skipped", reason: "enqueue_failed" };
    }
  });
}
