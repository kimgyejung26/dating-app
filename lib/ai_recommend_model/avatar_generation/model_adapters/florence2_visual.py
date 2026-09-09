from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Sequence, Tuple

from avatar_generation.analysis.visual_risk import (
    TASK_MORE_DETAILED_CAPTION,
    TASK_OCR_WITH_REGION,
    TASK_OD,
    VisualRiskAnalysis,
    analyze_florence_visual_risk_outputs,
    unavailable_visual_risk_analysis,
)

ProcessorFactory = Callable[..., Any]
ModelFactory = Callable[..., Any]


class Florence2VisualRiskAdapter:
    provider = "florence2"

    def __init__(
        self,
        model_id: str = "microsoft/Florence-2-large-ft",
        *,
        device: Optional[str] = None,
        torch_dtype: Optional[Any] = None,
        include_detailed_caption: bool = False,
        local_files_only: bool = True,
        processor_factory: Optional[ProcessorFactory] = None,
        model_factory: Optional[ModelFactory] = None,
    ) -> None:
        self.model_id = model_id
        self.device = device
        self.torch_dtype = torch_dtype
        self.include_detailed_caption = include_detailed_caption
        self.local_files_only = local_files_only
        self._processor_factory = processor_factory
        self._model_factory = model_factory
        self._processor: Any = None
        self._model: Any = None

    def analyze(
        self,
        image: Any,
        *,
        primary_face_bbox_xyxy: Optional[Sequence[float]] = None,
    ) -> VisualRiskAnalysis:
        try:
            outputs = self.detect(image)
            image_size = _image_size(image)
        except Exception:
            return unavailable_visual_risk_analysis(
                self.provider,
                error_code="florence2_inference_unavailable",
            )
        return analyze_florence_visual_risk_outputs(
            outputs,
            provider=self.provider,
            image_size=image_size,
            primary_face_bbox_xyxy=primary_face_bbox_xyxy,
        )

    def detect(self, image: Any) -> Dict[str, Any]:
        self._ensure_loaded()
        tasks = [TASK_OCR_WITH_REGION, TASK_OD]
        if self.include_detailed_caption:
            tasks.append(TASK_MORE_DETAILED_CAPTION)
        return {task: self._run_task(image, task) for task in tasks}

    def _ensure_loaded(self) -> None:
        if self._processor is not None and self._model is not None:
            return
        processor_factory, model_factory = self._factories()
        common_kwargs = {"local_files_only": self.local_files_only}
        model_kwargs: Dict[str, Any] = dict(common_kwargs)
        if self.torch_dtype is not None:
            model_kwargs["torch_dtype"] = self.torch_dtype
        self._processor = processor_factory(self.model_id, **common_kwargs)
        self._model = model_factory(self.model_id, **model_kwargs)
        if self.device:
            self._model = self._model.to(self.device)

    def _factories(self) -> Tuple[ProcessorFactory, ModelFactory]:
        if self._processor_factory is not None and self._model_factory is not None:
            return self._processor_factory, self._model_factory
        from transformers import (  # type: ignore
            Florence2ForConditionalGeneration,
            Florence2Processor,
        )

        return (
            Florence2Processor.from_pretrained,
            Florence2ForConditionalGeneration.from_pretrained,
        )

    def _run_task(self, image: Any, task: str) -> Any:
        inputs = self._processor(text=task, images=image, return_tensors="pt")
        if self.device and hasattr(inputs, "to"):
            inputs = inputs.to(self.device)
        base_kwargs = {
            "input_ids": inputs["input_ids"],
            "pixel_values": inputs["pixel_values"],
            "max_new_tokens": NUM_MAX_NEW_TOKENS,
            "num_beams": NUM_BEAMS,
        }
        scored = True
        try:
            # Beam search already computes a sequence score. Asking for it costs
            # nothing and is the only way OCR evidence can ever carry a real
            # confidence; today every watermark decision reads "unknown".
            generated = self._model.generate(
                **base_kwargs,
                return_dict_in_generate=True,
                output_scores=True,
            )
        except TypeError:
            # A runtime that rejects the scoring kwargs must still produce OCR.
            # analyze() swallows exceptions into an unavailable analysis, so
            # letting this propagate would downgrade every candidate over a
            # telemetry nicety.
            scored = False
            generated = self._model.generate(**base_kwargs)
        generated_ids = getattr(generated, "sequences", generated)
        generated_text = self._processor.batch_decode(
            generated_ids,
            skip_special_tokens=False,
        )[0]
        parsed = self._processor.post_process_generation(
            generated_text,
            task=task,
            image_size=_image_size(image),
        )
        return _attach_shadow_ocr_evidence(
            parsed,
            task,
            generated if scored else None,
            generated_ids,
            self._length_penalty(),
        )

    def _length_penalty(self) -> Optional[float]:
        config = getattr(self._model, "generation_config", None)
        value = getattr(config, "length_penalty", None)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


