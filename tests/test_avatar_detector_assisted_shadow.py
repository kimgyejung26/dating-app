"""CI tests for B3-L6: labeling tooling, OWLv2 calibration and the H3 shadow.

No model, no user image, no human labels and no network in CI.
"""

import json
import re
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import avatar_detector_assisted_shadow as h3  # noqa: E402
import avatar_florence_ceiling as bench  # noqa: E402
import avatar_owlv2_calibration as calib  # noqa: E402
import avatar_watermark_label_ingest as ingest  # noqa: E402
import avatar_watermark_label_local as ui  # noqa: E402
from avatar_generation.analysis import watermark  # noqa: E402
from avatar_generation.analysis.watermark import (  # noqa: E402
    WATERMARK_EVIDENCE_SCHEMA_VERSION,
    classify_watermark_evidence_document,
)

PREREG = Path(__file__).resolve().parents[1] / "docs" / "avatar-production" / "b3-l6-preregistration.md"


def region(**kwargs):
    base = {
        "kind": "text",
        "confidenceBand": "unknown",
        "areaBand": "small",
        "location": "corner",
        "overlayLike": True,
        "textQuality": "plausible",
        "sourceConsistent": None,
        "repeated": False,
        "artifactHint": False,
    }
    base.update(kwargs)
    return base


def evidence(*regions):
    return {"schemaVersion": WATERMARK_EVIDENCE_SCHEMA_VERSION, "regionEvidence": list(regions)}


# ---------------------------------------------------------------- labeling UI


def test_label_ui_is_network_free_and_blinded():
    page = ui.build_html([{"opaqueId": "g004-avatar-001", "dataUri": "data:image/jpeg;base64,AAAA"}], "A")
    assert "http://" not in page and "https://" not in page
    assert "src=\"data:image/jpeg" in page
    assert "default-src 'none'" in page
    lowered = page.lower()
    for forbidden in ui.FORBIDDEN_IN_UI:
        assert forbidden.lower() not in lowered, forbidden
    assert "g004-avatar-001" in page


def test_label_ui_uses_only_the_pr114_taxonomy():
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "avatar_watermark_label_schema_v2.json").read_text(
            encoding="utf-8"
        )
    )
    known = set(schema["visibleTextClasses"]) | {"NO_VISIBLE_RELEVANT_TEXT_OR_MARK", "UNCERTAIN"}
    assert set(ui.PRIMARY_LABELS) <= known
    assert ui.LABEL_SCHEMA_VERSION == "avatar_watermark_label_schema_v2"


def test_label_ui_never_renders_a_filename_or_path():
    page = ui.build_html([{"opaqueId": "g004-avatar-004", "dataUri": "data:image/jpeg;base64,AAAA"}], "B")
    body = re.sub(r"data:image/jpeg;base64,[A-Za-z0-9+/=]*", "", page)
    assert not bench.privacy_violations({"page": body})


# ---------------------------------------------------------------- label ingest


def _export(rater, rows):
    return {"labelSchema": ui.LABEL_SCHEMA_VERSION, "raterId": rater, "labels": rows}


def _row(eid, primary="GRAPHICAL_LOGO", mark="yes", integration="overlay_like", **extra):
    row = {
        "evaluationId": eid,
        "primaryLabel": primary,
        "allVisibleClasses": [primary] if primary != "UNCERTAIN" else [],
        "visibleGraphicalMark": mark,
        "markIntegration": integration,
        "markType": "graphical_logo",
        "labelConfidence": "high",
    }
    row.update(extra)
    return row


def test_ingest_requires_two_distinct_independent_raters(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(_export("A", [_row("g004-avatar-001")])), encoding="utf-8")
    b.write_text(json.dumps(_export("A", [_row("g004-avatar-001")])), encoding="utf-8")
    with pytest.raises(SystemExit, match="RATERS_NOT_DISTINCT"):
        ingest.ingest(a, b)
    b.write_text(json.dumps(_export("B", [_row("g004-avatar-001")])), encoding="utf-8")
    with pytest.raises(SystemExit, match="RATER_PASSES_IDENTICAL_NOT_INDEPENDENT"):
        ingest.ingest(a, b)


