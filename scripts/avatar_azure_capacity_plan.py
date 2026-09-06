#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.model_adapters.azure_capacity_planning import calculate_capacity_plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calculate Azure avatar worker concurrency with Little's Law."
    )
    parser.add_argument("--endpoint-rpm", action="append", type=float, required=True)
    parser.add_argument("--provider-p50-seconds", type=float, required=True)
    parser.add_argument("--provider-p95-seconds", type=float, required=True)
    parser.add_argument("--calls-per-job", type=int, default=4)
    parser.add_argument("--job-p95-seconds", type=float)
    parser.add_argument("--safe-container-request-concurrency", type=int)
    parser.add_argument("--headroom-factor", type=float, default=1.2)
    args = parser.parse_args()
    plan = calculate_capacity_plan(
        endpoint_rpm_limits=args.endpoint_rpm,
        provider_p50_seconds=args.provider_p50_seconds,
        provider_p95_seconds=args.provider_p95_seconds,
        calls_per_job=args.calls_per_job,
        measured_job_p95_seconds=args.job_p95_seconds,
        safe_container_request_concurrency=args.safe_container_request_concurrency,
        headroom_factor=args.headroom_factor,
    )
    print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
