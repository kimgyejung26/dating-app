#!/usr/bin/env bash
# Deploy specific Cloud Functions, but never silently drop their environment.
#
# `firebase deploy` replaces a function's environment with the env file's
# contents. On 2026-09-08 an incomplete file removed 19 variables from five
# production functions in one command, including the one that keeps queue
# dispatch fail-closed. Run the regression guard against the live revisions
# first, then deploy exactly the named functions.
#
# Usage:
#   scripts/deploy_functions_guarded.sh \
#     --project seolleyeon-final --region asia-northeast3 \
#     --env-file functions/.env.seolleyeon-final \
#     getCurrentAvatarGenerationStatus retryCurrentAvatarGeneration
#
# Declare each intended config change one key and one operation at a time:
#   --allow-remove-key KEY   --allow-add-key KEY   --allow-change-key KEY
# A declaration authorises exactly that key and exactly that operation. Any
# other difference still refuses the deploy.
set -euo pipefail

PROJECT=""
REGION=""
ENV_FILE=""
ALLOWED=()
FUNCTIONS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --allow-remove-key) ALLOWED+=(--allow-remove-key "$2"); shift 2 ;;
    --allow-add-key) ALLOWED+=(--allow-add-key "$2"); shift 2 ;;
    --allow-change-key) ALLOWED+=(--allow-change-key "$2"); shift 2 ;;
    --allow-removal|--allow-addition)
      echo "$1 waived every check for that key, a value change included." >&2
      echo "Use --allow-remove-key / --allow-add-key / --allow-change-key." >&2
      exit 2 ;;
    --) shift; break ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) FUNCTIONS+=("$1"); shift ;;
  esac
done
FUNCTIONS+=("$@")

[ -n "$PROJECT" ] || { echo "--project is required" >&2; exit 2; }
[ -n "$REGION" ] || { echo "--region is required" >&2; exit 2; }
[ -n "$ENV_FILE" ] || { echo "--env-file is required" >&2; exit 2; }
[ "${#FUNCTIONS[@]}" -gt 0 ] || { echo "name at least one function" >&2; exit 2; }

GUARD_ARGS=(--project "$PROJECT" --region "$REGION" --env-file "$ENV_FILE")
for fn in "${FUNCTIONS[@]}"; do
  GUARD_ARGS+=(--function "$fn")
done

echo "[deploy] environment regression guard"
python scripts/functions_env_regression_guard.py "${GUARD_ARGS[@]}" "${ALLOWED[@]+"${ALLOWED[@]}"}"

TARGETS=""
for fn in "${FUNCTIONS[@]}"; do
  TARGETS="${TARGETS:+$TARGETS,}functions:$fn"
done

echo "[deploy] firebase deploy --only $TARGETS"
firebase deploy --only "$TARGETS" --project "$PROJECT" --non-interactive

# No declarations on the way back. The intended change has been applied, so the
# serving revision must now match the env file exactly - any remaining
# difference is drift the deploy introduced.
echo "[deploy] post-deploy environment comparison"
python scripts/functions_env_regression_guard.py "${GUARD_ARGS[@]}"
echo "[deploy] done"
