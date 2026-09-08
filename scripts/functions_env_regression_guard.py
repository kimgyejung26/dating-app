#!/usr/bin/env python3
"""Refuse a Functions deploy that would drop environment variables.

`firebase deploy` replaces a function's environment with whatever the env file
contains. A key that is live but missing from the file is silently deleted. On
2026-09-08 that removed `JOB_QUEUE_MODE`, `TASK_INVOKER_SERVICE_ACCOUNT` and 17
other variables from five production functions in a single command.

The check that missed it compared the candidate deploy against the same
incomplete local file it came from - a circular comparison that can only ever
agree with itself. The authority here is the environment of the revision that
is actually serving traffic, plus the variables the source code reads.

Usage:
    python scripts/functions_env_regression_guard.py \\
        --project seolleyeon-final --region asia-northeast3 \\
        --env-file functions/.env.seolleyeon-final \\
        --function getCurrentAvatarGenerationStatus [--function ...] \\
        [--allow-removal KEY] [--source-dir functions/src]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

# Injected by Cloud Run / the Functions framework. Never carried in an env file.
PLATFORM_MANAGED_KEYS = frozenset({
    "EVENTARC_CLOUD_EVENT_SOURCE",
    "FIREBASE_CONFIG",
    "FUNCTION_SIGNATURE_TYPE",
    "FUNCTION_TARGET",
    "GCLOUD_PROJECT",
    "GOOGLE_CLOUD_PROJECT",
    "K_CONFIGURATION",
    "K_REVISION",
    "K_SERVICE",
    "LOG_EXECUTION_ID",
    "PORT",
})

# Values that must never be printed, even when they differ.
SECRET_KEY_PATTERN = re.compile(
    r"(SECRET|TOKEN|PASSWORD|PRIVATE_KEY|API_KEY|CREDENTIAL|SIGNING)",
    re.IGNORECASE,
)

ENV_READ_PATTERN = re.compile(r"process\.env(?:\.([A-Z][A-Z0-9_]*)|\[\"([A-Z][A-Z0-9_]*)\"\])")


@dataclass
class EnvFinding:
    function: str
    key: str
    kind: str  # "removed" | "changed" | "missing_required"
    detail: str = ""

    def render(self) -> str:
        suffix = f" ({self.detail})" if self.detail else ""
        return f"{self.function}: {self.kind} {self.key}{suffix}"


@dataclass
class EnvCheckResult:
    findings: list[EnvFinding] = field(default_factory=list)
    checked_functions: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


def is_secret_key(key: str) -> bool:
    return bool(SECRET_KEY_PATTERN.search(key))


def redact(key: str, value: str) -> str:
    if is_secret_key(key):
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
        return f"<secret sha256:{digest}>"
    return repr(value)


def parse_env_file(text: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        env[key] = value
    return env


def required_env_keys_from_source(source_dir: Path) -> set[str]:
    """Environment variables the deployed code actually reads."""
    keys: set[str] = set()
    for path in sorted(source_dir.rglob("*.ts")):
        if path.name.endswith(".test.ts"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for direct, bracketed in ENV_READ_PATTERN.findall(text):
            keys.add(direct or bracketed)
    return keys - set(PLATFORM_MANAGED_KEYS)


def plan_functions_env_check(
    *,
    deployed: Mapping[str, Mapping[str, str]],
    candidate: Mapping[str, str],
    required_from_source: Iterable[str] = (),
    allowed_removals: Iterable[str] = (),
) -> EnvCheckResult:
    """Compare each function's live environment against the candidate deploy.

    Pure: no gcloud, no filesystem. The caller supplies the live environments.
    """
    allowed = set(allowed_removals)
    required = set(required_from_source)
    result = EnvCheckResult()

    for function in sorted(deployed):
        result.checked_functions.append(function)
        live = {
            key: value
            for key, value in deployed[function].items()
            if key not in PLATFORM_MANAGED_KEYS
        }
        for key in sorted(live):
            if key in allowed:
                continue
            if key not in candidate:
                result.findings.append(EnvFinding(
                    function, key, "removed",
                    "live on the serving revision but absent from the candidate env",
                ))
            elif candidate[key] != live[key]:
                result.findings.append(EnvFinding(
                    function, key, "changed",
                    f"{redact(key, live[key])} -> {redact(key, candidate[key])}",
                ))
        # A variable the code reads and the platform does not inject must be
        # present somewhere; losing it is how a guard turns into a silent
        # fallback.
        for key in sorted(required & set(live) - set(candidate) - allowed):
            result.findings.append(EnvFinding(
                function, key, "missing_required",
                "read by functions/src but absent from the candidate env",
            ))
    return result


def deployed_env_for(function: str, project: str, region: str) -> dict[str, str]:
    service = function.lower()
    described = subprocess.run(
        [
            "gcloud", "run", "services", "describe", service,
            f"--project={project}", f"--region={region}", "--format=json",
        ],
        capture_output=True, text=True, encoding="utf-8", shell=True,
    )
    if described.returncode != 0:
        raise SystemExit(f"cannot describe {service}: {described.stderr.strip()[:300]}")
    spec = json.loads(described.stdout)["spec"]["template"]["spec"]
    return {
        item["name"]: item["value"]
        for item in spec["containers"][0].get("env", [])
        if "value" in item
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--function", action="append", required=True, dest="functions")
    parser.add_argument("--allow-removal", action="append", default=[], dest="allowed")
    parser.add_argument("--source-dir", default="functions/src")
    args = parser.parse_args(argv)

    candidate = parse_env_file(Path(args.env_file).read_text(encoding="utf-8"))
    source_dir = Path(args.source_dir)
    required = required_env_keys_from_source(source_dir) if source_dir.is_dir() else set()
    deployed = {
        function: deployed_env_for(function, args.project, args.region)
        for function in args.functions
    }

    result = plan_functions_env_check(
        deployed=deployed,
        candidate=candidate,
        required_from_source=required,
        allowed_removals=args.allowed,
    )
    for function in result.checked_functions:
        print(f"checked {function}: {len(deployed[function])} live variables")
    if result.ok:
        print("ENV REGRESSION GUARD: PASS (no variable is dropped or altered)")
        return 0
    print("ENV REGRESSION GUARD: FAIL")
    for finding in result.findings:
        print(f"  {finding.render()}")
    print(
        "\nDeploying now would change these variables. Restore them in the env "
        "file, or pass --allow-removal KEY for each one you intend to drop."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
