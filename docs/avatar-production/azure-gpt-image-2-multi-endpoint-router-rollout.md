# Azure GPT Image 2 multi-endpoint router rollout

Status: implementation and test preparation only. No Azure call, Secret Manager
write, Cloud Run revision/env change, Cloud Tasks queue update, or queue resume was
performed by this change.

## Runtime algorithm

One logical candidate generation follows this order:

1. Load the configured endpoint IDs and per-endpoint RPM limits. Endpoint URLs,
   deployments, API versions, and injected keys remain process-local.
2. In one transaction on
   `avatarProviderRouterState/gpt-image-2`, calculate the endpoint with the earliest
   `max(now, nextAvailableAt, capacityBlockedUntil)`. `now` is the transaction
   snapshot's Firestore server `read_time`, never a container wall clock. If the start is close enough
   and the provider timeout still fits the request deadline, atomically advance its
   `nextAvailableAt` by `60 / rpmLimit + safetyGuardSeconds` and return the
   reservation.
3. Sleep once inside the worker until a future reserved start. The slot has already
   been reserved before sleeping.
4. If the calculated start is too far away or risks the request deadline, do not
   consume a reservation, make no Azure call, and return a retryable capacity
   deferral. Cloud Tasks is used only for this longer deferral, not for a 5–20
   second pacing wait.
5. After waking, compare the clock with the reservation grace deadline. A late
   worker discards the stale slot and transactionally reserves again; it never sends
   on the stale slot.
6. Call exactly one configured endpoint. A successful result is returned without
   exposing endpoint/region identity in candidate metadata.
7. A definitive pre-send connection failure may reserve another endpoint. A 429
   records `capacityBlockedUntil`, consumes its already-reserved slot, and may try a
   different endpoint. It is capacity feedback, not a health failure.
   This router contract treats an HTTP 429 response as a definite rejection: no
   generation was accepted. That assumption must be revalidated in the approved
   low-volume staging canary before production traffic.
8. Read/write timeout, read/write error, remote protocol/reset after send, and any
   unclassified transport error are ambiguous. They become
   `azure_unknown_post_send_outcome`; there is no retry or cross-endpoint failover.
   A 5xx response is also fail-closed as a potentially accepted application failure;
   it is not retried or failed over.

The transaction document stores only schema/version, opaque endpoint IDs, RPM,
reservation sequence, and timestamps. It never stores endpoint URLs or credentials.
Firestore transaction failure is fail-closed.

There are no active health probes. Health/capacity is inferred only from real,
already-authorized candidate calls.

## Artifact persistence and stale reconciliation

The deterministic candidate object remains:

`users/{uid}/jobs/{jobId}/candidates/{candidateId}.png`

`generationId` is a deterministic digest of job identity and the job idempotency
contract; `candidateIndex` and an opaque hash of the locked source identity are
recorded in object metadata. On Azure success, the
worker writes the PNG immediately, before moving to another candidate. The create
includes an atomic recovery manifest containing schema, generation ID, candidate
index/ID, seed, SHA-256, and sanitized generation parameters.

On redelivery, the worker checks this object before any Azure call:

- valid object and complete matching manifest: reconstruct the candidate document
  and continue the existing QA/rerank pipeline;
- object exists but its manifest, identity, hash, or PNG is invalid: set
  `needs_review`; never regenerate;
- Storage cannot be read: fail closed and retry without calling Azure;
- stale `provider_inflight` with every expected object valid: reclaim the stale
  generation claim and continue QA without a paid call;
- stale `provider_inflight` with a missing/unknown expected object: set
  `needs_review` because the provider outcome may be ambiguous.

An HTTP duplicate that observes an active generation is returned as 503, so Cloud
Tasks does not acknowledge it before the stale reconciliation window. This avoids a
stranded `provider_inflight` claim after a process crash.

## Configuration

Non-secret configuration:

