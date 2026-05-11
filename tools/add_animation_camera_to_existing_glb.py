import argparse
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description=(
            "Import an existing static stamp GLB, preserve its design, "
            "add StampRoot animation and TopDownCamera, then export a new GLB."
        )
    )

    parser.add_argument(
        "--in",
        dest="input_glb",
        type=str,
        default=str(project_root / "assets" / "models" / "stamp_scene.glb"),
        help="Input static GLB path.",
    )

    parser.add_argument(
        "--out",
        dest="output_glb",
        type=str,
        default=str(project_root / "assets" / "models" / "stamp_scene_animated.glb"),
        help="Output animated GLB path.",
    )

    parser.add_argument(
        "--decal",
        type=str,
        default=str(project_root / "assets" / "models" / "stamp_decal_transparent.png"),
        help="Optional decal texture path. Used only with --add-paper-decal.",
    )

    parser.add_argument(
        "--add-paper-decal",
        action="store_true",
        help=(
            "Optionally add Paper and InkDecal scene nodes. "
            "This does not change the stamp design itself."
        ),
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Animation FPS.",
    )

    parser.add_argument(
        "--frame-end",
        type=int,
        default=35,
        help="Animation end frame.",
    )

    return parser.parse_args(argv)


# ---------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def import_glb(path: Path):
    print(f"[import] GLB: {path}")
    bpy.ops.import_scene.gltf(filepath=str(path))


def object_is_descendant_of(obj, parent):
    p = obj.parent
    while p is not None:
        if p == parent:
            return True
        p = p.parent
    return False


def is_stamp_design_object(obj):
    """
    Select only existing stamp design objects.
    Do not include cameras, lights, paper, decal, pulse, or hidden reference markers.
    """
    if obj.type not in {"MESH", "CURVE", "SURFACE", "FONT"}:
        return False

    name = obj.name

    excluded_prefixes = (
        "Paper",
        "InkDecal",
        "InkDecalPlane",
        "ImpactPulse",
        "TopDownCamera",
        "StampTopDownCamera",
        "FrontPreviewCamera",
        "TopDownPreviewCamera",
        "Camera",
        "RedDot_Center_Origin_Marker",
    )

    return not name.startswith(excluded_prefixes)


def collect_stamp_objects():
    stamp_objects = [obj for obj in bpy.context.scene.objects if is_stamp_design_object(obj)]

    if not stamp_objects:
        raise RuntimeError(
            "No stamp mesh objects found. "
            "The GLB may not contain visible mesh geometry."
        )

    print("[stamp] objects that will move with StampRoot:")
    for obj in stamp_objects:
        print(f"  - {obj.name} ({obj.type})")

    return stamp_objects


def compute_bbox(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()

    points = []

    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)

        if not hasattr(evaluated, "bound_box"):
            continue

        for corner in evaluated.bound_box:
            points.append(obj.matrix_world @ Vector(corner))

    if not points:
        raise RuntimeError("Could not compute bounding box for stamp objects.")

    min_v = Vector((
        min(p.x for p in points),
        min(p.y for p in points),
        min(p.z for p in points),
    ))

    max_v = Vector((
        max(p.x for p in points),
        max(p.y for p in points),
        max(p.z for p in points),
    ))

    center = (min_v + max_v) * 0.5
    size = max_v - min_v

    print("[bbox]")
    print(f"  min   : {tuple(round(v, 4) for v in min_v)}")
    print(f"  max   : {tuple(round(v, 4) for v in max_v)}")
    print(f"  center: {tuple(round(v, 4) for v in center)}")
    print(f"  size  : {tuple(round(v, 4) for v in size)}")

    return min_v, max_v, center, size


def ensure_stamp_root(stamp_objects):
    """
    Create an Empty named StampRoot if it does not exist.
    Parent all stamp design meshes under it without changing their world transforms.
    """
    existing = bpy.data.objects.get("StampRoot")

    if existing is not None:
        root = existing
        print("[root] Existing StampRoot found.")
    else:
        root = bpy.data.objects.new("StampRoot", None)
        root.empty_display_type = "PLAIN_AXES"
        root.empty_display_size = 0.4
        root.location = (0.0, 0.0, 0.0)
        bpy.context.collection.objects.link(root)
        print("[root] Created new Empty: StampRoot")

    for obj in stamp_objects:
        if obj == root:
            continue

        if object_is_descendant_of(obj, root):
            continue

        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world

    return root


