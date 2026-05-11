import argparse
import math
import sys
from collections import deque
from pathlib import Path

bpy = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GREEN_LINE_PREVIEW = PROJECT_ROOT / "assets" / "models" / "stamp_green_line_preview.glb"
RUNTIME_STAMP_SCENE = PROJECT_ROOT / "assets" / "models" / "stamp_scene.glb"


# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------

DEFAULT_TARGET_BASE_RADIUS = 1.55
DEFAULT_SCREW_STEPS = 160
DEFAULT_RDP_EPSILON = 3.5

GREEN_THRESHOLD = {
    "g_min": 120,
    "r_max": 120,
    "b_max": 150,
}

RED_THRESHOLD = {
    "r_min": 210,
    "g_max": 90,
    "b_max": 90,
}


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(
        description="Create a stamp mesh by revolving a green reference profile line around the red center dot."
    )
    parser.add_argument(
        "--image",
        type=str,
        default=str(PROJECT_ROOT / "assets" / "reference" / "stamp_green_line.png"),
        help="Reference image containing the green profile line and red center dot.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_GREEN_LINE_PREVIEW),
        help=(
            "Output GLB path. Defaults to a preview asset so this Blender-only "
            "mesh export does not overwrite the Flutter runtime stamp_scene.glb."
        ),
    )
    parser.add_argument(
        "--allow-runtime-asset",
        action="store_true",
        help=(
            "Allow writing assets/models/stamp_scene.glb even though this preview "
            "export does not include the Flutter Stamp animation contract."
        ),
    )
    parser.add_argument(
        "--target-base-radius",
        type=float,
        default=DEFAULT_TARGET_BASE_RADIUS,
        help="Maximum radius in Blender units after normalization.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=DEFAULT_SCREW_STEPS,
        help="Screw modifier segment count.",
    )
    parser.add_argument(
        "--rdp-epsilon",
        type=float,
        default=DEFAULT_RDP_EPSILON,
        help="Profile simplification tolerance in image pixels.",
    )
    parser.add_argument(
        "--apply-screw",
        action="store_true",
        help="Apply the Screw modifier after creating it. Leave unset if you want to inspect the modifier stack.",
    )

    return parser.parse_args(argv)


def load_blender_api():
    global bpy
    if bpy is None:
        import bpy as blender_api

        bpy = blender_api


def validate_output_path(out_path: Path, allow_runtime_asset: bool) -> None:
    runtime_asset = RUNTIME_STAMP_SCENE.resolve()

    if out_path.resolve() == runtime_asset and not allow_runtime_asset:
        raise SystemExit(
            "Refusing to overwrite assets/models/stamp_scene.glb. "
            "This green-line generator is a Blender preview export and does not "
            "include the Flutter Stamp animation, InkDecal, or Paper nodes. "
            "Use the default stamp_green_line_preview.glb output, or run "
            "tools/create_stamp_scene_glb.py for the app runtime asset."
        )


# ---------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------

class PixelSource:
    def __init__(self, path: Path):
        self.path = path
        self._pil_image = None
        self._bpy_pixels = None
        self.width = 0
        self.height = 0

        self._load()

    def _load(self):
        try:
            from PIL import Image

            img = Image.open(self.path).convert("RGBA")
            self._pil_image = img
            self.width, self.height = img.size
            print(f"[image] Loaded with Pillow: {self.path} ({self.width}x{self.height})")
            return
        except Exception as exc:
            print(f"[image] Pillow unavailable or failed: {exc}")
            print("[image] Falling back to Blender image API.")

        img = bpy.data.images.load(str(self.path))
        self.width, self.height = img.size
        self._bpy_pixels = list(img.pixels)
        print(f"[image] Loaded with Blender API: {self.path} ({self.width}x{self.height})")

    def get_rgba(self, x: int, y_top: int):
        """
        Return RGBA as 0~255 integers.
        x/y_top use normal image coordinates: origin at top-left.
        """
        if self._pil_image is not None:
            return self._pil_image.getpixel((x, y_top))

        # Blender image.pixels is stored bottom-left first.
        y_bottom = self.height - 1 - y_top
        idx = (y_bottom * self.width + x) * 4
        p = self._bpy_pixels
        return (
            int(max(0.0, min(1.0, p[idx + 0])) * 255),
            int(max(0.0, min(1.0, p[idx + 1])) * 255),
            int(max(0.0, min(1.0, p[idx + 2])) * 255),
            int(max(0.0, min(1.0, p[idx + 3])) * 255),
        )


