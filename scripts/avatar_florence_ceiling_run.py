"""B3-L4 local Florence inference runner. LOCAL ONLY -- never run in CI.

Reads the two owner-authorized G004 image sets through the restricted opaque-ID
manifest, renders deterministic derivatives IN MEMORY (nothing is written next
to the originals, no derivative image is persisted), runs the production
Florence2VisualRiskAdapter task path, and appends raw Florence outputs to a
restricted private directory. Raw outputs contain OCR transcriptions and must
never leave that directory; the repo report is produced by
avatar_florence_ceiling.aggregate() from scored, text-free rows.

Originals are opened read-only and fingerprinted (sha256 + mtime) before and
after the run; any change fails the run. No network: HF_HUB_OFFLINE is forced.

  python scripts/avatar_florence_ceiling_run.py --private-dir <dir> --model-dir <florence2 dir>
  python scripts/avatar_florence_ceiling_run.py --private-dir <dir> --score-only
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import avatar_florence_ceiling as bench  # noqa: E402
import avatar_watermark_controls as controls  # noqa: E402

PINNED_FLORENCE_REPO = "florence-community/Florence-2-large-ft"
PINNED_FLORENCE_REVISION = "26b734a54fdfbf9c398351eedfabb7f27fc470b7"


def _fingerprint(entries):
    return {
        e["opaqueId"]: [hashlib.sha256(Path(e["path"]).read_bytes()).hexdigest(), Path(e["path"]).stat().st_mtime_ns]
        for e in entries
    }


def _group_key(entry):
    if entry["domain"] != bench.DOMAIN_AVATAR:
        return None
    match = re.search(r"P(\d{2})_C\d{2}", Path(entry["path"]).name)
    return f"G{int(match.group(1))}" if match else None


def _load_manifest(private_dir: Path):
    manifest = json.loads((private_dir / "restricted_manifest.json").read_text(encoding="utf-8"))
    entries = manifest["entries"]
    for domain, expected in bench.EXPECTED_COUNTS.items():
        actual = sum(1 for e in entries if e["domain"] == domain)
        if actual != expected:
            tag = "SOURCE" if domain == bench.DOMAIN_SOURCE else "AVATAR"
            raise SystemExit(f"BLOCKED_G004_{tag}_SET_COUNT_{actual}")
    return entries


def _model_revision(model_dir: Path):
    for meta in (model_dir / ".cache" / "huggingface" / "download").glob("*.metadata"):
        first = meta.read_text(encoding="utf-8").splitlines()[:1]
        if first:
            return first[0].strip()
    return None


def run(private_dir: Path, model_dir: Path, phases):
    import psutil
    import torch
    import transformers
    import PIL
    from PIL import Image
    from avatar_generation.model_adapters.florence2_visual import Florence2VisualRiskAdapter

    entries = _load_manifest(private_dir)
    by_id = {e["opaqueId"]: e for e in entries}
    revision = _model_revision(model_dir)
    if revision != PINNED_FLORENCE_REVISION:
        raise SystemExit(f"model revision mismatch: {revision}")
    before = _fingerprint(entries)
    inventory = {e["opaqueId"]: e["sha256"] for e in entries}
    if any(before[k][0] != inventory[k] for k in inventory):
        raise SystemExit("original changed since inventory")

    control_images = {spec.evaluation_id: image for spec, image in controls.build_controls()}
    plan = bench.build_plan(entries, sorted(control_images))
    digest = bench.plan_digest(plan)
    (private_dir / "plan.json").write_text(json.dumps({"planDigest": digest, "conditions": plan}, indent=2), encoding="utf-8")

    out_path = private_dir / "raw_outputs.jsonl"
    done = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["conditionId"])

    process = psutil.Process()
    adapter = Florence2VisualRiskAdapter(model_id=str(model_dir), local_files_only=True)
    t0 = time.perf_counter()
    adapter._ensure_loaded()
    load_sec = time.perf_counter() - t0
    peak_rss = process.memory_info().rss
    warm = True
    base_cache = {}
    todo = [c for c in plan if c["phase"] in phases and c["conditionId"] not in done]
    print(f"plan={len(plan)} digest={digest[:12]} done={len(done)} todo={len(todo)} load={load_sec:.1f}s", flush=True)
    with out_path.open("a", encoding="utf-8") as sink:
        for index, condition in enumerate(todo, 1):
            if condition["domain"] == bench.DOMAIN_SYNTHETIC:
                image, truth = control_images[condition["baseOpaqueId"]], []
            else:
                base_id = condition["baseOpaqueId"]
                if base_id not in base_cache:
                    base_cache.clear()
                    with Image.open(by_id[base_id]["path"]) as handle:  # read-only
                        base_cache[base_id] = handle.convert("RGB")
                image, truth = bench.render(base_cache[base_id], bench.spec_for(condition["variant"]))
            latency, tasks = {}, {}
            for task in condition["tasks"]:
                started = time.perf_counter()
                tasks[task] = adapter._run_task(image, task)
                latency["ocr" if task == bench.TASK_OCR_WITH_REGION else "od"] = round(time.perf_counter() - started, 3)
            latency["combined"] = round(sum(latency.values()), 3)
            peak_rss = max(peak_rss, process.memory_info().rss)
            record = {
                **condition,
                "imageSize": list(image.size),
                "groundTruth": truth,
                "tasks": tasks,
                "latencySec": latency,
                "warmup": warm,
                "groupKey": _group_key(by_id[condition["baseOpaqueId"]]) if condition["baseOpaqueId"] in by_id else None,
            }
            warm = False
            sink.write(json.dumps(record) + "\n")
            sink.flush()
            del image
            gc.collect()
            if index % 10 == 0 or index == len(todo):
                print(f"{index}/{len(todo)} last={latency['combined']:.1f}s rss={peak_rss / 2**30:.2f}GB", flush=True)

    after = _fingerprint(entries)
    if after != before:
        raise SystemExit("ORIGINALS_CHANGED")
    meta = {
        "florenceRepo": PINNED_FLORENCE_REPO,
        "florenceRevision": revision,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "pillow": PIL.__version__,
        "device": str(next(adapter._model.parameters()).device),
        "dtype": str(next(adapter._model.parameters()).dtype),
        "torchThreads": torch.get_num_threads(),
        "modelLoadSec": round(load_sec, 1),
        "peakRssGb": round(peak_rss / 2**30, 2),
        "planDigest": digest,
        "originalsUnchanged": True,
        "benchmarkLabel": "LOCAL_CPU_BENCHMARK",
    }
    (private_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


def score(private_dir: Path, report_out: Path | None):
    records = [json.loads(line) for line in (private_dir / "raw_outputs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [bench.score_condition(record) for record in records]
    (private_dir / "scored_rows.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    meta_path = private_dir / "run_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    report = bench.aggregate(rows, meta={k: v for k, v in meta.items() if k != "planDigest"} | {"planDigestPrefix": str(meta.get("planDigest", ""))[:12]})
    forbidden = set()
    for record in records:
        for task in record["tasks"].values():
            for payload in task.values():
                if isinstance(payload, dict):
                    forbidden.update(str(label) for label in payload.get("labels", []) if len(str(label).strip()) >= 3)
    manifest = json.loads((private_dir / "restricted_manifest.json").read_text(encoding="utf-8"))
    forbidden.update(Path(e["path"]).name for e in manifest["entries"])
    forbidden -= {label for label in forbidden if bench.sanitize_od_label(label) == label.strip().lower()}  # OD nouns are allowed
    problems = bench.privacy_violations(report, forbidden)
    if problems:
        raise SystemExit(f"PRIVACY_VIOLATION {problems}")
    text = json.dumps(report, indent=2, sort_keys=True)
    (private_dir / "aggregate_report.json").write_text(text + "\n", encoding="utf-8")
    if report_out:
        report_out.write_text(text + "\n", encoding="utf-8")
    print(f"scored {len(rows)} conditions; privacy guard clean")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--phases", default="raw,control,core,curve")
    parser.add_argument("--score-only", action="store_true")
    parser.add_argument("--report-out", type=Path)
    args = parser.parse_args(argv)
    if not args.score_only:
        run(args.private_dir, args.model_dir, set(args.phases.split(",")))
    score(args.private_dir, args.report_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