# ---------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------

def ensure_topdown_camera(bbox_center, bbox_size):
    """
    Blender internal coordinate is Z-up.
    This creates a camera above +Z looking down -Z.
    Blender's glTF exporter will handle the coordinate conversion.
    """
    max_xy = max(bbox_size.x, bbox_size.y)
    height = max(bbox_size.z, 0.1)

    camera_z = bbox_center.z + height + max(max_xy * 2.2, 4.5)
    ortho_scale = max(max_xy * 1.45, 3.2)

    cam = bpy.data.objects.get("TopDownCamera")

    if cam is None:
        cam_data = bpy.data.cameras.new("TopDownCameraData")
        cam = bpy.data.objects.new("TopDownCamera", cam_data)
        bpy.context.collection.objects.link(cam)
        print("[camera] Created TopDownCamera.")
    else:
        print("[camera] Updating existing TopDownCamera.")

    cam.location = (bbox_center.x, bbox_center.y, camera_z)

    # Camera with zero rotation looks along local -Z.
    # From +Z position, this is a top-down view.
    cam.rotation_euler = (0.0, 0.0, 0.0)

    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho_scale
    cam.data.clip_start = 0.01
    cam.data.clip_end = 100.0

    bpy.context.scene.camera = cam

    print("[camera] TopDownCamera settings:")
    print(f"  location   : {tuple(round(v, 4) for v in cam.location)}")
    print(f"  rotation   : {tuple(round(math.degrees(v), 4) for v in cam.rotation_euler)} degrees")
    print(f"  type       : {cam.data.type}")
    print(f"  orthoScale : {cam.data.ortho_scale:.4f}")

    # Compatibility fallback: some older scripts try "Camera" after "TopDownCamera".
    if bpy.data.objects.get("Camera") is None:
        compat_data = cam.data.copy()
        compat = bpy.data.objects.new("Camera", compat_data)
        compat.matrix_world = cam.matrix_world.copy()
        bpy.context.collection.objects.link(compat)
        print("[camera] Created compatibility camera node: Camera")

    return cam


# ---------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------

def clear_animation(obj):
    if obj.animation_data:
        obj.animation_data_clear()


def insert_root_key(root, frame, base_loc, base_rot, z_offset, rot_degrees):
    bpy.context.scene.frame_set(frame)

    rx, ry, rz = rot_degrees

    root.location = (
        base_loc.x,
        base_loc.y,
        base_loc.z + z_offset,
    )

    root.rotation_euler = (
        base_rot.x + math.radians(rx),
        base_rot.y + math.radians(ry),
        base_rot.z + math.radians(rz),
    )

    root.keyframe_insert(data_path="location", frame=frame)
    root.keyframe_insert(data_path="rotation_euler", frame=frame)


def add_stamp_animation(root, bbox_size, topdown_camera, fps=30, frame_end=35):
    """
    Add a top-down friendly stamping animation.
    The design is not changed; only the StampRoot transform is animated.
    """
    clear_animation(root)

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_end
    bpy.context.scene.render.fps = fps

    base_loc = root.location.copy()
    base_rot = root.rotation_euler.copy()

    # Use model height to choose a reasonable lift distance.
    height = max(bbox_size.z, 1.0)
    lift = max(1.35, min(2.1, height * 0.55))
    exit_lift = max(
        topdown_camera.location.z - root.location.z + 1.0,
        lift * 1.4,
    )

    keyframes = [
        # frame, z offset, rotation degrees
        (1,  lift,        (1.2, -1.0, -8.0)),
        (9,  lift * 0.55, (0.8, -0.6, -4.0)),
        (14, lift * 0.16, (0.3, -0.2, -1.0)),
        (16, 0.020,       (0.0,  0.0,  0.0)),  # impact
        (21, lift * 0.27, (1.0,  0.6,  3.0)),
        (29, lift * 0.20, (0.5,  0.2,  1.5)),
        # Move only along camera depth so the paper decal remains visible
        # when Flutter pauses near the end of the one-shot animation.
        (30, exit_lift * 0.62, (0.5, 0.2, 1.5)),
        (31, exit_lift,        (0.5, 0.2, 1.5)),
        (35, exit_lift,        (0.5, 0.2, 1.5)),
    ]

    for frame, z_offset, rot in keyframes:
        insert_root_key(
            root=root,
            frame=frame,
            base_loc=base_loc,
            base_rot=base_rot,
            z_offset=z_offset,
            rot_degrees=rot,
        )

    if root.animation_data and root.animation_data.action:
        root.animation_data.action.name = "Stamp"

        for fcurve in root.animation_data.action.fcurves:
            for key in fcurve.keyframe_points:
                key.interpolation = "BEZIER"

    print("[animation] Added Stamp animation to StampRoot.")
    print(f"  fps       : {fps}")
    print(f"  frame end : {frame_end}")
    print(f"  lift      : {lift:.4f}")
    print(f"  exit lift : {exit_lift:.4f}")


