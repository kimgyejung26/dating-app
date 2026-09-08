#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/p1_chat_real_photo_common.sh
source "$SCRIPT_DIR/p1_chat_real_photo_common.sh" "$@"

require_command gcloud
require_standard_env_defaults
require_runtime_service_account

[ "$P1_APPLY" -eq 1 ] || info "Dry-run only. Re-run with --apply to create/update staging bucket and IAM."

PROJECT="$(effective_gcp_project)"
prepare_mutation_project "$PROJECT"
assert_runtime_service_account_project "$FUNCTIONS_RUNTIME_SERVICE_ACCOUNT" "$PROJECT"

info "Preparing bucket=$CHAT_PROFILE_PHOTO_BUCKET location=$GCP_LOCATION runtime_sa=$FUNCTIONS_RUNTIME_SERVICE_ACCOUNT worker_sa=$AVATAR_WORKER_SERVICE_ACCOUNT"

if bucket_exists "$CHAT_PROFILE_PHOTO_BUCKET"; then
  verify_bucket_ownership "$CHAT_PROFILE_PHOTO_BUCKET" "$PROJECT"
  info "Bucket already exists: gs://$CHAT_PROFILE_PHOTO_BUCKET"
else
  run_or_print gcloud storage buckets create "gs://$CHAT_PROFILE_PHOTO_BUCKET" \
    --project="$PROJECT" \
    --location="$GCP_LOCATION" \
    --uniform-bucket-level-access
fi

run_or_print gcloud storage buckets update "gs://$CHAT_PROFILE_PHOTO_BUCKET" \
  --uniform-bucket-level-access \
  --public-access-prevention=enforced

if [ "$P1_APPLY" -eq 1 ]; then
  verify_bucket_ownership "$CHAT_PROFILE_PHOTO_BUCKET" "$PROJECT"
fi

run_or_print gcloud storage buckets add-iam-policy-binding "gs://$CHAT_PROFILE_PHOTO_BUCKET" \
  --member="serviceAccount:$FUNCTIONS_RUNTIME_SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"

# 이 버킷에 객체를 실제로 쓰는 주체는 Functions 런타임이 아니라 아바타 워커다
# (`_persist_chat_real_photo_if_consented`). 이 바인딩이 없어서 프로덕션에서
# GCS 403 이 났고, 그 실패가 아바타 생성 전체를 죽였다. 워커는 새 객체를 만들
# 뿐 읽거나 지우지 않으므로 objectCreator 로 충분하다.
run_or_print gcloud storage buckets add-iam-policy-binding "gs://$CHAT_PROFILE_PHOTO_BUCKET" \
  --member="serviceAccount:$AVATAR_WORKER_SERVICE_ACCOUNT" \
  --role="roles/storage.objectCreator"

if [ "${USE_CHAT_PROFILE_SIGNED_URL:-true}" = "true" ] && [ "${GRANT_SIGN_BLOB:-false}" = "true" ]; then
  run_or_print gcloud iam service-accounts add-iam-policy-binding "$FUNCTIONS_RUNTIME_SERVICE_ACCOUNT" \
    --member="serviceAccount:$FUNCTIONS_RUNTIME_SERVICE_ACCOUNT" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --project="$PROJECT"
else
  info "Token Creator grant not applied. Set GRANT_SIGN_BLOB=true only if staging signed URL generation needs IAM signBlob."
fi
