<#
.SYNOPSIS
  The only sanctioned way to build the avatar worker image.

.DESCRIPTION
  Every invariant lives in scripts/avatar_build_contract.py; this script asks it
  for the command rather than spelling one out, so the recipe cannot be retyped
  wrong. It refuses before calling gcloud if anything is off.

  Guarded here because these are the failures that actually happened or would be
  worst:
    * source staged outside asia-southeast1 (2026-09-10 -- the US multi-region
      bucket, because --default-buckets-behavior was dropped when the command
      was reconstructed from the YAML)
    * building something other than the commit the operator approved
    * building a dirty tree, so the image matches no reviewable SHA

.EXAMPLE
  ./scripts/build_avatar_worker.ps1 -Sha 46485a05e592d6a09d0f29d90673a958829a75c6 -Tag qa107-46485a05
#>
param(
  [Parameter(Mandatory = $true)][string]$Sha,
  [Parameter(Mandatory = $true)][string]$Tag,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Fail([string]$Code, [string]$Detail) {
  Write-Error "BUILD PREFLIGHT FAILED [$Code] $Detail"
  exit 1
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

# --- the commit must be exactly what was approved -------------------------
$head = (git rev-parse HEAD).Trim()
if ($head -ne $Sha) {
  Fail "head_sha_mismatch" "HEAD=$head requested=$Sha"
}

# --- and it must be reviewable: no uncommitted drift ----------------------
$dirty = (git status --porcelain)
if (-not [string]::IsNullOrWhiteSpace($dirty)) {
  Fail "worktree_dirty" "commit or stash before building"
}

# --- the contract builds and checks its own command -----------------------
$argvJson = & python -c @"
import json, sys
sys.path.insert(0, 'scripts')
from avatar_build_contract import build_submit_argv, validate_submit_argv, BuildRecipeError
try:
    argv = build_submit_argv(sha=sys.argv[1], tag=sys.argv[2])
    validate_submit_argv(argv)
except BuildRecipeError as exc:
    print(json.dumps({'error': str(exc)}))
    sys.exit(0)
print(json.dumps({'argv': argv}))
"@ $Sha $Tag

$parsed = $argvJson | ConvertFrom-Json
if ($parsed.error) {
  Fail $parsed.error "contract rejected the command"
}

$argv = @($parsed.argv)
Write-Host "Sanctioned build command:"
Write-Host ("  " + ($argv -join " "))

if ($DryRun) {
  Write-Host "DryRun: no Cloud Build call made."
  exit 0
}

& $argv[0] $argv[1..($argv.Length - 1)]
if ($LASTEXITCODE -ne 0) {
  Fail "cloud_build_failed" "gcloud exited $LASTEXITCODE"
}
