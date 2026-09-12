"""CI tests for the B3-L4 Florence ceiling benchmark. No model, no user image."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import avatar_florence_ceiling as bench  # noqa: E402
import avatar_florence_ceiling_run as runner  # noqa: E402
import avatar_watermark_controls as controls  # noqa: E402
from avatar_generation.analysis import watermark  # noqa: E402

SENTINEL = "ZQXSENTINELTEXT"


def _entries(src=8, avatar=20):
    return [{"opaqueId": f"g004-src-{i:03d}", "domain": bench.DOMAIN_SOURCE} for i in range(1, src + 1)] + [
        {"opaqueId": f"g004-avatar-{i:03d}", "domain": bench.DOMAIN_AVATAR} for i in range(1, avatar + 1)
    ]


def _base():
    return controls.build_controls()[8][1]  # ctl-09: synthetic, no text


def _record(variant, domain=bench.DOMAIN_AVATAR, labels=None, quads=None, od=None, phase="core"):
    image, truth = bench.render(_base(), bench.spec_for(variant))
    if quads is None:
        quads = [[b["box"][0], b["box"][1], b["box"][2], b["box"][1], b["box"][2], b["box"][3], b["box"][0], b["box"][3]] for b in truth]
    if labels is None:
        labels = [b["text"] or "" for b in truth]
    return {
        "conditionId": f"x:{variant}",
        "domain": domain,
        "baseOpaqueId": "x",
        "variant": variant,
        "phase": phase,
        "imageSize": list(image.size),
        "groundTruth": truth,
        "tasks": {
            bench.TASK_OCR_WITH_REGION: {bench.TASK_OCR_WITH_REGION: {"quad_boxes": quads, "labels": labels}},
            bench.TASK_OD: {bench.TASK_OD: od or {"bboxes": [], "labels": []}},
        },
        "latencySec": {"ocr": 1.0, "od": 1.0, "combined": 2.0},
    }


# A. both authorized set counts validated
def test_plan_requires_exact_authorized_counts():
    plan = bench.build_plan(_entries(), ["ctl-01"])
    assert sum(1 for c in plan if c["phase"] == "raw") == 28
    with pytest.raises(ValueError):
        bench.build_plan(_entries(src=7), [])
    with pytest.raises(ValueError):
        bench.build_plan(_entries(avatar=19), [])


def test_runner_blocks_on_count_mismatch(tmp_path):
    entries = [dict(e, path="unused") for e in _entries(src=5)]
    (tmp_path / "restricted_manifest.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")
    with pytest.raises(SystemExit, match="BLOCKED_G004_SOURCE_SET_COUNT_5"):
        runner._load_manifest(tmp_path)


# B/C. originals never overwritten (render never mutates its input)
def test_render_never_mutates_base():
    base = _base()
    before = base.tobytes()
    for spec in bench.CORE_VARIANTS + bench.curve_specs():
        image, _ = bench.render(base, spec)
        assert image is not base
    assert base.tobytes() == before


# D. derivatives go to scratch only: the runner has no image write path at all
def test_runner_never_persists_images():
    source = (SCRIPTS / "avatar_florence_ceiling_run.py").read_text(encoding="utf-8")
    assert ".save(" not in source
    assert "write_bytes" not in source


# E. ground truth deterministic
def test_plan_and_render_deterministic():
    a = bench.build_plan(_entries(), ["ctl-01", "ctl-02"])
    b = bench.build_plan(_entries(), ["ctl-02", "ctl-01"][::-1])
    assert bench.plan_digest(a) == bench.plan_digest(b)
    for spec in bench.CORE_VARIANTS:
        first, truth_a = bench.render(_base(), spec)
        second, truth_b = bench.render(_base(), spec)
        assert first.tobytes() == second.tobytes() and truth_a == truth_b


def test_vocabulary_is_fixed():
    texts = {spec.text for spec in bench.CORE_VARIANTS + bench.curve_specs() if spec.text}
    assert texts <= set(bench.VOCABULARY)


# F. domain field mandatory
def test_domain_is_mandatory():
    with pytest.raises(KeyError):
        bench.build_plan([{"opaqueId": "g004-src-001"}], [])
    record = _record("V1")
    del record["domain"]
    with pytest.raises(KeyError):
        bench.score_condition(record)


# G. raw filenames / paths / hashes excluded
@pytest.mark.parametrize(
    "leak",
    ["P98_C97", "participant-98", "C:\\Users\\x\\a.png", "photo.jpg", "a" * 64, "data:image/png;base64,AAAA"],
)
def test_privacy_guard_rejects_identifiers(leak):
    assert bench.privacy_violations({"x": leak})


# H. OCR text excluded from rows and report
def test_ocr_text_never_reaches_rows_or_report():
    record = _record("V1", labels=[SENTINEL])
    row = bench.score_condition(record)
    report = bench.aggregate([row])
    assert SENTINEL not in json.dumps(row)
    assert SENTINEL not in json.dumps(report)
    assert not bench.privacy_violations(report, [SENTINEL])
    assert bench.privacy_violations({"leak": SENTINEL}, [SENTINEL])


# I. Florence parser regression
def test_parser_boxes_and_transcription():
    row = bench.score_condition(_record("V1"))
    assert row["gtBestIous"] == [1.0] and row["ocrImageHit"]
    assert row["transcriptionExactCount"] == 1 and row["cerMean"] == 0.0
    miss = bench.score_condition(_record("V1", labels=[], quads=[]))
    assert miss["ocrImageHit"] is False and miss["cerMean"] == 1.0
    tiled = bench.score_condition(_record("V4"))
    assert tiled["gtBoxCount"] == 12 and tiled["gtBoxHits"] == 12
    assert bench.normalize_transcription("n e-w!") == "NEW"


# J. model miss vs policy miss
def test_model_miss_vs_policy_miss():
    assert bench.classify_miss({"riskPositive": True, "ocrImageHit": False}, "currentAction") == "MODEL_MISS"
    assert bench.classify_miss({"riskPositive": True, "ocrImageHit": True, "currentAction": "allow"}, "currentAction") == "POLICY_MISS"
    assert bench.classify_miss({"riskPositive": True, "ocrImageHit": True, "currentAction": "review"}, "currentAction") is None
    assert bench.classify_miss({"riskPositive": False, "ocrImageHit": False}, "currentAction") is None
    logo = {"riskPositive": True, "logoLikePresent": True, "ocrImageHit": False, "odImageHit": True, "currentAction": "allow"}
    assert bench.classify_miss(logo, "currentAction") == "POLICY_MISS"


# K. H1 decision-neutral; L. current policy unchanged
def test_h1_is_shadow_only_and_live_policy_unchanged():
    assert watermark.WATERMARK_POLICY_VERSION == "watermark_policy_v4_runtime_evidence_parity_v1"
    fragmented_center = bench.score_condition(_record("V7"))
    assert fragmented_center["currentAction"] == "review"
    assert fragmented_center["h1Action"] == "allow"
    repeated = bench.score_condition(_record("V4"))
    assert repeated["currentAction"] == "reject" and repeated["h1Action"] == "reject"
    source = (SCRIPTS / "avatar_florence_ceiling.py").read_text(encoding="utf-8")
    assert "worker" not in source.split('"""', 2)[2].split("import")[0]
    for forbidden in ("previewAllowed", "rejectReasons", "reviewReasons", "firestore", "google.cloud"):
        assert forbidden not in source


