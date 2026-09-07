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

Excluded class-C/D artifacts include Flutter failure images, build reports,
Firebase caches, SDK-local lockfile drift, environment backups, approval
packets, production exports, and real-user consent/smoke maps.

## Production boundary

Repository tests, builds, zero-traffic deployment, and readiness checks are
allowed by this integration. A real authenticated App Check client flow and any
paid Azure generation call remain a separate approval gate.
