# Firestore analysis: Google Play review access

Target: `seolleyeon-final/(default)` (Standard, `asia-northeast3`).

This is the pre-rules implementation inventory required for the review-access
change. It intentionally lives under the ignored `tmp/` tree and is not a
product artifact.

## Authentication and authority

- Normal sessions are Firebase custom-token sessions with `appSession == true`.
- Normal privileged callables resolve only `users/{request.auth.uid}` and then
  require a verified `studentEmail` plus `isStudentVerified == true`.
- Play review sessions must remain valid without claiming ownership of a real
  Yonsei mailbox. Both a custom claim and immutable server-owned fields on the
  caller's user document are required.
- App Check remains enforced on pre-auth review sign-in and every post-auth
  review callable.

## Existing paths touched by this feature

- `users/{uid}`: private account record. Owner `get`; client field allowlists
  on update; server creates accounts and review fixtures.
- `publicProfiles/{uid}`: server-written authenticated display projection.
  Existing client reads are exact document `get` calls; collection `list` is
  denied. Review callers may get only `dataPartition == play_review` profiles;
  production callers may get only documents with absent/`production` partition.
- `interactions/{id}`: participant reads; canonical caller creates with
  `fromUserId == auth.uid`; immutable afterwards. Review creates must target a
  review-partition user, and trigger-created matches/rooms retain the partition.
- `matches/{id}`: server creates; participants read; limited unmatch update.
- `chat_rooms/{id}` and `chat_rooms/{id}/messages/{id}`: server creates rooms;
  participant query/read and authored message creates. Review rooms carry a
  server-owned partition and never dispatch FCM.
- `blocks/{uid}/targets/{targetUid}` and `reports/{id}`: server report callable
  writes both block directions plus a report. Review reports are marked test
  data and cannot enter the operations queue.
- `users/{uid}/recommendationRefreshes/{dateKey}`: owner exact get; server write.
  Review refresh uses the same receipt surface with a review source marker.
- `modelRecs/{uid}/daily/{dateKey}/sources/{algo}`: production owner-only feed.
  Review feeds do not write this path, preventing training/batch contamination.
- `recEvents/{uid}/events/{id}`: production interaction telemetry. Review
  sessions use `playReviewEvents`, which is server-owned and not part of model
  input.
- `blindMeetings/{id}`, participant/profile subcollections, and `chat_rooms`:
  the existing blind-meeting UI reads participant-scoped server documents.
  Review preparation uses deterministic review-only IDs and whitelisted UIDs.

## New paths

- `playReviewRateLimits/{ipHash}`: Admin SDK only. Pre-auth abuse throttle; the
  raw IP and credentials are never stored.
- `playReviewConfig/current`: Admin SDK only. Optional kill switch and fixture
  manifest. No client authority is derived from this document.
- `playReviewSessions/{reviewerUid}`: Admin SDK only. Reset/version audit with no
  credentials or PII.
- `playReviewEvents/{reviewerUid}/events/{eventId}`: Admin SDK only; synthetic
  review telemetry, isolated from recommendation model input.

## Data contract and immutability

- Production partition is represented by missing `dataPartition` or the exact
  string `production` for backward compatibility.
- Review partition is the exact string `play_review`.
- Privileged account fields are server-owned and immutable to clients:
  `accountType`, `dataPartition`, `reviewAccess`, `reviewProfileReady`, and
  `reviewFixtureEnabled`.
- Reviewer contract: `accountType == google_play_review`,
  `dataPartition == play_review`, `reviewAccess == true`, and
  `reviewProfileReady == true`.
- Fixture contract: one of eight fixed UIDs, `accountType ==
  google_play_fixture`, `dataPartition == play_review`, and
  `reviewFixtureEnabled == true`.
- Mixed production/review writes, matches, rooms, reports, blocks, team
  membership, and notification delivery fail closed.

## Queries and indexes

- Review feed uses eight exact document gets; it needs no composite index.
- Reset uses equality/array membership queries already represented by existing
  interaction/match/chat query shapes. Results are revalidated against the
  fixed UID set before deletion.
- No collection query is opened by the rules change. Exact profile reads keep
  the current `allow list: false` privacy boundary.

## Failure behavior

- Missing secret, disabled access, wrong credentials, missing App Check,
  mismatched claim/document, incomplete fixture set, or a non-whitelisted UID
  aborts without granting access or deleting data.
- Reset deletes only documents that both carry `dataPartition == play_review`
  and contain only fixed review UIDs.
- Normal accounts and legacy production documents continue through the current
  verified-Yonsei resolver and missing-partition compatibility path.