# ---------------------------------------------------------------------
# Optional Paper + InkDecal
# ---------------------------------------------------------------------

def create_simple_material(name, color, roughness=0.5, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color

    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = color
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha

    if alpha < 1.0:
        mat.blend_method = "BLEND"
        mat.show_transparent_back = True

    return mat


def create_image_alpha_material(name, image_path: Path):
    image = bpy.data.images.load(str(image_path))

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    mat.show_transparent_back = True
    mat.use_backface_culling = False

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.name = "DecalTexture"
    tex.image = image

    if bsdf:
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

        if "Alpha" in bsdf.inputs:
            links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])

        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.55

    return mat


def create_uv_plane(name, size, z, material):
    half = size * 0.5

    verts = [
        (-half, -half, z),
        ( half, -half, z),
        ( half,  half, z),
        (-half,  half, z),
    ]

    faces = [(0, 1, 2, 3)]

    mesh = bpy.data.meshes.new(f"{name}Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    uv = mesh.uv_layers.new(name="UVMap")
    # Loop order follows face vertex order.
    uv_coords = [
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ]

    for i, coord in enumerate(uv_coords):
        uv.data[i].uv = coord

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    return obj


def add_paper_and_ink_decal_if_requested(decal_path: Path, bbox_size):
    max_xy = max(bbox_size.x, bbox_size.y)
    paper_size = max(max_xy * 1.75, 4.0)
    decal_size = max(max_xy * 0.88, 1.6)

    if bpy.data.objects.get("Paper") is None:
        paper_mat = create_simple_material(
            "WarmWhitePaper",
            color=(1.0, 0.96, 0.88, 1.0),
            roughness=0.85,
            metallic=0.0,
            alpha=1.0,
        )

        paper = create_uv_plane(
            name="Paper",
            size=paper_size,
            z=-0.035,
            material=paper_mat,
        )

        print("[paper] Created Paper.")

    ink_root = bpy.data.objects.get("InkDecal")

    if ink_root is None:
        ink_root = bpy.data.objects.new("InkDecal", None)
        ink_root.empty_display_type = "CIRCLE"
        ink_root.empty_display_size = decal_size * 0.5
        bpy.context.collection.objects.link(ink_root)
        print("[decal] Created InkDecal empty.")

    if decal_path.exists():
        if bpy.data.objects.get("InkDecalPlane") is None:
            decal_mat = create_image_alpha_material(
                "StampDecalTransparentMaterial",
                decal_path,
            )

            plane = create_uv_plane(
                name="InkDecalPlane",
                size=decal_size,
                z=0.006,
                material=decal_mat,
            )

            plane.parent = ink_root
            print(f"[decal] Created InkDecalPlane using: {decal_path}")
    else:
        print(f"[decal] Decal image not found, skipping decal plane: {decal_path}")

    # Animate InkDecal scale.
    clear_animation(ink_root)

    scale_keys = [
        (1,  0.001),
        (14, 0.001),
        (16, 1.12),
        (21, 1.0),
        (35, 1.0),
    ]

    for frame, scale in scale_keys:
        bpy.context.scene.frame_set(frame)
        ink_root.scale = (scale, scale, scale)
        ink_root.keyframe_insert(data_path="scale", frame=frame)

    if ink_root.animation_data and ink_root.animation_data.action:
        ink_root.animation_data.action.name = "Stamp_InkDecal"

        for fcurve in ink_root.animation_data.action.fcurves:
            for key in fcurve.keyframe_points:
                key.interpolation = "BEZIER"

    print("[decal] Added InkDecal scale animation.")


# ---------------------------------------------------------------------
# GLB JSON patch / inspect
# ---------------------------------------------------------------------

GLB_MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A


def read_glb_chunks(path: Path):
    data = path.read_bytes()

    magic, version, total_length = struct.unpack_from("<III", data, 0)

    if magic != GLB_MAGIC:
        raise RuntimeError("Not a GLB file.")

    chunks = []
    offset = 12

    while offset < len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk_data = data[offset: offset + chunk_length]
        offset += chunk_length
        chunks.append((chunk_type, chunk_data))

    return version, chunks


def write_glb_chunks(path: Path, version: int, chunks):
    body = bytearray()

    for chunk_type, chunk_data in chunks:
        body.extend(struct.pack("<II", len(chunk_data), chunk_type))
        body.extend(chunk_data)

    total_length = 12 + len(body)

    output = bytearray()
    output.extend(struct.pack("<III", GLB_MAGIC, version, total_length))
    output.extend(body)

    path.write_bytes(output)


def load_glb_json(path: Path):
    version, chunks = read_glb_chunks(path)

    for chunk_type, chunk_data in chunks:
        if chunk_type == JSON_CHUNK:
            text = chunk_data.decode("utf-8").rstrip(" \t\r\n\0")
            return version, chunks, json.loads(text)

    raise RuntimeError("No JSON chunk found in GLB.")


def save_glb_json(path: Path, version: int, chunks, doc):
    json_bytes = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)

    new_chunks = []

    for chunk_type, chunk_data in chunks:
        if chunk_type == JSON_CHUNK:
            new_chunks.append((chunk_type, json_bytes))
        else:
            new_chunks.append((chunk_type, chunk_data))

    write_glb_chunks(path, version, new_chunks)


