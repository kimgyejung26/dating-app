"""Deterministic, non-user synthetic control images for watermark evaluation.

Every image is drawn from scratch with Pillow: a flat gradient, an abstract
silhouette, and the one construct the control exists to test. No photograph, no
face, no user data, no network, no model. The label is the construction intent,
fixed before any model or policy sees the image.

Purpose and limits (repeated in the manifest so it travels with the images):

  * POLICY REACHABILITY and MODEL CAPABILITY only -- can the pipeline see an
    overlay at all, does a known-positive reach review/reject, does garment or
    signage text stay allowed.
  * NEVER production prevalence, precision, or recall. Synthetic controls are
    cleaner than generated avatars; a model that finds these can still miss the
    real thing, and the mix here says nothing about the mix in production.

Brand and watermark words are fictitious on purpose.

  python scripts/avatar_watermark_controls.py --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

GENERATOR_VERSION = "avatar_watermark_controls_v1"
LABEL_SCHEMA_VERSION = "avatar_watermark_label_schema_v2"
PROVENANCE_CATEGORY = "locally_generated_synthetic_without_user_data"
WIDTH, HEIGHT = 512, 768
WATERMARK_WORD = "SAMPLEMARK"
BRAND_WORD = "KORVA"

REQUIRED_CONTROL_KINDS = (
    "overlay_watermark",
    "corner_watermark",
    "edge_watermark",
    "transparent_watermark",
    "garment_text",
    "background_signage",
    "brand_text",
    "graphical_logo",
    "no_text",
)


@dataclass(frozen=True)
class ControlSpec:
    evaluation_id: str
    control_kind: str
    primary_label: str
    all_visible_classes: tuple[str, ...]
    construction: dict = field(default_factory=dict)


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1 has no sized default font
        return ImageFont.load_default()


def _base() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        shade = 200 - int(60 * y / HEIGHT)
        draw.line([(0, y), (WIDTH, y)], fill=(shade, shade - 10, shade - 25))
    # Abstract silhouette: an ellipse and a trapezoid. Not a person, not a face.
    draw.ellipse([186, 150, 326, 310], fill=(170, 140, 120))
    draw.polygon([(150, 740), (362, 740), (330, 360), (182, 360)], fill=(60, 80, 110))
    return image


def _overlay(image: Image.Image, painter: Callable[[ImageDraw.ImageDraw], None]) -> Image.Image:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    painter(ImageDraw.Draw(layer))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def _tiled_watermark(image):
    font = _font(28)

    def paint(draw):
        for row in range(0, HEIGHT, 130):
            for col in range(-60, WIDTH, 220):
                draw.text((col + (row // 130) % 2 * 90, row + 40), WATERMARK_WORD, font=font, fill=(255, 255, 255, 110))

    return _overlay(image, paint)


def _corner_watermark(image):
    font = _font(18)
    return _overlay(image, lambda d: d.text((372, 738), WATERMARK_WORD, font=font, fill=(255, 255, 255, 235)))


def _edge_watermark(image):
    font = _font(16)
    return _overlay(image, lambda d: d.text((206, 6), WATERMARK_WORD, font=font, fill=(255, 255, 255, 235)))


def _transparent_watermark(image):
    font = _font(64)
    return _overlay(image, lambda d: d.text((40, 400), WATERMARK_WORD, font=font, fill=(255, 255, 255, 55)))


def _garment_text(image):
    draw = ImageDraw.Draw(image)
    draw.text((200, 470), "OCEAN CLUB", font=_font(22), fill=(235, 235, 235))
    return image


def _background_signage(image):
    draw = ImageDraw.Draw(image)
    draw.rectangle([24, 60, 150, 120], fill=(120, 40, 40), outline=(40, 20, 20), width=3)
    draw.line([(87, 120), (87, 250)], fill=(40, 30, 30), width=4)
    draw.text((46, 76), "CAFE", font=_font(26), fill=(245, 230, 200))
    return image


def _brand_text(image):
    draw = ImageDraw.Draw(image)
    draw.ellipse([232, 440, 252, 460], outline=(230, 230, 230), width=2)
    draw.text((258, 440), BRAND_WORD, font=_font(18), fill=(230, 230, 230))
    return image


def _graphical_logo(image):
    def paint(draw):
        draw.ellipse([424, 16, 496, 88], fill=(250, 200, 40, 230))
        draw.polygon([(460, 26), (486, 76), (434, 76)], fill=(30, 30, 30, 230))

    return _overlay(image, paint)


def _generative_text_artifact(image):
    rng = random.Random(20260911)
    draw = ImageDraw.Draw(image)
    x = 196
    for _ in range(9):
        for _ in range(3):
            x0 = x + rng.randint(0, 8)
            y0 = 470 + rng.randint(0, 14)
            draw.line([(x0, y0), (x0 + rng.randint(-6, 6), y0 + rng.randint(4, 16))], fill=(230, 230, 230), width=2)
        x += 14
    return image


def _no_text(image):
    return image


CONTROLS: tuple[tuple[ControlSpec, Callable[[Image.Image], Image.Image]], ...] = (
    (ControlSpec("ctl-01", "overlay_watermark", "OVERLAY_WATERMARK", ("OVERLAY_WATERMARK",),
                 {"placement": "tiled", "repeated": True, "alpha": 110}), _tiled_watermark),
    (ControlSpec("ctl-02", "corner_watermark", "OVERLAY_WATERMARK", ("OVERLAY_WATERMARK",),
                 {"placement": "corner", "repeated": False, "alpha": 235}), _corner_watermark),
    (ControlSpec("ctl-03", "edge_watermark", "OVERLAY_WATERMARK", ("OVERLAY_WATERMARK",),
                 {"placement": "edge", "repeated": False, "alpha": 235}), _edge_watermark),
    (ControlSpec("ctl-04", "transparent_watermark", "OVERLAY_WATERMARK", ("OVERLAY_WATERMARK",),
                 {"placement": "central", "repeated": False, "alpha": 55}), _transparent_watermark),
    (ControlSpec("ctl-05", "garment_text", "GARMENT_TEXT", ("GARMENT_TEXT",),
                 {"placement": "clothing_zone"}), _garment_text),
    (ControlSpec("ctl-06", "background_signage", "BACKGROUND_SIGNAGE", ("BACKGROUND_SIGNAGE",),
                 {"placement": "background"}), _background_signage),
    (ControlSpec("ctl-07", "brand_text", "BRAND_TEXT_OR_MARK", ("BRAND_TEXT_OR_MARK",),
                 {"placement": "clothing_zone", "word": "fictitious"}), _brand_text),
    (ControlSpec("ctl-08", "graphical_logo", "GRAPHICAL_LOGO", ("GRAPHICAL_LOGO",),
                 {"placement": "corner", "hasText": False}), _graphical_logo),
    (ControlSpec("ctl-09", "no_text", "NO_VISIBLE_RELEVANT_TEXT_OR_MARK", (),
                 {}), _no_text),
    (ControlSpec("ctl-10", "generative_text_artifact", "GENERATIVE_TEXT_ARTIFACT", ("GENERATIVE_TEXT_ARTIFACT",),
                 {"placement": "clothing_zone", "seed": 20260911}), _generative_text_artifact),
)


def build_controls() -> list[tuple[ControlSpec, Image.Image]]:
    return [(spec, painter(_base())) for spec, painter in CONTROLS]


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def build_manifest(controls: list[tuple[ControlSpec, Image.Image]]) -> dict:
    return {
        "generatorVersion": GENERATOR_VERSION,
        "labelSchema": LABEL_SCHEMA_VERSION,
        "provenanceCategory": PROVENANCE_CATEGORY,
        "labelProvenance": "construction_intent",
        "purpose": "policy reachability and model capability controls",
        "forbiddenUse": "production prevalence, precision or recall estimation",
        "imageSize": [WIDTH, HEIGHT],
        "controls": [
            {
                "evaluationId": spec.evaluation_id,
                "controlKind": spec.control_kind,
                "primaryLabel": spec.primary_label,
                "allVisibleClasses": list(spec.all_visible_classes),
                "construction": dict(spec.construction),
                "pngSha256": hashlib.sha256(png_bytes(image)).hexdigest(),
            }
            for spec, image in controls
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    controls = build_controls()
    for spec, image in controls:
        (args.out / f"{spec.evaluation_id}.png").write_bytes(png_bytes(image))
    manifest = build_manifest(controls)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(controls)} controls and manifest.json to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
