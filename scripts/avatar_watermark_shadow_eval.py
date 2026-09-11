"""Offline current-vs-shadow watermark evaluation.

Never opens an image, loads a model, calls a network service, or writes
anywhere except stdout / --out. Two modes:

  fixtures  Florence-shaped synthetic OUTPUTS with human image labels fixed by
            construction. These are known-positive / known-negative evidence
            rows for evaluating policy LOGIC. They are not images, involve no
            model, and say nothing about Florence's image-level recall.

  replay    A JSON export of already-persisted candidate documents. Uses only the
            typed watermark evidence each document carries (no raw OCR exists
            in them) and reports candidate- and job-level disagreement.
            Production documents carry no human label, so replay never reports
            precision or recall.

Output is aggregate only: no candidate, job or user identifier is emitted.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.analysis.visual_risk import (  # noqa: E402
    TASK_OCR_WITH_REGION,
    TASK_OD,
    analyze_florence_visual_risk_outputs,
)
from avatar_generation.analysis.watermark import (  # noqa: E402
    classify_watermark_evidence_document,
    evaluate_watermark_risk,
    watermark_risk_for_action,
)
from avatar_generation.analysis.watermark_construct_shadow import (  # noqa: E402
    classify_watermark_construct_shadow,
)
from avatar_generation.preview_policy import is_preview_eligible  # noqa: E402

LABEL_SCHEMA_PATH = REPO_ROOT / "tests" / "fixtures" / "avatar_watermark_label_schema_v2.json"
REPORT_VERSION = "avatar_watermark_shadow_eval_v2"


def label_schema() -> Mapping[str, Any]:
    return json.loads(LABEL_SCHEMA_PATH.read_text(encoding="utf-8"))


def _flagged(action: Optional[str]) -> bool:
    return action in {"review", "reject"}


def derive_model_error(
    human_label: str,
    ocr_region_count: int,
    schema: Mapping[str, Any],
) -> Optional[str]:
    """Model errors are derived from a human image label and model output; a
    human is never asked to label one."""

    if human_label == "NO_VISIBLE_RELEVANT_TEXT" and ocr_region_count > 0:
        return "OCR_HALLUCINATION"
    if human_label in schema["visibleTextClasses"] and ocr_region_count == 0:
        return "OCR_MISS"
    return None


def evaluate_fixture_outputs(payload: Mapping[str, Any]) -> dict[str, Any]:
    schema = label_schema()
    risk_positive = set(schema["riskPositiveClasses"])
    scene_native = set(schema["sceneNativeClasses"])
    width, height = payload["imageSize"]
    rows = []
    for fixture in payload["fixtures"]:
        outputs = {
            TASK_OCR_WITH_REGION: fixture["ocr"],
            TASK_OD: fixture.get("od", {"bboxes": [], "labels": []}),
        }
        analysis = analyze_florence_visual_risk_outputs(outputs, image_size=(width, height))
        decision = evaluate_watermark_risk(analysis.regions, image_size=(width, height))
        shadow = classify_watermark_construct_shadow(decision.evidence) or {}
        rows.append(
            {
                "id": fixture["id"],
                "label": fixture["label"],
                "derivedModelError": derive_model_error(
                    fixture["label"], len(fixture["ocr"]["labels"]), schema
                ),
                "currentAction": decision.watermark_qa_action,
                "shadowAction": shadow.get("shadowWatermarkAction"),
                "shadowClass": shadow.get("shadowWatermarkClass"),
            }
        )

    def rate(selector, key):
        chosen = [row for row in rows if selector(row["label"])]
        return {"n": len(chosen), "flagged": sum(1 for row in chosen if _flagged(row[key]))}

    return {
        "reportVersion": REPORT_VERSION,
        "mode": "fixtures",
        "scope": (
            "synthetic known-positive/known-negative evidence rows for policy-logic "
            "evaluation; not images, not Florence recall, not production accuracy"
        ),
        "rows": rows,
        "syntheticKnownPositiveFlagged": {
            "current": rate(lambda label: label in risk_positive, "currentAction"),
            "shadow": rate(lambda label: label in risk_positive, "shadowAction"),
        },
        "syntheticSceneNativeFlagged": {
            "current": rate(lambda label: label in scene_native, "currentAction"),
            "shadow": rate(lambda label: label in scene_native, "shadowAction"),
        },
        "byLabel": {
            label: {
                "current": rate(lambda value, target=label: value == target, "currentAction"),
                "shadow": rate(lambda value, target=label: value == target, "shadowAction"),
            }
            for label in sorted({row["label"] for row in rows})
        },
        "derivedModelErrors": dict(
            Counter(row["derivedModelError"] for row in rows if row["derivedModelError"])
        ),
        "actionDiff": sum(1 for row in rows if row["currentAction"] != row["shadowAction"]),
    }


def _counterfactual_qa(qa: Mapping[str, Any], shadow_action: str) -> dict[str, Any]:
    """The same QA document with only the watermark outcome swapped.

    Conservative: requiresHumanReview and the review tier are not recomputed, so
    a candidate withheld for any other reason stays withheld. This can
    under-state what a shadow policy would release; it never over-states it.
    """

    counterfactual = copy.deepcopy(dict(qa))
    counterfactual["watermarkQaAction"] = shadow_action
    risk = watermark_risk_for_action(shadow_action)
    counterfactual["textLogoWatermarkRisk"] = risk
    counterfactual["logoTextWatermarkRisk"] = risk
    if shadow_action == "allow":
        counterfactual["reviewReasons"] = [
            reason
            for reason in (qa.get("reviewReasons") or [])
            if reason != "watermark_artifact_review"
        ]
    return counterfactual


def replay_candidate_documents(
    documents: Iterable[Mapping[str, Any]],
    *,
    allow_soft_review: bool,
) -> dict[str, Any]:
    evaluated = 0
    parity_mismatch = 0
    action_pairs: Counter = Counter()
    shadow_classes: Counter = Counter()
    eligible_by_job: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    newly_eligible_with_reject = 0

    for document in documents:
        qa = document.get("qa") or {}
        debug = qa.get("debug") or {}
        evidence = debug.get("watermarkEvidence")
        shadow = classify_watermark_construct_shadow(evidence)
        if shadow is None:
            continue
        evaluated += 1
        live_action = str(qa.get("watermarkQaAction") or "")
        replayed = classify_watermark_evidence_document(evidence)
        replayed_action = replayed.watermark_qa_action if replayed is not None else "allow"
        if replayed_action != live_action:
            parity_mismatch += 1
        shadow_action = shadow["shadowWatermarkAction"]
        action_pairs[(live_action, shadow_action)] += 1
        shadow_classes[shadow["shadowWatermarkClass"]] += 1

        candidate = {"status": document.get("status"), "qa": qa}
        counterfactual = {"status": document.get("status"), "qa": _counterfactual_qa(qa, shadow_action)}
        current_eligible = is_preview_eligible(candidate, allow_soft_review=allow_soft_review)
        shadow_eligible = is_preview_eligible(counterfactual, allow_soft_review=allow_soft_review)
        if shadow_eligible and not current_eligible and qa.get("rejectReasons"):
            newly_eligible_with_reject += 1
        eligible_by_job[str(document.get("jobId"))].append((current_eligible, shadow_eligible))

    def distribution(index: int) -> dict[str, int]:
        result: Counter = Counter()
        for rows in eligible_by_job.values():
            count = sum(1 for row in rows if row[index])
            result["zero" if count == 0 else ("one" if count == 1 else "two_plus")] += 1
        return dict(result)

    return {
        "reportVersion": REPORT_VERSION,
        "mode": "replay",
        "scope": (
            "persisted typed evidence; no human labels, so disagreement only. "
            "Eligibility, not realised preview: selection and preview counts are not modelled."
        ),
        "candidatesEvaluated": evaluated,
        "evidenceReplayParityMismatches": parity_mismatch,
        "liveVsShadowAction": {f"{live}->{shadow}": count for (live, shadow), count in sorted(action_pairs.items())},
        "shadowClasses": dict(sorted(shadow_classes.items())),
        "candidateActionDiff": sum(count for (live, shadow), count in action_pairs.items() if live != shadow),
        "newlyEligibleWithRejectReasons": newly_eligible_with_reject,
        "jobs": len(eligible_by_job),
        "jobEligibleDistribution": {"current": distribution(0), "shadow": distribution(1)},
        "jobsChanged": sum(
            1
            for rows in eligible_by_job.values()
            if sum(r[0] for r in rows) != sum(r[1] for r in rows)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("fixtures", "replay"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--allow-soft-review", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if args.mode == "fixtures":
        report = evaluate_fixture_outputs(payload)
    else:
        documents = payload if isinstance(payload, list) else payload.get("candidates", [])
        report = replay_candidate_documents(documents, allow_soft_review=args.allow_soft_review)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
