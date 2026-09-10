from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image, ImageOps

from .config import SmallFacePipelineConfig
from .types import CropTransform, InternalFaceDetection, PixelBox


PAD_FILL = (247, 242, 236)
VERTICAL_CENTRE_BIAS = 0.08


def head_shoulders_window(face: PixelBox, config: SmallFacePipelineConfig) -> PixelBox:
    """The square crop window for a face, in original image coordinates.

    Extracted so the identity-similarity shadow can crop both sides of its
    comparison exactly the way this pipeline already crops -- calling this
    rather than restating the arithmetic, which is the only way "same crop
    convention" can be asserted instead of hoped for. The window may extend
    outside the image; render_head_shoulders_crop pads it.
    """

    fw = max(1, face.width)
    fh = max(1, face.height)
    cx = (face.x_min + face.x_max) / 2.0
    cy = (face.y_min + face.y_max) / 2.0 + fh * VERTICAL_CENTRE_BIAS

    expand_h = config.crop_expand_horizontal
    expand_top = config.crop_expand_top
    expand_bottom = config.crop_expand_bottom

    x0 = int(round(cx - fw * (0.5 + expand_h)))
    x1 = int(round(cx + fw * (0.5 + expand_h)))
    y0 = int(round(cy - fh * (0.5 + expand_top)))
    y1 = int(round(cy + fh * (0.5 + expand_bottom)))

    # Force square crop aligned to the square reference contract.
    side = max(x1 - x0, y1 - y0, 1)
    x0 = int(round(cx - side / 2.0))
    y0 = int(round(cy - side / 2.0))
    return PixelBox(x0, y0, x0 + side, y0 + side)


def render_head_shoulders_crop(image: Image.Image, window: PixelBox) -> Image.Image:
    """Cut `window` out of `image`, padding neutrally where it overhangs."""

    width, height = image.size
    pad_left = max(0, -window.x_min)
    pad_top = max(0, -window.y_min)
    pad_right = max(0, window.x_max - width)
    pad_bottom = max(0, window.y_max - height)

    working = image
    crop_box_working = window
    if pad_left or pad_top or pad_right or pad_bottom:
        # Neutral solid padding — never reflect other faces/text into the canvas.
        working = ImageOps.expand(
            image,
            border=(pad_left, pad_top, pad_right, pad_bottom),
            fill=PAD_FILL,
        )
        crop_box_working = PixelBox(
            window.x_min + pad_left,
            window.y_min + pad_top,
            window.x_max + pad_left,
            window.y_max + pad_top,
        )
    return working.crop(crop_box_working.as_tuple())


@dataclass(frozen=True)
class HeadShouldersCropResult:
    image: Image.Image
    transform: CropTransform
    used_max_size: bool


class HeadShouldersCropper:
    def __init__(self, config: SmallFacePipelineConfig) -> None:
        self._config = config

    def crop(
        self,
        image: Image.Image,
        primary: InternalFaceDetection,
    ) -> HeadShouldersCropResult:
        width, height = image.size
        face = primary.bbox_pixels.clamp(width, height)
        desired_original = head_shoulders_window(face, self._config)
        cropped = render_head_shoulders_crop(image, desired_original)
        target = self._config.primary_crop_target_size
        used_max = False
        if (
            primary.face_short_side_px < self._config.min_short_side_trait_px
            and self._config.primary_crop_max_size > target
        ):
            target = self._config.primary_crop_max_size
            used_max = True

        resized = cropped.resize((target, target), Image.Resampling.LANCZOS)
        scale = target / float(max(1, desired_original.width))
        # padded_box stores the crop window in original coordinates for mapping.
        transform = CropTransform(
            original_box=face,
            padded_box=desired_original,
            target_width=target,
            target_height=target,
            scale_x=scale,
            scale_y=scale,
            offset_x=0.0,
            offset_y=0.0,
        )
        return HeadShouldersCropResult(
            image=resized,
            transform=transform,
            used_max_size=used_max,
        )


__all__ = ["HeadShouldersCropper", "HeadShouldersCropResult"]
