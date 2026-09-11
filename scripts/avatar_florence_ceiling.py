"""B3-L4 Florence model-ceiling benchmark: deterministic overlay derivatives,
pre-registered conditions, and privacy-safe scoring. DECISION-NEUTRAL.

This module never opens a file and never loads a model. Callers hand it PIL
images (to render a derivative) or Florence outputs (to score one). Scoring
runs the production parser (visual_risk), the live watermark policy
(evaluate_watermark_risk) and the H1 shadow (classify_watermark_construct_shadow)
unchanged; nothing here is read by the worker.

What the numbers mean
---------------------
* Injected derivatives carry ground truth by construction, so region recall,
  IoU and transcription error are measurable -- but only for the injected
  signal. They are a MODEL CEILING on real backgrounds, never production
  prevalence, precision or recall.
* Clean images (V0) have no watermark/text/logo human label. Their output is an
  OBSERVED_RESPONSE_DISTRIBUTION: region counts, typed evidence and actions.
  Nothing on them is called correct, incorrect, a hallucination or a miss.
* Raw OCR text is consumed in-process to compute a typed match outcome and is
  never placed in a scored row or a report.

Pre-registered constants (fixed before any inference): IOU_MATCH, the variant
table, the curve design, CURVE_BASE_ORDINALS and the transcription
normalisation rule.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Optional, Sequence

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.analysis.visual_risk import (  # noqa: E402
    TASK_OCR_WITH_REGION,
    TASK_OD,
    _classify_od_label,
    _normalize_bbox,
    _quad_to_xyxy,
    _task_payload,
    analyze_florence_visual_risk_outputs,
)
from avatar_generation.analysis.watermark import evaluate_watermark_risk  # noqa: E402
from avatar_generation.analysis.watermark_construct_shadow import (  # noqa: E402
    classify_watermark_construct_shadow,
)

BENCHMARK_VERSION = "avatar_florence_ceiling_v1"

DOMAIN_SOURCE = "SOURCE_PHOTO_DOMAIN"
DOMAIN_AVATAR = "GENERATED_AVATAR_DOMAIN"
DOMAIN_SYNTHETIC = "PURE_SYNTHETIC_CONTROL_DOMAIN"
DOMAINS = (DOMAIN_SOURCE, DOMAIN_AVATAR, DOMAIN_SYNTHETIC)
REAL_DOMAINS = (DOMAIN_SOURCE, DOMAIN_AVATAR)
DOMAIN_VARIANT_PREFIX = {DOMAIN_SOURCE: "V", DOMAIN_AVATAR: "A"}

EXPECTED_COUNTS = {DOMAIN_SOURCE: 8, DOMAIN_AVATAR: 20}
OPAQUE_PREFIX = {DOMAIN_SOURCE: "g004-src", DOMAIN_AVATAR: "g004-avatar"}

BOTH_TASKS = (TASK_OCR_WITH_REGION, TASK_OD)
OCR_ONLY = (TASK_OCR_WITH_REGION,)

# Fixed synthetic vocabulary. No participant, brand, school or user text.
VOCABULARY = ("SAMPLE", "PREVIEW", "DEMO", "TEST", "ALPHA", "N E W", "A 1 X", "NO 23 ST")

IOU_MATCH = 0.3
ACTION_FLAGGED = frozenset({"review", "reject"})


@dataclass(frozen=True)
class OverlaySpec:
    variant: str
    construct: str
    text: Optional[str] = None
    anchor: str = "mm"
    at: tuple = (0.5, 0.5)
    rel_size: float = 0.0  # font height / logo diameter as a fraction of min(W, H)
    alpha: float = 1.0
    stroke: bool = False
    repeated: bool = False
    logo: bool = False
    watermark: bool = False
    risk_positive: bool = False
    expected_class: str = "NO_INJECTED_SIGNAL"
    placement_class: str = "none"
    size_class: str = "none"

    @property
    def overlay_present(self) -> bool:
        return self.construct != "clean"

    @property
    def text_present(self) -> bool:
        return self.text is not None


CORE_VARIANTS: tuple[OverlaySpec, ...] = (
    OverlaySpec("V0", "clean"),
    OverlaySpec("V1", "corner_opaque_watermark", "SAMPLE", "rd", (0.98, 0.98), 0.035, 1.0, True,
                watermark=True, risk_positive=True, expected_class="OVERLAY_WATERMARK",
                placement_class="corner", size_class="medium"),
    OverlaySpec("V2", "edge_small_watermark", "PREVIEW", "mt", (0.5, 0.02), 0.022, 1.0, True,
                watermark=True, risk_positive=True, expected_class="OVERLAY_WATERMARK",
                placement_class="edge", size_class="small"),
    OverlaySpec("V3", "transparent_watermark", "DEMO", "mm", (0.5, 0.5), 0.12, 0.35, False,
                watermark=True, risk_positive=True, expected_class="OVERLAY_WATERMARK",
                placement_class="center", size_class="large"),
    OverlaySpec("V4", "tiled_repeated_watermark", "SAMPLE", "mm", (0.5, 0.5), 0.04, 0.45, False,
                repeated=True, watermark=True, risk_positive=True, expected_class="OVERLAY_WATERMARK",
                placement_class="tiled", size_class="medium"),
    OverlaySpec("V5", "center_overlay_text", "PREVIEW", "mm", (0.5, 0.5), 0.07, 0.85, True,
                risk_positive=True, expected_class="OVERLAY_TEXT",
                placement_class="center", size_class="large"),
    OverlaySpec("V6", "fragmented_corner_text", "N E W", "ld", (0.02, 0.98), 0.035, 1.0, True,
                risk_positive=True, expected_class="FRAGMENTED_OVERLAY_TEXT",
                placement_class="corner", size_class="medium"),
    OverlaySpec("V7", "fragmented_center_text", "A 1 X", "mm", (0.5, 0.30), 0.05, 1.0, False,
                risk_positive=True, expected_class="GENERATIVE_TEXT_ARTIFACT_PROXY",
                placement_class="center", size_class="medium"),
    OverlaySpec("V8", "graphical_logo_like_mark", None, "rt", (0.98, 0.02), 0.08, 0.9,
                logo=True, risk_positive=True, expected_class="OVERLAY_LOGO",
                placement_class="corner", size_class="medium"),
    # Benign-by-construction control for H1: fragmented text in the garment zone.
    OverlaySpec("V9", "benign_fragmented_garment_text", "NO 23 ST", "mm", (0.5, 0.70), 0.04, 1.0, False,
                risk_positive=False, expected_class="BENIGN_FRAGMENTED_SCENE_TEXT",
                placement_class="garment", size_class="medium"),
)
CORE_BY_VARIANT = {spec.variant: spec for spec in CORE_VARIANTS}
OVERLAY_VARIANTS = ("V1", "V2", "V3", "V4", "V5", "V6", "V8")
ARTIFACT_VARIANTS = ("V7",)
BENIGN_VARIANTS = ("V9",)

CURVE_PLACEMENTS = {
    "corner": ("rd", (0.98, 0.98)),
    "edge": ("mt", (0.5, 0.02)),
    "center": ("mm", (0.5, 0.5)),
}
CURVE_SIZES = {"large": 0.08, "medium": 0.04, "small": 0.02}
CURVE_ALPHAS = (1.0, 0.65, 0.35, 0.15)
# Matched bases, identical in both real domains' design (4 each).
CURVE_BASE_ORDINALS = {DOMAIN_SOURCE: (1, 3, 5, 7), DOMAIN_AVATAR: (1, 6, 11, 16)}


def curve_specs() -> tuple[OverlaySpec, ...]:
    """Alpha curve at medium size + size curve at alpha 1.0, per placement."""

    specs = []
    for placement, (anchor, at) in CURVE_PLACEMENTS.items():
        grid = {("medium", alpha) for alpha in CURVE_ALPHAS} | {(size, 1.0) for size in CURVE_SIZES}
        for size, alpha in sorted(grid, key=lambda item: (list(CURVE_SIZES).index(item[0]), -item[1])):
            specs.append(
                OverlaySpec(
                    f"C-{placement}-{size}-a{int(round(alpha * 100)):03d}",
                    "curve_watermark", "SAMPLE", anchor, at, CURVE_SIZES[size], alpha, True,
                    watermark=True, risk_positive=True, expected_class="OVERLAY_WATERMARK",
                    placement_class=placement, size_class=size,
                )
            )
    return tuple(specs)


def _font(px: float) -> ImageFont.ImageFont:
    return ImageFont.load_default(size=max(8, int(round(px))))


def _tile_points(width: int, height: int) -> list[tuple[float, float]]:
    return [((col + 0.5) / 3.0 * width, (row + 0.5) / 4.0 * height) for row in range(4) for col in range(3)]


def render(base: Image.Image, spec: OverlaySpec) -> tuple[Image.Image, list[dict[str, Any]]]:
    """Deterministic derivative + ground-truth boxes (pixel xyxy). Never mutates base."""

    image = base.convert("RGB")
    if not spec.overlay_present:
        return image.copy(), []
    width, height = image.size
    ref = min(width, height)
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    alpha = int(round(255 * spec.alpha))
    boxes: list[dict[str, Any]] = []
    if spec.logo:
        diameter = int(round(spec.rel_size * ref))
        right = int(round(spec.at[0] * width))
        top = int(round(spec.at[1] * height))
        box = (right - diameter, top, right, top + diameter)
        draw.ellipse(box, fill=(250, 200, 40, alpha))
        left = box[0]
        draw.polygon(
            [
                (left + diameter * 0.5, top + diameter * 0.14),
                (left + diameter * 0.86, top + diameter * 0.8),
                (left + diameter * 0.14, top + diameter * 0.8),
            ],
            fill=(30, 30, 30, alpha),
        )
        boxes.append({"box": [float(v) for v in box], "text": None})
    else:
        font_px = spec.rel_size * ref
        font = _font(font_px)
        stroke = max(1, int(round(font_px / 18.0))) if spec.stroke else 0
        points = _tile_points(width, height) if spec.repeated else [(spec.at[0] * width, spec.at[1] * height)]
        anchor = "mm" if spec.repeated else spec.anchor
        for x, y in points:
            bbox = draw.textbbox((x, y), spec.text, font=font, anchor=anchor, stroke_width=stroke)
            kwargs: dict[str, Any] = {"font": font, "anchor": anchor, "fill": (255, 255, 255, alpha)}
            if stroke:
                kwargs.update(stroke_width=stroke, stroke_fill=(0, 0, 0, alpha))
            draw.text((x, y), spec.text, **kwargs)
            boxes.append(
                {
                    "box": [
                        float(max(0, bbox[0])),
                        float(max(0, bbox[1])),
                        float(min(width, bbox[2])),
                        float(min(height, bbox[3])),
                    ],
                    "text": spec.text,
                }
            )
    out = Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")
    return out, boxes


def display_variant(domain: str, variant: str) -> str:
    prefix = DOMAIN_VARIANT_PREFIX.get(domain)
    if prefix and re.fullmatch(r"V\d", variant):
        return prefix + variant[1:]
    return variant


def build_plan(entries: Sequence[Mapping[str, Any]], control_ids: Sequence[str]) -> list[dict[str, Any]]:
    """Pre-registered condition list. entries: [{opaqueId, domain}] only."""

    by_domain: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        by_domain[entry["domain"]].append(entry["opaqueId"])
    for domain, expected in EXPECTED_COUNTS.items():
        if len(by_domain[domain]) != expected:
            raise ValueError(f"{domain} expected {expected} got {len(by_domain[domain])}")
    plan: list[dict[str, Any]] = []

    def add(domain, base, spec, tasks, phase):
        plan.append(
            {
                "conditionId": f"{base}:{spec.variant}" if base else spec.variant,
                "domain": domain,
                "baseOpaqueId": base,
                "variant": spec.variant,
                "displayVariant": display_variant(domain, spec.variant),
                "phase": phase,
                "tasks": list(tasks),
            }
        )

    for domain in REAL_DOMAINS:
        for base in by_domain[domain]:
            add(domain, base, CORE_BY_VARIANT["V0"], BOTH_TASKS, "raw")
    for control_id in control_ids:
        plan.append(
            {
                "conditionId": control_id,
                "domain": DOMAIN_SYNTHETIC,
                "baseOpaqueId": control_id,
                "variant": control_id,
                "displayVariant": control_id,
                "phase": "control",
                "tasks": list(BOTH_TASKS),
            }
        )
    for domain in (DOMAIN_AVATAR, DOMAIN_SOURCE):
        for base in by_domain[domain]:
            for spec in CORE_VARIANTS[1:]:
                add(domain, base, spec, BOTH_TASKS, "core")
    for domain in REAL_DOMAINS:
        for ordinal in CURVE_BASE_ORDINALS[domain]:
            base = f"{OPAQUE_PREFIX[domain]}-{ordinal:03d}"
            for spec in curve_specs():
                add(domain, base, spec, OCR_ONLY, "curve")
    return plan


def spec_for(variant: str) -> Optional[OverlaySpec]:
    if variant in CORE_BY_VARIANT:
        return CORE_BY_VARIANT[variant]
    for spec in curve_specs():
        if spec.variant == variant:
            return spec
    return None


def plan_digest(plan: Sequence[Mapping[str, Any]]) -> str:
    design = {
        "benchmarkVersion": BENCHMARK_VERSION,
        "iouMatch": IOU_MATCH,
        "core": [asdict(spec) for spec in CORE_VARIANTS],
        "curves": [asdict(spec) for spec in curve_specs()],
        "curveBaseOrdinals": {k: list(v) for k, v in CURVE_BASE_ORDINALS.items()},
        "conditions": [[c["conditionId"], c["phase"], c["tasks"]] for c in plan],
    }
    return hashlib.sha256(json.dumps(design, sort_keys=True).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Scoring (raw text is consumed here and never returned)
# --------------------------------------------------------------------------


def normalize_transcription(value: str) -> str:
    """Pre-registered: uppercase, keep [A-Z0-9], drop everything else."""

    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def _tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[^A-Z0-9]+", str(value).upper()) if token]


def _levenshtein(a: Sequence[Any], b: Sequence[Any]) -> int:
    previous = list(range(len(b) + 1))
    for i, item_a in enumerate(a, 1):
        current = [i]
        for j, item_b in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (item_a != item_b)))
        previous = current
    return previous[-1]


def iou(a: Sequence[float], b: Sequence[float]) -> float:
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, right - left) * max(0.0, bottom - top)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _center_inside(box: Sequence[float], target: Sequence[float], pad: float = 0.1) -> bool:
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    pw, ph = (target[2] - target[0]) * pad, (target[3] - target[1]) * pad
    return target[0] - pw <= cx <= target[2] + pw and target[1] - ph <= cy <= target[3] + ph


def _ocr_regions(tasks: Mapping[str, Any], size: tuple[int, int]) -> list[tuple[tuple[float, ...], str]]:
    payload = _task_payload(tasks, TASK_OCR_WITH_REGION)
    regions = []
    for quad, label in zip(payload.get("quad_boxes", []), payload.get("labels", [])):
        if not str(label).strip():
            continue  # production drops invisible labels too
        try:
            regions.append((_quad_to_xyxy(quad, size), str(label)))
        except (TypeError, ValueError):
            continue
    return regions


def _od_regions(tasks: Mapping[str, Any], size: tuple[int, int]) -> list[tuple[tuple[float, ...], str]]:
    payload = _task_payload(tasks, TASK_OD)
    regions = []
    for bbox, label in zip(payload.get("bboxes", []), payload.get("labels", [])):
        try:
            regions.append((_normalize_bbox(bbox, size), str(label)))
        except (TypeError, ValueError):
            continue
    return regions


_OD_LABEL_RE = re.compile(r"^[a-z][a-z \-]{0,30}$")


def sanitize_od_label(label: str) -> str:
    value = str(label).strip().lower()
    return value if _OD_LABEL_RE.fullmatch(value) else "<unlisted>"


def score_condition(record: Mapping[str, Any]) -> dict[str, Any]:
    """One typed, text-free row per condition."""

    size = (int(record["imageSize"][0]), int(record["imageSize"][1]))
    tasks = record["tasks"]
    truth = record.get("groundTruth") or []
    spec = spec_for(record["variant"]) if record["domain"] != DOMAIN_SYNTHETIC else None
    ocr = _ocr_regions(tasks, size)
    row: dict[str, Any] = {
        "conditionId": record["conditionId"],
        "domain": record["domain"],
        "baseOpaqueId": record["baseOpaqueId"],
        "variant": record["variant"],
        "displayVariant": record.get("displayVariant", record["variant"]),
        "phase": record["phase"],
        "groupKey": record.get("groupKey"),
        "ocrRegionCount": len(ocr),
        "latencySec": dict(record.get("latencySec") or {}),
        "warmup": bool(record.get("warmup")),
    }
    if spec is not None:
        row.update(
            construct=spec.construct,
            expectedClass=spec.expected_class,
            riskPositive=spec.risk_positive,
            overlayPresent=spec.overlay_present,
            textPresent=spec.text_present,
            logoLikePresent=spec.logo,
            repeated=spec.repeated,
            alpha=spec.alpha,
            relativeSize=spec.rel_size,
            placementClass=spec.placement_class,
            sizeClass=spec.size_class,
        )

    # Region recall against injected ground truth.
    box_ious = []
    for item in truth:
        best = max((iou(region[0], item["box"]) for region in ocr), default=0.0)
        box_ious.append(best)
    row["gtBoxCount"] = len(truth)
    row["gtBoxHits"] = sum(1 for value in box_ious if value >= IOU_MATCH)
    row["gtBestIous"] = [round(value, 4) for value in box_ious]
    row["ocrImageHit"] = bool(truth) and row["gtBoxHits"] > 0

    # Transcription (typed outcome only).
    text_truth = [item for item in truth if item.get("text")]
    if text_truth:
        exact, cers, wers = [], [], []
        for item in text_truth:
            matched = sorted(
                (region for region in ocr if iou(region[0], item["box"]) >= IOU_MATCH or _center_inside(region[0], item["box"])),
                key=lambda region: region[0][0],
            )
            predicted = " ".join(region[1] for region in matched)
            gold = normalize_transcription(item["text"])
            pred = normalize_transcription(predicted)
            exact.append(pred == gold)
            cers.append(min(1.0, _levenshtein(pred, gold) / max(1, len(gold))))
            gold_tokens = _tokens(item["text"])
            if len(gold_tokens) > 1:
                wers.append(min(1.0, _levenshtein(_tokens(predicted), gold_tokens) / len(gold_tokens)))
        row["transcriptionExactCount"] = sum(exact)
        row["transcriptionEvaluated"] = len(exact)
        row["cerMean"] = round(mean(cers), 4)
        row["werMean"] = round(mean(wers), 4) if wers else None

    if TASK_OD in tasks:
        od = _od_regions(tasks, size)
        row["odRegionCount"] = len(od)
        row["odLabels"] = dict(Counter(sanitize_od_label(label) for _, label in od))
        if truth:
            row["odImageHit"] = any(iou(region[0], item["box"]) >= IOU_MATCH for region in od for item in truth)
            row["odLogoKindHit"] = any(
                _classify_od_label(region[1]) in {"logo", "sign"} and iou(region[0], item["box"]) >= IOU_MATCH
                for region in od
                for item in truth
            )

    if all(task in tasks for task in BOTH_TASKS):
        row.update(_policy_row(tasks, size, truth))
    return row


def _policy_row(tasks: Mapping[str, Any], size: tuple[int, int], truth: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    analysis = analyze_florence_visual_risk_outputs(tasks, image_size=size, primary_face_bbox_xyxy=None)
    decision = evaluate_watermark_risk(analysis.regions, image_size=size)
    shadow = classify_watermark_construct_shadow(decision.evidence) or {}
    text_like = [region for region in analysis.regions if region.kind in {"text", "logo", "sign"}]
    typed = list((decision.evidence or {}).get("regionEvidence") or [])
    matched_typed = []
    for region, evidence in zip(text_like, typed):
        if any(iou(region.bbox_xyxy, item["box"]) >= IOU_MATCH for item in truth):
            matched_typed.append(evidence)
    return {
        "providerAvailable": bool(analysis.provider_available),
        "currentAction": decision.watermark_qa_action,
        "currentDecisionClass": decision.decision_class,
        "h1Action": shadow.get("shadowWatermarkAction"),
        "h1Class": shadow.get("shadowWatermarkClass"),
        "typedRegionCount": len(typed),
        "overlayLikeRegions": sum(1 for item in typed if item.get("overlayLike")),
        "repeatedRegions": sum(1 for item in typed if item.get("repeated")),
        "fragmentedRegions": sum(1 for item in typed if item.get("textQuality") == "implausible"),
        "locationCounts": dict(Counter(item.get("location") for item in typed)),
        "matchedInjectedTyped": {
            "count": len(matched_typed),
            "overlayLike": sum(1 for item in matched_typed if item.get("overlayLike")),
            "repeated": sum(1 for item in matched_typed if item.get("repeated")),
            "fragmented": sum(1 for item in matched_typed if item.get("textQuality") == "implausible"),
        },
    }


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def _rate(numerator: int, denominator: int) -> Optional[float]:
    return round(numerator / denominator, 4) if denominator else None


def _flagged(action: Optional[str]) -> bool:
    return action in ACTION_FLAGGED


def model_hit(row: Mapping[str, Any]) -> bool:
    """Florence produced evidence on the injected region (OCR, or OD for a logo)."""

    if row.get("logoLikePresent"):
        return bool(row.get("ocrImageHit") or row.get("odImageHit"))
    return bool(row.get("ocrImageHit"))


def classify_miss(row: Mapping[str, Any], action_key: str) -> Optional[str]:
    """MODEL_MISS vs POLICY_MISS for a risk-positive injected condition."""

    if not row.get("riskPositive"):
        return None
    if not model_hit(row):
        return "MODEL_MISS"
    if row.get(action_key) == "allow":
        return "POLICY_MISS"
    return None


def _latency_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("ocr", "od", "combined"):
        # combined is only meaningful where both tasks ran (curves are OCR-only).
        values = sorted(
            float(row["latencySec"][key])
            for row in rows
            if not row.get("warmup")
            and key in (row.get("latencySec") or {})
            and (key != "combined" or "od" in row["latencySec"])
        )
        if values:
            result[key] = {
                "n": len(values),
                "mean": round(mean(values), 2),
                "median": round(median(values), 2),
                "p90": round(values[min(len(values) - 1, int(0.9 * len(values)))], 2),
            }
    return result


def _box_recall(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    boxes = sum(row.get("gtBoxCount", 0) for row in rows)
    hits = sum(row.get("gtBoxHits", 0) for row in rows)
    ious = [value for row in rows for value in row.get("gtBestIous", [])]
    return {
        "conditions": len(rows),
        "imageHitRate": _rate(sum(1 for row in rows if row.get("ocrImageHit")), len(rows)),
        "boxRecall": _rate(hits, boxes),
        "missRate": _rate(boxes - hits, boxes),
        "meanIoU": round(mean(ious), 4) if ious else None,
        "medianIoU": round(median(ious), 4) if ious else None,
    }


def _transcription(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    evaluated = [row for row in rows if row.get("transcriptionEvaluated")]
    if not evaluated:
        return {"conditions": 0}
    wers = [row["werMean"] for row in evaluated if row.get("werMean") is not None]
    return {
        "conditions": len(evaluated),
        "normalizedExactMatchRate": _rate(
            sum(row["transcriptionExactCount"] for row in evaluated),
            sum(row["transcriptionEvaluated"] for row in evaluated),
        ),
        "cerMean": round(mean(row["cerMean"] for row in evaluated), 4),
        "werMean": round(mean(wers), 4) if wers else None,
    }


def _raw_distribution(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    buckets = Counter(
        "0" if row["ocrRegionCount"] == 0 else "1" if row["ocrRegionCount"] == 1
        else "2-3" if row["ocrRegionCount"] <= 3 else "4+"
        for row in rows
    )
    n = len(rows)
    return {
        "label": "OBSERVED_RESPONSE_DISTRIBUTION",
        "n": n,
        "ocrRegionCountBuckets": dict(sorted(buckets.items())),
        "noRegionRate": _rate(sum(1 for r in rows if r["ocrRegionCount"] == 0), n),
        "multiRegionRate": _rate(sum(1 for r in rows if r["ocrRegionCount"] > 1), n),
        "overlayLikeEvidenceRate": _rate(sum(1 for r in rows if r.get("overlayLikeRegions", 0) > 0), n),
        "repeatedEvidenceRate": _rate(sum(1 for r in rows if r.get("repeatedRegions", 0) > 0), n),
        "fragmentedEvidenceRate": _rate(sum(1 for r in rows if r.get("fragmentedRegions", 0) > 0), n),
        "locationCounts": dict(sum((Counter(r.get("locationCounts") or {}) for r in rows), Counter())),
        "currentActions": dict(Counter(r.get("currentAction") for r in rows)),
        "h1Actions": dict(Counter(r.get("h1Action") for r in rows)),
        "currentDecisionClasses": dict(Counter(r.get("currentDecisionClass") for r in rows)),
        "transitions": transitions(rows),
        "odRegionCountMean": round(mean(r.get("odRegionCount", 0) for r in rows), 3) if rows else None,
    }


def transitions(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counter: Counter = Counter()
    for row in rows:
        current, h1 = row.get("currentAction"), row.get("h1Action")
        if current is None or h1 is None:
            continue
        counter["same" if current == h1 else f"{current}->{h1}"] += 1
    return dict(sorted(counter.items()))


def _h1_domain(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    core = [row for row in rows if row["phase"] == "core"]

    def pick(variants):
        return [row for row in core if row["variant"] in variants]

    overlay, artifact, benign = pick(OVERLAY_VARIANTS), pick(ARTIFACT_VARIANTS), pick(BENIGN_VARIANTS)
    positive = [row for row in core if row.get("riskPositive")]

    def flag_rate(selected, key):
        return {"n": len(selected), "flagged": sum(1 for r in selected if _flagged(r.get(key))),
                "rate": _rate(sum(1 for r in selected if _flagged(r.get(key))), len(selected))}

    def miss(selected, key):
        return {"n": len(selected), "allowed": sum(1 for r in selected if r.get(key) == "allow")}

    return {
        "riskPositiveFlagRate": {"current": flag_rate(positive, "currentAction"), "h1": flag_rate(positive, "h1Action")},
        "benignFalseFlag": {"current": flag_rate(benign, "currentAction"), "h1": flag_rate(benign, "h1Action")},
        "overlayMiss": {"current": miss(overlay, "currentAction"), "h1": miss(overlay, "h1Action")},
        "generativeArtifactMiss": {"current": miss(artifact, "currentAction"), "h1": miss(artifact, "h1Action")},
        "hardRejectBypass": sum(1 for r in core if r.get("currentAction") == "reject" and r.get("h1Action") != "reject"),
        "transitionsByVariant": {
            variant: transitions(pick((variant,))) for variant in sorted({r["variant"] for r in core})
        },
    }


def aggregate(rows: Sequence[Mapping[str, Any]], *, meta: Mapping[str, Any] | None = None) -> dict[str, Any]:
    by_domain: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_domain[row["domain"]].append(row)
    report: dict[str, Any] = {
        "benchmarkVersion": BENCHMARK_VERSION,
        "meta": dict(meta or {}),
        "conditionCounts": {
            domain: dict(Counter(row["phase"] for row in domain_rows)) for domain, domain_rows in sorted(by_domain.items())
        },
        "domains": {},
    }
    for domain in REAL_DOMAINS:
        domain_rows = by_domain.get(domain, [])
        core = [row for row in domain_rows if row["phase"] == "core"]
        raw = [row for row in domain_rows if row["phase"] == "raw"]
        curves = [row for row in domain_rows if row["phase"] == "curve"]
        variants = sorted({row["variant"] for row in core})
        report["domains"][domain] = {
            "rawClean": _raw_distribution(raw),
            "regionRecallByVariant": {
                display_variant(domain, v): _box_recall([r for r in core if r["variant"] == v])
                for v in variants
            },
            "transcriptionByVariant": {
                display_variant(domain, v): _transcription([r for r in core if r["variant"] == v])
                for v in variants
            },
            "curves": _curve_tables(curves),
            "logoEvidence": _logo_table([r for r in core if r["variant"] == "V8"]),
            "modelMissByVariant": {
                display_variant(domain, v): sum(1 for r in core if r["variant"] == v and classify_miss(r, "currentAction") == "MODEL_MISS")
                for v in variants
            },
            "policyMissByVariant": {
                display_variant(domain, v): {
                    "current": sum(1 for r in core if r["variant"] == v and classify_miss(r, "currentAction") == "POLICY_MISS"),
                    "h1": sum(1 for r in core if r["variant"] == v and classify_miss(r, "h1Action") == "POLICY_MISS"),
                }
                for v in variants
            },
            "currentActionByVariant": {
                display_variant(domain, v): dict(Counter(r.get("currentAction") for r in core if r["variant"] == v))
                for v in variants
            },
            "h1": _h1_domain(domain_rows),
            "odVocabulary": dict(
                sorted(sum((Counter(r.get("odLabels") or {}) for r in domain_rows), Counter()).items())
            ),
            "latency": _latency_summary(domain_rows),
        }
    report["crossDomainDelta"] = _cross_domain(report["domains"])
    synthetic = by_domain.get(DOMAIN_SYNTHETIC, [])
    report["domains"][DOMAIN_SYNTHETIC] = {
        "controls": {
            r["conditionId"]: {
                "ocrRegionCount": r["ocrRegionCount"],
                "odRegionCount": r.get("odRegionCount"),
                "currentAction": r.get("currentAction"),
                "h1Action": r.get("h1Action"),
                "currentDecisionClass": r.get("currentDecisionClass"),
            }
            for r in sorted(synthetic, key=lambda r: r["conditionId"])
        },
        "odVocabulary": dict(sorted(sum((Counter(r.get("odLabels") or {}) for r in synthetic), Counter()).items())),
        "latency": _latency_summary(synthetic),
    }
    groups = [r for r in by_domain.get(DOMAIN_AVATAR, []) if r["phase"] == "raw" and r.get("groupKey")]
    if groups:
        report["g004GroupLevelSimulation"] = _group_simulation(groups)
    return report


def _curve_tables(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    alpha: dict[str, Any] = {}
    size: dict[str, Any] = {}
    for row in rows:
        key_alpha = f"{row['placementClass']}|a{int(round(row['alpha'] * 100)):03d}"
        key_size = f"{row['placementClass']}|{row['sizeClass']}"
        if row["sizeClass"] == "medium":
            alpha.setdefault(key_alpha, []).append(row)
        if abs(row["alpha"] - 1.0) < 1e-9:
            size.setdefault(key_size, []).append(row)
    return {
        "alphaAtMediumSize": {k: _box_recall(v) for k, v in sorted(alpha.items())},
        "sizeAtAlpha100": {k: _box_recall(v) for k, v in sorted(size.items())},
    }


def _logo_table(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    table = Counter()
    for row in rows:
        ocr, od = bool(row.get("ocrImageHit")), bool(row.get("odImageHit"))
        table["both" if ocr and od else "ocrOnly" if ocr else "odOnly" if od else "neither"] += 1
    return {
        "n": len(rows),
        "table": {key: table.get(key, 0) for key in ("ocrOnly", "odOnly", "both", "neither")},
        "odLogoOrSignKindHits": sum(1 for row in rows if row.get("odLogoKindHit")),
        "currentActions": dict(Counter(row.get("currentAction") for row in rows)),
    }


def _cross_domain(domains: Mapping[str, Any]) -> dict[str, Any]:
    source = domains.get(DOMAIN_SOURCE, {}).get("regionRecallByVariant", {})
    avatar = domains.get(DOMAIN_AVATAR, {}).get("regionRecallByVariant", {})
    result = {}
    for spec in CORE_VARIANTS[1:]:
        s = source.get("V" + spec.variant[1:], {})
        a = avatar.get("A" + spec.variant[1:], {})
        entry = {"construct": spec.construct}
        for key in ("imageHitRate", "boxRecall"):
            if s.get(key) is not None and a.get(key) is not None:
                entry[key] = {"source": s[key], "avatar": a[key], "deltaAvatarMinusSource": round(a[key] - s[key], 4)}
        result[spec.variant] = entry
    return result


def _group_simulation(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_group: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_group[row["groupKey"]].append(row)

    def bucket(count: int) -> str:
        return "zero" if count == 0 else "one" if count == 1 else "two_plus"

    current = Counter()
    shadow = Counter()
    changed = 0
    for group_rows in by_group.values():
        c = sum(1 for r in group_rows if r.get("currentAction") == "allow")
        h = sum(1 for r in group_rows if r.get("h1Action") == "allow")
        current[bucket(c)] += 1
        shadow[bucket(h)] += 1
        changed += int(c != h)
    return {
        "label": "G004_GROUP_LEVEL_SIMULATION",
        "groups": len(by_group),
        "candidatesPerGroup": sorted({len(v) for v in by_group.values()}),
        "watermarkAllowedDistribution": {"current": dict(current), "h1": dict(shadow)},
        "groupsChanged": changed,
        "scope": "watermark action only; other QA gates not modelled",
    }


# --------------------------------------------------------------------------
# Privacy guard for anything that leaves the restricted directory
# --------------------------------------------------------------------------

_FORBIDDEN_PATTERNS = (
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"/Users/|\\Users\\|AppData", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{64}\b"),
    re.compile(r"participant-\d", re.IGNORECASE),
    re.compile(r"\bP\d{2}_C\d{2}\b"),
    re.compile(r"\.(png|jpe?g|webp)\b", re.IGNORECASE),
    re.compile(r"data:image|base64", re.IGNORECASE),
)


def privacy_violations(report: Any, forbidden_strings: Iterable[str] = ()) -> list[str]:
    """Returns violations. forbidden_strings: raw OCR labels, UIDs, filenames."""

    text = json.dumps(report, ensure_ascii=False)
    problems = [pattern.pattern for pattern in _FORBIDDEN_PATTERNS if pattern.search(text)]
    for value in forbidden_strings:
        value = str(value).strip()
        if len(value) >= 3 and value in text:
            problems.append("forbidden_string_present")
            break
    return problems
