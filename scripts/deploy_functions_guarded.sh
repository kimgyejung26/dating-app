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
# Add --allow-removal KEY / --allow-addition KEY for each variable you
# intend to drop or introduce.
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
    --allow-removal) ALLOWED+=(--allow-removal "$2"); shift 2 ;;
    --allow-addition) ALLOWED+=(--allow-addition "$2"); shift 2 ;;
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

echo "[deploy] post-deploy environment comparison"
python scripts/functions_env_regression_guard.py "${GUARD_ARGS[@]}" "${ALLOWED[@]+"${ALLOWED[@]}"}"
echo "[deploy] done"
