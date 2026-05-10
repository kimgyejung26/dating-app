from pathlib import Path

from gltf_glb import GlbDocument, degquat, find_animation, find_node_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = PROJECT_ROOT / "assets" / "models" / "stamp_scene.glb"

STAMP_TIMES = [0.0, 0.12, 0.32, 0.44, 0.50, 0.68, 1.15]
STAMP_TRANSLATIONS = [
    (0.0, 6.25, 0.0),
    (0.0, 5.70, 0.0),
    (0.0, 1.25, 0.0),
    (0.0, 0.22, 0.0),
    (0.0, 0.022, 0.0),
    (0.0, 0.42, 0.0),
    (0.0, 0.30, 0.0),
]
STAMP_ROTATIONS = [
    degquat(1.5, -8.0, -1.0),
    degquat(1.2, -6.0, -0.8),
    degquat(0.8, -4.0, -0.5),
    degquat(0.2, -1.0, 0.0),
    degquat(0.0, 0.0, 0.0),
    degquat(1.0, 3.5, -0.8),
    degquat(0.5, 1.5, -0.4),
]

INK_TIMES = [0.0, 0.46, 0.50, 0.68, 1.15]
INK_SCALES = [
    (0.001, 0.001, 0.001),
    (0.001, 0.001, 0.001),
    (1.12, 1.12, 1.12),
    (1.0, 1.0, 1.0),
    (1.0, 1.0, 1.0),
]


def replace_channel(doc, animation, node_index, path, times, values, value_type):
    for channel in animation.get("channels", []):
        target = channel.get("target", {})
        if target.get("node") == node_index and target.get("path") == path:
            sampler = animation["samplers"][channel["sampler"]]
            sampler["input"] = doc.append_accessor([(time,) for time in times], "SCALAR")
            sampler["output"] = doc.append_accessor(values, value_type)
            sampler["interpolation"] = "LINEAR"
            return
    raise ValueError(f"Animation channel not found: node={node_index}, path={path}")


def configure_top_down_camera(doc):
    json_doc = doc.json
    try:
        camera_node_index = find_node_index(json_doc, "TopDownCamera")
    except ValueError:
        camera_node_index = find_node_index(json_doc, "Camera")
    camera_node = json_doc["nodes"][camera_node_index]
    camera_node["name"] = "TopDownCamera"
    camera_node["translation"] = [0.0, 6.0, 0.0]
    camera_node["rotation"] = list(degquat(-90.0, 0.0, 0.0))
    camera_node.pop("scale", None)

    camera = json_doc["cameras"][camera_node["camera"]]
    camera["name"] = "TopDownCamera"
    camera["type"] = "orthographic"
    camera.pop("perspective", None)
    camera["orthographic"] = {
        "xmag": 4.8,
        "ymag": 4.8,
        "znear": 0.01,
        "zfar": 20.0,
    }


def configure_stamp_animation(doc):
    json_doc = doc.json
    stamp_root_index = find_node_index(json_doc, "StampRoot")
    ink_root_index = find_node_index(json_doc, "InkDecal")
    animation = find_animation(json_doc, "Stamp")

    stamp_root = json_doc["nodes"][stamp_root_index]
    stamp_root["translation"] = list(STAMP_TRANSLATIONS[0])
    stamp_root["rotation"] = list(STAMP_ROTATIONS[0])

    ink_root = json_doc["nodes"][ink_root_index]
    ink_root["scale"] = list(INK_SCALES[0])

    replace_channel(
        doc,
        animation,
        stamp_root_index,
        "translation",
        STAMP_TIMES,
        STAMP_TRANSLATIONS,
        "VEC3",
    )
    replace_channel(
        doc,
        animation,
        stamp_root_index,
        "rotation",
        STAMP_TIMES,
        STAMP_ROTATIONS,
        "VEC4",
    )
    replace_channel(
        doc,
        animation,
        ink_root_index,
        "scale",
        INK_TIMES,
        INK_SCALES,
        "VEC3",
    )


def main():
    if not OUT_FILE.exists():
        raise FileNotFoundError(f"Missing source GLB: {OUT_FILE}")

    doc = GlbDocument.load(OUT_FILE)
    doc.json.setdefault("asset", {})[
        "generator"
    ] = "tools/create_stamp_scene_glb.py top-down patcher"

    configure_top_down_camera(doc)
    configure_stamp_animation(doc)
    doc.save(OUT_FILE)

    print(f"Exported: {OUT_FILE}")
    print(f"Size: {OUT_FILE.stat().st_size} bytes")


if __name__ == "__main__":
    main()