def detect_colored_pixels(src: PixelSource):
    green = []
    red = []

    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = src.get_rgba(x, y)
            if a < 80:
                continue

            is_green = (
                g >= GREEN_THRESHOLD["g_min"]
                and r <= GREEN_THRESHOLD["r_max"]
                and b <= GREEN_THRESHOLD["b_max"]
                and g > r * 1.4
                and g > b * 1.2
            )

            is_red = (
                r >= RED_THRESHOLD["r_min"]
                and g <= RED_THRESHOLD["g_max"]
                and b <= RED_THRESHOLD["b_max"]
                and r > g * 2.5
                and r > b * 2.5
            )

            if is_green:
                green.append((x, y))
            elif is_red:
                red.append((x, y))

    if not green:
        raise RuntimeError(
            "No green profile line was detected. Make sure the reference image contains a clear green outline."
        )

    if not red:
        raise RuntimeError(
            "No red center dot was detected. Make sure the reference image contains a clear red dot."
        )

    red_x = sum(p[0] for p in red) / len(red)
    red_y = sum(p[1] for p in red) / len(red)

    print(f"[detect] green pixels: {len(green)}")
    print(f"[detect] red pixels: {len(red)}")
    print(f"[detect] red center: ({red_x:.2f}, {red_y:.2f})")

    return green, (red_x, red_y)


# ---------------------------------------------------------------------
# Green-line path tracing
# ---------------------------------------------------------------------

def trace_green_path(green_pixels, red_center):
    """
    Trace one connected green path.

    Start:
      nearest green pixel to the red dot.

    End:
      topmost green pixel in the same connected component,
      preferring the pixel closest to the rotation axis.
    """
    green_set = set(green_pixels)
    red_x, red_y = red_center

    start = min(
        green_set,
        key=lambda p: (p[0] - red_x) ** 2 + (p[1] - red_y) ** 2,
    )

    neighbors = [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1),
    ]

    queue = deque([start])
    parent = {start: None}

    while queue:
        x, y = queue.popleft()

        for dx, dy in neighbors:
            q = (x + dx, y + dy)
            if q in green_set and q not in parent:
                parent[q] = (x, y)
                queue.append(q)

    component = list(parent.keys())
    if len(component) < 50:
        raise RuntimeError(
            f"Detected green component is too small: {len(component)} pixels."
        )

    top_y = min(p[1] for p in component)
    top_candidates = [p for p in component if p[1] == top_y]

    # Choose top point closest to the red-dot x-axis.
    # This includes the flat top part of the green profile line.
    end = min(top_candidates, key=lambda p: abs(p[0] - red_x))

    path = []
    p = end
    while p is not None:
        path.append(p)
        p = parent[p]

    path.reverse()

    print(f"[trace] start: {start}")
    print(f"[trace] end: {end}")
    print(f"[trace] raw path points: {len(path)}")

    return path


def smooth_path(points, window=7):
    if window <= 1 or len(points) < window:
        return points

    half = window // 2
    result = []

    for i in range(len(points)):
        if i == 0 or i == len(points) - 1:
            result.append(points[i])
            continue

        lo = max(0, i - half)
        hi = min(len(points), i + half + 1)
        chunk = points[lo:hi]

        x = sum(p[0] for p in chunk) / len(chunk)
        y = sum(p[1] for p in chunk) / len(chunk)
        result.append((x, y))

    return result


