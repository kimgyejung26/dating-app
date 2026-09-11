"""B3: does watermark QA measure watermarks, or transcription strings?

Florence <OCR_WITH_REGION> returns transcribed text per region -- the
transformers post-processor sets ``labels = [inst["text"] ...]`` -- and returns
no per-region score. Two consequences are pinned here rather than "fixed":

  * the substring kind classifier (DESIGN -> sign, LOGON -> logo) reads a
    transcription as if it were a semantic class. It is construct-invalid, and
    today it is action-inert: kind only renames the decision class.
  * with the current Florence adapter and region-confidence schema every OCR
    region's confidence is None, so the high-confidence hard-reject branch is
    unreachable there; the only live path to a watermark reject is repetition
    in overlay geometry. A future adapter with per-region scores changes this.

The construct-valid shadow (analysis/watermark_construct_shadow.py) is read by
nothing. These tests pin that it changes no effective decision, persists no
text, and differs from the live policy only where hypothesis H1 says it should.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
SCRIPTS = REPO_ROOT / "scripts"
for path in (AI_MODEL_DIR, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from avatar_generation.analysis.visual_risk import (  # noqa: E402
    KIND_LOGO,
    KIND_SIGN,
    KIND_TEXT,
    TASK_OCR_WITH_REGION,
    TASK_OD,
    VisualRiskRegion,
    _classify_ocr_label,
    _parallel_scores,
    analyze_florence_visual_risk_outputs,
)
from avatar_generation.analysis.watermark import (  # noqa: E402
    WATERMARK_EVIDENCE_SCHEMA_VERSION,
    classify_watermark_evidence_document,
    evaluate_watermark_risk,
)
from avatar_generation.analysis.watermark_construct_shadow import (  # noqa: E402
    SHADOW_CLASSES,
    WATERMARK_CONSTRUCT_SHADOW_VERSION,
    classify_watermark_construct_shadow,
    sanitize_watermark_construct_shadow,
)
from avatar_generation.qa import AvatarQAThresholds, build_avatar_qa_from_signals  # noqa: E402
from avatar_generation.qa_signals import _add_visual_signals  # noqa: E402
from avatar_watermark_shadow_eval import (  # noqa: E402
    evaluate_fixture_outputs,
    replay_candidate_documents,
)

FIXTURES = json.loads(
    (REPO_ROOT / "tests" / "fixtures" / "avatar_watermark_construct_fixtures_v1.json").read_text(
        encoding="utf-8"
    )
)
LABEL_SCHEMA = json.loads(
    (REPO_ROOT / "tests" / "fixtures" / "avatar_watermark_label_schema_v2.json").read_text(
        encoding="utf-8"
    )
)
IMAGE_SIZE = tuple(FIXTURES["imageSize"])


def _analyze(ocr):
    return analyze_florence_visual_risk_outputs(
        {TASK_OCR_WITH_REGION: ocr, TASK_OD: {"bboxes": [], "labels": []}},
        image_size=IMAGE_SIZE,
    )


def _decide(ocr):
    analysis = _analyze(ocr)
    return evaluate_watermark_risk(analysis.regions, image_size=IMAGE_SIZE)


# ---------------------------------------------------------------------------
# 1. What the OCR label is, and what the live classifier does with it
# ---------------------------------------------------------------------------

SUBSTRING_CASES = [
    ("DESIGN", KIND_SIGN),
    ("Designer", KIND_SIGN),
    ("assignment", KIND_SIGN),
    ("resigned", KIND_SIGN),
    ("Signature", KIND_SIGN),
    ("LOGON", KIND_LOGO),
    ("logout", KIND_LOGO),
    ("brandy", KIND_LOGO),
    ("Brandon", KIND_LOGO),
    ("SIGN", KIND_SIGN),
    ("LOGO", KIND_LOGO),
    ("BRAND", KIND_LOGO),
    ("HELLO", KIND_TEXT),
    ("NIKE", KIND_TEXT),
]


@pytest.mark.parametrize("transcription,live_kind", SUBSTRING_CASES)
def test_live_kind_is_a_substring_match_on_a_transcription(transcription, live_kind):
    """Pins current behaviour, not a desired one. The OCR label is transcribed
    text; even the literal word SIGN is a transcription, not a sign object."""

    assert _classify_ocr_label(transcription) == live_kind


def test_florence_ocr_carries_no_per_region_score():
    """The Florence ocr post-processor returns {quad_boxes, labels} only, so the
    parser sees no scores and every region confidence is None."""

    assert _parallel_scores(None, 3) == (None, None, None)
    analysis = _analyze({"quad_boxes": [[10, 10, 90, 10, 90, 28, 10, 28]], "labels": ["iStock"]})
    assert [region.confidence for region in analysis.regions] == [None]


def test_substring_kind_never_changes_the_watermark_action():
    """Construct-invalid but action-inert. If a rule ever starts reading kind as
    a decision input, this fails and forces a construct review first."""

    geometries = {
        "corner_small": (5, 5, 60, 30),
        "edge_tiny": (230, 5, 280, 20),
        "central": (180, 300, 330, 360),
        "clothing_zone": (190, 470, 320, 520),
    }
    tokens = ["DESIGN", "NEW YORK NY", "WATERMARK", "HELLO", "A F", "LOGON"]
    for (name, bbox), token, repeats in itertools.product(geometries.items(), tokens, (1, 2)):
        actions = set()
        for kind in (KIND_TEXT, KIND_LOGO, KIND_SIGN):
            regions = [
                VisualRiskRegion(
                    kind,
                    (bbox[0] + 3 * i, bbox[1], bbox[2] + 3 * i, bbox[3]),
                    confidence=None,
                    raw_label=token,
                )
                for i in range(repeats)
            ]
            actions.add(evaluate_watermark_risk(regions, image_size=IMAGE_SIZE).watermark_qa_action)
        assert len(actions) == 1, (name, token, repeats, actions)


# ---------------------------------------------------------------------------
# 2. Hard-reject reachability
# ---------------------------------------------------------------------------


def _typed_region(**overrides):
    region = {
        "kind": "text",
        "confidenceBand": "unknown",
        "areaBand": "small",
        "location": "corner",
        "overlayLike": False,
        "textQuality": "plausible",
        "sourceConsistent": None,
        "repeated": False,
        "artifactHint": False,
    }
    region.update(overrides)
    return region


def _evidence(*regions):
    return {"schemaVersion": WATERMARK_EVIDENCE_SCHEMA_VERSION, "regionEvidence": list(regions)}


def test_with_production_confidence_reject_is_reachable_only_through_repeated_overlay():
    """Exhaustive over the typed single-region space with confidence "unknown"
    -- the only band production has ever produced (12/12 current, 20/20 G004)."""

    space = itertools.product(
        ("small", "medium", "large"),
        ("corner", "edge", "central", "clothing_zone"),
        (True, False),
        (True, False),
        ("plausible", "implausible", "unknown"),
        (None, True, False),
        (True, False),
    )
    for area, location, overlay, repeated, quality, consistent, hint in space:
        decision = classify_watermark_evidence_document(
            _evidence(
                _typed_region(
                    areaBand=area,
                    location=location,
                    overlayLike=overlay,
                    repeated=repeated,
                    textQuality=quality,
                    sourceConsistent=consistent,
                    artifactHint=hint,
                )
            )
        )
        rejected = decision is not None and decision.watermark_qa_action == "reject"
        assert rejected == (overlay and repeated), (area, location, overlay, repeated, quality, consistent, hint)


def test_high_confidence_branch_exists_but_needs_a_score_the_current_adapter_never_emits():
    decision = classify_watermark_evidence_document(
        _evidence(_typed_region(overlayLike=True, confidenceBand="high", textQuality="implausible"))
    )
    assert decision.watermark_qa_action == "reject"
    decision = classify_watermark_evidence_document(
        _evidence(_typed_region(overlayLike=True, confidenceBand="unknown", textQuality="implausible"))
    )
    assert decision.watermark_qa_action == "review"


# ---------------------------------------------------------------------------
# 3. Synthetic construct fixtures
# ---------------------------------------------------------------------------


def test_fixture_labels_come_from_the_label_schema():
    classes = set(LABEL_SCHEMA["humanImageLabels"])
    assert FIXTURES["labelProvenance"] == "synthetic_by_construction"
    assert FIXTURES["labelSchema"] == LABEL_SCHEMA["schemaVersion"]
    for fixture in FIXTURES["fixtures"]:
        assert fixture["label"] in classes, fixture["id"]


def test_humans_never_label_a_model_error():
    """A person looking at an image can see that no text is there; they cannot
    see that the OCR invented some. Model errors are derived, never labelled."""

    human = set(LABEL_SCHEMA["humanImageLabels"])
    derived = set(LABEL_SCHEMA["derivedModelErrors"])
    assert human.isdisjoint(derived)
    assert "OCR_HALLUCINATION" in derived and "OCR_HALLUCINATION" not in human
    assert all(entry["labeledByHumans"] is False for entry in LABEL_SCHEMA["derivedModelErrors"].values())
    for group in ("visibleTextClasses", "riskPositiveClasses", "sceneNativeClasses", "artifactClasses"):
        assert set(LABEL_SCHEMA[group]) <= human, group
    assert set(LABEL_SCHEMA["primaryLabelPrecedence"]) == human - {"UNCERTAIN"}


def test_model_errors_are_derived_from_label_and_output():
    report = evaluate_fixture_outputs(FIXTURES)
    for row in report["rows"]:
        fixture = next(f for f in FIXTURES["fixtures"] if f["id"] == row["id"])
        assert row["derivedModelError"] == fixture.get("expectedDerivedModelError"), row["id"]
    assert report["derivedModelErrors"] == {"OCR_HALLUCINATION": 1}


@pytest.mark.parametrize("fixture", FIXTURES["fixtures"], ids=lambda f: f["id"])
def test_current_and_shadow_actions_on_synthetic_fixtures(fixture):
    decision = _decide(fixture["ocr"])
    shadow = classify_watermark_construct_shadow(decision.evidence)
    assert decision.watermark_qa_action == fixture["expectedCurrentAction"], fixture["id"]
    assert shadow["shadowWatermarkAction"] == fixture["expectedShadowAction"], fixture["id"]


def test_known_positive_is_reachable_by_both_policies():
    fixture = next(f for f in FIXTURES["fixtures"] if f["id"] == "overlay_watermark_repeated_corners")
    decision = _decide(fixture["ocr"])
    shadow = classify_watermark_construct_shadow(decision.evidence)
    assert decision.watermark_qa_action == "reject"
    assert shadow["shadowWatermarkAction"] == "reject"
    assert shadow["shadowWatermarkClass"] == "repeated_overlay_text"


def test_shadow_differs_from_live_only_where_h1_says_it_should():
    """Every diff must be fragmented text outside overlay geometry, reviewed by
    live and allowed by shadow. Anything else is an unintended change."""

    for fixture in FIXTURES["fixtures"]:
        decision = _decide(fixture["ocr"])
        shadow = classify_watermark_construct_shadow(decision.evidence)
        if decision.watermark_qa_action == shadow["shadowWatermarkAction"]:
            continue
        regions = decision.evidence["regionEvidence"]
        assert decision.watermark_qa_action == "review", fixture["id"]
        assert shadow["shadowWatermarkAction"] == "allow", fixture["id"]
        assert all(r["textQuality"] == "implausible" for r in regions), fixture["id"]
        assert not any(r["overlayLike"] for r in regions), fixture["id"]


def test_shadow_replay_agrees_with_evidence_replay_except_h1():
    for fixture in FIXTURES["fixtures"]:
        decision = _decide(fixture["ocr"])
        shadow = classify_watermark_construct_shadow(decision.evidence)
        # evidence replay reproduces the live action exactly
        assert shadow["evidenceReplayWatermarkAction"] == decision.watermark_qa_action, fixture["id"]


def test_evaluator_reports_the_synthetic_construct_honestly():
    report = evaluate_fixture_outputs(FIXTURES)
    assert report["scope"].startswith("synthetic known-positive")
    assert "not Florence recall" in report["scope"]
    assert "realPositiveCaught" not in report and "benignFlagged" not in report
    # two synthetic known-positive rows are missed by BOTH policies; H1 does not touch them
    known = report["syntheticKnownPositiveFlagged"]
    assert known["current"] == known["shadow"] == {"n": 4, "flagged": 2}
    native = report["syntheticSceneNativeFlagged"]
    assert native["current"] == {"n": 8, "flagged": 3}
    assert native["shadow"] == {"n": 8, "flagged": 0}


# ---------------------------------------------------------------------------
# 4. Shadow isolation
# ---------------------------------------------------------------------------

BASE_SIGNALS = {
    "adultLike": True,
    "brandFit": True,
    "cropConsistent": True,
    "cropIsolationQuality": "pass",
    "faceSimilarityReliable": True,
    "faceSimilarityScore": 0.10,
    "childlikeScore": 0.05,
    "beautificationScore": 0.05,
    "localSafetyRiskAvailability": "available",
}

DECISION_FIELDS = (
    "previewAllowed",
    "requiresHumanReview",
    "rejectReasons",
    "reviewReasons",
    "watermarkQaAction",
    "textLogoWatermarkRisk",
    "logoTextWatermarkRisk",
)


@pytest.mark.parametrize("fixture", FIXTURES["fixtures"], ids=lambda f: f["id"])
def test_shadow_changes_no_effective_decision(fixture):
    signals = {}
    _add_visual_signals(signals, _analyze(fixture["ocr"]), image_size=IMAGE_SIZE)
    assert "shadowWatermark" in signals
    with_shadow = build_avatar_qa_from_signals({**BASE_SIGNALS, **signals}, thresholds=AvatarQAThresholds())
    without = {key: value for key, value in signals.items() if key != "shadowWatermark"}
    baseline = build_avatar_qa_from_signals({**BASE_SIGNALS, **without}, thresholds=AvatarQAThresholds())
    for field in DECISION_FIELDS:
        assert getattr(with_shadow, field) == getattr(baseline, field), (fixture["id"], field)
    assert with_shadow.debug.get("watermarkDecisionClass") == baseline.debug.get("watermarkDecisionClass")


def test_shadow_does_not_touch_region_confidence():
    fixture = FIXTURES["fixtures"][0]
    analysis = _analyze(fixture["ocr"])
    before = [region.confidence for region in analysis.regions]
    decision = evaluate_watermark_risk(analysis.regions, image_size=IMAGE_SIZE)
    classify_watermark_construct_shadow(decision.evidence)
    assert [region.confidence for region in analysis.regions] == before


def test_shadow_is_persisted_and_marked_unconsumed():
    fixture = next(f for f in FIXTURES["fixtures"] if f["id"] == "garment_text_fragmented")
    signals = {}
    _add_visual_signals(signals, _analyze(fixture["ocr"]), image_size=IMAGE_SIZE)
    result = build_avatar_qa_from_signals({**BASE_SIGNALS, **signals}, thresholds=AvatarQAThresholds())
    block = result.debug["measurements"]["shadowWatermark"]
    assert block["consumedByPolicy"] is False
    assert block["policyVersion"] == WATERMARK_CONSTRUCT_SHADOW_VERSION
    assert block["shadowWatermarkAction"] == "allow"
    assert block["evidenceReplayWatermarkAction"] == "review"
    assert block["agreesWithEvidenceReplay"] is False
    # and the effective decision is still the live one
    assert result.watermarkQaAction == "review"


def test_legacy_or_malformed_evidence_yields_no_shadow():
    assert classify_watermark_construct_shadow(None) is None
    assert classify_watermark_construct_shadow({"regionEvidence": []}) is None
    assert classify_watermark_construct_shadow(
        {"schemaVersion": "watermark_evidence_v2", "regionEvidence": []}
    ) is None
    assert classify_watermark_construct_shadow(
        _evidence({"kind": "text", "confidenceBand": "made-up"})
    ) is None


# ---------------------------------------------------------------------------
# 5. Privacy
# ---------------------------------------------------------------------------


def test_no_transcription_reaches_the_shadow_or_its_persisted_form():
    transcriptions = {label for f in FIXTURES["fixtures"] for label in f["ocr"]["labels"]}
    for fixture in FIXTURES["fixtures"]:
        signals = {}
        _add_visual_signals(signals, _analyze(fixture["ocr"]), image_size=IMAGE_SIZE)
        result = build_avatar_qa_from_signals({**BASE_SIGNALS, **signals}, thresholds=AvatarQAThresholds())
        serialized = json.dumps(result.debug["measurements"].get("shadowWatermark", {}))
        for text in transcriptions:
            assert text not in serialized, (fixture["id"], text)


def test_sanitizer_drops_anything_outside_the_vocabulary():
    poisoned = {
        "policyVersion": WATERMARK_CONSTRUCT_SHADOW_VERSION,
        "shadowWatermarkClass": "garment_zone_text",
        "shadowWatermarkAction": "allow",
        "evidenceReplayWatermarkAction": "review",
        "regionClassCounts": {"garment_zone_text": 1, "SECRET TEXT": 3},
        "hypotheses": ["H1_fragmented_text_requires_overlay_geometry", "rawText: SECRET"],
        "rawText": "SECRET TEXT",
        "labels": ["SECRET TEXT"],
        "bbox": [1, 2, 3, 4],
    }
    clean = sanitize_watermark_construct_shadow(poisoned)
    assert "SECRET" not in json.dumps(clean)
    assert set(clean) <= {
        "policyVersion", "consumedByPolicy", "shadowWatermarkClass", "shadowWatermarkAction",
        "inputSchemaVersion", "evidenceReplayWatermarkAction", "agreesWithEvidenceReplay",
        "regionClassCounts", "hypotheses",
    }
    assert set(clean["regionClassCounts"]) <= SHADOW_CLASSES
    # a class outside the vocabulary rejects the whole block
    assert sanitize_watermark_construct_shadow({**poisoned, "shadowWatermarkClass": "NIKE"}) == {}


# ---------------------------------------------------------------------------
# 6. Job-level replay tooling
# ---------------------------------------------------------------------------


def _candidate_doc(job_id, fixture_id, status="needs_review"):
    fixture = next(f for f in FIXTURES["fixtures"] if f["id"] == fixture_id)
    signals = {}
    _add_visual_signals(signals, _analyze(fixture["ocr"]), image_size=IMAGE_SIZE)
    result = build_avatar_qa_from_signals({**BASE_SIGNALS, **signals}, thresholds=AvatarQAThresholds())
    qa = result.to_dict() if hasattr(result, "to_dict") else dict(vars(result))
    return {"jobId": job_id, "status": status, "qa": qa}


def test_replay_reports_job_level_effect_and_safety_invariant():
    documents = [
        _candidate_doc("job-a", "garment_text_fragmented"),
        _candidate_doc("job-a", "overlay_watermark_repeated_corners", status="rejected"),
        _candidate_doc("job-b", "background_sign_plausible"),
    ]
    report = replay_candidate_documents(documents, allow_soft_review=False)
    assert report["candidatesEvaluated"] == 3
    assert report["evidenceReplayParityMismatches"] == 0
    assert report["newlyEligibleWithRejectReasons"] == 0
    assert report["jobs"] == 2
    assert set(report["jobEligibleDistribution"]) == {"current", "shadow"}
