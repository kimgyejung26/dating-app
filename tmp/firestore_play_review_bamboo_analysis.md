# Google Play review Bamboo Forest isolation

## Scope and trust boundary

The Google Play reviewer signs in as the single Firebase Auth user
`play-reviewer-v1`, with the `playReviewer`, `appSession`, and
`dataPartition: play_review` custom claims. Production members must never be
able to read or write the review-only community data, and the reviewer must
never be able to enumerate production community documents.

## Chosen data model

Keep production data in its existing collections:

- `bamboo_posts`
- `bamboo_post_authors`
- `bamboo_comment_authors`

Use separate root collections for reviewer-only data:

- `playReviewBambooPosts`
- `playReviewBambooPostAuthors`
- `playReviewBambooCommentAuthors`

This is deliberately a separate collection rather than a `dataPartition`
filter on `bamboo_posts`. Existing production posts predate that field, and a
query without an equality filter cannot be proven by Firestore Rules to omit
review documents. A separate root collection prevents cross-partition query
results without migrating or changing existing production posts.

Each review community document also carries `dataPartition: play_review`.
That marker is checked by the reset path before deletion and makes accidental
mixed data visible during server-side inspection.

## Access and reset behavior

- The Flutter repository selects the review root only when the currently
  authenticated Firebase UID is `play-reviewer-v1`; all normal sessions retain
  the current production collection names and queries.
- Security Rules permit every direct client operation on the review roots only
  for a valid Play Review session. All production Bamboo rules continue to
  reject Play Review sessions.
- `preparePlayReviewSession` clears only documents in the separate review
  roots after validating their partition and author identities, then seeds a
  small synthetic post/comment/like fixture set. These writes use the Admin
  SDK and do not invoke production Bamboo notification triggers, whose paths
  remain `bamboo_posts/...`.
- The reviewer may add and interact with their own review-only content; the
  reset makes the next reviewer session deterministic again.

## Indexes and verification

The existing four Bamboo post list indexes are duplicated for
`playReviewBambooPosts`, covering whole-list, popular, author, and category
queries. No production index or existing document is modified.

Automated checks cover the root-collection selection, review fixture schema,
Rules gates, TypeScript tests, Dart tests, static analysis, and release bundle
build. Firestore Emulator authorization tests require Java 21; the local host
currently has Java 17, so emulator execution remains an environment blocker.