def test_ingest_marks_disagreements_uncertain_and_reports_completion(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(_export("A", [_row("i1"), _row("i2", primary="GARMENT_TEXT", mark="no", integration="scene_native")])), encoding="utf-8")
    b.write_text(json.dumps(_export("B", [_row("i1"), _row("i2", primary="BRAND_TEXT_OR_MARK", mark="yes")])), encoding="utf-8")
    report = ingest.ingest(a, b, expected_items=["i1", "i2"])
    assert report["complete"] is True
    assert report["agreementCount"] == 1 and report["disagreementCount"] == 1
    by_id = {row["evaluationId"]: row for row in report["labels"]}
    assert by_id["i1"]["adjudicationState"] == "agreed"
    assert by_id["i2"]["primaryLabel"] == "UNCERTAIN"
    assert by_id["i2"]["adjudicationState"] == "unresolved_disagreement"


def test_ingest_is_incomplete_when_a_rater_has_not_finished(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(_export("A", [_row("i1"), _row("i2")])), encoding="utf-8")
    b.write_text(json.dumps(_export("B", [_row("i1", mark="no")])), encoding="utf-8")
    report = ingest.ingest(a, b, expected_items=["i1", "i2"])
    assert report["complete"] is False and report["itemsCompletedByBoth"] == 1


def test_ingest_strips_everything_outside_the_allowed_fields():
    clean = ingest.sanitize(
        {
            "evaluationId": "i1",
            "primaryLabel": "OVERLAY_WATERMARK",
            "allVisibleClasses": ["OVERLAY_WATERMARK"],
            "visibleGraphicalMark": "yes",
            "markIntegration": "overlay_like",
            "markType": "watermark",
            "labelConfidence": "high",
            "transcription": "SAMPLEMARK",
            "filename": "P98_C97.png",
            "uid": "abc123",
            "detectorScore": 0.9,
            "box": [1, 2, 3, 4],
        },
        "A",
    )
    assert set(clean) <= set(ingest.ALLOWED_FIELDS)
    text = json.dumps(clean)
    for leak in ("SAMPLEMARK", "P98_C97", "abc123", "0.9"):
        assert leak not in text


def test_ingest_rejects_values_outside_the_frozen_vocabulary():
    with pytest.raises(SystemExit, match="INVALID_LABEL_VALUE"):
        ingest.sanitize({"evaluationId": "i1", "primaryLabel": "MADE_UP_CLASS", "allVisibleClasses": []}, "A")
    with pytest.raises(SystemExit, match="INVALID_LABEL_VALUE"):
        ingest.sanitize({"evaluationId": "i1", "visibleGraphicalMark": "probably", "allVisibleClasses": []}, "A")


# ---------------------------------------------------------------- calibration


def test_group_split_is_deterministic_disjoint_and_covers_five_groups():
    dev, holdout = set(calib.DEVELOPMENT_GROUPS), set(calib.HOLDOUT_GROUPS)
    assert dev.isdisjoint(holdout)
    assert dev | holdout == {"G1", "G2", "G3", "G4", "G5"}
    assert len(dev) == 3 and len(holdout) == 2
    assert calib._split("G1") == "development" and calib._split("G5") == "holdout"
    assert calib._split(None) == "unassigned"


def test_threshold_grid_and_prompt_modes_are_frozen():
    assert calib.THRESHOLD_GRID == (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)
    assert set(calib.PROMPT_MODES) == {
        "logo_only",
        "watermark_only",
        "brand_emblem_only",
        "graphic_symbol_only",
        "combined",
    }
    assert calib.PROMPT_MODES["combined"] == tuple(ui_prompts := ("a logo", "a watermark", "a brand emblem", "a graphic symbol"))
    import avatar_logo_detector_benchmark as logo

    assert logo.PROMPTS == ui_prompts


