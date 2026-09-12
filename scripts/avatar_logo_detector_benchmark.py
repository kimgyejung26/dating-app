"""B3-L5 Part B - local offline benchmark of graphical-logo detector candidates.

LOCAL ONLY. Never run in CI: it loads detection models and reads the
owner-authorized G004 images. No image, crop, embedding, filename or box from a
real image ever leaves the restricted local directory; the report carries
counts, rates, IoU statistics and timings only.

Why: B3-L4 measured that Florence gives essentially no graphical-logo signal
(OCR hit 0/8 source and 5/20 avatar; <OD> never localized the injected mark).
That is a MODEL gap, so this benchmarks other local detectors against the same
injected ground truth, on the same corpus, with Florence as the baseline column.

Pre-registered before any candidate ran (see the report):
  * conditions: the V8/A8 injected graphical-logo derivative of every
    authorized base image, every clean base image, and the 10 PR #114 controls
  * ground truth: the injected mark's construction box (and, for ctl-08, the
    control generator's own logo box)
  * match rule: IoU >= 0.3, identical to B3-L4
  * prompts and thresholds: frozen per candidate in CANDIDATES below
No threshold is tuned after seeing results.

Clean images carry no human logo label, so their detections are reported as
CLEAN_IMAGE_REGION_RESPONSE_RATE and never as false positives.

  python scripts/avatar_logo_detector_benchmark.py --private-dir <dir> --models-dir <dir>
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
import avatar_watermark_controls as controls  # noqa: E402

BENCHMARK_VERSION = "avatar_logo_detector_benchmark_v1"
IOU_MATCH = bench.IOU_MATCH
LOGO_VARIANT = "V8"
CLEAN_VARIANT = "V0"

# Generic, non-brand queries. Frozen before inference.
PROMPTS = ("a logo", "a watermark", "a brand emblem", "a graphic symbol")

CANDIDATES = {
    "owlv2-base-patch16-ensemble": {
        "repo": "google/owlv2-base-patch16-ensemble",
        "revision": "cfd3195ba4ea9592eec887ded089f4c08eff231d",
        "license": "apache-2.0",
        "dir": "owlv2",
        "kind": "owl",
        "threshold": 0.10,
    },
    "grounding-dino-tiny": {
        "repo": "IDEA-Research/grounding-dino-tiny",
        "revision": "a2bb814dd30d776dcf7e30523b00659f4f141c71",
        "license": "apache-2.0",
        "dir": "gdino",
        "kind": "gdino",
        "box_threshold": 0.25,
        "text_threshold": 0.25,
    },
}

# Pre-registered preprocessing: an image whose long side exceeds this is
# downscaled (LANCZOS) BEFORE injection, so ground truth scales with it. Both
# detectors resize internally far below this (OWLv2 960x960, Grounding DINO
# ~800 short side), so it does not change what either model sees -- it avoids
# the OWLv2 image processor's float64 upcast allocating ~0.5 GB per 5712px
# photo. Avatars (1254px) and controls (512x768) are untouched.
MAX_LONG_SIDE = 2048

# The control generator draws its graphical logo with this exact box.
CTL08_GROUND_TRUTH = [424.0, 16.0, 496.0, 88.0]


def _group_key_for(entry) -> str | None:
    """Opaque participant-group key from the avatar filename pattern (P##_C##).

    The group identity is a property of the corpus, not of any result, which is
    why the pre-registered development/holdout split can be assigned from it.
    """

    import re

    if entry.get("domain") != bench.DOMAIN_AVATAR:
        return None
    match = re.search(r"P(\d{2})_C\d{2}", Path(entry["path"]).name)
    return f"G{int(match.group(1))}" if match else None


def _load(kind: str, path: Path):
    import torch
    from transformers import AutoProcessor

    if kind == "owl":
        from transformers import Owlv2ForObjectDetection

        model = Owlv2ForObjectDetection.from_pretrained(path, local_files_only=True)
    else:
        from transformers import GroundingDinoForObjectDetection

        model = GroundingDinoForObjectDetection.from_pretrained(path, local_files_only=True)
    processor = AutoProcessor.from_pretrained(path, local_files_only=True)
    model.eval()
    torch.set_grad_enabled(False)
    return processor, model


def _detect(kind: str, processor, model, image, spec) -> list[dict]:
    import torch

    target = torch.tensor([[image.size[1], image.size[0]]])
    if kind == "owl":
        inputs = processor(text=[list(PROMPTS)], images=image, return_tensors="pt")
        outputs = model(**inputs)
        results = processor.post_process_grounded_object_detection(
            outputs=outputs, target_sizes=target, threshold=spec["threshold"]
        )[0]
        labels = [PROMPTS[int(i)] for i in results.get("labels", [])]
    else:
        text = ". ".join(PROMPTS) + "."
        inputs = processor(images=image, text=text, return_tensors="pt")
        outputs = model(**inputs)
        results = processor.post_process_grounded_object_detection(
            outputs,
            inputs["input_ids"],
            threshold=spec["box_threshold"],
            text_threshold=spec["text_threshold"],
            target_sizes=target,
        )[0]
        labels = [str(label) for label in results.get("labels", [])]
    boxes = [[float(v) for v in box] for box in results["boxes"].tolist()]
    scores = [float(s) for s in results["scores"].tolist()]
    return [{"box": b, "score": s, "label": l} for b, s, l in zip(boxes, scores, labels)]


def _row(name, domain, condition, truth, detections, seconds):
    ious = [max((bench.iou(d["box"], t) for d in detections), default=0.0) for t in truth]
    hits = sum(1 for value in ious if value >= IOU_MATCH)
    return {
        "detector": name,
        "domain": domain,
        "condition": condition,
        "gtBoxCount": len(truth),
        "gtBoxHits": hits,
        "imageHit": bool(truth) and hits > 0,
        "bestIous": [round(v, 4) for v in ious],
        "detectionCount": len(detections),
        "maxScore": round(max((d["score"] for d in detections), default=0.0), 4),
        "labelCounts": {
            bench.sanitize_od_label(d["label"]): 1 for d in detections
        },
        "seconds": round(seconds, 3),
    }


def run(private_dir: Path, models_dir: Path, only: str | None) -> dict:
    import psutil
    from PIL import Image

    process = psutil.Process()
    manifest = json.loads((private_dir / "restricted_manifest.json").read_text(encoding="utf-8"))
    entries = manifest["entries"]
    for domain, expected in bench.EXPECTED_COUNTS.items():
        actual = sum(1 for e in entries if e["domain"] == domain)
        if actual != expected:
            tag = "SOURCE" if domain == bench.DOMAIN_SOURCE else "AVATAR"
            raise SystemExit(f"BLOCKED_G004_{tag}_SET_COUNT_{actual}")
    before = {e["opaqueId"]: Path(e["path"]).stat().st_mtime_ns for e in entries}
    control_images = {spec.evaluation_id: image for spec, image in controls.build_controls()}

    rows: list[dict] = []
    meta: dict[str, dict] = {}
    for name, spec in CANDIDATES.items():
        if only and only != name:
            continue
        path = models_dir / spec["dir"]
        started = time.perf_counter()
        processor, model = _load(spec["kind"], path)
        load_seconds = time.perf_counter() - started
        peak = process.memory_info().rss
        size_bytes = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())

        for entry in entries:
            with Image.open(entry["path"]) as handle:  # read-only
                base = handle.convert("RGB")
            if max(base.size) > MAX_LONG_SIDE:
                scale = MAX_LONG_SIDE / max(base.size)
                base = base.resize(
                    (max(1, round(base.width * scale)), max(1, round(base.height * scale))),
                    Image.LANCZOS,
                )
            for variant in (CLEAN_VARIANT, LOGO_VARIANT):
                image, truth_boxes = bench.render(base, bench.spec_for(variant))
                truth = [item["box"] for item in truth_boxes]
                t0 = time.perf_counter()
                detections = _detect(spec["kind"], processor, model, image, spec)
                rows.append(
                    _row(
                        name,
                        entry["domain"],
                        bench.display_variant(entry["domain"], variant),
                        truth,
                        detections,
                        time.perf_counter() - t0,
                    )
                )
                peak = max(peak, process.memory_info().rss)
                del image
            del base
            gc.collect()

        for control_id, image in control_images.items():
            truth = [CTL08_GROUND_TRUTH] if control_id == "ctl-08" else []
            t0 = time.perf_counter()
            detections = _detect(spec["kind"], processor, model, image, spec)
            rows.append(
                _row(name, bench.DOMAIN_SYNTHETIC, control_id, truth, detections, time.perf_counter() - t0)
            )
            peak = max(peak, process.memory_info().rss)

        meta[name] = {
            "repo": spec["repo"],
            "revision": spec["revision"],
            "license": spec["license"],
            "modelDiskBytes": size_bytes,
            "modelLoadSeconds": round(load_seconds, 1),
            "peakRssGb": round(peak / 2**30, 2),
            "prompts": list(PROMPTS),
            "thresholds": {k: v for k, v in spec.items() if "threshold" in k},
        }
        del model, processor
        gc.collect()

    after = {e["opaqueId"]: Path(e["path"]).stat().st_mtime_ns for e in entries}
    if after != before:
        raise SystemExit("ORIGINALS_CHANGED")
    return {"rows": rows, "meta": meta}


def aggregate(rows, meta, florence_rows=None) -> dict:
    from statistics import mean

    report: dict = {
        "benchmarkVersion": BENCHMARK_VERSION,
        "label": "LOCAL_CPU_BENCHMARK",
        "iouMatch": IOU_MATCH,
        "prompts": list(PROMPTS),
        "candidates": meta,
        "detectors": {},
    }
    names = sorted({row["detector"] for row in rows})
    for name in names:
        block: dict = {}
        for domain in (bench.DOMAIN_SOURCE, bench.DOMAIN_AVATAR, bench.DOMAIN_SYNTHETIC):
            selected = [r for r in rows if r["detector"] == name and r["domain"] == domain]
            injected = [r for r in selected if r["gtBoxCount"]]
            clean = [r for r in selected if not r["gtBoxCount"]]
            ious = [v for r in injected for v in r["bestIous"]]
            block[domain] = {
                "injected": {
                    "n": len(injected),
                    "imageHitRate": round(sum(1 for r in injected if r["imageHit"]) / len(injected), 4) if injected else None,
                    "boxRecall": round(sum(r["gtBoxHits"] for r in injected) / sum(r["gtBoxCount"] for r in injected), 4) if injected else None,
                    "meanIoU": round(mean(ious), 4) if ious else None,
                },
                "cleanImageRegionResponseRate": {
                    "n": len(clean),
                    "imagesWithAnyDetection": sum(1 for r in clean if r["detectionCount"]),
                    "meanDetectionsPerImage": round(mean([r["detectionCount"] for r in clean]), 3) if clean else None,
                    "label": "CLEAN_IMAGE_REGION_RESPONSE_RATE",
                },
                "latencySeconds": {
                    "mean": round(mean([r["seconds"] for r in selected]), 2) if selected else None,
                    "max": round(max([r["seconds"] for r in selected]), 2) if selected else None,
                },
            }
        report["detectors"][name] = block
    if florence_rows:
        report["florenceBaseline"] = florence_rows
    return report


def florence_baseline(private_dir: Path) -> dict:
    """Florence numbers for the same injected logo conditions, from B3-L4 rows."""

    path = private_dir / "scored_rows.jsonl"
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    out = {}
    for domain in (bench.DOMAIN_SOURCE, bench.DOMAIN_AVATAR):
        logo = [r for r in rows if r["domain"] == domain and r["variant"] == LOGO_VARIANT and r["phase"] == "core"]
        clean = [r for r in rows if r["domain"] == domain and r["phase"] == "raw"]
        if not logo:
            continue
        out[domain] = {
            "ocrImageHitRate": round(sum(1 for r in logo if r.get("ocrImageHit")) / len(logo), 4),
            "odImageHitRate": round(sum(1 for r in logo if r.get("odImageHit")) / len(logo), 4),
            "odLogoOrSignKindHits": sum(1 for r in logo if r.get("odLogoKindHit")),
            "n": len(logo),
            "cleanOcrRegionsPerImage": round(sum(r["ocrRegionCount"] for r in clean) / len(clean), 3) if clean else None,
        }
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--only", default=None)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = run(args.private_dir, args.models_dir, args.only)
    (args.private_dir / "logo_rows.jsonl").write_text(
        "\n".join(json.dumps(r) for r in result["rows"]) + "\n", encoding="utf-8"
    )
    report = aggregate(result["rows"], result["meta"], florence_baseline(args.private_dir))
    problems = bench.privacy_violations(report)
    if problems:
        raise SystemExit(f"PRIVACY_VIOLATION {problems}")
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