- `AZURE_OPENAI_ENDPOINT_IDS=ep1,ep2,ep3,ep4,ep5`
- `AZURE_OPENAI_ENDPOINT_QUOTAS=ep1=2,ep2=2,ep3=2,ep4=2,ep5=2`
- `AZURE_OPENAI_{EPn}_ENDPOINT`
- `AZURE_OPENAI_{EPn}_DEPLOYMENT`
- `AZURE_OPENAI_{EPn}_API_VERSION`
- optional `AZURE_OPENAI_{EPn}_API_STYLE`
- `AZURE_OPENAI_PACING_GUARD_SECONDS` (initial conservative default `0.25`)
- `AZURE_OPENAI_MAX_BOUNDED_WAIT_SECONDS` (default `20`)
- `AZURE_OPENAI_RESERVATION_GRACE_SECONDS` (default `5`)
- `AZURE_OPENAI_DEADLINE_GUARD_SECONDS` (default `10`)
- `AZURE_OPENAI_ROUTER_MAX_ATTEMPTS` (five-endpoint default `5`, bounded to `10`)
- `AZURE_PROVIDER_INFLIGHT_STALE_SECONDS` (default `2100`)
- `AVATAR_ARTIFACT_BUDGET_SECONDS_PER_CANDIDATE` (default `10`)
- `AVATAR_QA_BUDGET_SECONDS_PER_CANDIDATE` (default `30`)
- `AVATAR_FIRESTORE_BUDGET_SECONDS_PER_CANDIDATE` (default `5`)
- `AVATAR_FINALIZATION_BUDGET_SECONDS` (default `30`)
- `AVATAR_COLD_START_BUDGET_SECONDS` (default `60`)

With the defaults, the conservative budget is 410 seconds for the two-call path
and 720 seconds for the four-call path. The worker defaults its request/job limit
to 900 seconds and rechecks the remaining round budget before both initial and
extra rounds. An unsafe round defers before consuming a reservation.

The Cloud Tasks retry horizon must extend beyond the stale-claim threshold. With
30/60/120/240/480/600-second backoff and eight total attempts, the eighth attempt
arrives at about 2130 seconds. The staging setup therefore defaults to eight
attempts; this is safe only together with deterministic artifact recovery and must
be approved before changing an existing queue.

Secret Manager bindings only:

- `AZURE_OPENAI_EP1_API_KEY`
- `AZURE_OPENAI_EP2_API_KEY`
- `AZURE_OPENAI_EP3_API_KEY`
- `AZURE_OPENAI_EP4_API_KEY`
- `AZURE_OPENAI_EP5_API_KEY`

Suggested Secret Manager resource names are
`seolleyeon-avatar-azure-ep1-api-key` through
`seolleyeon-avatar-azure-ep5-api-key`. Values must not be placed in source,
Firestore, command history, or plain environment files. The legacy single-endpoint
variables remain a one-entry router input during rollout.

Changing one endpoint from 2 to 6 RPM requires only changing its quota entry. The
pacing interval automatically changes from `30 + guard` to `10 + guard` seconds.

## Concurrency calculation

Five endpoints are not a Cloud Run instance ceiling. For target provider throughput
`R` calls/minute and measured latency `W` seconds, Little's Law gives:

`minimum concurrent provider calls = ceil((R / 60) * W)`

Each avatar job currently performs up to four provider calls sequentially, but it
also occupies a request while waiting for reservations, persisting artifacts,
running QA, and finalizing. Therefore provider concurrency is not an automatic
Cloud Run or Cloud Tasks setting:

- nominal job throughput = `sum(endpoint RPM) / callsPerJob`;
- required in-flight job requests =
  `ceil((nominal job RPM / 60) * measured end-to-end job p95 * headroom)`;
- Cloud Run max instances =
  `ceil(in-flight requests / measured-safe container request concurrency)`;
- Cloud Tasks `maxConcurrentDispatches` should be at least the in-flight request
  target, subject to measured CPU/GPU/memory and QA capacity.

Run the calculator after staging measurements:

```powershell
python scripts/avatar_azure_capacity_plan.py `
  --endpoint-rpm 2 --endpoint-rpm 2 --endpoint-rpm 2 --endpoint-rpm 2 --endpoint-rpm 2 `
  --provider-p50-seconds 60 `
  --provider-p95-seconds 60 `
  --calls-per-job 4 `
  --job-p95-seconds 300 `
  --safe-container-request-concurrency 1 `
  --headroom-factor 1.2
