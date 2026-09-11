"""Florence OCR score, recorded as telemetry and nothing else.

Every watermark decision in production read confidenceBand "unknown". That is
not Florence withholding a score: _run_task called generate() without
return_dict_in_generate/output_scores, so beam search computed a sequence score
and the adapter discarded it.

Feeding that score into VisualRiskRegion.confidence would not be shadow. On one
fixed image, only the score differing, the current policy returns:

    None -> allow      0.30 -> review      0.70 -> review      0.97 -> reject

so wiring it into the decision path would silently enable a hard-reject branch
that has never been reachable in production. The score therefore lands in its
own telemetry namespace, and these tests pin that it changes no decision.

The score is also not a calibrated OCR probability. It is a beam-search
sequence log-probability for the whole generated string, so it is recorded raw,
with its generation parameters, and marked uncalibrated.
"""

import importlib.util
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE = REPO_ROOT / "lib" / "ai_recommend_model" / "avatar_generation"
VISUAL_RISK_PATH = BASE / "analysis" / "visual_risk.py"
WATERMARK_PATH = BASE / "analysis" / "watermark.py"
ADAPTER_PATH = BASE / "model_adapters" / "florence2_visual.py"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Real package, not ModuleType stubs: see test_avatar_visual_risk.py. The
# watermark module used to be re-executed under the private name
# avatar_generation.analysis.watermark_shadow, giving a second copy of the
# policy module that nothing else in the process used.
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))
import avatar_generation.analysis.visual_risk as visual_risk  # noqa: E402
import avatar_generation.analysis.watermark as watermark  # noqa: E402
florence2_visual = _load_module("florence2_visual_shadow_under_test", ADAPTER_PATH)

TASK_OCR_WITH_REGION = visual_risk.TASK_OCR_WITH_REGION
TASK_OD = visual_risk.TASK_OD
Florence2VisualRiskAdapter = florence2_visual.Florence2VisualRiskAdapter
evaluate_watermark_risk = watermark.evaluate_watermark_risk
analyze_florence_visual_risk_outputs = visual_risk.analyze_florence_visual_risk_outputs

ONE_REGION = ([[11, 13, 41, 13, 41, 29, 11, 29]], ["METALLICA"])
TWO_REGIONS = (
    [[11, 13, 41, 13, 41, 29, 11, 29], [80, 90, 110, 90, 110, 104, 80, 104]],
    ["METALLICA", "a l"],
)


class _FakeImage:
    size = (200, 200)


class _FakeSequences:
    def __init__(self, sequences, sequences_scores):
        self.sequences = sequences
        self.sequences_scores = sequences_scores


class _FakeProcessor:
    def __init__(self, regions):
        self._regions = regions

    def __call__(self, text=None, images=None, return_tensors=None):
        return {"input_ids": [[1]], "pixel_values": [[0.0]]}

    def batch_decode(self, ids, skip_special_tokens=False):
        return ["<decoded>"]

    def post_process_generation(self, text, task=None, image_size=None):
        quads, labels = self._regions
        return {task: {"quad_boxes": list(quads), "labels": list(labels)}}


class _FakeModel:
    def __init__(self, score, accept_scoring=True):
        self.score = score
        self.accept_scoring = accept_scoring
        self.last_kwargs = None

    def generate(self, **kwargs):
        if not self.accept_scoring and (
            "return_dict_in_generate" in kwargs or "output_scores" in kwargs
        ):
            raise TypeError("unexpected keyword argument")
        self.last_kwargs = kwargs
        if kwargs.get("return_dict_in_generate"):
            return _FakeSequences([[1, 2, 3, 4]], [self.score])
        return [[1, 2, 3, 4]]


def _payload(regions, score, accept_scoring=True):
    model = _FakeModel(score, accept_scoring=accept_scoring)
    adapter = Florence2VisualRiskAdapter(
        processor_factory=lambda *a, **k: _FakeProcessor(regions),
        model_factory=lambda *a, **k: model,
    )
    adapter._ensure_loaded()
    parsed = adapter._run_task(_FakeImage(), TASK_OCR_WITH_REGION)
    return parsed[TASK_OCR_WITH_REGION], model


def test_generation_is_asked_for_the_score_it_already_computes():
    _, model = _payload(ONE_REGION, -0.21)
    assert model.last_kwargs.get("return_dict_in_generate") is True
    assert model.last_kwargs.get("output_scores") is True


def test_score_never_lands_in_the_decision_confidence_field():
    payload, _ = _payload(ONE_REGION, -0.21)
    assert "scores" not in payload, "scores feeds VisualRiskRegion.confidence"
    assert "confidences" not in payload


def test_shadow_evidence_records_uncalibrated_provenance():
    payload, _ = _payload(ONE_REGION, -0.21)
    shadow = payload.get("shadowOcrEvidence")
    assert shadow is not None
    assert shadow["scoreSource"] == "florence_beam_sequence_score"
    assert shadow["scoreCalibrated"] is False
    assert shadow["rawSequenceScore"] == -0.21
    assert shadow["numBeams"] == 3
    assert shadow["generationMode"] == "beam_search"
    assert shadow["regionCount"] == 1
    assert shadow["attributionScope"] == "single_region"
    assert shadow["outputTokenCount"] == 4


def test_multiple_regions_are_recorded_as_unattributable():
    payload, _ = _payload(TWO_REGIONS, -0.21)
    shadow = payload["shadowOcrEvidence"]
    assert shadow["attributionScope"] == "whole_sequence"
    assert shadow["regionCount"] == 2
    assert "scores" not in payload


def test_runtime_without_scoring_support_still_produces_ocr():
    payload, _ = _payload(ONE_REGION, -0.21, accept_scoring=False)
    assert payload["labels"] == ["METALLICA"]
    shadow = payload["shadowOcrEvidence"]
    assert shadow["scoreAvailable"] is False
    assert shadow["scoreUnavailableReason"] == "scores_not_supported_by_runtime"


def test_visual_risk_parser_ignores_shadow_evidence():
    outputs = {
        TASK_OCR_WITH_REGION: {
            TASK_OCR_WITH_REGION: {
                "quad_boxes": ONE_REGION[0],
                "labels": ONE_REGION[1],
                "shadowOcrEvidence": {
                    "rawSequenceScore": -0.21,
                    "scoreCalibrated": False,
                },
            }
        },
        TASK_OD: {TASK_OD: {"bboxes": [], "labels": []}},
    }
    analysis = analyze_florence_visual_risk_outputs(outputs, image_size=(200, 200))
    text_regions = [r for r in analysis.regions if r.kind == "text"]
    assert text_regions, "the region must still be parsed"
    assert all(
        r.confidence is None for r in text_regions
    ), "shadow telemetry must not become decision confidence"


def test_decision_is_identical_across_every_shadow_score_band():
    region = visual_risk.VisualRiskRegion(
        kind="text", bbox_xyxy=(30, 40, 90, 70), confidence=None, raw_label="xx yy"
    )
    baseline = evaluate_watermark_risk(
        [region], source_regions=[], image_size=(1024, 1536)
    )
    for raw in (-0.01, -0.21, -1.4, -6.0):
        payload, _ = _payload(ONE_REGION, raw)
        assert "scores" not in payload
        again = evaluate_watermark_risk(
            [region], source_regions=[], image_size=(1024, 1536)
        )
        assert again.watermark_qa_action == baseline.watermark_qa_action
        assert again.decision_class == baseline.decision_class
        assert again.hard_reject == baseline.hard_reject
        assert again.needs_review == baseline.needs_review
