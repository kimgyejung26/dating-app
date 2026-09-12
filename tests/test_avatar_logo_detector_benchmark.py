"""CI tests for the B3-L5 logo-detector benchmark. No model download, no inference, no image."""

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import avatar_florence_ceiling as bench  # noqa: E402
import avatar_logo_detector_benchmark as logo  # noqa: E402


def _row(detector, domain, condition, truth, detections, seconds=1.0):
    return logo._row(detector, domain, condition, truth, detections, seconds)


def test_candidates_are_pinned_and_licensed():
    assert 2 <= len(logo.CANDIDATES) <= 3
    for name, spec in logo.CANDIDATES.items():
        assert len(spec["revision"]) == 40 and all(c in "0123456789abcdef" for c in spec["revision"])
        assert spec["license"] == "apache-2.0"
        assert spec["repo"].count("/") == 1
        assert spec["kind"] in {"owl", "gdino"}


def test_prompts_are_generic_and_carry_no_brand():
    assert logo.PROMPTS == ("a logo", "a watermark", "a brand emblem", "a graphic symbol")
    for prompt in logo.PROMPTS:
        assert prompt.islower()


def test_ground_truth_matching_uses_the_b3l4_rule():
    truth = [[100.0, 100.0, 200.0, 200.0]]
    hit = _row("d", bench.DOMAIN_AVATAR, "A8", truth, [{"box": [101.0, 101.0, 199.0, 199.0], "score": 0.9, "label": "a logo"}])
    assert hit["imageHit"] and hit["gtBoxHits"] == 1 and hit["bestIous"][0] > 0.9
    miss = _row("d", bench.DOMAIN_AVATAR, "A8", truth, [{"box": [0.0, 0.0, 20.0, 20.0], "score": 0.9, "label": "a logo"}])
    assert miss["imageHit"] is False and miss["gtBoxHits"] == 0
    assert logo.IOU_MATCH == bench.IOU_MATCH == 0.3


def test_clean_conditions_have_no_ground_truth_and_are_not_scored_as_errors():
    clean = _row("d", bench.DOMAIN_AVATAR, "A0", [], [{"box": [1.0, 1.0, 9.0, 9.0], "score": 0.5, "label": "a logo"}])
    assert clean["gtBoxCount"] == 0 and clean["imageHit"] is False
    report = logo.aggregate([clean], {})
    block = report["detectors"]["d"][bench.DOMAIN_AVATAR]
    assert block["cleanImageRegionResponseRate"]["label"] == "CLEAN_IMAGE_REGION_RESPONSE_RATE"
    assert block["cleanImageRegionResponseRate"]["imagesWithAnyDetection"] == 1
    assert block["injected"]["imageHitRate"] is None
    text = json.dumps(report).lower()
    for word in ("false_positive", "false positive", "precision", "hallucination"):
        assert word not in text


def test_aggregation_separates_detectors_and_domains():
    rows = [
        _row("a", bench.DOMAIN_SOURCE, "V8", [[10.0, 10.0, 50.0, 50.0]], [{"box": [10.0, 10.0, 50.0, 50.0], "score": 0.8, "label": "a logo"}]),
        _row("a", bench.DOMAIN_AVATAR, "A8", [[10.0, 10.0, 50.0, 50.0]], []),
        _row("b", bench.DOMAIN_AVATAR, "A8", [[10.0, 10.0, 50.0, 50.0]], [{"box": [12.0, 12.0, 52.0, 52.0], "score": 0.4, "label": "a watermark"}]),
    ]
    report = logo.aggregate(rows, {"a": {"license": "apache-2.0"}, "b": {"license": "apache-2.0"}})
    assert report["detectors"]["a"][bench.DOMAIN_SOURCE]["injected"]["boxRecall"] == 1.0
    assert report["detectors"]["a"][bench.DOMAIN_AVATAR]["injected"]["boxRecall"] == 0.0
    assert report["detectors"]["b"][bench.DOMAIN_AVATAR]["injected"]["imageHitRate"] == 1.0


def test_report_is_privacy_clean_and_free_of_raw_identifiers():
    rows = [_row("a", bench.DOMAIN_AVATAR, "A8", [[1.0, 2.0, 3.0, 4.0]], [{"box": [1.0, 2.0, 3.0, 4.0], "score": 0.7, "label": "P98_C97.png"}])]
    report = logo.aggregate(rows, {"a": {"license": "apache-2.0"}})
    assert not bench.privacy_violations(report)
    assert "P98_C97" not in json.dumps(report)


def test_benchmark_never_persists_images_or_crops():
    source = (SCRIPTS / "avatar_logo_detector_benchmark.py").read_text(encoding="utf-8")
    assert ".save(" not in source
    assert "write_bytes" not in source
    assert "crop(" not in source
    for forbidden in ("requests.post", "upload", "azure", "openai"):
        assert forbidden not in source.lower()


def test_offline_is_forced_and_originals_are_verified():
    source = (SCRIPTS / "avatar_logo_detector_benchmark.py").read_text(encoding="utf-8")
    assert 'os.environ.setdefault("HF_HUB_OFFLINE", "1")' in source
    assert "local_files_only=True" in source
    assert "ORIGINALS_CHANGED" in source
    assert "BLOCKED_G004_" in source


def test_control_ground_truth_matches_the_pr114_generator():
    """ctl-08's logo box is the control generator's own ellipse box."""

    assert logo.CTL08_GROUND_TRUTH == [424.0, 16.0, 496.0, 88.0]
    import avatar_watermark_controls as controls

    source = Path(controls.__file__).read_text(encoding="utf-8")
    assert "draw.ellipse([424, 16, 496, 88]" in source


def test_large_images_are_downscaled_before_injection():
    """Pre-registered: long side capped, ground truth scales with the image."""

    assert logo.MAX_LONG_SIDE == 2048
    source = (SCRIPTS / "avatar_logo_detector_benchmark.py").read_text(encoding="utf-8")
    assert "if max(base.size) > MAX_LONG_SIDE:" in source
    assert "Image.LANCZOS" in source
    # Ground truth comes from render() on the already-downscaled base, so a mark
    # injected at a relative position stays inside the image at either size.
    import avatar_watermark_controls as controls

    base = controls.build_controls()[8][1]
    small = base.resize((base.width // 2, base.height // 2))
    _, truth = bench.render(small, bench.spec_for("V8"))
    assert truth and truth[0]["box"][2] <= small.width and truth[0]["box"][3] <= small.height
