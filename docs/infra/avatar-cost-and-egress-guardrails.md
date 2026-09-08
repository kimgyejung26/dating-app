# Avatar Infrastructure Cost And Egress Guardrails

Date: 2026-09-08
Scope: `seolleyeon-final` avatar generation infrastructure.

## Why This Exists

The avatar worker runs on Cloud Run in `asia-southeast1`, because that is the
only region where this project holds NVIDIA L4 GPU quota. Everything else —
Functions, Firestore, Cloud Tasks and the avatar buckets — lives in
`asia-northeast3`. That split is deliberate, but it makes the build and
release path an easy place to leak money:

- a worker image is ~4-12 GB, so pushing it to the Seoul registry means every
  Cloud Run cold start pulls it back across regions, billed each time;
- a global Cloud Build runs in the US, so the same image also crosses a
  continent on the way in.

Neither cost appears in the app-level `AVATAR_COST_*` guards. Those model
Cloud Run GPU, vCPU and memory runtime only, and explicitly exclude network
egress, Artifact Registry storage, Cloud Build and GCS
(`docs/avatar-media-migration/pr7-cost-model.md`).

## Invariant

For the avatar worker, all four of these stay in `asia-southeast1`:

| Stage | Resource |
| --- | --- |
| Source staging | `gs://seolleyeon-final_asia-southeast1_cloudbuild` |
| Build execution | Cloud Build, `--region asia-southeast1` |
| Registry | `seolleyeon-avatar-repo` |
| Runtime | Cloud Run `seolleyeon-avatar-worker` |

Non-avatar artifacts (`recs-pipeline`) legitimately stay in the Seoul
repository and are out of scope.

## How It Is Enforced

`tests/test_avatar_build_region_guard.py` runs in CI and asserts:

- no tracked `cloudbuild*.yaml` names an avatar worker destination outside
  `asia-southeast1` / `seolleyeon-avatar-repo`;
- `scripts/staging_avatar_live_setup.ps1` defaults to the canonical registry
  and passes `--region` plus
  `--default-buckets-behavior=REGIONAL_USER_OWNED_BUCKET`.

`--region` alone is not sufficient. Build `ea55a59b` (2026-08-23) ran in
`asia-southeast1` and still staged source in the US multi-region bucket and
pushed to the Seoul registry.

The pre-existing assertion in
`tests/test_avatar_retired_generation_paths.py` covers the canonical root
config, but CI does not run that file, so it did not gate anything.

## Artifact Registry Retention — Constraint To Respect

Old images cannot be deleted on age alone. Cloud Run retains revisions, and a
revision pins its image by digest, so deleting the image makes that revision
unstartable.

As surveyed on 2026-09-08, of 61 `seolleyeon-avatar-worker` images in the
Seoul repository, **54 are still referenced by retained revisions of the live
`seolleyeon-avatar-worker` service**. Only 5 are referenced by no revision at
all, and 2 more are referenced solely by the retired festival bridge.

Consequences:

1. Any cleanup policy must be expressed in terms of what Cloud Run still
   references, not age or tag count alone. An age-based policy would break the
   rollback surface.
2. Reclaiming the bulk of the Seoul repository requires first deleting the old
   Cloud Run revisions that pin those images. That is a separate decision about
   how much rollback history to keep, and it is not a cost decision alone.
3. Manifest sizes overstate reclaimable bytes. Layers are shared, so the 61
   Seoul images sum to ~344 GB of manifests against ~119 GB of billed
   repository storage.

## GCS Lifecycle — What Must Not Be Automated

`docs/gcs_lifecycle_avatar_temp.json` proposes deleting `users/` in
`seolleyeon-final-avatar-temp` at age 3 and `tmp/`, `working/` at age 1. It is
**not applied**, and it must not be applied on cost grounds alone.

Avatar candidates are addressed under a `users/{uid}/...` prefix and are
referenced from Firestore by `candidate.imageRef`. Selection is now a deferred
onboarding step, so a user can generate candidates and choose one later. If
that gap exceeds the lifecycle age, the objects vanish while Firestore still
points at them.

Applying a temp lifecycle therefore requires an explicit product decision on
how long an unchosen candidate may live, and a reconciliation path for
candidates whose object is gone.

`seolleyeon-final-private-source-photos` and
`seolleyeon-final-approved-avatars` get no age-based lifecycle at all. Deletion
authority for those stays with the existing contracts: avatar replacement,
account deletion, and the retention purge in `functions/src/avatarCleanup.ts`,
which deletes by explicit reference rather than by age.

## Detection Gap Still Open

There is no GCP-level budget on this project. The Cloud Billing Budget API is
now enabled, but creating a budget requires a billing-account role that the
operator account does not hold. Until that grant exists, network egress,
Artifact Registry storage, Cloud Build and GCS spend have no alerting layer,
because the app-level guards do not model them.