def ramer_douglas_peucker(points, epsilon):
    if len(points) < 3:
        return points

    x1, y1 = points[0]
    x2, y2 = points[-1]

    dx = x2 - x1
    dy = y2 - y1
    denom = math.hypot(dx, dy)

    max_dist = -1.0
    max_index = 0

    for i, (x, y) in enumerate(points[1:-1], start=1):
        if denom == 0:
            dist = math.hypot(x - x1, y - y1)
        else:
            dist = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / denom

        if dist > max_dist:
            max_dist = dist
            max_index = i

    if max_dist > epsilon:
        left = ramer_douglas_peucker(points[:max_index + 1], epsilon)
        right = ramer_douglas_peucker(points[max_index:], epsilon)
        return left[:-1] + right

    return [points[0], points[-1]]


def convert_path_to_profile(path, red_center, target_base_radius):
    """
    Convert image-space green line to Blender XZ profile.

    Image:
      x increases right
      y increases down

    Blender profile:
      radius = image_x - red_x
      z      = red_y - image_y

    The red dot becomes the origin / Z-axis center.
    """
    red_x, red_y = red_center

    raw = []

    for x, y in path:
        radius_px = x - red_x
        z_px = red_y - y

        if radius_px < -2:
            continue

        radius_px = max(0.0, radius_px)
        z_px = max(0.0, z_px)

        raw.append((radius_px, z_px))

    if len(raw) < 3:
        raise RuntimeError("Not enough profile points after converting the green line.")

    max_radius_px = max(p[0] for p in raw)
    if max_radius_px <= 0:
        raise RuntimeError("Invalid profile: max radius is zero.")

    scale = target_base_radius / max_radius_px

    profile = []
    for radius_px, z_px in raw:
        r = radius_px * scale
        z = z_px * scale

        if not profile:
            profile.append((r, z))
            continue

        prev_r, prev_z = profile[-1]
        if math.hypot(r - prev_r, z - prev_z) > 0.008:
            profile.append((r, z))

    print(f"[profile] max radius px: {max_radius_px:.2f}")
    print(f"[profile] scale: {scale:.6f}")
    print(f"[profile] generated profile points: {len(profile)}")
    print(f"[profile] height: {profile[-1][1]:.3f} Blender units")
    print(f"[profile] max radius: {max(p[0] for p in profile):.3f} Blender units")

    return profile


# ---------------------------------------------------------------------
# Blender helpers
# ---------------------------------------------------------------------

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def set_principled_input(mat, input_name, value):
    if not mat.use_nodes:
        return

    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf and input_name in bsdf.inputs:
        bsdf.inputs[input_name].default_value = value


def create_material(name, color, roughness=0.2, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    set_principled_input(mat, "Base Color", color)
    set_principled_input(mat, "Roughness", roughness)
    set_principled_input(mat, "Metallic", metallic)
    set_principled_input(mat, "Alpha", alpha)

    if alpha < 1.0:
        mat.blend_method = "BLEND"
        mat.use_screen_refraction = True
        mat.show_transparent_back = True

    return mat


def create_profile_mesh(profile):
    """
    Create an open edge profile in the XZ plane.

    Vertex order:
      bottom center axis
      green-line profile points
      top center axis

    Screw Modifier revolves these edges around the Z-axis.
    """
    verts = []
    edges = []

    # Red dot / rotation-axis bottom center.
    verts.append((0.0, 0.0, 0.0))

    for r, z in profile:
        verts.append((r, 0.0, z))

    top_z = profile[-1][1]
    verts.append((0.0, 0.0, top_z))

    for i in range(len(verts) - 1):
        edges.append((i, i + 1))

    mesh = bpy.data.meshes.new("Stamp_Profile_GreenLine_Mesh")
    mesh.from_pydata(verts, edges, [])
    mesh.update()

    obj = bpy.data.objects.new("Stamp_Profile_GreenLine", mesh)
    bpy.context.collection.objects.link(obj)

    return obj


def add_screw_modifier(obj, steps, apply=False):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    screw = obj.modifiers.new("Screw_360_Z_From_Green_Line", "SCREW")
    screw.axis = "Z"
    screw.angle = math.tau
    screw.steps = steps
    screw.render_steps = max(steps, 192)

    if hasattr(screw, "use_smooth_shade"):
        screw.use_smooth_shade = True

    if hasattr(screw, "use_merge_vertices"):
        screw.use_merge_vertices = True

    if hasattr(screw, "merge_threshold"):
        screw.merge_threshold = 0.0005

    bevel = obj.modifiers.new("Small_Product_Bevel", "BEVEL")
    bevel.width = 0.008
    bevel.segments = 2

    normal = obj.modifiers.new("Weighted_Product_Normals", "WEIGHTED_NORMAL")

    if apply:
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)

    obj.select_set(False)


