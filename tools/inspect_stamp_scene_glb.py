from pathlib import Path

from gltf_glb import GlbDocument, find_animation, find_node_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GLB_FILE = PROJECT_ROOT / "assets" / "models" / "stamp_scene.glb"


def approx(value, target, tolerance):
    return abs(value - target) <= tolerance


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def channel_values(doc, animation, node_index, path):
    for channel in animation.get("channels", []):
        target = channel.get("target", {})
        if target.get("node") == node_index and target.get("path") == path:
            sampler = animation["samplers"][channel["sampler"]]
            times = [value[0] for value in doc.accessor_values(sampler["input"])]
            values = doc.accessor_values(sampler["output"])
            return times, values
    raise AssertionError(f"Missing animation channel: node={node_index}, path={path}")


def main():
    require(GLB_FILE.exists(), f"Missing GLB file: {GLB_FILE}")

    doc = GlbDocument.load(GLB_FILE)
    json_doc = doc.json

    animation = find_animation(json_doc, "Stamp")
    camera_node_index = find_node_index(json_doc, "TopDownCamera")
    camera_node = json_doc["nodes"][camera_node_index]
    camera = json_doc["cameras"][camera_node["camera"]]

    require(camera["type"] == "orthographic", "TopDownCamera must be orthographic")
    require(camera_node["translation"][1] >= 4.0, "TopDownCamera Y must be >= 4")
    require(
        approx(camera_node["rotation"][0], -0.70710678, 0.02)
        and approx(camera_node["rotation"][3], 0.70710678, 0.02),
        "TopDownCamera must look down from +Y toward -Y",
    )

    stamp_root_index = find_node_index(json_doc, "StampRoot")
    stamp_times, stamp_trans = channel_values(
        doc, animation, stamp_root_index, "translation"
    )
    require(stamp_times[-1] >= 1.1, "Stamp animation should last about 1.15s")
    require(
        all(abs(value[0]) <= 0.001 and abs(value[2]) <= 0.001 for value in stamp_trans),
        "StampRoot translation must keep X/Z nearly fixed",
    )

    y_values = [value[1] for value in stamp_trans]
    require(y_values[0] >= 6.0, "StampRoot should start out of the top-down view")
    require(
        y_values[1] >= 5.5,
        "StampRoot should remain high at the beginning of the stamp motion",
    )
    require(min(y_values) <= 0.03, "StampRoot should reach the paper at impact")
    require(y_values[-2] > y_values[-1] > min(y_values), "StampRoot should bounce up")

    _stamp_rot_times, stamp_rots = channel_values(doc, animation, stamp_root_index, "rotation")
    impact_rotation = stamp_rots[3]
    require(
        abs(impact_rotation[0]) < 0.02 and abs(impact_rotation[2]) < 0.02,
        "StampRoot impact rotation should be nearly vertical",
    )

    ink_root_index = find_node_index(json_doc, "InkDecal")
    ink_times, ink_scales = channel_values(doc, animation, ink_root_index, "scale")
    require(ink_times[1] >= 0.45, "InkDecal should remain hidden until impact")
    require(
        ink_scales[0][0] <= 0.002 and ink_scales[1][0] <= 0.002,
        "InkDecal scale should stay near zero before impact",
    )
    require(ink_scales[2][0] >= 1.0, "InkDecal should pop above full scale at impact")
    require(ink_scales[-1][0] == 1.0, "InkDecal should settle at full scale")

    print("GLB inspection passed")
    print(f"Animation: {animation['name']}")
    print(f"Camera: {camera_node['name']} {camera['type']} {camera_node['translation']}")
    print(f"StampRoot Y keyframes: {[round(value, 3) for value in y_values]}")
    print(f"InkDecal scale keyframes: {[round(value[0], 3) for value in ink_scales]}")


if __name__ == "__main__":
    main()