def _image_size(image: Any) -> Tuple[int, int]:
    if hasattr(image, "size") and isinstance(image.size, tuple) and len(image.size) == 2:
        return (int(image.size[0]), int(image.size[1]))
    return (int(image.width), int(image.height))


NUM_BEAMS = 3
NUM_MAX_NEW_TOKENS = 1024
SHADOW_OCR_SCORE_SOURCE = "florence_beam_sequence_score"
SHADOW_OCR_EVIDENCE_KEY = "shadowOcrEvidence"


def _raw_sequence_score(generated: Any) -> Optional[float]:
    scores = getattr(generated, "sequences_scores", None)
    if scores is None:
        return None
    try:
        raw = float(scores[0])
    except (TypeError, ValueError, IndexError):
        return None
    if raw != raw:  # NaN
        return None
    return raw


def _output_token_count(generated_ids: Any) -> Optional[int]:
    try:
        return int(len(generated_ids[0]))
    except (TypeError, ValueError, IndexError):
        return None


def _attach_shadow_ocr_evidence(
    parsed: Any,
    task: str,
    generated: Any,
    generated_ids: Any,
    length_penalty: Optional[float],
) -> Any:
    """Record the OCR score as telemetry, never as decision confidence.

    The parser turns a "scores" key into VisualRiskRegion.confidence, which the
    watermark policy reads directly, so writing there would change decisions --
    including enabling a hard-reject branch that has never been reachable. This
    keeps the score in its own namespace instead.

    It is a beam-search sequence log-probability for the whole generated string,
    not a per-region OCR probability, so it is stored raw and marked
    uncalibrated. It is attributed to a region only when the model emitted
    exactly one; otherwise the scope says so.
    """

    if task != TASK_OCR_WITH_REGION or not isinstance(parsed, dict):
        return parsed
    payload = parsed.get(task)
    if not isinstance(payload, dict):
        return parsed

    labels = payload.get("labels") or []
    region_count = len(labels)
    shadow: Dict[str, Any] = {
        "scoreSource": SHADOW_OCR_SCORE_SOURCE,
        "scoreCalibrated": False,
        "generationMode": "beam_search",
        "numBeams": NUM_BEAMS,
        "regionCount": region_count,
        "attributionScope": "single_region" if region_count == 1 else "whole_sequence",
    }
    if length_penalty is not None:
        shadow["lengthPenalty"] = length_penalty
    token_count = _output_token_count(generated_ids)
    if token_count is not None:
        shadow["outputTokenCount"] = token_count

    if generated is None:
        shadow["scoreAvailable"] = False
        shadow["scoreUnavailableReason"] = "scores_not_supported_by_runtime"
    else:
        raw = _raw_sequence_score(generated)
        if raw is None:
            shadow["scoreAvailable"] = False
            shadow["scoreUnavailableReason"] = "sequence_score_missing"
        else:
            shadow["scoreAvailable"] = True
            shadow["rawSequenceScore"] = raw

    payload[SHADOW_OCR_EVIDENCE_KEY] = shadow
    return parsed
