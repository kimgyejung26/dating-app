"""One crop convention, applied identically to both sides of a comparison.

Today the two sides are not comparable. ``build_candidate_qa_signals`` crops the
candidate to the detector's face box and the source to
``_source_primary_bbox(source_analysis)`` -- and that reads
``sourceAnalysis.primaryFaceBbox``, which ``SourceAnalysisResult.to_document``
deliberately never writes, because a face box is not allowed to persist. So the
lookup returns None in production, ``_crop_face(image, None)`` returns
``image.copy()``, and the "identity comparison" is a whole photograph against a
tight face crop.

Whatever that number measures, it is not the same quantity on both sides, which
is why the score it produces cannot be reasoned about -- and why the existing
calibration (threshold 0.799743, review margin 0.185528) must keep consuming the
existing asymmetric score. Replacing the score under a calibration fitted to a
different distribution would be a silent semantic change, not a fix. The
symmetric score defined here is therefore telemetry only.

The geometry is not invented for this module. The expansion ratios, the square
normalisation, the neutral pad colour and the target size are the ones
``analysis.small_face.cropper.HeadShouldersCropper`` already uses, so the
convention has one definition in this repository rather than two.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from PIL import Image, ImageOps

from .analysis.small_face.config import SmallFacePipelineConfig

IDENTITY_CROP_METHOD = "head_shoulders_square"
IDENTITY_CROP_VERSION = "identity_crop_v1"

_CONFIG = SmallFacePipelineConfig()
# Sourced from the canonical cropper rather than chosen here. Restated as
# module constants so a change to either definition breaks a test instead of
# silently desynchronising the two sides of a comparison.
EXPAND_HORIZONTAL = _CONFIG.crop_expand_horizontal
EXPAND_TOP = _CONFIG.crop_expand_top
EXPAND_BOTTOM = _CONFIG.crop_expand_bottom
VERTICAL_CENTRE_BIAS = 0.08
PAD_FILL = (247, 242, 236)
TARGET_SIZE = _CONFIG.primary_crop_target_size


@dataclass(frozen=True)
class IdentityCropProvenance:
    """How a crop was taken, with no geometry in it.

    Records the method, not the box. A bbox may not leave process memory, so
    nothing here can be used to reconstruct where a face was.
    """

    method: str
    version: str
    expand_horizontal: float
    expand_top: float
    expand_bottom: float
    target_size: int

    def to_document(self) -> dict[str, object]:
        return {
            "identityCropMethod": self.method,
            "identityCropVersion": self.version,
            "identityCropExpandHorizontal": self.expand_horizontal,
            "identityCropExpandTop": self.expand_top,
            "identityCropExpandBottom": self.expand_bottom,
            "identityCropTargetSize": self.target_size,
        }


def identity_crop_provenance() -> IdentityCropProvenance:
    return IdentityCropProvenance(
        method=IDENTITY_CROP_METHOD,
        version=IDENTITY_CROP_VERSION,
        expand_horizontal=EXPAND_HORIZONTAL,
        expand_top=EXPAND_TOP,
        expand_bottom=EXPAND_BOTTOM,
        target_size=TARGET_SIZE,
    )


def crop_identity_region(
    image: Image.Image,
    bbox: Optional[Sequence[float]],
) -> Optional[Image.Image]:
    """Crop `image` to the identity region around `bbox`.

    Returns None when there is no box. That is deliberately not the same as
    "use the whole image": a missing box on one side is exactly the condition
    that produced the asymmetry, so the shadow score is simply not computed.
    """

    if bbox is None:
        return None
    box = _bbox_to_pixels(bbox, image.size)
    if box is None:
        return None
    left, top, right, bottom = box
    face_width = max(1.0, right - left)
    face_height = max(1.0, bottom - top)
    centre_x = (left + right) / 2.0
    centre_y = (top + bottom) / 2.0 + face_height * VERTICAL_CENTRE_BIAS

    x0 = centre_x - face_width * (0.5 + EXPAND_HORIZONTAL)
    x1 = centre_x + face_width * (0.5 + EXPAND_HORIZONTAL)
    y0 = centre_y - face_height * (0.5 + EXPAND_TOP)
    y1 = centre_y + face_height * (0.5 + EXPAND_BOTTOM)

    side = max(x1 - x0, y1 - y0, 1.0)
    x0 = int(round(centre_x - side / 2.0))
    y0 = int(round(centre_y - side / 2.0))
    x1 = x0 + int(round(side))
    y1 = y0 + int(round(side))

    width, height = image.size
    pad_left = max(0, -x0)
    pad_top = max(0, -y0)
    pad_right = max(0, x1 - width)
    pad_bottom = max(0, y1 - height)

    working = image
    if pad_left or pad_top or pad_right or pad_bottom:
        # Solid neutral fill, never a reflection: a mirrored border can fold
        # another face or a sign back into the frame.
        working = ImageOps.expand(
            image,
            border=(pad_left, pad_top, pad_right, pad_bottom),
            fill=PAD_FILL,
        )
    cropped = working.crop(
        (x0 + pad_left, y0 + pad_top, x1 + pad_left, y1 + pad_top)
    )
    if cropped.width <= 0 or cropped.height <= 0:
        return None
    return cropped.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)


def _bbox_to_pixels(
    bbox: Sequence[float],
    size: Tuple[int, int],
) -> Optional[Tuple[float, float, float, float]]:
    values = [float(value) for value in list(bbox)[:4]]
    if len(values) < 4:
        return None
    width, height = size
    x, y, third, fourth = values
    if all(0.0 <= value <= 1.0 for value in values):
        left, top = x * width, y * height
        right, bottom = (x + third) * width, (y + fourth) * height
    elif third > x and fourth > y:
        left, top, right, bottom = x, y, third, fourth
    else:
        left, top, right, bottom = x, y, x + third, y + fourth
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


__all__ = [
    "IDENTITY_CROP_METHOD",
    "IDENTITY_CROP_VERSION",
    "IdentityCropProvenance",
    "crop_identity_region",
    "identity_crop_provenance",
]
