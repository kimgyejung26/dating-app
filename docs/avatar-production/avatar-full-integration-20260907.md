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
