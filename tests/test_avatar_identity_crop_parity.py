"""The identity shadow must crop exactly the way the canonical pipeline crops.

Asserting that two modules read the same config constants proves only that they
agree about the constants. The first version of ``identity_crop`` did exactly
that while quietly re-implementing the arithmetic, and the re-implementation
differed: it rounded after computing the square side instead of before, and it
never clamped the face box to the image. Either difference moves the window by
whole pixels, which is enough to make "the same crop convention on both sides"
false while every constant-equality test still passes.

So the expectations here are produced by calling ``HeadShouldersCropper``
itself. No expected geometry is restated in this file. If the two ever diverge
again -- by refactor, by rounding, by a config change -- these fail.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.analysis.small_face.config import SmallFacePipelineConfig  # noqa: E402
from avatar_generation.analysis.small_face.cropper import (  # noqa: E402
    HeadShouldersCropper,
    head_shoulders_window,
    render_head_shoulders_crop,
)
from avatar_generation.analysis.small_face.types import (  # noqa: E402
    InternalFaceDetection,
    NormalizedBox,
    PixelBox,
    normalized_to_pixel,
    pixel_to_normalized,
)
from avatar_generation.identity_crop import (  # noqa: E402
    RESAMPLING,
    TARGET_SIZE,
    crop_identity_region,
)

CONFIG = SmallFacePipelineConfig()

# (label, image size, normalized xywh face box)
FIXTURES = [
    ("centred face, portrait", (900, 1200), (0.34, 0.18, 0.30, 0.24)),
    ("centred face, landscape", (1600, 900), (0.42, 0.22, 0.16, 0.30)),
    ("centred face, square", (768, 768), (0.32, 0.30, 0.34, 0.30)),
    ("left-edge face", (900, 1200), (0.00, 0.30, 0.18, 0.16)),
    ("right-edge face", (900, 1200), (0.82, 0.30, 0.18, 0.16)),
    ("top-edge face", (900, 1200), (0.40, 0.00, 0.22, 0.14)),
    ("bottom-edge face", (900, 1200), (0.40, 0.86, 0.22, 0.14)),
    ("corner face", (640, 480), (0.00, 0.00, 0.12, 0.14)),
    ("tiny face", (1600, 2400), (0.48, 0.44, 0.04, 0.05)),
    ("large face", (800, 800), (0.10, 0.08, 0.78, 0.80)),
]


def _gradient(size):
    """Non-uniform content, so a one-pixel window shift is visible."""

    width, height = size
    image = Image.new("RGB", size)
    pixels = image.load()
    for x in range(width):
        for y in range(height):
            pixels[x, y] = ((x * 7) % 256, (y * 11) % 256, ((x + y) * 13) % 256)
    return image


def _canonical_crop(image, normalized_xywh):
    """What HeadShouldersCropper produces, at the identity target size.

    The cropper enlarges its own target for small faces; the identity shadow
    fixes it so both sides of a comparison are one size. The window is what must
    match, so the canonical window is rendered at the identity target here.
    """

    width, height = image.size
    x, y, w, h = normalized_xywh
    face = normalized_to_pixel(
        NormalizedBox(x, y, x + w, y + h), width, height
    )
    window = head_shoulders_window(face, CONFIG)
    return render_head_shoulders_crop(image, window).resize(
        (TARGET_SIZE, TARGET_SIZE), RESAMPLING
    )


@pytest.mark.parametrize("label,size,box", FIXTURES, ids=[f[0] for f in FIXTURES])
def test_identity_crop_is_pixel_identical_to_the_canonical_crop(label, size, box):
    image = _gradient(size)
    expected = _canonical_crop(image, box)
    actual = crop_identity_region(image, box)
    assert actual is not None, label
    assert actual.size == expected.size == (TARGET_SIZE, TARGET_SIZE), label
    assert actual.tobytes() == expected.tobytes(), label


@pytest.mark.parametrize("label,size,box", FIXTURES, ids=[f[0] for f in FIXTURES])
def test_pixel_and_normalized_bbox_forms_agree(label, size, box):
    """`_crop_face` accepts normalized xywh and pixel xyxy. Both must land on the
    same window, or the two sides of a comparison could be cropped differently
    purely by how the detector happened to report."""

    image = _gradient(size)
    width, height = size
    x, y, w, h = box
    pixel_xyxy = (
        round(x * width),
        round(y * height),
        round((x + w) * width),
        round((y + h) * height),
    )
    from_normalized = crop_identity_region(image, box)
    from_pixels = crop_identity_region(image, pixel_xyxy)
    assert from_normalized is not None and from_pixels is not None, label
    assert from_normalized.tobytes() == from_pixels.tobytes(), label


def test_the_real_cropper_still_produces_the_same_window_after_extraction():
    """HeadShouldersCropper.crop must be unchanged by having the primitive
    pulled out of it. Drive the real class and compare against the primitive."""

    image = _gradient((900, 1200))
    face_pixels = normalized_to_pixel(NormalizedBox(0.34, 0.18, 0.64, 0.42), 900, 1200)
    primary = InternalFaceDetection(
        bbox_normalized=pixel_to_normalized(face_pixels, 900, 1200),
        bbox_pixels=face_pixels,
        face_short_side_px=face_pixels.short_side,
    )
    result = HeadShouldersCropper(CONFIG).crop(image, primary)
    window = head_shoulders_window(face_pixels.clamp(900, 1200), CONFIG)
    assert result.transform.padded_box.as_tuple() == window.as_tuple()
    expected = render_head_shoulders_crop(image, window).resize(
        (result.image.width, result.image.height), RESAMPLING
    )
    assert result.image.tobytes() == expected.tobytes()


def test_window_is_square_for_every_fixture():
    for label, size, box in FIXTURES:
        width, height = size
        x, y, w, h = box
        face = normalized_to_pixel(NormalizedBox(x, y, x + w, y + h), width, height)
        window = head_shoulders_window(face, CONFIG)
        assert window.width == window.height, label


def test_out_of_frame_pixel_box_is_clamped_like_the_canonical_cropper():
    """HeadShouldersCropper clamps the face box to the image before expanding.
    The first identity_crop did not, so an over-hanging detector box produced a
    different window on that side only."""

    image = _gradient((640, 480))
    overhanging = (-60, -40, 190, 130)
    clamped = PixelBox(-60, -40, 190, 130).clamp(640, 480)
    expected = render_head_shoulders_crop(
        image, head_shoulders_window(clamped, CONFIG)
    ).resize((TARGET_SIZE, TARGET_SIZE), RESAMPLING)
    actual = crop_identity_region(image, overhanging)
    assert actual is not None
    assert actual.tobytes() == expected.tobytes()


def test_negative_origin_normalized_box_is_ambiguous_and_measures_nothing():
    """A pre-existing ambiguity, inherited deliberately rather than fixed here.

    `_bbox_to_xyxy` decides between normalized-xywh and pixel-xyxy by testing
    whether every value is in [0, 1]. A MediaPipe relative box whose face runs
    off the left or top edge has a negative origin, fails that test, and is read
    as pixel xyxy -- collapsing to a degenerate box. `_crop_face` has always
    behaved this way, and the effective identity score depends on it, so
    changing the interpretation is a decision change and is out of scope for a
    shadow-only PR.

    What matters here is that it degrades to "no measurement" rather than to a
    silent whole-image comparison, and that it degrades identically on both
    sides.
    """

    image = _gradient((640, 480))
    assert crop_identity_region(image, (-0.10, -0.08, 0.30, 0.28)) is None


def test_ambiguous_box_degrades_symmetrically_on_both_sides():
    source = _gradient((900, 1200))
    candidate = _gradient((768, 768))
    ambiguous = (-0.10, -0.08, 0.30, 0.28)
    assert crop_identity_region(source, ambiguous) is None
    assert crop_identity_region(candidate, ambiguous) is None


def test_degenerate_boxes_yield_no_measurement():
    image = _gradient((640, 480))
    for bad in ((0.5, 0.5, 0.0, 0.0), (0.5, 0.5, -0.1, -0.1), (0.2,), None):
        assert crop_identity_region(image, bad) is None, bad
