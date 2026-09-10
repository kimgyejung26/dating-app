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

The geometry is not restated here. ``head_shoulders_window`` and
``render_head_shoulders_crop`` are the primitives ``HeadShouldersCropper``
itself uses, so there is one implementation of the convention rather than two
that can drift. Only the resize target is decided locally: the cropper enlarges
it for small faces, while a similarity comparison needs both sides at one fixed
size or they are not comparable after all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from PIL import Image

from .analysis.small_face.config import SmallFacePipelineConfig
from .analysis.small_face.cropper import (
    VERTICAL_CENTRE_BIAS,
    head_shoulders_window,
    render_head_shoulders_crop,
)
from .analysis.small_face.types import PixelBox

IDENTITY_CROP_METHOD = "head_shoulders_square"
IDENTITY_CROP_VERSION = "identity_crop_v1"

_CONFIG = SmallFacePipelineConfig()
# Read from the canonical config for provenance only. The geometry itself is
# computed by the shared primitive, not by these numbers.
EXPAND_HORIZONTAL = _CONFIG.crop_expand_horizontal
EXPAND_TOP = _CONFIG.crop_expand_top
EXPAND_BOTTOM = _CONFIG.crop_expand_bottom
TARGET_SIZE = _CONFIG.primary_crop_target_size
RESAMPLING = Image.Resampling.LANCZOS

__all__ = [
    "EXPAND_BOTTOM",
    "EXPAND_HORIZONTAL",
    "EXPAND_TOP",
    "IDENTITY_CROP_METHOD",
    "IDENTITY_CROP_VERSION",
    "TARGET_SIZE",
    "VERTICAL_CENTRE_BIAS",
    "IdentityCropProvenance",
    "crop_identity_region",
    "identity_crop_provenance",
]


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
    face = _bbox_to_pixel_box(bbox, image.size)
    if face is None:
        return None
    window = head_shoulders_window(face, _CONFIG)
    cropped = render_head_shoulders_crop(image, window)
    if cropped.width <= 0 or cropped.height <= 0:
        return None
    return cropped.resize((TARGET_SIZE, TARGET_SIZE), RESAMPLING)


def _bbox_to_pixel_box(
    bbox: Sequence[float],
    size: Tuple[int, int],
) -> Optional[PixelBox]:
    """Interpret a detector box the way `_crop_face` already does, then clamp it
    the way `HeadShouldersCropper.crop` already does."""

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
    box = PixelBox(
        int(round(left)), int(round(top)), int(round(right)), int(round(bottom))
    ).clamp(width, height)
    if box.width <= 0 or box.height <= 0:
        return None
    return box