def test_sweep_is_deterministic_and_splits_do_not_leak():
    capture = {
        "rows": [
            {
                "conditionId": "g004-avatar-001:V8",
                "opaqueId": "g004-avatar-001",
                "groupKey": "G1",
                "variant": "V8",
                "groundTruth": [[10.0, 10.0, 50.0, 50.0]],
                "detections": [{"box": [10.0, 10.0, 50.0, 50.0], "score": 0.4, "label": "a logo"}],
                "seconds": 1.0,
            },
            {
                "conditionId": "g004-avatar-020:V8",
                "opaqueId": "g004-avatar-020",
                "groupKey": "G5",
                "variant": "V8",
                "groundTruth": [[10.0, 10.0, 50.0, 50.0]],
                "detections": [],
                "seconds": 1.0,
            },
            {
                "conditionId": "g004-avatar-001:V0",
                "opaqueId": "g004-avatar-001",
                "groupKey": "G1",
                "variant": "V0",
                "groundTruth": [],
                "detections": [{"box": [1.0, 1.0, 9.0, 9.0], "score": 0.2, "label": "a watermark"}],
                "seconds": 1.0,
            },
        ]
    }
    first, second = calib.sweep(capture), calib.sweep(capture)
    assert first == second
    dev = first["combined"]["0.10"]["development"]
    holdout = first["combined"]["0.10"]["holdout"]
    assert dev["injectedLogoImageHit"]["n"] == 1 and dev["injectedLogoImageHit"]["k"] == 1
    assert holdout["injectedLogoImageHit"]["n"] == 1 and holdout["injectedLogoImageHit"]["k"] == 0
    # threshold filtering: the clean detection at 0.2 disappears at 0.25
    assert first["combined"]["0.20"]["development"]["cleanImageRegionResponse"]["k"] == 1
    assert first["combined"]["0.25"]["development"]["cleanImageRegionResponse"]["k"] == 0
    # prompt filtering: that detection is a watermark query, not a logo query
    assert first["logo_only"]["0.10"]["development"]["cleanImageRegionResponse"]["k"] == 0


def test_wilson_interval_brackets_the_rate():
    assert calib.wilson(0, 0)["rate"] is None
    low, high = calib.wilson(10, 20)["ci95"]
    assert low < 0.5 < high
    assert calib.wilson(20, 20)["ci95"][1] == 1.0


def test_label_dependent_metrics_are_blocked_without_labels():
    capture = {"rows": []}
    blocked = calib.label_metrics(capture, None, 0.10, calib.PROMPT_MODES["combined"])
    assert blocked["status"] == "BLOCKED_HUMAN_LABELS_REQUIRED"


def test_recall_is_not_estimable_without_human_positives():
    capture = {
        "rows": [
            {"opaqueId": "i1", "variant": "V0", "detections": [{"box": [0, 0, 1, 1], "score": 0.9, "label": "a logo"}], "groundTruth": []}
        ]
    }
    labels = {"i1": {"visibleGraphicalMark": "no"}}
    metrics = calib.label_metrics(capture, labels, 0.10, calib.PROMPT_MODES["combined"])
    assert metrics["recall"] == {"status": "NOT_ESTIMABLE"}
    assert metrics["falsePositive"] == 1
    assert metrics["label"] == calib.EVIDENCE_LABEL


# ---------------------------------------------------------------- H3 shadow


def test_box_match_rule_is_iou_or_containment():
    region_box = [100.0, 100.0, 200.0, 200.0]
    assert h3.boxes_match(region_box, [100.0, 100.0, 200.0, 200.0])
    assert h3.boxes_match(region_box, [0.0, 0.0, 400.0, 400.0])  # containment of the region
    assert not h3.boxes_match(region_box, [300.0, 300.0, 320.0, 320.0])
    assert h3.IOU_MATCH == 0.3 and h3.CONTAINMENT_MATCH == 0.5


def test_h3_escalates_only_with_a_matched_mark():
    doc = evidence(region())
    assert classify_watermark_evidence_document(doc).watermark_qa_action == "allow"
    unmatched = h3.classify_detector_assisted_shadow(doc, mark_matched=[False], rule=h3.RULE_A)
    assert unmatched["shadowWatermarkAction"] == "allow" and unmatched["escalatedFromReplay"] is False
    matched = h3.classify_detector_assisted_shadow(doc, mark_matched=[True], rule=h3.RULE_A)
    assert matched["shadowWatermarkAction"] == "review" and matched["escalatedFromReplay"] is True
    assert matched["consumedByPolicy"] is False


def test_h3_a_needs_overlay_geometry_and_h3_b_needs_source_inconsistency():
    central = evidence(region(overlayLike=False, location="central"))
    assert h3.classify_detector_assisted_shadow(central, mark_matched=[True], rule=h3.RULE_A)["shadowWatermarkAction"] == "allow"
    assert h3.classify_detector_assisted_shadow(central, mark_matched=[True], rule=h3.RULE_B)["shadowWatermarkAction"] == "review"
    consistent = evidence(region(sourceConsistent=True))
    assert h3.classify_detector_assisted_shadow(consistent, mark_matched=[True], rule=h3.RULE_B)["shadowWatermarkAction"] == "allow"