def add_top_holes(profile, body_mat, dark_mat, rose_gold_mat):
    """
    Add visual 4-hole detail on the generated top surface.
    This does not boolean-cut the mesh; it uses dark disks + rose-gold rims.
    """
    top_z = profile[-1][1]
    top_radius = max(0.12, profile[-1][0])

    hole_offset = min(0.16, top_radius * 0.42)
    hole_radius = min(0.045, top_radius * 0.13)
    rim_minor = hole_radius * 0.18

    positions = [
        (0.0, hole_offset),
        (0.0, -hole_offset),
        (-hole_offset, 0.0),
        (hole_offset, 0.0),
    ]

    for i, (x, y) in enumerate(positions, start=1):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=40,
            radius=hole_radius,
            depth=0.006,
            location=(x, y, top_z + 0.006),
        )
        disk = bpy.context.object
        disk.name = f"StampTop_HoleDark_{i:02d}"
        disk.data.materials.append(dark_mat)

        bpy.ops.mesh.primitive_torus_add(
            major_radius=hole_radius + rim_minor,
            minor_radius=rim_minor,
            major_segments=48,
            minor_segments=8,
            location=(x, y, top_z + 0.010),
        )
        rim = bpy.context.object
        rim.name = f"StampTop_HoleGoldRim_{i:02d}"
        rim.data.materials.append(rose_gold_mat)


def interpolate_radius_at_z(profile, z):
    if not profile:
        return 0.0

    pts = sorted(profile, key=lambda p: p[1])

    if z <= pts[0][1]:
        return pts[0][0]

    for i in range(len(pts) - 1):
        r1, z1 = pts[i]
        r2, z2 = pts[i + 1]

        if z1 <= z <= z2:
            t = 0.0 if z2 == z1 else (z - z1) / (z2 - z1)
            return r1 * (1.0 - t) + r2 * t

    return pts[-1][0]


def add_rose_gold_ring(profile, rose_gold_mat):
    """
    Add a decorative rose-gold ring around the neck area.
    The ring height is estimated from the generated profile.
    """
    max_z = profile[-1][1]
    ring_z = max_z * 0.17
    ring_radius = interpolate_radius_at_z(profile, ring_z) + 0.015

    bpy.ops.mesh.primitive_torus_add(
        major_radius=ring_radius,
        minor_radius=0.035,
        major_segments=128,
        minor_segments=14,
        location=(0.0, 0.0, ring_z),
    )
    ring = bpy.context.object
    ring.name = "StampNeck_RoseGoldRing"
    ring.data.materials.append(rose_gold_mat)


def add_reference_axis_marker():
    """
    Optional tiny marker at the red-dot origin. Hidden by default.
    """
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24,
        ring_count=12,
        radius=0.025,
        location=(0.0, 0.0, 0.0),
    )
    marker = bpy.context.object
    marker.name = "RedDot_Center_Origin_Marker"
    marker.hide_viewport = True
    marker.hide_render = True


