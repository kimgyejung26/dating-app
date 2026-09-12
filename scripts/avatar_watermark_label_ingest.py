"""B3-L6 Part A - ingest two independent rater exports, measure agreement, emit a repo-safe artifact.

Enforces the pre-registered contract:

  * two raters, labelled independently; identical files are rejected as a
    copy rather than an independent second pass;
  * only the allowed fields survive (no filename, UID, path, transcription,
    detector score or detector box);
  * every item must be labelled by both raters before the corpus counts as
    complete -- otherwise the caller must stop at BLOCKED_HUMAN_LABELS_REQUIRED;
  * disagreements are reported, and stay UNCERTAIN unless an adjudication file
    resolves them.

  python scripts/avatar_watermark_label_ingest.py --rater-a a.json --rater-b b.json --out labels.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import avatar_florence_ceiling as bench  # noqa: E402
from avatar_watermark_label_local import (  # noqa: E402
    LABEL_CONFIDENCE,
    LABEL_SCHEMA_VERSION,
    MARK_INTEGRATION,
    MARK_TYPE,
    PRIMARY_LABELS,
    VISIBLE_GRAPHICAL_MARK,
)

INGEST_VERSION = "avatar_watermark_label_ingest_v1"
ALLOWED_FIELDS = (
    "evaluationId",
    "primaryLabel",
    "allVisibleClasses",
    "visibleGraphicalMark",
    "markIntegration",
    "markType",
    "labelConfidence",
    "raterId",
    "adjudicationState",
)
_VOCAB = {
    "primaryLabel": set(PRIMARY_LABELS),
    "visibleGraphicalMark": set(VISIBLE_GRAPHICAL_MARK),
    "markIntegration": set(MARK_INTEGRATION),
    "markType": set(MARK_TYPE),
    "labelConfidence": set(LABEL_CONFIDENCE),
}


def sanitize(row: Mapping[str, Any], rater: str) -> dict[str, Any]:
    out: dict[str, Any] = {"evaluationId": str(row["evaluationId"]), "raterId": str(rater)}
    for field, vocabulary in _VOCAB.items():
        value = row.get(field)
        if value is not None:
            if str(value) not in vocabulary:
                raise SystemExit(f"INVALID_LABEL_VALUE {field}")
            out[field] = str(value)
    classes = row.get("allVisibleClasses") or []
    if not isinstance(classes, Sequence) or isinstance(classes, (str, bytes)):
        raise SystemExit("INVALID_LABEL_VALUE allVisibleClasses")
    unknown = [c for c in classes if str(c) not in set(PRIMARY_LABELS)]
    if unknown:
        raise SystemExit("INVALID_LABEL_VALUE allVisibleClasses")
    out["allVisibleClasses"] = [str(c) for c in classes]
    return out


def _load(path: Path) -> tuple[str, dict[str, dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("labelSchema") != LABEL_SCHEMA_VERSION:
        raise SystemExit("LABEL_SCHEMA_MISMATCH")
    rater = str(payload.get("raterId") or "")
    if not rater:
        raise SystemExit("MISSING_RATER_ID")
    rows = {}
    for row in payload.get("labels") or []:
        clean = sanitize(row, rater)
        rows[clean["evaluationId"]] = clean
    return rater, rows


def ingest(path_a: Path, path_b: Path, expected_items: Sequence[str] | None = None) -> dict[str, Any]:
    rater_a, rows_a = _load(path_a)
    rater_b, rows_b = _load(path_b)
    if rater_a == rater_b:
        raise SystemExit("RATERS_NOT_DISTINCT")
    def _content(rows):
        return {
            item: {field: value for field, value in row.items() if field != "raterId"}
            for item, row in rows.items()
        }

    # Identical label content across every item is a copy, not an independent
    # second pass. Compared without raterId, which always differs.
    if rows_a and _content(rows_a) == _content(rows_b):
        raise SystemExit("RATER_PASSES_IDENTICAL_NOT_INDEPENDENT")

    items = sorted(set(rows_a) | set(rows_b) | set(expected_items or ()))
    complete = [i for i in items if i in rows_a and i in rows_b]
    agreements, disagreements = [], []
    for item in complete:
        a, b = rows_a[item], rows_b[item]
        same = a.get("primaryLabel") == b.get("primaryLabel") and a.get("visibleGraphicalMark") == b.get(
            "visibleGraphicalMark"
        )
        (agreements if same else disagreements).append(item)

    resolved = []
    for item in complete:
        a, b = rows_a[item], rows_b[item]
        if item in agreements:
            resolved.append(
                {
                    "evaluationId": item,
                    "primaryLabel": a.get("primaryLabel"),
                    "visibleGraphicalMark": a.get("visibleGraphicalMark"),
                    "markIntegration": a.get("markIntegration") if a.get("markIntegration") == b.get("markIntegration") else "uncertain",
                    "markType": a.get("markType") if a.get("markType") == b.get("markType") else "uncertain",
                    "allVisibleClasses": sorted(set(a["allVisibleClasses"]) & set(b["allVisibleClasses"])),
                    "adjudicationState": "agreed",
                }
            )
        else:
            resolved.append(
                {
                    "evaluationId": item,
                    "primaryLabel": "UNCERTAIN",
                    "visibleGraphicalMark": "uncertain",
                    "markIntegration": "uncertain",
                    "markType": "uncertain",
                    "allVisibleClasses": [],
                    "adjudicationState": "unresolved_disagreement",
                }
            )

    return {
        "ingestVersion": INGEST_VERSION,
        "labelSchema": LABEL_SCHEMA_VERSION,
        "raters": sorted([rater_a, rater_b]),
        "itemsExpected": len(items),
        "itemsCompletedByBoth": len(complete),
        "complete": bool(items) and len(complete) == len(items),
        "agreementCount": len(agreements),
        "disagreementCount": len(disagreements),
        "rawAgreementRate": round(len(agreements) / len(complete), 4) if complete else None,
        "primaryLabelDistribution": dict(Counter(r["primaryLabel"] for r in resolved)),
        "visibleGraphicalMarkDistribution": dict(Counter(r["visibleGraphicalMark"] for r in resolved)),
        "labels": resolved,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rater-a", type=Path, required=True)
    parser.add_argument("--rater-b", type=Path, required=True)
    parser.add_argument("--worksheet", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    expected = None
    if args.worksheet:
        expected = [i["evaluationId"] for i in json.loads(args.worksheet.read_text(encoding="utf-8"))["items"]]
    report = ingest(args.rater_a, args.rater_b, expected)
    problems = bench.privacy_violations(report)
    if problems:
        raise SystemExit(f"PRIVACY_VIOLATION {problems}")
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    if not report["complete"]:
        print("BLOCKED_HUMAN_LABELS_REQUIRED", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