def ensure_animation_name_stamp(path: Path):
    version, chunks, doc = load_glb_json(path)

    animations = doc.get("animations", [])

    if not animations:
        raise RuntimeError(
            "Exported GLB still has no animations. "
            "Check whether keyframes were inserted and export_animations=True was used."
        )

    if not any(anim.get("name") == "Stamp" for anim in animations):
        animations[0]["name"] = "Stamp"
        print("[glb] Renamed first animation clip to Stamp.")
        save_glb_json(path, version, chunks, doc)

    return doc


def merge_animations_into_stamp(path: Path):
    version, chunks, doc = load_glb_json(path)
    animations = doc.get("animations", [])

    if not animations:
        raise RuntimeError(
            "Exported GLB still has no animations. "
            "Check whether keyframes were inserted and export_animations=True was used."
        )

    stamp_animation = next(
        (animation for animation in animations if animation.get("name") == "Stamp"),
        animations[0],
    )
    stamp_animation["name"] = "Stamp"

    merged_samplers = list(stamp_animation.get("samplers", []))
    merged_channels = list(stamp_animation.get("channels", []))
    existing_targets = {
        (
            channel.get("target", {}).get("node"),
            channel.get("target", {}).get("path"),
        )
        for channel in merged_channels
    }

    changed = stamp_animation is not animations[0] or len(animations) != 1

    for animation in animations:
        if animation is stamp_animation:
            continue

        for channel in animation.get("channels", []):
            target = channel.get("target", {})
            target_key = (target.get("node"), target.get("path"))

            if target_key in existing_targets:
                continue

            sampler = animation["samplers"][channel["sampler"]]
            new_sampler_index = len(merged_samplers)
            merged_samplers.append(dict(sampler))

            merged_channel = dict(channel)
            merged_channel["target"] = dict(target)
            merged_channel["sampler"] = new_sampler_index
            merged_channels.append(merged_channel)
            existing_targets.add(target_key)
            changed = True

    stamp_animation["samplers"] = merged_samplers
    stamp_animation["channels"] = merged_channels
    doc["animations"] = [stamp_animation]

    if changed:
        print("[glb] Merged exported object actions into one Stamp animation.")
        save_glb_json(path, version, chunks, doc)

    return doc


