"""CI tests for the B3-L5 H2 single-overlay shadow. No model, no image, no network."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import avatar_single_overlay_eval as evaluation  # noqa: E402
import avatar_single_overlay_shadow as h2  # noqa: E402
from avatar_generation.analysis import watermark  # noqa: E402
from avatar_generation.analysis.watermark import (  # noqa: E402
    WATERMARK_EVIDENCE_SCHEMA_VERSION,
    classify_watermark_evidence_document,
)

PREREG = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "avatar-production"
    / "b3-single-overlay-shadow-preregistration.md"
)


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


def test_single_overlay_escalates_allow_to_review():
    doc = evidence(region())
    assert classify_watermark_evidence_document(doc).watermark_qa_action == "allow"
    for rule in h2.H2_RULES:
        shadow = h2.classify_single_overlay_shadow(doc, rule=rule)
        assert shadow["shadowWatermarkAction"] == "review"
        assert shadow["escalatedFromReplay"] is True
        assert shadow["consumedByPolicy"] is False


def test_source_consistent_and_non_overlay_are_not_escalated():
    for doc in (
        evidence(region(sourceConsistent=True)),
        evidence(region(overlayLike=False, location="clothing_zone")),
    ):
        for rule in h2.H2_RULES:
            assert h2.classify_single_overlay_shadow(doc, rule=rule)["shadowWatermarkAction"] == "allow"


def test_escalate_only_never_downgrades_a_reject_or_review():
    repeated = evidence(region(repeated=True), region(repeated=True))
    assert classify_watermark_evidence_document(repeated).watermark_qa_action == "reject"
    fragmented = evidence(region(overlayLike=False, location="central", textQuality="implausible"))
    assert classify_watermark_evidence_document(fragmented).watermark_qa_action == "review"
    for rule in h2.H2_RULES:
        assert h2.classify_single_overlay_shadow(repeated, rule=rule)["shadowWatermarkAction"] == "reject"
        assert h2.classify_single_overlay_shadow(fragmented, rule=rule)["shadowWatermarkAction"] == "review"


def test_rule_b_bound_is_the_existing_small_band():
    corner_medium = evidence(region(areaBand="medium"))
    assert h2.classify_single_overlay_shadow(corner_medium, rule=h2.RULE_A)["shadowWatermarkAction"] == "review"
    assert h2.classify_single_overlay_shadow(corner_medium, rule=h2.RULE_B)["shadowWatermarkAction"] == "allow"
    assert watermark.TINY_REGION_AREA == 0.03


def test_rule_c_is_structurally_implied_by_rule_a():
    """overlayLike already requires corner or edge geometry, so C cannot differ."""

    for location in ("corner", "edge"):
        doc = evidence(region(location=location))
        assert h2.classify_single_overlay_shadow(doc, rule=h2.RULE_A)["shadowWatermarkAction"] == h2.classify_single_overlay_shadow(
            doc, rule=h2.RULE_C
        )["shadowWatermarkAction"]


def test_legacy_or_malformed_evidence_returns_none():
    assert h2.classify_single_overlay_shadow(None, rule=h2.RULE_A) is None
    assert h2.classify_single_overlay_shadow({"regionEvidence": []}, rule=h2.RULE_A) is None
    assert h2.classify_single_overlay_shadow(evidence({"kind": "bogus"}), rule=h2.RULE_A) is None
    with pytest.raises(ValueError):
        h2.classify_single_overlay_shadow(evidence(region()), rule="H2-Z")


def test_h2_is_shadow_only_and_live_policy_unchanged():
    assert watermark.WATERMARK_POLICY_VERSION == "watermark_policy_v4_runtime_evidence_parity_v1"
    doc = evidence(region())
    before = classify_watermark_evidence_document(doc).to_document()
    h2.classify_single_overlay_shadow(doc, rule=h2.RULE_A)
    assert classify_watermark_evidence_document(doc).to_document() == before
    source = (SCRIPTS / "avatar_single_overlay_shadow.py").read_text(encoding="utf-8")
    for forbidden in ("previewAllowed", "rejectReasons =", "firestore", "google.cloud", "requests"):
        assert forbidden not in source


def test_sanitized_form_is_fixed_vocabulary_only():
    shadow = h2.classify_single_overlay_shadow(evidence(region()), rule=h2.RULE_A)
    shadow["leak"] = "SECRETTEXT"
    clean = h2.sanitize_single_overlay_shadow(shadow)
    assert "leak" not in clean and "SECRETTEXT" not in json.dumps(clean)
    assert clean["consumedByPolicy"] is False
    assert h2.sanitize_single_overlay_shadow({"policyVersion": "other"}) == {}


def test_preregistration_document_is_frozen_and_matches_code():
    text = PREREG.read_text(encoding="utf-8")
    for rule in h2.H2_RULES:
        assert f"**{rule}**" in text
    assert "ESCALATE-ONLY" in text
    assert "H2_LIVE_POLICY_READY" in text and "not a permitted outcome" in text
    assert "PRE-INJECTION BASELINE" in text


def test_local_rows_separate_current_and_shadow_and_stay_text_free():
    record = {
        "conditionId": "g004-avatar-001:V1",
        "domain": evaluation.bench.DOMAIN_AVATAR,
        "baseOpaqueId": "g004-avatar-001",
        "variant": "V1",
        "displayVariant": "A1",
        "phase": "core",
        "imageSize": [512, 768],
        "groundTruth": [],
        "tasks": {
            evaluation.TASK_OCR_WITH_REGION: {
                evaluation.TASK_OCR_WITH_REGION: {
                    "quad_boxes": [[470, 740, 500, 740, 500, 758, 470, 758]],
                    "labels": ["ZQXSENTINEL"],
                }
            },
            evaluation.TASK_OD: {evaluation.TASK_OD: {"bboxes": [], "labels": []}},
        },
    }
    rows = evaluation.local_rows([record])
    assert len(rows) == 1
    row = rows[0]
    assert row["currentAction"] == "allow"
    assert row["h2Action:H2-A"] == "review"
    assert "ZQXSENTINEL" not in json.dumps(row)
    report = evaluation.aggregate_local(rows)
    assert not evaluation.bench.privacy_violations(report, ["ZQXSENTINEL"])


def test_curve_conditions_without_od_are_skipped():
    record = {
        "conditionId": "g004-src-001:C-corner-small-a100",
        "domain": evaluation.bench.DOMAIN_SOURCE,
        "baseOpaqueId": "g004-src-001",
        "variant": "C-corner-small-a100",
        "phase": "curve",
        "imageSize": [512, 768],
        "groundTruth": [],
        "tasks": {evaluation.TASK_OCR_WITH_REGION: {evaluation.TASK_OCR_WITH_REGION: {"quad_boxes": [], "labels": []}}},
    }
    assert evaluation.local_rows([record]) == []


def test_production_replay_reports_no_hard_reject_bypass_and_job_level():
    document = {
        "jobId": "j1",
        "status": "ready",
        "qa": {
            "watermarkQaAction": "allow",
            "previewAllowed": True,
            "debug": {"watermarkEvidence": evidence(region(sourceConsistent=False))},
        },
    }
    report = evaluation.replay_production([document], allow_soft_review=False)
    assert report["candidatesEvaluated"] == 1 and report["jobs"] == 1
    for rule in h2.H2_RULES:
        block = report["rules"][rule]
        assert block["hardRejectBypass"] == 0
        assert block["escalatedCandidates"] == 1
        assert block["transitions"] == {"allow->review": 1}
        assert set(block["jobPreviewDistribution"]) <= {"zero", "one", "two_plus"}
