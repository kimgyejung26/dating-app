from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_stamp_scene_glb as generator
from gltf_glb import GlbDocument, find_animation, find_node_index

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def channel_values(doc: GlbDocument, animation: dict, node_index: int, path: str):
    for channel in animation.get("channels", []):
        target = channel.get("target", {})
        if target.get("node") == node_index and target.get("path") == path:
            sampler = animation["samplers"][channel["sampler"]]
            times = [round(value[0], 3) for value in doc.accessor_values(sampler["input"])]
            values = doc.accessor_values(sampler["output"])
            return times, values
    raise AssertionError(f"Missing animation channel: node={node_index}, path={path}")


class CreateStampSceneGlbPatcherTest(unittest.TestCase):
    def test_patcher_preserves_design_payload_while_updating_top_down_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = PROJECT_ROOT / "assets" / "models" / "stamp_scene.glb"
            target = Path(tmp) / "stamp_scene.glb"
            shutil.copyfile(source, target)

            before = GlbDocument.load(target).json

            with mock.patch.object(generator, "OUT_FILE", target):
                generator.main()

            patched_doc = GlbDocument.load(target)
            after = patched_doc.json

            self.assertEqual(after.get("meshes"), before.get("meshes"))
            self.assertEqual(after.get("materials"), before.get("materials"))
            self.assertEqual(after.get("images"), before.get("images"))
            self.assertEqual(after.get("textures"), before.get("textures"))

            camera_node = after["nodes"][find_node_index(after, "TopDownCamera")]
            camera = after["cameras"][camera_node["camera"]]
            self.assertEqual(camera["type"], "orthographic")
            self.assertEqual(camera_node["translation"], [0.0, 5.8, 0.0])
            self.assertAlmostEqual(camera_node["rotation"][0], -0.70710678, delta=0.02)
            self.assertAlmostEqual(camera_node["rotation"][3], 0.70710678, delta=0.02)
            self.assertEqual(camera["orthographic"]["xmag"], 4.65)
            self.assertEqual(camera["orthographic"]["ymag"], 4.65)

            animation = find_animation(after, "Stamp")
            stamp_root = find_node_index(after, "StampRoot")
            ink_decal = find_node_index(after, "InkDecal")

            stamp_times, stamp_translations = channel_values(patched_doc, animation, stamp_root, "translation")
            self.assertEqual(stamp_times, [0.0, 0.28, 0.44, 0.5, 0.68, 1.15])
            self.assertEqual(
                [(round(x, 3), round(y, 3), round(z, 3)) for x, y, z in stamp_translations],
                [
                    (0.0, 1.65, 0.0),
                    (0.0, 0.9, 0.0),
                    (0.0, 0.22, 0.0),
                    (0.0, 0.022, 0.0),
                    (0.0, 0.42, 0.0),
                    (0.0, 0.3, 0.0),
                ],
            )

            ink_times, ink_scales = channel_values(patched_doc, animation, ink_decal, "scale")
            self.assertEqual(ink_times, [0.0, 0.46, 0.5, 0.68, 1.15])
            self.assertLessEqual(ink_scales[1][0], 0.002)
            self.assertGreaterEqual(ink_scales[2][0], 1.0)
            self.assertEqual(tuple(round(value, 3) for value in ink_scales[-1]), (1.0, 1.0, 1.0))


if __name__ == "__main__":
    unittest.main()
