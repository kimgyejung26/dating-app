from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

from gltf_glb import GlbDocument


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLB_FILE = PROJECT_ROOT / "assets" / "models" / "stamp_scene_animated.glb"
JSON_CHUNK = 0x4E4F534A

REQUIRED_NODES = [
    "StampRoot",
    "InkDecal",
    "InkDecalPlane",
    "Paper",
    "TopDownCamera",
]
OPTIONAL_NODES = [
    "StampInkPlate",
    "FrontPreviewCamera",
]
REQUIRED_ANIMATION = "Stamp"
REQUIRED_CHANNELS = [
    ("StampRoot", "translation"),
    ("StampRoot", "rotation"),
    ("InkDecal", "scale"),
]


def read_glb_json(path: Path) -> dict:
    with path.open("rb") as handle:
        header = handle.read(12)
        if len(header) != 12:
            raise ValueError("File is too small to be a GLB")
        magic, version, length = struct.unpack("<4sII", header)
        if magic != b"glTF":
            raise ValueError(f"Invalid GLB magic: {magic!r}")
        if version != 2:
            raise ValueError(f"Unsupported GLB version: {version}")
        if length != path.stat().st_size:
            raise ValueError(f"Header length {length} does not match file size {path.stat().st_size}")

        chunk_header = handle.read(8)
        if len(chunk_header) != 8:
            raise ValueError("Missing GLB JSON chunk header")
        chunk_length, chunk_type = struct.unpack("<II", chunk_header)
        if chunk_type != JSON_CHUNK:
            raise ValueError(f"First GLB chunk is not JSON: {chunk_type}")
        chunk = handle.read(chunk_length)
        return json.loads(chunk.decode("utf-8").rstrip("\x00 "))


def node_index_by_name(json_doc: dict) -> dict[str, int]:
    return {
        node.get("name"): index
        for index, node in enumerate(json_doc.get("nodes", []))
        if node.get("name")
    }


def camera_names(json_doc: dict) -> list[str]:
    names = []
    cameras = json_doc.get("cameras", [])
    for node in json_doc.get("nodes", []):
        camera_index = node.get("camera")
        if camera_index is None:
            continue
        camera = cameras[camera_index]
        names.append(node.get("name") or camera.get("name") or f"camera_{camera_index}")
    return names


def animation_names(json_doc: dict) -> list[str]:
    return [animation.get("name", "") for animation in json_doc.get("animations", [])]


def approx(value: float, expected: float, tolerance: float = 0.02) -> bool:
    return abs(value - expected) <= tolerance


def find_animation(json_doc: dict, name: str) -> dict | None:
    for animation in json_doc.get("animations", []):
        if animation.get("name") == name:
            return animation
    return None


def has_channel(json_doc: dict, animation: dict, node_index: int, path: str) -> bool:
    for channel in animation.get("channels", []):
        target = channel.get("target", {})
        if target.get("node") == node_index and target.get("path") == path:
            return True
    return False


def channel_values(glb: GlbDocument, animation: dict, node_index: int, path: str) -> tuple[list[float], list[tuple[float, ...]]]:
    for channel in animation.get("channels", []):
        target = channel.get("target", {})
        if target.get("node") == node_index and target.get("path") == path:
            sampler = animation["samplers"][channel["sampler"]]
            times = [value[0] for value in glb.accessor_values(sampler["input"])]
            values = glb.accessor_values(sampler["output"])
            return times, values
    raise ValueError(f"Missing animation channel: node={node_index}, path={path}")


