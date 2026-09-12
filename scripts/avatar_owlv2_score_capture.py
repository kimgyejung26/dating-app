"""B3-L6 Part B - capture raw OWLv2 detections once, at a floor threshold.

LOCAL ONLY, never in CI. One pass over the owner-authorized generated-avatar set
(clean + the injected graphical-logo derivative of each), storing every
detection above a floor score. OWLv2 scores each text query independently, so
filtering the stored rows by query label is equivalent to having run that prompt
alone, and filtering by score is equivalent to having run at that threshold.
That is why the threshold sweep and the prompt ablation need no re-inference.

Raw rows stay in the restricted local directory: they carry boxes and scores for
real user-derived images. Only aggregates leave it.

  python scripts/avatar_owlv2_score_capture.py --private-dir <dir> --models-dir <dir>
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import avatar_florence_ceiling as bench  # noqa: E402
import avatar_logo_detector_benchmark as logo  # noqa: E402

CAPTURE_VERSION = "avatar_owlv2_score_capture_v1"
DETECTOR = "owlv2-base-patch16-ensemble"
# Floor, not a decision threshold: everything at or above this is stored so the
# pre-registered sweep can be computed offline.
FLOOR_SCORE = 0.01


def run(private_dir: Path, models_dir: Path) -> dict:
    import psutil
    from PIL import Image

    spec = dict(logo.CANDIDATES[DETECTOR])
    spec["threshold"] = FLOOR_SCORE
    manifest = json.loads((private_dir / "restricted_manifest.json").read_text(encoding="utf-8"))
    entries = [e for e in manifest["entries"] if e["domain"] == bench.DOMAIN_AVATAR]
    if len(entries) != bench.EXPECTED_COUNTS[bench.DOMAIN_AVATAR]:
        raise SystemExit(f"BLOCKED_G004_AVATAR_SET_COUNT_{len(entries)}")
    before = {e["opaqueId"]: Path(e["path"]).stat().st_mtime_ns for e in entries}

    process = psutil.Process()
    started = time.perf_counter()
    processor, model = logo._load(spec["kind"], models_dir / spec["dir"])
    load_seconds = time.perf_counter() - started
    peak = process.memory_info().rss

    rows = []
    for entry in entries:
        with Image.open(entry["path"]) as handle:  # read-only
            base = handle.convert("RGB")
        if max(base.size) > logo.MAX_LONG_SIDE:
            scale = logo.MAX_LONG_SIDE / max(base.size)
            base = base.resize((round(base.width * scale), round(base.height * scale)), Image.LANCZOS)
        group = logo._group_key_for(entry)
        for variant in (logo.CLEAN_VARIANT, logo.LOGO_VARIANT):
            image, truth = bench.render(base, bench.spec_for(variant))
            t0 = time.perf_counter()
            detections = logo._detect(spec["kind"], processor, model, image, spec)
            rows.append(
                {
                    "conditionId": f"{entry['opaqueId']}:{variant}",
                    "opaqueId": entry["opaqueId"],
                    "groupKey": group,
                    "domain": entry["domain"],
                    "variant": variant,
                    "imageSize": list(image.size),
                    "groundTruth": [item["box"] for item in truth],
                    "detections": detections,
                    "seconds": round(time.perf_counter() - t0, 3),
                }
            )
            peak = max(peak, process.memory_info().rss)
            del image
        del base
        gc.collect()

    after = {e["opaqueId"]: Path(e["path"]).stat().st_mtime_ns for e in entries}
    if after != before:
        raise SystemExit("ORIGINALS_CHANGED")
    return {
        "captureVersion": CAPTURE_VERSION,
        "detector": DETECTOR,
        "repo": spec["repo"],
        "revision": spec["revision"],
        "floorScore": FLOOR_SCORE,
        "prompts": list(logo.PROMPTS),
        "modelLoadSeconds": round(load_seconds, 1),
        "peakRssGb": round(peak / 2**30, 2),
        "imageResolutionNote": "production-like generated-avatar resolution; no source photo in this pass",
        "rows": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.private_dir, args.models_dir)
    args.out.write_text(json.dumps(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "rows": len(result["rows"]),
                "peakRssGb": result["peakRssGb"],
                "modelLoadSeconds": result["modelLoadSeconds"],
                "meanSeconds": round(sum(r["seconds"] for r in result["rows"]) / len(result["rows"]), 2),
                "totalDetections": sum(len(r["detections"]) for r in result["rows"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