def inspect_glb(path: Path):
    _, _, doc = load_glb_json(path)

    nodes = doc.get("nodes", [])
    cameras = doc.get("cameras", [])
    animations = doc.get("animations", [])

    node_names = [n.get("name", "") for n in nodes]
    camera_names = []

    for node in nodes:
        if "camera" in node:
            camera_names.append(node.get("name", ""))

    animation_names = [a.get("name", "") for a in animations]

    print("[inspect]")
    print(f"  nodes      : {len(nodes)}")
    print(f"  meshes     : {len(doc.get('meshes', []))}")
    print(f"  materials  : {len(doc.get('materials', []))}")
    print(f"  images     : {len(doc.get('images', []))}")
    print(f"  cameras    : {camera_names}")
    print(f"  animations : {animation_names}")

    required_nodes = ["StampRoot", "TopDownCamera"]
    for name in required_nodes:
        print(f"  has {name}: {name in node_names}")

    print(f"  has Stamp animation: {'Stamp' in animation_names}")


# ---------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------

def export_glb(out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    attempts = [
        {
            "filepath": str(out_path),
            "export_format": "GLB",
            "export_animations": True,
            "export_frame_range": True,
            "export_frame_step": 1,
            "export_force_sampling": True,
            "export_cameras": True,
            "export_lights": True,
            "export_animation_mode": "SCENE",
            "export_nla_strips_merged_animation_name": "Stamp",
        },
        {
            "filepath": str(out_path),
            "export_format": "GLB",
            "export_animations": True,
            "export_frame_range": True,
            "export_frame_step": 1,
            "export_force_sampling": True,
            "export_cameras": True,
            "export_animation_mode": "SCENE",
            "export_nla_strips_merged_animation_name": "Stamp",
        },
        {
            "filepath": str(out_path),
            "export_format": "GLB",
            "export_animations": True,
            "export_frame_range": True,
            "export_frame_step": 1,
            "export_force_sampling": True,
            "export_cameras": True,
        },
        {
            "filepath": str(out_path),
            "export_format": "GLB",
            "export_animations": True,
            "export_cameras": True,
        },
    ]

    last_error = None

    for kwargs in attempts:
        try:
            bpy.ops.export_scene.gltf(**kwargs)
            size_mb = out_path.stat().st_size / (1024 * 1024)
            print(f"[export] GLB exported: {out_path}")
            print(f"[export] size: {size_mb:.2f} MB")
            return
        except TypeError as exc:
            last_error = exc
            print(f"[export] Retry with fewer options because: {exc}")

    raise RuntimeError(f"Failed to export GLB: {last_error}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    args = parse_args()

    input_path = Path(args.input_glb).resolve()
    output_path = Path(args.output_glb).resolve()
    decal_path = Path(args.decal).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input GLB not found: {input_path}")

    clear_scene()
    import_glb(input_path)

    stamp_objects = collect_stamp_objects()
    min_v, max_v, center, size = compute_bbox(stamp_objects)

    root = ensure_stamp_root(stamp_objects)

    # Recompute bbox after parenting just for camera scale.
    stamp_objects_after = collect_stamp_objects()
    min_v, max_v, center, size = compute_bbox(stamp_objects_after)

    topdown_camera = ensure_topdown_camera(center, size)
    add_stamp_animation(
        root,
        size,
        topdown_camera=topdown_camera,
        fps=args.fps,
        frame_end=args.frame_end,
    )

    if args.add_paper_decal:
        add_paper_and_ink_decal_if_requested(decal_path, size)

    export_glb(output_path)
    ensure_animation_name_stamp(output_path)
    merge_animations_into_stamp(output_path)
    inspect_glb(output_path)

    print("[done] Existing stamp design was preserved.")
    print("[done] Added/updated nodes: StampRoot, TopDownCamera, Stamp animation.")


if __name__ == "__main__":
    main()