def inspect(path: Path) -> int:
    failures = []
    glb = GlbDocument.load(path)
    json_doc = glb.json
    nodes = json_doc.get("nodes", [])
    meshes = json_doc.get("meshes", [])
    materials = json_doc.get("materials", [])
    images = json_doc.get("images", [])
    textures = json_doc.get("textures", [])
    cameras = camera_names(json_doc)
    animations = animation_names(json_doc)
    node_lookup = node_index_by_name(json_doc)

    print(f"path: {path}")
    print(f"nodes count: {len(nodes)}")
    print(f"meshes count: {len(meshes)}")
    print(f"materials count: {len(materials)}")
    print(f"images count: {len(images)}")
    print(f"textures count: {len(textures)}")
    print(f"cameras names: {cameras}")
    print(f"animation names: {animations}")

    for node_name in REQUIRED_NODES:
        exists = node_name in node_lookup
        print(f"required node {node_name}: {'OK' if exists else 'MISSING'}")
        if not exists:
            failures.append(f"missing required node: {node_name}")

    for node_name in OPTIONAL_NODES:
        exists = node_name in node_lookup
        print(f"optional node {node_name}: {'OK' if exists else 'MISSING'}")

    stamp_animations = [
        animation for animation in json_doc.get("animations", []) if animation.get("name") == REQUIRED_ANIMATION
    ]
    if not stamp_animations:
        failures.append("missing required animation: Stamp")
    print(f"required animation Stamp: {'OK' if stamp_animations else 'MISSING'}")

    if stamp_animations:
        stamp = stamp_animations[0]
        for node_name, path_name in REQUIRED_CHANNELS:
            node_index = node_lookup.get(node_name)
            ok = node_index is not None and has_channel(json_doc, stamp, node_index, path_name)
            print(f"required channel {node_name}.{path_name}: {'OK' if ok else 'MISSING'}")
            if not ok:
                failures.append(f"missing required channel: {node_name}.{path_name}")

    if len(stamp_animations) > 1:
        failures.append("multiple animations named Stamp")
    if len(json_doc.get("animations", [])) != 1:
        failures.append(f"expected exactly one animation clip, found {len(json_doc.get('animations', []))}")

    camera_node_index = node_lookup.get("TopDownCamera")
    if camera_node_index is None:
        camera_node_index = node_lookup.get("StampTopDownCamera")
    if camera_node_index is None:
        failures.append("missing top-down camera node named TopDownCamera or StampTopDownCamera")
    else:
        camera_node = nodes[camera_node_index]
        camera = json_doc.get("cameras", [])[camera_node.get("camera", -1)]
        translation = camera_node.get("translation", [0.0, 0.0, 0.0])
        rotation = camera_node.get("rotation", [0.0, 0.0, 0.0, 1.0])
        print(f"top-down camera: {camera_node.get('name')} {camera.get('type')} translation={translation} rotation={rotation}")
        if camera.get("type") != "orthographic":
            failures.append("top-down camera must be orthographic")
        if translation[1] < 4.0:
            failures.append("top-down camera Y translation must be >= 4")
        if abs(translation[0]) > 0.001 or abs(translation[2]) > 0.001:
            failures.append("top-down camera X/Z translation should stay centered on the paper")
        if not (
            approx(rotation[0], -0.70710678)
            and approx(rotation[1], 0.0)
            and approx(rotation[2], 0.0)
            and approx(rotation[3], 0.70710678)
        ):
            failures.append("top-down camera must look from +Y toward -Y")
        orthographic = camera.get("orthographic", {})
        xmag = orthographic.get("xmag", 0.0)
        ymag = orthographic.get("ymag", 0.0)
        print(f"top-down orthographic xmag={xmag} ymag={ymag}")
        if not (0.1 < xmag <= 15.0 and 0.1 < ymag <= 15.0):
            failures.append("top-down orthographic xmag/ymag must be positive and reasonable")

    animation = find_animation(json_doc, REQUIRED_ANIMATION)
    if animation is not None:
        stamp_root_index = node_lookup.get("StampRoot")
        ink_root_index = node_lookup.get("InkDecal")
        if stamp_root_index is not None:
            stamp_times, stamp_trans = channel_values(glb, animation, stamp_root_index, "translation")
            y_values = [value[1] for value in stamp_trans]
            print(f"StampRoot translation times: {[round(value, 3) for value in stamp_times]}")
            print(f"StampRoot Y keyframes: {[round(value, 3) for value in y_values]}")
            if any(abs(value[0]) > 0.001 or abs(value[2]) > 0.001 for value in stamp_trans):
                failures.append("StampRoot translation must keep X/Z nearly fixed")
            impact_candidates = [index for index, time in enumerate(stamp_times) if time <= 0.60]
            impact_index = min(impact_candidates, key=lambda index: y_values[index])
            impact_time = stamp_times[impact_index]
            impact_y = y_values[impact_index]

            if not (0.48 <= impact_time <= 0.56):
                failures.append("StampRoot impact keyframe should be near 0.50s")
            if not y_values[0] > impact_y:
                failures.append("StampRoot Y should move downward into impact")
            post_impact_y = [
                value
                for time, value in zip(stamp_times, y_values)
                if impact_time < time <= 0.90
            ]
            if not post_impact_y or max(post_impact_y) <= impact_y + 0.20:
                failures.append("StampRoot Y should bounce up after impact and settle above paper")
            if camera_node_index is not None:
                camera_y = nodes[camera_node_index].get("translation", [0.0, 0.0, 0.0])[1]
                held_samples = [
                    value
                    for time, value in zip(stamp_times, y_values)
                    if time >= 1.08
                ]
                if not held_samples or any(value <= camera_y for value in held_samples):
                    failures.append(
                        "StampRoot should move behind the top-down camera before Flutter pauses"
                    )

            _stamp_rot_times, stamp_rots = channel_values(glb, animation, stamp_root_index, "rotation")
            print(f"StampRoot rotation keyframes: {[tuple(round(part, 4) for part in value) for value in stamp_rots]}")
            if any(abs(rotation[0]) > 0.02 or abs(rotation[2]) > 0.02 for rotation in stamp_rots):
                failures.append("StampRoot X/Z tilt should stay at top-down-friendly levels")
            impact_rotation = stamp_rots[impact_index]
            if any(abs(component) > 0.005 for component in impact_rotation[:3]):
                failures.append("StampRoot impact rotation should be nearly identity")

        if ink_root_index is not None:
            ink_times, ink_scales = channel_values(glb, animation, ink_root_index, "scale")
            print(f"InkDecal scale times: {[round(value, 3) for value in ink_times]}")
            print(f"InkDecal scale keyframes: {[tuple(round(part, 3) for part in value) for value in ink_scales]}")
            hidden_scales = [
                scale[0]
                for time, scale in zip(ink_times, ink_scales)
                if time <= 0.47
            ]
            if not hidden_scales or max(hidden_scales) > 0.002:
                failures.append("InkDecal scale should remain near zero before impact")
            impact_scales = [
                scale[0]
                for time, scale in zip(ink_times, ink_scales)
                if 0.48 <= time <= 0.56
            ]
            if not impact_scales or max(impact_scales) < 1.0:
                failures.append("InkDecal should pop to at least full scale at impact")
            if tuple(round(value, 3) for value in ink_scales[-1]) != (1.0, 1.0, 1.0):
                failures.append("InkDecal should settle at full scale")

    if not images:
        failures.append("expected at least one embedded decal image")
    if not textures:
        failures.append("expected at least one decal texture")

    if failures:
        print("inspection failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("GLB inspection passed")
    return 0


def main(argv: list[str]) -> int:
    path = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_GLB_FILE
    if not path.exists():
        print(f"Missing GLB file: {path}", file=sys.stderr)
        return 1
    try:
        return inspect(path)
    except Exception as exc:
        print(f"GLB inspection error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