```

For this example the Little's Law minimum is 10 concurrent provider calls and the
20% headroom checkpoint is 12. Task concurrency is calculated independently from
the measured 300-second job p95: `ceil(2.5 / 60 * 300 * 1.2) = 15`; only after a
safe per-instance request concurrency of 1 is measured does that imply 15 max
instances. These are calculator examples, never rollout defaults or a fixed ceiling.

## Staging measurements required

Collect enough low-volume, explicitly approved samples to report:

- Azure provider-only p50/p95/p99 latency by opaque endpoint ID;
- router reservation wait p50/p95 and stale-reservation count;
- 429 rate, exact `Retry-After` behavior, and whether `0.25` seconds is a sufficient
  pacing guard;
- pre-send connect failures versus ambiguous post-send failures;
- Firestore transaction p50/p95 latency, contention retries, and failures;
- Cloud Tasks schedule delay, attempt count, and concurrent dispatches;
- end-to-end job p50/p95, provider calls per job, initial-only versus extra-round
  frequency, and achieved calls/minute;
- Cloud Run request concurrency, instance count, CPU, memory, GPU/QA utilization,
  cold starts, and deadline margin;
- artifact-recovery hits, manifest-invalid review cases, and any duplicate paid-call
  evidence.

Router events are `reservation_acquired`, `reservation_wait`, `stale_reservation`,
`capacity_deferred`, `provider_call_started`, `pre_send_failure`,
`capacity_feedback`, `ambiguous_failure`, and `provider_call_succeeded`. They expose
reservation wait/slot age and transaction-attempt counts. Provider usage separately
records routing attempts, request attempts, definite rejections, ambiguous outcomes,
and successes. Endpoint identity remains
inside provider infrastructure logs; it is absent from public/user and candidate
generation audit contracts.

## Draft rollout procedure (do not execute without separate approval)

1. Keep the production Cloud Tasks queue PAUSED. Record its current state and Cloud
   Run revision/env/secret bindings.
2. Create the five API-key secrets and grant only the avatar worker service account
   `roles/secretmanager.secretAccessor`.
3. Prepare endpoint URLs/deployments/API versions and quotas as Cloud Run env values;
   bind API keys with `--set-secrets`. Deploy a no-traffic staging revision.
4. Validate `/readyz`, Firestore permissions, deterministic artifact recovery, and
   zero-call simulations. Do not run an Azure load test yet.
5. After explicit Azure-call approval, run a very small canary at Cloud Run
   concurrency 1, max instances 1, and Cloud Tasks max concurrent dispatches 1.
6. Review latency, 429/Retry-After, ambiguous errors, Firestore contention, and cost.
   If healthy, repeat at temporary checkpoints 2 and 5. These are rollout checkpoints,
   not the final maximum.
7. Run `avatar_azure_capacity_plan.py` with measured p50/p95 and benchmark container
   concurrency. Propose the resulting Cloud Run max instances/request concurrency
   and Cloud Tasks max concurrent dispatches for approval.
8. Only after that approval, update staging queue limits without resuming production,
   shift staging traffic gradually, and verify rollback.
9. Production revision/env/secret binding, queue limit changes, traffic migration,
   and queue resume each require separate approval.

Command shapes for the separately approved change:

```powershell
# Staging no-traffic revision — draft only.
gcloud run deploy seolleyeon-avatar-worker `
  --project STAGING_PROJECT_ID --region WORKER_REGION --image IMAGE `
  --concurrency CALCULATED_CONTAINER_CONCURRENCY `
  --max-instances CALCULATED_MAX_INSTANCES `
  --no-traffic `
  --set-env-vars "ENVIRONMENT=staging,AVATAR_QA_ALLOW_STAGING_HEURISTIC_PREVIEW=true,AVATAR_DISABLE_NEW_GENERATION=false,AZURE_OPENAI_ENDPOINT_IDS=ep1,ep2,ep3,ep4,ep5,..." `
  --set-secrets "AZURE_OPENAI_EP1_API_KEY=SECRET_EP1:latest,..."

# Production no-traffic revision — a later, separately approved phase only.
# Never copy the staging heuristic flag into this command.
gcloud run deploy seolleyeon-avatar-worker `
  --project PRODUCTION_PROJECT_ID --region WORKER_REGION --image IMAGE `
  --concurrency MEASURED_CONTAINER_CONCURRENCY `
  --max-instances MEASURED_MAX_INSTANCES `
  --no-traffic `
  --set-env-vars "ENVIRONMENT=production,AVATAR_QA_ALLOW_STAGING_HEURISTIC_PREVIEW=false,AVATAR_DISABLE_NEW_GENERATION=false,AZURE_OPENAI_ENDPOINT_IDS=ep1,ep2,ep3,ep4,ep5,..." `
  --set-secrets "AZURE_OPENAI_EP1_API_KEY=SECRET_EP1:latest,..."

# Queue rate update — does not resume a paused queue; draft only.
gcloud tasks queues update avatar-generation `
  --project PROJECT_ID --location QUEUE_REGION `
  --max-concurrent-dispatches CALCULATED_TASK_CONCURRENCY `
  --max-dispatches-per-second APPROVED_JOB_START_RATE
```

There is intentionally no `gcloud tasks queues resume` command in this runbook.