def add_lighting_and_camera(profile):
    max_z = profile[-1][1]
    max_r = max(p[0] for p in profile)

    bpy.ops.object.light_add(type="AREA", location=(-3.0, -4.0, max_z * 0.85))
    key = bpy.context.object
    key.name = "KeyLight_LargeSoftbox"
    key.data.energy = 850
    key.data.size = 5.0

    bpy.ops.object.light_add(type="AREA", location=(3.5, 2.5, max_z * 0.75))
    fill = bpy.context.object
    fill.name = "FillLight"
    fill.data.energy = 180
    fill.data.size = 4.0

    bpy.ops.object.camera_add(
        location=(0.0, -max(max_r * 4.2, 5.0), max_z * 0.55),
        rotation=(math.radians(68), 0.0, 0.0),
    )
    cam = bpy.context.object
    cam.name = "FrontPreviewCamera"
    cam.data.lens = 70
    bpy.context.scene.camera = cam

    # Set origin-facing camera more accurately.
    look_at(cam, (0.0, 0.0, max_z * 0.45))


def look_at(obj, target):
    from mathutils import Vector

    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def export_glb(out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    kwargs = {
        "filepath": str(out_path),
        "export_format": "GLB",
        "export_apply": True,
    }

    try:
        bpy.ops.export_scene.gltf(**kwargs)
    except TypeError:
        kwargs.pop("export_apply", None)
        bpy.ops.export_scene.gltf(**kwargs)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"[export] GLB exported: {out_path}")
    print(f"[export] size: {size_mb:.2f} MB")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    args = parse_args()

    image_path = Path(args.image).resolve()
    out_path = Path(args.out).resolve()
    validate_output_path(out_path, args.allow_runtime_asset)

    if not image_path.exists():
        raise FileNotFoundError(f"Reference image not found: {image_path}")

    load_blender_api()

    src = PixelSource(image_path)
    green_pixels, red_center = detect_colored_pixels(src)

    raw_path = trace_green_path(green_pixels, red_center)
    smooth = smooth_path(raw_path, window=7)
    simplified = ramer_douglas_peucker(smooth, args.rdp_epsilon)

    print(f"[profile] simplified path points: {len(simplified)}")

    profile = convert_path_to_profile(
        simplified,
        red_center,
        target_base_radius=args.target_base_radius,
    )

    clear_scene()

    pink_mat = create_material(
        "Glossy_Pink_Stamp_Body",
        color=(0.95, 0.34, 0.38, 1.0),
        roughness=0.18,
        metallic=0.0,
        alpha=1.0,
    )

    rose_gold_mat = create_material(
        "Rose_Gold_Metal",
        color=(1.0, 0.47, 0.32, 1.0),
        roughness=0.22,
        metallic=1.0,
        alpha=1.0,
    )

    dark_mat = create_material(
        "Dark_Recess_Holes",
        color=(0.025, 0.012, 0.010, 1.0),
        roughness=0.25,
        metallic=0.0,
        alpha=1.0,
    )

    stamp_obj = create_profile_mesh(profile)
    stamp_obj.name = "StampRoot_RevolvedFromGreenLine"
    stamp_obj.data.materials.append(pink_mat)

    add_screw_modifier(
        stamp_obj,
        steps=args.steps,
        apply=args.apply_screw,
    )

    add_rose_gold_ring(profile, rose_gold_mat)
    add_top_holes(profile, pink_mat, dark_mat, rose_gold_mat)
    add_reference_axis_marker()
    add_lighting_and_camera(profile)

    export_glb(out_path)

    print("[done] Stamp model generated from green profile line.")
    print("[done] Red dot was used as the Z-axis center/origin.")
    print("[done] Screw Modifier angle: 360 degrees around Z-axis.")


if __name__ == "__main__":
    main()