def test_h3_c_requires_the_human_field_and_is_flagged_evaluation_only():
    doc = evidence(region())
    with pytest.raises(ValueError, match="H3-C requires"):
        h3.classify_detector_assisted_shadow(doc, mark_matched=[True], rule=h3.RULE_C)
    shadow = h3.classify_detector_assisted_shadow(
        doc, mark_matched=[True], rule=h3.RULE_C, human_mark_not_scene_native=True
    )
    assert shadow["shadowWatermarkAction"] == "review" and shadow["evaluationOnly"] is True
    scene = h3.classify_detector_assisted_shadow(
        doc, mark_matched=[True], rule=h3.RULE_C, human_mark_not_scene_native=False
    )
    assert scene["shadowWatermarkAction"] == "allow"
    assert h3.EVALUATION_ONLY_RULES == ("H3-C",)


def test_h3_never_downgrades_a_reject_or_review():
    repeated = evidence(region(repeated=True), region(repeated=True))
    assert classify_watermark_evidence_document(repeated).watermark_qa_action == "reject"
    fragmented = evidence(region(overlayLike=False, location="central", textQuality="implausible"))
    assert classify_watermark_evidence_document(fragmented).watermark_qa_action == "review"
    for rule in (h3.RULE_A, h3.RULE_B):
        assert h3.classify_detector_assisted_shadow(repeated, mark_matched=[False, False], rule=rule)["shadowWatermarkAction"] == "reject"
        assert h3.classify_detector_assisted_shadow(fragmented, mark_matched=[False], rule=rule)["shadowWatermarkAction"] == "review"


def test_h3_requires_parallel_match_flags_and_rejects_legacy_evidence():
    with pytest.raises(ValueError, match="parallel"):
        h3.classify_detector_assisted_shadow(evidence(region()), mark_matched=[], rule=h3.RULE_A)
    assert h3.classify_detector_assisted_shadow({"regionEvidence": []}, mark_matched=[], rule=h3.RULE_A) is None
    with pytest.raises(ValueError, match="unknown rule"):
        h3.classify_detector_assisted_shadow(evidence(region()), mark_matched=[True], rule="H3-Z")


def test_h3_is_shadow_only_and_live_policy_is_unchanged():
    assert watermark.WATERMARK_POLICY_VERSION == "watermark_policy_v4_runtime_evidence_parity_v1"
    doc = evidence(region())
    before = classify_watermark_evidence_document(doc).to_document()
    for rule in (h3.RULE_A, h3.RULE_B):
        h3.classify_detector_assisted_shadow(doc, mark_matched=[True], rule=rule)
    assert classify_watermark_evidence_document(doc).to_document() == before
    source = (SCRIPTS / "avatar_detector_assisted_shadow.py").read_text(encoding="utf-8")
    for forbidden in ("previewAllowed", "rejectReasons =", "firestore", "google.cloud", "requests"):
        assert forbidden not in source


def test_sanitized_h3_form_is_fixed_vocabulary_only():
    shadow = h3.classify_detector_assisted_shadow(evidence(region()), mark_matched=[True], rule=h3.RULE_A)
    shadow["leak"] = "SECRET"
    shadow["score"] = 0.97
    clean = h3.sanitize_detector_assisted_shadow(shadow)
    assert "leak" not in clean and "score" not in clean
    assert "SECRET" not in json.dumps(clean) and "0.97" not in json.dumps(clean)
    assert h3.sanitize_detector_assisted_shadow({"policyVersion": "nope"}) == {}


def test_preregistration_is_frozen_and_matches_the_code():
    text = PREREG.read_text(encoding="utf-8")
    for rule in h3.H3_RULES:
        assert f"**{rule}**" in text
    assert "G1, G2, G3" in text and "G4, G5" in text
    assert "0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50" in text
    assert "BLOCKED_HUMAN_LABELS_REQUIRED" in text
    assert "H3_LIVE_POLICY_READY` is not a permitted outcome" in text
    assert "upper bound" in text.lower()
