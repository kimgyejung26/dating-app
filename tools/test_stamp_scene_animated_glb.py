from __future__ import annotations

import hashlib
import struct
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gltf_glb import GlbDocument, find_animation, find_node_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANIMATED_GLB = PROJECT_ROOT / "assets" / "models" / "stamp_scene_animated.glb"
REFERENCE_DECAL = PROJECT_ROOT / "assets" / "reference" / "safety_stamp_decal.png"


def embedded_images(path: Path) -> list[bytes]:
    doc = GlbDocument.load(path)
    images: list[bytes] = []
    for image in doc.json.get("images", []):
        buffer_view = doc.json["bufferViews"][image["bufferView"]]
        offset = buffer_view.get("byteOffset", 0)
        length = buffer_view["byteLength"]
        images.append(bytes(doc.bin[offset : offset + length]))
    return images


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)

    if pa <= pb and pa <= pc:
        return a

    if pb <= pc:
        return b

    return c


def decode_png_rgba(data: bytes) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Not a PNG file")

    offset = 8
    width = height = color_type = bit_depth = None
    compressed = bytearray()

    while offset < len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        offset += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _comp, _filter, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if bit_depth != 8 or color_type not in {2, 6} or interlace != 0:
                raise ValueError(
                    "Only non-interlaced 8-bit RGB/RGBA PNG files are supported"
                )
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None or color_type is None or bit_depth is None:
        raise ValueError("PNG is missing IHDR")

    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    rows: list[bytearray] = []
    read_offset = 0

    for _row_index in range(height):
        filter_type = raw[read_offset]
        read_offset += 1
        row = bytearray(raw[read_offset : read_offset + stride])
        read_offset += stride
        previous = rows[-1] if rows else bytearray(stride)

        for index in range(stride):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0

            if filter_type == 1:
                row[index] = (row[index] + left) & 0xFF
            elif filter_type == 2:
                row[index] = (row[index] + up) & 0xFF
            elif filter_type == 3:
                row[index] = (row[index] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                row[index] = (row[index] + paeth(left, up, upper_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"Unsupported PNG filter type: {filter_type}")

        rows.append(row)

    pixels: list[tuple[int, int, int, int]] = []
    for row in rows:
        for index in range(0, stride, channels):
            if channels == 4:
                pixels.append(tuple(row[index : index + 4]))
            else:
                r, g, b = row[index : index + 3]
                pixels.append((r, g, b, 255))

    return width, height, pixels


def animation_channel(doc: GlbDocument, node_name: str, path: str):
    animation = find_animation(doc.json, "Stamp")
    node_index = find_node_index(doc.json, node_name)

    for channel in animation.get("channels", []):
        target = channel.get("target", {})
        if target.get("node") == node_index and target.get("path") == path:
            sampler = animation["samplers"][channel["sampler"]]
            return (
                doc.accessor_values(sampler["input"]),
                doc.accessor_values(sampler["output"]),
            )

    raise AssertionError(f"Missing Stamp channel: {node_name}.{path}")


class StampSceneAnimatedGlbTest(unittest.TestCase):
    def test_has_only_stamp_animation_clip(self) -> None:
        doc = GlbDocument.load(ANIMATED_GLB)

        self.assertEqual(["Stamp"], [a.get("name") for a in doc.json.get("animations", [])])

    def test_embeds_reference_safety_stamp_decal_as_transparent_texture(self) -> None:
        ref_width, ref_height, ref_pixels = decode_png_rgba(REFERENCE_DECAL.read_bytes())
        ref_rgb = [pixel[:3] for pixel in ref_pixels]
        embedded = embedded_images(ANIMATED_GLB)

        for image_data in embedded:
            width, height, pixels = decode_png_rgba(image_data)

            if width != ref_width or height != ref_height:
                continue

            if [pixel[:3] for pixel in pixels] != ref_rgb:
                continue

            alpha_values = [pixel[3] for pixel in pixels]
            if min(alpha_values) == 0 and max(alpha_values) == 255:
                return

        embedded_hashes = [
            hashlib.sha256(image_data).hexdigest().upper() for image_data in embedded
        ]
        self.fail(
            "stamp_scene_animated.glb does not embed a transparent texture that "
            "visually matches assets/reference/safety_stamp_decal.png. "
            f"Embedded image hashes: {embedded_hashes}"
        )

    def test_ink_decal_remains_scaled_after_impact(self) -> None:
        doc = GlbDocument.load(ANIMATED_GLB)
        _times, scales = animation_channel(doc, "InkDecal", "scale")

        self.assertLessEqual(max(scales[0]), 0.0011)
        self.assertEqual((1.0, 1.0, 1.0), tuple(round(v, 4) for v in scales[-1]))

    def test_stamp_moves_behind_topdown_camera_before_pause_frame(self) -> None:
        doc = GlbDocument.load(ANIMATED_GLB)
        camera_index = find_node_index(doc.json, "TopDownCamera")
        camera_y = doc.json["nodes"][camera_index]["translation"][1]
        times, translations = animation_channel(doc, "StampRoot", "translation")

        for translation in translations:
            self.assertLess(abs(translation[0]), 0.001)
            self.assertLess(abs(translation[2]), 0.001)

        held_samples = [
            translation
            for time, translation in zip(times, translations)
            if time[0] >= 1.08
        ]

        self.assertGreaterEqual(len(held_samples), 2)
        for translation in held_samples:
            self.assertGreater(translation[1], camera_y)


if __name__ == "__main__":
    unittest.main()
