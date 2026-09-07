# Avatar full-integration reconciliation — 2026-09-07

## Baseline

- Integration baseline: GitHub `main` at `4b029621`.
- PR #88 is already merged into that baseline.
- The integration branch preserves the deferred onboarding work as two commits
  on top of the baseline.

## Dirty-worktree reconciliation

Every registered worktree was inventoried without modifying its source checkout.
Changes were classified by semantics rather than file path alone.

| Class | Disposition |
| --- | --- |
| A — missing legitimate source change | integrated and tested here |
| B — already included or superseded | not copied again |
| C — generated/cache/local artifact | excluded |
| D — secret, PII, consent map, or private evidence | excluded |
| E — conflicting/obsolete architecture | excluded with explicit authority |

The security, router, phase-2 provenance, merge snapshot, and consolidation
changes are represented by later commits already in `main` or by stricter
current tests. The old FLUX files and single-photo paths are intentionally
retired. The Phase 3 orchestrator worktree is an independently gated
architecture and is not partially imported into the canonical Azure worker.

Integrated class-A changes:

- soft QA review reasons no longer masquerade as critical model outages;
- production worker request/job defaults cover the four-call Azure budget;
- optional Firebase token claims use fail-closed `.get` access;
- deferred avatar selection remains non-blocking through onboarding;
- account-deletion hosting, retention copy, and profile-edit golden safeguards;
- CI dependency resolution is locked to Flutter 3.47.2.
- Cloud Build, setup, and verification use the Singapore avatar registry;
  Cloud Tasks remains in asia-northeast3. Tests assert both lookup regions.
- Privacy QA accepts the existing canonical private bucket aliases and both
  gs/gcs schemes, without accepting public or signed source references.
- With explicit operator approval, Festival was removed from the release,
  rollback, and observability project allowlists and its deployment env template
  was deleted. Historical privacy-denial fixtures remain intentional.

Excluded class-C/D artifacts include Flutter failure images, build reports,
Firebase caches, SDK-local lockfile drift, environment backups, approval
packets, production exports, and real-user consent/smoke maps.

## Production boundary

Repository tests, builds, zero-traffic deployment, and readiness checks are
allowed by this integration. A real authenticated App Check client flow and any
paid Azure generation call remain a separate approval gate.

## Verification follow-up

- Related Python operations/privacy tests: 133 passed.
- Corrected regional query regression: 20 queue/preflight tests passed.
- Integrated profile-copy contract: 4 Flutter tests passed.
- Live preflight after the regional fix: ok=true.
- PR CI at 5bc601dd: Functions, Firestore, Storage, recsys, Web, Android APK,
  and production AAB compile checks passed. Flutter and gitleaks failed.
- Gitleaks reported the same five historical findings as the main run at
  4b029621: two Podfile checksums and three Festival generated-web entries.
  They are not introduced by this PR; scanning was not disabled or relaxed.
- Flutter's stale profile-copy expectation was corrected in aeb8be8b. A fresh
  main worktree under the same local SDK produced 1064 passes and 15 failures;
  integration produced 1134 passes and 13 failures. All integration failures
  also reproduced in main (goldens and two stale ownership-source assertions).
  Golden baselines and tolerance thresholds were not modified during comparison.
- Subsequent session review reproduced a late-response account-isolation race.
  A session generation guard now discards old responses and permits new-session
  refreshes independently. Controller, banner, and selection tests were rerun.
- Singapore worker build submitted from aeb8be8b:
  3a43d928-0e74-4578-bedf-3dda3cf9e338. Deployment/readiness is a separate gate.

## Production rollout

The Singapore image built from this branch was deployed as a zero-traffic
revision, validated, and then promoted:

- Revision `seolleyeon-avatar-worker-fullint-aeb8be8b`, image digest
  `sha256:2edd200652425be2ec80ba105ad06d67fd3297dc6bdbe0c5781e79b92baee43a`,
  produced by Cloud Build `3a43d928-0e74-4578-bedf-3dda3cf9e338`. The digest
  recorded in the revision environment matches the deployed image.
- Runtime shape is unchanged from the previous production revision: 8 vCPU,
  32 GiB, 1 GPU, request timeout 1800 s, concurrency 1, max scale 1. The only
  intended configuration delta is the internal budget, now
  `AVATAR_WORKER_MAX_REQUEST_SECONDS` and `AVATAR_WORKER_MAX_JOB_SECONDS` at
  1500 s. `AVATAR_WORKER_DEADLINE_SECONDS` remains the separate lease deadline
  aligned to the Cloud Run timeout.
- `/readyz` on the zero-traffic revision reported `ok`: QA ready with no
  blocking components, five configured provider endpoints at a 240 s transport
  timeout, and DINO reported as a non-critical component outside the active QA
  contract.
- Traffic was then moved to 100 % on that revision and `/readyz` was rechecked
  on the serving URL with the same result. The previous serving revision,
  `seolleyeon-avatar-worker-softreview-47a16c11`, is retained as the rollback
  target. Queue configuration was not touched.
- No image was generated during this rollout. Paid provider generation calls
  for the whole validation: zero.

A real authenticated client flow and any paid generation run remain a separate
approval gate and were not executed.
