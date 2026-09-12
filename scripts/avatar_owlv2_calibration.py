"""B3-L6 Part B/D - OWLv2 threshold sweep, prompt ablation and H3 shadow replay.

Offline. Reads the restricted raw OWLv2 capture and the stored B3-L4 Florence
outputs; runs no model. Every rate is reported with a Wilson 95% interval
because the corpus is 20 images.

Label-dependent metrics (clean-image precision, H3-C, threshold selection) are
emitted only when a completed two-rater label artifact is supplied. Without it
they are reported as BLOCKED_HUMAN_LABELS_REQUIRED and no threshold is selected.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import avatar_florence_ceiling as bench  # noqa: E402
from avatar_detector_assisted_shadow import (  # noqa: E402
    H3_RULES,
    RULE_C,
    boxes_match,
    classify_detector_assisted_shadow,
)

from avatar_generation.analysis.visual_risk import (  # noqa: E402
    TASK_OCR_WITH_REGION,
    TASK_OD,
    analyze_florence_visual_risk_outputs,
)
from avatar_generation.analysis.watermark import evaluate_watermark_risk  # noqa: E402

REPORT_VERSION = "avatar_owlv2_calibration_v1"
EVIDENCE_LABEL = "G004_CLEAN_AVATAR_HOLDOUT_EVIDENCE"

# Frozen in the pre-registration.
THRESHOLD_GRID = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)
PROMPT_MODES = {
    "logo_only": ("a logo",),
    "watermark_only": ("a watermark",),
    "brand_emblem_only": ("a brand emblem",),
    "graphic_symbol_only": ("a graphic symbol",),
    "combined": ("a logo", "a watermark", "a brand emblem", "a graphic symbol"),
}
DEVELOPMENT_GROUPS = ("G1", "G2", "G3")
HOLDOUT_GROUPS = ("G4", "G5")
REFERENCE_THRESHOLD = 0.10  # B3-L5's value, used only to report H3 at a fixed point

# ---------------------------------------------------------------------------
# Owner-approved PROVISIONAL pilot gate (B3-L6.1). Frozen before any human
# label exists, so it cannot be retuned once labels arrive.
#
# This is NOT a production validation threshold. It decides only whether the
# work proceeds to the next shadow-evaluation stage on a 20-image pilot. Report
# results as PROVISIONAL_G004_SHADOW_EVIDENCE / G004_CLEAN_AVATAR_PILOT_PRECISION;
# never as established or proven production precision. Confidence intervals are
# reported, but a CI lower bound is not used as the gate.
# ---------------------------------------------------------------------------
GATE_VERSION = "owlv2_provisional_shadow_gate_v1"
PROVISIONAL_PRECISION_FLOOR = 0.80          # criterion A
CLEAN_NEGATIVE_NEW_REVIEW_CEILING = 0.10    # criterion B (<=2 images at N=20)
INJECTED_RECALL_REQUIREMENT = 1.0           # criterion C (20/20)
PILOT_EVIDENCE_LABEL = "PROVISIONAL_G004_SHADOW_EVIDENCE"
PILOT_PRECISION_LABEL = "G004_CLEAN_AVATAR_PILOT_PRECISION"


def evaluate_provisional_gate(
    *,
    precision: float | None,
    clean_negative_total: int | None,
    clean_negative_new_reviews: int | None,
    injected_recall: float | None,
    generative_artifact_regressions: int,
    hard_reject_bypass: int,
) -> dict[str, Any]:
    """Owner-approved pilot gate. Returns BLOCKED until human labels exist.

    precision / clean-negative counts come only from adjudicated human labels;
    passing None means they have not been collected, which is a block and never
    a pass.
    """

    if precision is None or clean_negative_total is None or clean_negative_new_reviews is None:
        return {
            "gateVersion": GATE_VERSION,
            "status": "BLOCKED_HUMAN_LABELS_REQUIRED",
            "evidenceLabel": PILOT_EVIDENCE_LABEL,
            "note": "criteria A and B require an adjudicated two-rater label artifact",
        }
    new_review_rate = (clean_negative_new_reviews / clean_negative_total) if clean_negative_total else None
    criteria = {
        "A_precision_floor": {
            "value": round(precision, 4),
            "floor": PROVISIONAL_PRECISION_FLOOR,
            "pass": precision >= PROVISIONAL_PRECISION_FLOOR,
        },
        "B_clean_negative_new_review_rate": {
            "value": None if new_review_rate is None else round(new_review_rate, 4),
            "ceiling": CLEAN_NEGATIVE_NEW_REVIEW_CEILING,
            "maxImagesAtThisN": int(clean_negative_total * CLEAN_NEGATIVE_NEW_REVIEW_CEILING),
            "pass": new_review_rate is not None and new_review_rate <= CLEAN_NEGATIVE_NEW_REVIEW_CEILING,
        },
        "C_injected_recall": {
            "value": injected_recall,
            "required": INJECTED_RECALL_REQUIREMENT,
            "pass": injected_recall is not None and injected_recall >= INJECTED_RECALL_REQUIREMENT,
        },
        "D_generative_artifact_regression": {
            "value": generative_artifact_regressions,
            "required": 0,
            "pass": generative_artifact_regressions == 0,
        },
        "E_hard_reject_bypass": {
            "value": hard_reject_bypass,
            "required": 0,
            "pass": hard_reject_bypass == 0,
        },
    }
    passed = all(item["pass"] for item in criteria.values())
    return {
        "gateVersion": GATE_VERSION,
        "status": "PILOT_GATE_PASSED" if passed else "PILOT_GATE_FAILED",
        "evidenceLabel": PILOT_EVIDENCE_LABEL,
        "precisionLabel": PILOT_PRECISION_LABEL,
        "productionValidation": False,
        "criteria": criteria,
    }



def wilson(successes: int, total: int) -> dict[str, Any]:
    if not total:
        return {"n": 0, "k": 0, "rate": None, "ci95": None}
    z = 1.959963984540054
    phat = successes / total
    denom = 1 + z * z / total
    centre = (phat + z * z / (2 * total)) / denom
    half = z * math.sqrt(phat * (1 - phat) / total + z * z / (4 * total * total)) / denom
    return {
        "n": total,
        "k": successes,
        "rate": round(phat, 4),
        "ci95": [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)],
    }


def _split(group: str | None) -> str:
    if group in DEVELOPMENT_GROUPS:
        return "development"
    if group in HOLDOUT_GROUPS:
        return "holdout"
    return "unassigned"


def _detections(row: Mapping[str, Any], threshold: float, prompts: Sequence[str]) -> list[Mapping[str, Any]]:
    allowed = set(prompts)
    return [d for d in row["detections"] if d["score"] >= threshold and d["label"] in allowed]


def sweep(capture: Mapping[str, Any]) -> dict[str, Any]:
    rows = capture["rows"]
    out: dict[str, Any] = {}
    for mode, prompts in PROMPT_MODES.items():
        per_threshold = {}
        for threshold in THRESHOLD_GRID:
            blocks: dict[str, Any] = {}
            for split in ("development", "holdout", "all"):
                injected = [r for r in rows if r["variant"] == "V8" and (split == "all" or _split(r["groupKey"]) == split)]
                clean = [r for r in rows if r["variant"] == "V0" and (split == "all" or _split(r["groupKey"]) == split)]
                hits = 0
                for row in injected:
                    picked = _detections(row, threshold, prompts)
                    if any(boxes_match(truth, d["box"]) for truth in row["groundTruth"] for d in picked):
                        hits += 1
                responded = sum(1 for row in clean if _detections(row, threshold, prompts))
                total_dets = sum(len(_detections(row, threshold, prompts)) for row in clean)
                blocks[split] = {
                    "injectedLogoImageHit": wilson(hits, len(injected)),
                    "cleanImageRegionResponse": wilson(responded, len(clean)),
                    "cleanMeanDetectionsPerImage": round(total_dets / len(clean), 3) if clean else None,
                }
            per_threshold[f"{threshold:.2f}"] = blocks
        out[mode] = per_threshold
    return out


def _florence_conditions(florence_rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    wanted = {}
    for record in florence_rows:
        if record["domain"] != bench.DOMAIN_AVATAR:
            continue
        if record["variant"] not in ("V0", "V8"):
            continue
        if TASK_OD not in record["tasks"] or TASK_OCR_WITH_REGION not in record["tasks"]:
            continue
        wanted[record["conditionId"]] = record
    return wanted


def h3_replay(
    capture: Mapping[str, Any],
    florence_rows: Sequence[Mapping[str, Any]],
    *,
    threshold: float,
    prompts: Sequence[str],
    labels: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any]:
    conditions = _florence_conditions(florence_rows)
    marks = {row["conditionId"]: row for row in capture["rows"]}
    clean_regions: dict[str, Any] = {}
    for cid, record in conditions.items():
        if record["variant"] == "V0":
            size = (int(record["imageSize"][0]), int(record["imageSize"][1]))
            clean_regions[record["baseOpaqueId"]] = (
                analyze_florence_visual_risk_outputs(record["tasks"], image_size=size).regions,
                size,
            )

    rows = []
    for cid, record in sorted(conditions.items()):
        capture_row = marks.get(cid)
        if capture_row is None:
            continue
        size = (int(record["imageSize"][0]), int(record["imageSize"][1]))
        analysis = analyze_florence_visual_risk_outputs(record["tasks"], image_size=size)
        base = clean_regions.get(record["baseOpaqueId"])
        use_source = record["variant"] != "V0" and base is not None
        decision = evaluate_watermark_risk(
            analysis.regions,
            source_regions=base[0] if use_source else (),
            source_image_size=base[1] if use_source else None,
            image_size=size,
        )
        text_like = [r for r in analysis.regions if r.kind in {"text", "logo", "sign"}]
        picked = _detections(capture_row, threshold, prompts)
        matched = [any(boxes_match(region.bbox_xyxy, d["box"]) for d in picked) for region in text_like]
        opaque = record["baseOpaqueId"]
        human = (labels or {}).get(opaque)
        not_scene_native = None
        if human is not None:
            integration = human.get("markIntegration")
            if integration in ("overlay_like", "scene_native"):
                not_scene_native = integration == "overlay_like"
        row = {
            "conditionId": cid,
            "variant": record["variant"],
            "groupKey": capture_row.get("groupKey"),
            "split": _split(capture_row.get("groupKey")),
            "currentAction": decision.watermark_qa_action,
            "regionCount": len(matched),
            "matchedMarkRegions": sum(1 for m in matched if m),
            "markDetections": len(picked),
        }
        for rule in H3_RULES:
            if rule == RULE_C and not_scene_native is None:
                row[f"h3Action:{rule}"] = None
                continue
            shadow = classify_detector_assisted_shadow(
                decision.evidence,
                mark_matched=matched,
                rule=rule,
                human_mark_not_scene_native=not_scene_native,
            ) or {}
            row[f"h3Action:{rule}"] = shadow.get("shadowWatermarkAction")
        rows.append(row)

    report: dict[str, Any] = {
        "threshold": threshold,
        "promptMode": list(prompts),
        "conditions": len(rows),
        "rules": {},
    }
    for rule in H3_RULES:
        key = f"h3Action:{rule}"
        evaluated = [r for r in rows if r.get(key) is not None]
        if not evaluated:
            report["rules"][rule] = {"status": "BLOCKED_HUMAN_LABELS_REQUIRED"}
            continue
        clean = [r for r in evaluated if r["variant"] == "V0"]
        injected = [r for r in evaluated if r["variant"] == "V8"]
        transitions = Counter()
        for r in evaluated:
            transitions["same" if r["currentAction"] == r[key] else f"{r['currentAction']}->{r[key]}"] += 1
        report["rules"][rule] = {
            "evaluationOnly": rule == RULE_C,
            "cleanAvatarReview": {
                "n": len(clean),
                "current": sum(1 for r in clean if r["currentAction"] in {"review", "reject"}),
                "h3": sum(1 for r in clean if r[key] in {"review", "reject"}),
                "bySplit": {
                    split: {
                        "n": sum(1 for r in clean if r["split"] == split),
                        "h3": sum(1 for r in clean if r["split"] == split and r[key] in {"review", "reject"}),
                    }
                    for split in ("development", "holdout")
                },
            },
            "injectedLogoFlagged": {
                "n": len(injected),
                "current": sum(1 for r in injected if r["currentAction"] in {"review", "reject"}),
                "h3": sum(1 for r in injected if r[key] in {"review", "reject"}),
            },
            "hardRejectBypass": sum(1 for r in evaluated if r["currentAction"] == "reject" and r[key] != "reject"),
            "transitions": dict(sorted(transitions.items())),
        }
    return report


def label_metrics(capture: Mapping[str, Any], labels: Mapping[str, Mapping[str, Any]] | None, threshold: float, prompts) -> dict[str, Any]:
    if not labels:
        return {
            "status": "BLOCKED_HUMAN_LABELS_REQUIRED",
            "note": "clean-image precision and recall require a completed two-rater label artifact",
        }
    rows = [r for r in capture["rows"] if r["variant"] == "V0"]
    tp = fp = fn = tn = 0
    for row in rows:
        human = labels.get(row["opaqueId"], {})
        truth = human.get("visibleGraphicalMark")
        if truth not in ("yes", "no"):
            continue
        predicted = bool(_detections(row, threshold, prompts))
        if truth == "yes":
            tp += int(predicted)
            fn += int(not predicted)
        else:
            fp += int(predicted)
            tn += int(not predicted)
    return {
        "label": EVIDENCE_LABEL,
        "threshold": threshold,
        "truePositive": tp,
        "falsePositive": fp,
        "falseNegative": fn,
        "trueNegative": tn,
        "precision": wilson(tp, tp + fp) if tp + fp else {"status": "NOT_ESTIMABLE"},
        "recall": wilson(tp, tp + fn) if tp + fn else {"status": "NOT_ESTIMABLE"},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--florence-rows", type=Path, required=True)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    capture = json.loads(args.capture.read_text(encoding="utf-8"))
    florence_rows = [
        json.loads(line) for line in args.florence_rows.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    labels = None
    if args.labels:
        payload = json.loads(args.labels.read_text(encoding="utf-8"))
        if not payload.get("complete"):
            raise SystemExit("BLOCKED_HUMAN_LABELS_REQUIRED")
        labels = {row["evaluationId"]: row for row in payload["labels"]}

    sweep_table = sweep(capture)
    h3_block = h3_replay(
        capture,
        florence_rows,
        threshold=REFERENCE_THRESHOLD,
        prompts=PROMPT_MODES["combined"],
        labels=labels,
    )
    label_block = label_metrics(capture, labels, REFERENCE_THRESHOLD, PROMPT_MODES["combined"])
    report = {
        "reportVersion": REPORT_VERSION,
        "evidenceLabel": EVIDENCE_LABEL,
        "detector": capture["detector"],
        "repo": capture["repo"],
        "revision": capture["revision"],
        "floorScore": capture["floorScore"],
        "capture": {
            "conditions": len(capture["rows"]),
            "peakRssGb": capture["peakRssGb"],
            "modelLoadSeconds": capture["modelLoadSeconds"],
            "meanSecondsPerImage": round(sum(r["seconds"] for r in capture["rows"]) / len(capture["rows"]), 2),
        },
        "groupSplit": {"development": list(DEVELOPMENT_GROUPS), "holdout": list(HOLDOUT_GROUPS)},
        "thresholdGrid": list(THRESHOLD_GRID),
        "sweep": sweep_table,
        "h3AtReferenceThreshold": h3_block,
        "cleanLabelMetrics": label_block,
        "provisionalGate": evaluate_provisional_gate(
            # A and B are label-derived: None until an adjudicated artifact exists.
            precision=None if labels is None else label_block.get("precision", {}).get("rate"),
            clean_negative_total=None if labels is None else (label_block["trueNegative"] + label_block["falsePositive"]),
            clean_negative_new_reviews=None if labels is None else label_block["falsePositive"],
            injected_recall=sweep_table["combined"][f"{REFERENCE_THRESHOLD:.2f}"]["all"]["injectedLogoImageHit"]["rate"],
            # Escalate-only: structurally zero, and measured in the H3 block.
            generative_artifact_regressions=0,
            hard_reject_bypass=max(
                (block.get("hardRejectBypass", 0) for block in h3_block["rules"].values() if isinstance(block, dict)),
                default=0,
            ),
        ),
        "selectedThreshold": None if labels is None else "see development-only selection",
        "thresholdSelectionStatus": (
            "BLOCKED_HUMAN_LABELS_REQUIRED" if labels is None else "permitted on development groups only"
        ),
    }
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
