"""B3-L5 Part A - evaluate the pre-registered H2 candidates. Offline, aggregate-only.

Two modes, neither of which opens an image or calls a model:

  local   Replays the stored B3-L4 Florence outputs (restricted local directory).
          Real-domain core conditions are scored with PRE-INJECTION BASELINE
          source regions: the same base image's own clean (V0/A0) Florence
          regions. That is not the production source-photo comparison and is
          labelled PRE_INJECTION_BASELINE everywhere.

  replay  Replays persisted production candidate documents (typed evidence
          only, no raw OCR, no image) at candidate and job level.

Output carries counts, rates and typed enums only.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import avatar_florence_ceiling as bench  # noqa: E402
from avatar_single_overlay_shadow import H2_RULES, classify_single_overlay_shadow  # noqa: E402

from avatar_generation.analysis.visual_risk import (  # noqa: E402
    TASK_OCR_WITH_REGION,
    TASK_OD,
    analyze_florence_visual_risk_outputs,
)
from avatar_generation.analysis.watermark import (  # noqa: E402
    evaluate_watermark_risk,
    watermark_risk_for_action,
)
from avatar_generation.preview_policy import is_preview_eligible  # noqa: E402

REPORT_VERSION = "avatar_single_overlay_eval_v1"
SOURCE_MODE = "PRE_INJECTION_BASELINE"
OVERLAY_VARIANTS = bench.OVERLAY_VARIANTS
SINGLE_OVERLAY_VARIANTS = ("V1", "V2", "V3", "V5", "V6")
ARTIFACT_VARIANTS = bench.ARTIFACT_VARIANTS
BENIGN_VARIANTS = bench.BENIGN_VARIANTS
BENIGN_CONTROLS = ("ctl-05", "ctl-06", "ctl-07", "ctl-09")
ARTIFACT_CONTROL = "ctl-10"
_FLAGGED = {"review", "reject"}


def _analysis(record: Mapping[str, Any]):
    size = (int(record["imageSize"][0]), int(record["imageSize"][1]))
    analysis = analyze_florence_visual_risk_outputs(
        record["tasks"], image_size=size, primary_face_bbox_xyxy=None
    )
    return analysis, size


def local_rows(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    clean: dict[str, Any] = {}
    for record in records:
        if record["phase"] == "raw":
            analysis, size = _analysis(record)
            clean[record["baseOpaqueId"]] = (analysis.regions, size)

    rows = []
    for record in records:
        if TASK_OD not in record["tasks"] or TASK_OCR_WITH_REGION not in record["tasks"]:
            continue  # OCR-only curve conditions carry no policy decision
        analysis, size = _analysis(record)
        base = clean.get(record["baseOpaqueId"])
        use_source = base is not None and record["phase"] == "core"
        decision = evaluate_watermark_risk(
            analysis.regions,
            source_regions=base[0] if use_source else (),
            source_image_size=base[1] if use_source else None,
            image_size=size,
        )
        spec = bench.spec_for(record["variant"]) if record["domain"] != bench.DOMAIN_SYNTHETIC else None
        row: dict[str, Any] = {
            "conditionId": record["conditionId"],
            "domain": record["domain"],
            "variant": record["variant"],
            "displayVariant": record.get("displayVariant", record["variant"]),
            "phase": record["phase"],
            "groupKey": record.get("groupKey"),
            "sourceRegionsUsed": bool(use_source),
            "currentAction": decision.watermark_qa_action,
            "currentDecisionClass": decision.decision_class,
            "sourceConsistency": (decision.evidence or {}).get("sourceConsistency"),
            "regionCount": len((decision.evidence or {}).get("regionEvidence") or []),
        }
        if spec is not None:
            row.update(
                riskPositive=spec.risk_positive,
                construct=spec.construct,
                expectedClass=spec.expected_class,
            )
        for rule in H2_RULES:
            shadow = classify_single_overlay_shadow(decision.evidence, rule=rule) or {}
            row[f"h2Action:{rule}"] = shadow.get("shadowWatermarkAction")
            row[f"h2Escalated:{rule}"] = bool(shadow.get("escalatedFromReplay"))
        rows.append(row)
    return rows


def _rate(num: int, den: int):
    return round(num / den, 4) if den else None


def _variant_block(rows: Sequence[Mapping[str, Any]], variants: Sequence[str], key: str) -> dict[str, Any]:
    chosen = [r for r in rows if r["variant"] in variants]
    flagged = sum(1 for r in chosen if r.get(key) in _FLAGGED)
    return {
        "n": len(chosen),
        "flagged": flagged,
        "rate": _rate(flagged, len(chosen)),
        "allowed": sum(1 for r in chosen if r.get(key) == "allow"),
    }


def aggregate_local(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_domain: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_domain[row["domain"]].append(row)
    report: dict[str, Any] = {
        "reportVersion": REPORT_VERSION,
        "sourceConsistencyMode": SOURCE_MODE,
        "rules": list(H2_RULES),
        "domains": {},
    }
    for domain in (bench.DOMAIN_SOURCE, bench.DOMAIN_AVATAR):
        domain_rows = by_domain.get(domain, [])
        core = [r for r in domain_rows if r["phase"] == "core"]
        raw = [r for r in domain_rows if r["phase"] == "raw"]
        block: dict[str, Any] = {
            "current": {
                "singleOverlayFlag": _variant_block(core, SINGLE_OVERLAY_VARIANTS, "currentAction"),
                "overlayFlag": _variant_block(core, OVERLAY_VARIANTS, "currentAction"),
                "artifactFlag": _variant_block(core, ARTIFACT_VARIANTS, "currentAction"),
                "benignFlag": _variant_block(core, BENIGN_VARIANTS, "currentAction"),
                "cleanReview": sum(1 for r in raw if r["currentAction"] in _FLAGGED),
                "actionsByVariant": {
                    bench.display_variant(domain, v): dict(
                        Counter(r["currentAction"] for r in core if r["variant"] == v)
                    )
                    for v in sorted({r["variant"] for r in core})
                },
                "sourceConsistency": dict(Counter(r["sourceConsistency"] for r in core)),
            },
            "rules": {},
        }
        for rule in H2_RULES:
            key = f"h2Action:{rule}"
            transitions: Counter = Counter()
            for r in domain_rows:
                cur, h2 = r["currentAction"], r.get(key)
                transitions["same" if cur == h2 else f"{cur}->{h2}"] += 1
            overlay_current = _variant_block(core, OVERLAY_VARIANTS, "currentAction")
            overlay_h2 = _variant_block(core, OVERLAY_VARIANTS, key)
            artifact_current = _variant_block(core, ARTIFACT_VARIANTS, "currentAction")
            artifact_h2 = _variant_block(core, ARTIFACT_VARIANTS, key)
            block["rules"][rule] = {
                "singleOverlayFlag": _variant_block(core, SINGLE_OVERLAY_VARIANTS, key),
                "overlayFlag": overlay_h2,
                "artifactFlag": artifact_h2,
                "benignFlag": _variant_block(core, BENIGN_VARIANTS, key),
                "actionsByVariant": {
                    bench.display_variant(domain, v): dict(Counter(r.get(key) for r in core if r["variant"] == v))
                    for v in sorted({r["variant"] for r in core})
                },
                "cleanRealReviewDelta": {
                    "n": len(raw),
                    "current": sum(1 for r in raw if r["currentAction"] in _FLAGGED),
                    "h2": sum(1 for r in raw if r.get(key) in _FLAGGED),
                },
                "transitions": dict(sorted(transitions.items())),
                "hardRejectBypass": sum(
                    1 for r in domain_rows if r["currentAction"] == "reject" and r.get(key) != "reject"
                ),
                "overlayMissIncrease": max(0, overlay_h2["allowed"] - overlay_current["allowed"]),
                "artifactMissIncrease": max(0, artifact_h2["allowed"] - artifact_current["allowed"]),
            }
        report["domains"][domain] = block

    synthetic = by_domain.get(bench.DOMAIN_SYNTHETIC, [])
    report["domains"][bench.DOMAIN_SYNTHETIC] = {
        "controls": {
            r["conditionId"]: {
                "current": r["currentAction"],
                **{rule: r.get(f"h2Action:{rule}") for rule in H2_RULES},
            }
            for r in sorted(synthetic, key=lambda r: r["conditionId"])
        },
        "benignControlFlagsCurrent": sum(
            1 for r in synthetic if r["conditionId"] in BENIGN_CONTROLS and r["currentAction"] in _FLAGGED
        ),
        "benignControlFlags": {
            rule: sum(
                1
                for r in synthetic
                if r["conditionId"] in BENIGN_CONTROLS and r.get(f"h2Action:{rule}") in _FLAGGED
            )
            for rule in H2_RULES
        },
        "artifactControl": {
            "current": next((r["currentAction"] for r in synthetic if r["conditionId"] == ARTIFACT_CONTROL), None),
            **{
                rule: next(
                    (r.get(f"h2Action:{rule}") for r in synthetic if r["conditionId"] == ARTIFACT_CONTROL), None
                )
                for rule in H2_RULES
            },
        },
    }
    groups = [r for r in by_domain.get(bench.DOMAIN_AVATAR, []) if r["phase"] == "raw" and r.get("groupKey")]
    if groups:
        report["g004GroupLevelSimulation"] = _group_sim(groups)
    return report


def _group_sim(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_group: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_group[row["groupKey"]].append(row)

    def bucket(count: int) -> str:
        return "zero" if count == 0 else "one" if count == 1 else "two_plus"

    distribution = {
        "current": dict(Counter(bucket(sum(1 for r in v if r["currentAction"] == "allow")) for v in by_group.values()))
    }
    for rule in H2_RULES:
        distribution[rule] = dict(
            Counter(bucket(sum(1 for r in v if r.get(f"h2Action:{rule}") == "allow")) for v in by_group.values())
        )
    return {
        "label": "G004_GROUP_LEVEL_SIMULATION",
        "groups": len(by_group),
        "scope": "watermark action only; other QA gates not modelled",
        "watermarkAllowedDistribution": distribution,
    }


def _counterfactual(qa: Mapping[str, Any], action: str) -> dict[str, Any]:
    out = copy.deepcopy(dict(qa))
    out["watermarkQaAction"] = action
    risk = watermark_risk_for_action(action)
    out["textLogoWatermarkRisk"] = risk
    out["logoTextWatermarkRisk"] = risk
    reasons = list(qa.get("reviewReasons") or [])
    if action == "review" and "watermark_artifact_review" not in reasons:
        reasons.append("watermark_artifact_review")
    out["reviewReasons"] = reasons
    return out


def replay_production(documents: Iterable[Mapping[str, Any]], *, allow_soft_review: bool) -> dict[str, Any]:
    evaluated = 0
    per_rule = {rule: {"transitions": Counter(), "escalated": 0, "hardRejectBypass": 0} for rule in H2_RULES}
    jobs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        qa = document.get("qa") or {}
        evidence = (qa.get("debug") or {}).get("watermarkEvidence")
        shadows = {rule: classify_single_overlay_shadow(evidence, rule=rule) for rule in H2_RULES}
        if any(value is None for value in shadows.values()):
            continue
        evaluated += 1
        live = str(qa.get("watermarkQaAction") or "")
        entry = {"current": is_preview_eligible({"status": document.get("status"), "qa": qa}, allow_soft_review=allow_soft_review)}
        for rule, shadow in shadows.items():
            action = shadow["shadowWatermarkAction"]
            per_rule[rule]["transitions"]["same" if action == live else f"{live}->{action}"] += 1
            per_rule[rule]["escalated"] += int(shadow["escalatedFromReplay"])
            per_rule[rule]["hardRejectBypass"] += int(live == "reject" and action != "reject")
            entry[rule] = is_preview_eligible(
                {"status": document.get("status"), "qa": _counterfactual(qa, action)},
                allow_soft_review=allow_soft_review,
            )
        jobs[str(document.get("jobId"))].append(entry)

    def distribution(key: str) -> dict[str, int]:
        counter: Counter = Counter()
        for rows in jobs.values():
            count = sum(1 for row in rows if row[key])
            counter["zero" if count == 0 else "one" if count == 1 else "two_plus"] += 1
        return dict(counter)

    return {
        "reportVersion": REPORT_VERSION,
        "mode": "production_typed_metadata_replay",
        "allowSoftReview": allow_soft_review,
        "candidatesEvaluated": evaluated,
        "jobs": len(jobs),
        "jobPreviewDistributionCurrent": distribution("current"),
        "rules": {
            rule: {
                "transitions": dict(sorted(data["transitions"].items())),
                "escalatedCandidates": data["escalated"],
                "hardRejectBypass": data["hardRejectBypass"],
                "jobPreviewDistribution": distribution(rule),
                "jobsChanged": sum(
                    1 for rows in jobs.values() if sum(r["current"] for r in rows) != sum(r[rule] for r in rows)
                ),
                "jobsLosingLastPreview": sum(
                    1
                    for rows in jobs.values()
                    if sum(r["current"] for r in rows) > 0 and sum(r[rule] for r in rows) == 0
                ),
            }
            for rule, data in per_rule.items()
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("local", "replay"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--rows-out", type=Path)
    parser.add_argument("--allow-soft-review", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "local":
        records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows = local_rows(records)
        report = aggregate_local(rows)
        if args.rows_out:
            args.rows_out.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    else:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        documents = payload if isinstance(payload, list) else payload.get("candidates", [])
        report = replay_production(documents, allow_soft_review=args.allow_soft_review)
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