# M. existing B3 controls untouched and included
def test_existing_b3_controls_are_included_unchanged():
    ids = [spec.evaluation_id for spec, _ in controls.build_controls()]
    assert ids == [f"ctl-{i:02d}" for i in range(1, 11)]
    assert controls.GENERATOR_VERSION == "avatar_watermark_controls_v1"
    plan = bench.build_plan(_entries(), ids)
    assert [c["conditionId"] for c in plan if c["domain"] == bench.DOMAIN_SYNTHETIC] == ids


# N. cross-domain aggregation
def test_cross_domain_delta_and_separation():
    source_hit = bench.score_condition(_record("V2", domain=bench.DOMAIN_SOURCE))
    avatar_miss = bench.score_condition(_record("V2", labels=[], quads=[]))
    report = bench.aggregate([source_hit, avatar_miss])
    delta = report["crossDomainDelta"]["V2"]["boxRecall"]
    assert delta == {"source": 1.0, "avatar": 0.0, "deltaAvatarMinusSource": -1.0}
    assert report["domains"][bench.DOMAIN_SOURCE]["regionRecallByVariant"]["V2"]["boxRecall"] == 1.0
    assert report["domains"][bench.DOMAIN_AVATAR]["regionRecallByVariant"]["A2"]["boxRecall"] == 0.0
    assert report["domains"][bench.DOMAIN_AVATAR]["modelMissByVariant"]["A2"] == 1


def test_clean_distribution_uses_unlabeled_vocabulary():
    raw = bench.score_condition(_record("V0", phase="raw"))
    report = bench.aggregate([raw])
    clean = report["domains"][bench.DOMAIN_AVATAR]["rawClean"]
    assert clean["label"] == "OBSERVED_RESPONSE_DISTRIBUTION"
    text = json.dumps(clean).lower()
    for word in ("precision", "recall", "hallucination", "false_positive"):
        assert word not in text
