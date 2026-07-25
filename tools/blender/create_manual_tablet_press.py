"""Build the production MoreDrugs manual tablet press and export it as GLB.

Run with:
    blender --background --python tools/blender/create_manual_tablet_press.py

The mesh is an original design generated entirely from primitives and authored
profiles. Marketplace images are local-only visual references for the broad
language of a manual arbor press; no source geometry or textures are reused.
"""

from __future__ import annotations

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "src" / "MoreDrugs" / "Assets" / "Models"
SOURCE_DIR = REPO_ROOT / "assets" / "source"
PREVIEW_DIR = REPO_ROOT / "artifacts" / "previews" / "manual-tablet-press"

BLEND_PATH = SOURCE_DIR / "manual_tablet_press.blend"
GLB_PATH = MODEL_DIR / "manual_tablet_press.glb"
HERO_PREVIEW_PATH = PREVIEW_DIR / "manual_tablet_press_hero.png"

FRAME_IDLE = 1
FRAME_FEED = 14
FRAME_FEED_RETRACTED = 22
FRAME_PRESS = 34
FRAME_PRESS_HOLD = 38
FRAME_RETRACTED = 48
FRAME_EJECT = 54
FRAME_EJECT_HOLD = 60
FRAME_COMPLETE = 68
FRAME_TABLET_LIFT = 66
FRAME_TABLET_TRAVEL = 75
FRAME_TABLET_LAND = 84
FRAME_TABLET_BOUNCE = 90
FRAME_END = 96
PEDESTAL_HEIGHT = 2.10


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def make_material(
    name: str,
    base_color: tuple[float, float, float, float],
    metallic: float,
    roughness: float,
) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = base_color
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = base_color
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    return result


def finish_mesh(
    obj: bpy.types.Object,
    mat: bpy.types.Material,
    *,
    bevel: float = 0.02,
    bevel_segments: int = 2,
    smooth: bool = False,
) -> bpy.types.Object:
    obj.data.name = f"{obj.name}_Mesh"
    obj.data.materials.append(mat)
    if bevel > 0:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = bevel
        modifier.segments = bevel_segments
        modifier.limit_method = "ANGLE"
    if smooth:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return obj


def box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    mat: bpy.types.Material,
    *,
    bevel: float = 0.02,
    rotation: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(value / 2 for value in dimensions)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish_mesh(obj, mat, bevel=bevel)


def cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    *,
    vertices: int = 20,
    rotation: tuple[float, float, float] = (0, 0, 0),
    bevel: float = 0.012,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, mat, bevel=bevel, smooth=True)


def cone(
    name: str,
    location: tuple[float, float, float],
    radius_bottom: float,
    radius_top: float,
    depth: float,
    mat: bpy.types.Material,
    *,
    vertices: int = 24,
    bevel: float = 0.01,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius_bottom,
        radius2=radius_top,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, mat, bevel=bevel, smooth=True)


def torus(
    name: str,
    location: tuple[float, float, float],
    major_radius: float,
    minor_radius: float,
    mat: bpy.types.Material,
    *,
    rotation: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_segments=24,
        minor_segments=8,
        major_radius=major_radius,
        minor_radius=minor_radius,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, mat, bevel=0, smooth=True)


def sphere(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=20,
        ring_count=10,
        radius=radius,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, mat, bevel=0, smooth=True)


def cylinder_between(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    mat: bpy.types.Material,
    *,
    vertices: int = 18,
) -> bpy.types.Object:
    start_vector = Vector(start)
    end_vector = Vector(end)
    direction = end_vector - start_vector
    obj = cylinder(
        name,
        tuple((start_vector + end_vector) / 2),
        radius,
        direction.length,
        mat,
        vertices=vertices,
    )
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    return obj


def extruded_profile(
    name: str,
    points_xz: list[tuple[float, float]],
    depth: float,
    center_y: float,
    mat: bpy.types.Material,
    *,
    bevel: float,
) -> bpy.types.Object:
    half_depth = depth / 2
    count = len(points_xz)
    vertices = [(x, center_y - half_depth, z) for x, z in points_xz]
    vertices.extend((x, center_y + half_depth, z) for x, z in points_xz)
    faces: list[tuple[int, ...]] = [
        tuple(reversed(range(count))),
        tuple(range(count, count * 2)),
    ]
    for index in range(count):
        following = (index + 1) % count
        faces.append((index, following, following + count, index + count))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)

    # Blender's render-time tessellation can bridge the concave throat of the
    # C-frame with a stray cap triangle. Triangulate only the two profile caps
    # explicitly, then recalculate the closed solid's winding before beveling.
    editable_mesh = bmesh.new()
    editable_mesh.from_mesh(mesh)
    profile_caps = [
        face for face in editable_mesh.faces if len(face.verts) == count
    ]
    if len(profile_caps) != 2:
        editable_mesh.free()
        raise RuntimeError(
            f"{name} expected two profile caps, found {len(profile_caps)}."
        )
    bmesh.ops.triangulate(
        editable_mesh,
        faces=profile_caps,
        quad_method="BEAUTY",
        ngon_method="BEAUTY",
    )
    bmesh.ops.recalc_face_normals(
        editable_mesh,
        faces=list(editable_mesh.faces),
    )
    editable_mesh.to_mesh(mesh)
    editable_mesh.free()

    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish_mesh(
        obj,
        mat,
        bevel=bevel,
        bevel_segments=3,
        smooth=False,
    )


def heart_prism(
    name: str,
    location: tuple[float, float, float],
    size: float,
    depth: float,
    mat: bpy.types.Material,
    *,
    rotation: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    segments = 24
    points: list[tuple[float, float]] = []
    for index in range(segments):
        t = (2 * math.pi * index) / segments
        x = 16 * math.sin(t) ** 3
        y = (
            13 * math.cos(t)
            - 5 * math.cos(2 * t)
            - 2 * math.cos(3 * t)
            - math.cos(4 * t)
        )
        points.append((x * size / 32, y * size / 32))

    vertices = [(x, y, -depth / 2) for x, y in points]
    vertices.extend((x, y, depth / 2) for x, y in points)
    faces: list[tuple[int, ...]] = [
        tuple(reversed(range(segments))),
        tuple(range(segments, segments * 2)),
    ]
    for index in range(segments):
        following = (index + 1) % segments
        faces.append((index, following, following + segments, index + segments))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    return finish_mesh(obj, mat, bevel=0.009, smooth=False)


def parent_keep_transform(
    child: bpy.types.Object,
    parent: bpy.types.Object,
) -> None:
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def empty(
    name: str,
    parent: bpy.types.Object | None = None,
    *,
    location: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    if parent is not None:
        parent_keep_transform(obj, parent)
    return obj


def interaction_anchor(
    name: str,
    location: tuple[float, float, float],
    parent: bpy.types.Object,
    purpose: str,
) -> bpy.types.Object:
    result = empty(name, parent, location=location)
    result.empty_display_type = "PLAIN_AXES"
    result.empty_display_size = 0.08
    result["interaction_anchor"] = True
    result["purpose"] = purpose
    return result


def add_fastener(
    name: str,
    x: float,
    z: float,
    washer_mat: bpy.types.Material,
    cap_mat: bpy.types.Material,
    parent: bpy.types.Object,
) -> None:
    # PressHead's front face is y=-0.48. The washer overlaps that plane by
    # 0.003 modeling units; the cap overlaps the washer by 0.011.
    washer = cylinder(
        f"{name}_Washer",
        (x, -0.492, z),
        0.082,
        0.030,
        washer_mat,
        vertices=20,
        rotation=(math.radians(90), 0, 0),
        bevel=0.006,
    )
    cap = cylinder(
        f"{name}_Cap",
        (x, -0.518, z),
        0.052,
        0.044,
        cap_mat,
        vertices=12,
        rotation=(math.radians(90), 0, 0),
        bevel=0.008,
    )
    parent_keep_transform(washer, parent)
    parent_keep_transform(cap, parent)


def add_nameplate(
    parent: bpy.types.Object,
    brass: bpy.types.Material,
    enamel: bpy.types.Material,
) -> None:
    plate = box(
        "ManufacturerPlate",
        (-0.78, -0.292, 2.45),
        (0.38, 0.035, 0.20),
        brass,
        bevel=0.014,
    )
    parent_keep_transform(plate, parent)
    bpy.ops.object.text_add(
        location=(-0.78, -0.315, 2.45),
        rotation=(math.radians(90), 0, 0),
    )
    label = bpy.context.object
    label.name = "ManufacturerPlateText"
    label.data.body = "MD-1"
    label.data.align_x = "CENTER"
    label.data.align_y = "CENTER"
    label.data.size = 0.095
    label.data.extrude = 0.004
    label.data.materials.append(enamel)
    bpy.ops.object.convert(target="MESH")
    label.data.name = "ManufacturerPlateText_Mesh"
    parent_keep_transform(label, parent)


def keyframe_transform(
    obj: bpy.types.Object,
    frames: list[int],
    data_path: str,
) -> None:
    for frame in frames:
        obj.keyframe_insert(data_path=data_path, frame=frame)


def set_linear_interpolation(*objects: bpy.types.Object) -> None:
    for obj in objects:
        if obj.animation_data is None or obj.animation_data.action is None:
            continue
        action = obj.animation_data.action
        if hasattr(action, "fcurves"):
            curves = list(action.fcurves)
        else:
            curves = [
                curve
                for layer in action.layers
                for strip in layer.strips
                for channel_bag in strip.channelbags
                for curve in channel_bag.fcurves
            ]
        for curve in curves:
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"


def set_bezier_interpolation(
    obj: bpy.types.Object,
    data_paths: set[str],
) -> None:
    if obj.animation_data is None or obj.animation_data.action is None:
        return
    action = obj.animation_data.action
    if hasattr(action, "fcurves"):
        curves = list(action.fcurves)
    else:
        curves = [
            curve
            for layer in action.layers
            for strip in layer.strips
            for channel_bag in strip.channelbags
            for curve in channel_bag.fcurves
        ]
    for curve in curves:
        if curve.data_path not in data_paths:
            continue
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"


def bounds_overlap(first: bpy.types.Object, second: bpy.types.Object) -> bool:
    first_corners = [first.matrix_world @ Vector(corner) for corner in first.bound_box]
    second_corners = [second.matrix_world @ Vector(corner) for corner in second.bound_box]
    for axis in range(3):
        if max(corner[axis] for corner in first_corners) < min(
            corner[axis] for corner in second_corners
        ):
            return False
        if max(corner[axis] for corner in second_corners) < min(
            corner[axis] for corner in first_corners
        ):
            return False
    return True


def validate_authored_contacts() -> None:
    press_head = bpy.data.objects["PressHead"]
    rack = bpy.data.objects["VerticalRack"]
    for name in (
        "HeadFastener_0.18_2.10_Washer",
        "HeadFastener_0.18_2.56_Washer",
        "HeadFastener_0.68_2.10_Washer",
        "HeadFastener_0.68_2.56_Washer",
    ):
        if not bounds_overlap(press_head, bpy.data.objects[name]):
            raise RuntimeError(f"{name} is floating clear of PressHead.")
    for index in range(9):
        tooth = bpy.data.objects[f"RackTooth_{index:02d}"]
        if not bounds_overlap(rack, tooth):
            raise RuntimeError(f"{tooth.name} is floating clear of VerticalRack.")
    contact_pairs = (
        ("PowderHopperNeck", "PowderFeedShoe"),
        ("PowderFeedShoe", "FeedGuideRailFront"),
        ("PowderFeedShoe", "FeedGuideRailRear"),
        ("FeedActuatorRod", "FeedActuatorSleeve"),
        ("FeedActuatorClevis", "PowderFeedShoe"),
        ("FeedRailSupportLeft", "WorkTable"),
        ("FeedRailSupportRight", "WorkTable"),
    )
    for first_name, second_name in contact_pairs:
        first = bpy.data.objects[first_name]
        second = bpy.data.objects[second_name]
        if not bounds_overlap(first, second):
            raise RuntimeError(
                f"{first_name} is floating clear of {second_name}."
            )


def create_press() -> bpy.types.Object:
    cast_green = make_material("CastIronGreen", (0.075, 0.19, 0.12, 1), 0.72, 0.40)
    dark_green = make_material("DarkGreen", (0.028, 0.085, 0.052, 1), 0.78, 0.34)
    steel = make_material("MachinedSteel", (0.42, 0.48, 0.50, 1), 0.88, 0.23)
    dark_steel = make_material("DarkSteel", (0.055, 0.065, 0.070, 1), 0.90, 0.27)
    brass = make_material("Brass", (0.50, 0.28, 0.065, 1), 0.82, 0.25)
    rubber = make_material("Rubber", (0.012, 0.016, 0.018, 1), 0.02, 0.76)
    enamel = make_material("Enamel", (0.77, 0.70, 0.50, 1), 0.22, 0.42)
    pill_pink = make_material("TabletPink", (0.95, 0.035, 0.43, 1), 0.06, 0.30)
    powder = make_material("Powder", (0.98, 0.58, 0.77, 1), 0.0, 0.82)

    root = empty("ManualTabletPress")
    pedestal = empty("PedestalAssembly", root)
    machine = empty("MachineAssembly", root)
    static = empty("StaticAssembly", machine)
    interaction = empty("Interaction", machine)
    lever_assembly = empty(
        "HandlePivot",
        machine,
        location=(0.44, -0.59, 2.34),
    )
    ram_assembly = empty("RamAssembly", machine)
    feed_assembly = empty("FeedShoeAssembly", machine)
    feed_powder_assembly = empty("FeedPowderAssembly", feed_assembly)
    die_fill_assembly = empty("DieFillAssembly", machine)
    ejector_assembly = empty("EjectorAssembly", machine)
    fresh_tablet_assembly = empty("FreshTabletAssembly", machine)

    for obj in (
        box(
            "FloorPlinth",
            (-0.05, 0.05, 0.13),
            (2.25, 1.48, 0.26),
            dark_green,
            bevel=0.065,
        ),
        box(
            "PedestalFootFront",
            (-0.05, -0.58, 0.25),
            (1.92, 0.22, 0.25),
            cast_green,
            bevel=0.045,
        ),
        box(
            "PedestalFootRear",
            (-0.05, 0.68, 0.25),
            (1.92, 0.22, 0.25),
            cast_green,
            bevel=0.045,
        ),
        box(
            "PedestalColumn",
            (-0.53, 0.10, 1.10),
            (0.72, 0.82, 1.88),
            cast_green,
            bevel=0.075,
        ),
        box(
            "PedestalColumnInset",
            (-0.53, -0.325, 1.10),
            (0.47, 0.035, 1.45),
            dark_green,
            bevel=0.025,
        ),
        box(
            "MachineMountingPlate",
            (-0.05, 0.05, 2.02),
            (2.20, 1.36, 0.20),
            steel,
            bevel=0.055,
        ),
    ):
        parent_keep_transform(obj, pedestal)

    for x in (-0.87, 0.77):
        support = cylinder_between(
            f"PedestalBrace_{'L' if x < 0 else 'R'}",
            (-0.46, 0.10, 1.60),
            (x, 0.10, 1.98),
            0.085,
            dark_green,
            vertices=16,
        )
        parent_keep_transform(support, pedestal)

    frame_profile = [
        (-1.06, 0.18),
        (0.20, 0.18),
        (0.20, 0.52),
        (-0.50, 0.52),
        (-0.67, 0.70),
        (-0.80, 1.08),
        (-0.82, 1.54),
        (-0.75, 1.88),
        (-0.60, 2.15),
        (-0.46, 2.28),
        (0.66, 2.28),
        (0.66, 2.70),
        (-1.06, 2.70),
    ]
    frame = extruded_profile(
        "FrameBody",
        frame_profile,
        depth=0.76,
        center_y=0.10,
        mat=cast_green,
        bevel=0.075,
    )
    parent_keep_transform(frame, static)

    for obj in (
        box("Base", (-0.05, 0.05, 0.17), (2.28, 1.46, 0.34), cast_green, bevel=0.075),
        box("BaseRailFront", (-0.05, -0.60, 0.08), (2.08, 0.18, 0.16), dark_green, bevel=0.035),
        box("BaseRailRear", (-0.05, 0.70, 0.08), (2.08, 0.18, 0.16), dark_green, bevel=0.035),
        box("PressHead", (0.44, -0.02, 2.33), (0.76, 0.92, 0.72), dark_green, bevel=0.065),
        box("BedSupport", (-0.10, 0.08, 0.72), (1.40, 0.72, 0.26), dark_green, bevel=0.050),
        box("WorkTable", (0.16, -0.03, 0.89), (1.05, 0.86, 0.16), steel, bevel=0.028),
    ):
        parent_keep_transform(obj, static)

    for x, z in ((0.18, 2.10), (0.68, 2.10), (0.18, 2.56), (0.68, 2.56)):
        add_fastener(f"HeadFastener_{x:.2f}_{z:.2f}", x, z, steel, brass, static)

    pivot_housing = cylinder(
        "PivotHousing",
        (0.44, -0.505, 2.34),
        0.225,
        0.105,
        dark_steel,
        vertices=24,
        rotation=(math.radians(90), 0, 0),
        bevel=0.016,
    )
    pivot_bushing = cylinder(
        "PivotBushing",
        (0.44, -0.565, 2.34),
        0.145,
        0.065,
        brass,
        vertices=24,
        rotation=(math.radians(90), 0, 0),
        bevel=0.012,
    )
    parent_keep_transform(pivot_housing, static)
    parent_keep_transform(pivot_bushing, lever_assembly)

    handwheel = torus(
        "HandleWheel",
        (0.44, -0.64, 2.34),
        0.49,
        0.045,
        steel,
        rotation=(math.radians(90), 0, 0),
    )
    handle_hub = cylinder(
        "HandleHub",
        (0.44, -0.65, 2.34),
        0.105,
        0.14,
        dark_steel,
        vertices=24,
        rotation=(math.radians(90), 0, 0),
        bevel=0.012,
    )
    spokes = []
    for index, angle_degrees in enumerate((0, 120, 240), start=1):
        angle = math.radians(angle_degrees)
        end = (
            0.44 + math.cos(angle) * 0.44,
            -0.65,
            2.34 + math.sin(angle) * 0.44,
        )
        spokes.append(
            cylinder_between(
                f"HandleSpoke_{index:02d}",
                (0.44, -0.65, 2.34),
                end,
                0.034,
                steel,
                vertices=14,
            )
        )

    crank_pin = cylinder(
        "HandleCrankPin",
        (0.88, -0.735, 2.34),
        0.045,
        0.22,
        brass,
        vertices=18,
        rotation=(math.radians(90), 0, 0),
        bevel=0.008,
    )
    grip = cylinder(
        "HandleGrip",
        (0.88, -0.89, 2.34),
        0.075,
        0.25,
        rubber,
        vertices=18,
        rotation=(math.radians(90), 0, 0),
        bevel=0.018,
    )
    grip_end = sphere("HandleGripEnd", (0.88, -1.03, 2.34), 0.078, rubber)
    for obj in (handwheel, handle_hub, *spokes, crank_pin, grip, grip_end):
        parent_keep_transform(obj, lever_assembly)

    ram_bar = box(
        "VerticalRack",
        (0.44, 0.00, 1.86),
        (0.23, 0.29, 0.98),
        steel,
        bevel=0.015,
    )
    parent_keep_transform(ram_bar, ram_assembly)
    for index in range(9):
        tooth = box(
            f"RackTooth_{index:02d}",
            (0.555, 0.00, 1.47 + index * 0.095),
            (0.090, 0.25, 0.050),
            dark_steel,
            bevel=0.005,
        )
        parent_keep_transform(tooth, ram_assembly)

    punch_shank = cylinder(
        "UpperPunchShank",
        (0.44, 0.00, 1.46),
        0.125,
        0.32,
        dark_steel,
        vertices=24,
        bevel=0.010,
    )
    upper_die = heart_prism(
        "HeartUpperPunch",
        (0.44, 0.00, 1.275),
        0.185,
        0.070,
        dark_steel,
    )
    parent_keep_transform(punch_shank, ram_assembly)
    parent_keep_transform(upper_die, ram_assembly)

    die_holder = cylinder(
        "DieHolder",
        (0.44, 0.00, 1.015),
        0.255,
        0.125,
        dark_steel,
        vertices=28,
        bevel=0.012,
    )
    die_ring = torus("DieRetainingRing", (0.44, 0.00, 1.083), 0.166, 0.026, brass)
    parent_keep_transform(die_holder, static)
    parent_keep_transform(die_ring, static)

    lower_die = cylinder(
        "LowerDie",
        (0.44, 0.00, 1.075),
        0.135,
        0.075,
        brass,
        vertices=24,
        bevel=0.008,
    )
    die_insert = heart_prism(
        "HeartDieInsert",
        (0.44, 0.00, 1.118),
        0.188,
        0.028,
        dark_steel,
    )
    parent_keep_transform(lower_die, ejector_assembly)
    parent_keep_transform(die_insert, ejector_assembly)

    hopper_body = cone(
        "PowderHopper",
        (-0.15, 0.00, 1.48),
        radius_bottom=0.095,
        radius_top=0.235,
        depth=0.38,
        mat=enamel,
        bevel=0.012,
    )
    hopper_rim = torus("PowderHopperRim", (-0.15, 0.00, 1.68), 0.222, 0.025, brass)
    hopper_neck = cylinder(
        "PowderHopperNeck",
        (-0.15, 0.00, 1.23),
        0.070,
        0.16,
        brass,
        vertices=20,
        bevel=0.008,
    )
    hopper_bracket = box(
        "HopperBracket",
        (-0.46, 0.24, 1.44),
        (0.42, 0.12, 0.10),
        dark_steel,
        bevel=0.018,
    )
    hopper_wiper = torus(
        "HopperWiperRing",
        (-0.15, 0.00, 1.195),
        0.118,
        0.020,
        rubber,
    )
    hopper_guard = box(
        "HopperOutletGuard",
        (-0.15, 0.17, 1.205),
        (0.34, 0.08, 0.07),
        dark_steel,
        bevel=0.018,
    )
    for obj in (
        hopper_body,
        hopper_rim,
        hopper_neck,
        hopper_bracket,
        hopper_wiper,
        hopper_guard,
    ):
        parent_keep_transform(obj, static)

    for obj in (
        box(
            "FeedGuideRailFront",
            (0.145, -0.165, 1.068),
            (1.07, 0.055, 0.055),
            dark_steel,
            bevel=0.009,
        ),
        box(
            "FeedGuideRailRear",
            (0.145, 0.165, 1.068),
            (1.07, 0.055, 0.055),
            dark_steel,
            bevel=0.009,
        ),
        box(
            "FeedRailSupportLeft",
            (-0.32, 0.00, 1.018),
            (0.09, 0.42, 0.11),
            dark_steel,
            bevel=0.012,
        ),
        box(
            "FeedRailSupportRight",
            (0.61, 0.00, 1.018),
            (0.09, 0.42, 0.11),
            dark_steel,
            bevel=0.012,
        ),
    ):
        parent_keep_transform(obj, static)

    actuator_sleeve = cylinder_between(
        "FeedActuatorSleeve",
        (-0.78, 0.17, 1.145),
        (-0.15, 0.17, 1.145),
        0.058,
        dark_steel,
        vertices=18,
    )
    actuator_mount = box(
        "FeedActuatorMount",
        (-0.72, 0.17, 1.245),
        (0.18, 0.24, 0.22),
        cast_green,
        bevel=0.028,
    )
    parent_keep_transform(actuator_sleeve, static)
    parent_keep_transform(actuator_mount, static)

    feed_shoe = box(
        "PowderFeedShoe",
        (-0.15, 0.00, 1.145),
        (0.36, 0.38, 0.10),
        brass,
        bevel=0.035,
    )
    feed_pocket = torus(
        "FeedPocketRim",
        (-0.15, 0.00, 1.198),
        0.105,
        0.018,
        dark_steel,
    )
    feed_powder = cylinder(
        "FeedPowder",
        (-0.15, 0.00, 1.205),
        0.105,
        0.025,
        powder,
        vertices=24,
        bevel=0.004,
    )
    actuator_rod = cylinder_between(
        "FeedActuatorRod",
        (-0.72, 0.17, 1.145),
        (-0.24, 0.17, 1.145),
        0.031,
        steel,
        vertices=16,
    )
    actuator_clevis = box(
        "FeedActuatorClevis",
        (-0.20, 0.17, 1.145),
        (0.10, 0.12, 0.11),
        dark_steel,
        bevel=0.016,
    )
    for obj in (feed_shoe, feed_pocket, actuator_rod, actuator_clevis):
        parent_keep_transform(obj, feed_assembly)
    parent_keep_transform(feed_powder, feed_powder_assembly)

    die_powder = cylinder(
        "DiePowderFill",
        (0.44, 0.00, 1.145),
        0.105,
        0.025,
        powder,
        vertices=24,
        bevel=0.004,
    )
    parent_keep_transform(die_powder, die_fill_assembly)

    collection_bed = box(
        "CollectionTrayBed",
        (1.00, -0.02, 0.76),
        (0.76, 0.82, 0.10),
        steel,
        bevel=0.025,
        rotation=(0, math.radians(-5), 0),
    )
    tray_outer = box(
        "CollectionTrayOuterWall",
        (1.34, -0.02, 0.86),
        (0.08, 0.82, 0.24),
        steel,
        bevel=0.018,
    )
    tray_front = box(
        "CollectionTrayFrontWall",
        (1.00, -0.39, 0.84),
        (0.76, 0.08, 0.20),
        steel,
        bevel=0.018,
    )
    tray_rear = box(
        "CollectionTrayRearWall",
        (1.00, 0.35, 0.84),
        (0.76, 0.08, 0.20),
        steel,
        bevel=0.018,
    )
    tray_bridge = box(
        "CollectionTrayBridge",
        (0.68, -0.02, 0.83),
        (0.24, 0.56, 0.08),
        steel,
        bevel=0.018,
        rotation=(0, math.radians(-8), 0),
    )
    for obj in (collection_bed, tray_outer, tray_front, tray_rear, tray_bridge):
        parent_keep_transform(obj, static)

    for index, (location, rotation_z) in enumerate(
        (
            ((0.91, -0.20, 0.835), -12),
            ((1.10, -0.05, 0.835), 18),
            ((0.93, 0.16, 0.835), 42),
        ),
        start=1,
    ):
        pill = heart_prism(
            f"FinishedTablet_{index:02d}",
            location,
            0.185,
            0.065,
            pill_pink,
            rotation=(0, 0, math.radians(rotation_z)),
        )
        parent_keep_transform(pill, static)

    fresh_tablet = heart_prism(
        "FreshTablet",
        (0.44, 0.00, 1.155),
        0.185,
        0.065,
        pill_pink,
    )
    parent_keep_transform(fresh_tablet, fresh_tablet_assembly)

    add_nameplate(static, brass, enamel)

    interaction_anchor(
        "HandleClickableAnchor",
        (0.88, -1.03, 2.34),
        interaction,
        "Native-style click target for starting and ending handle drag",
    )
    plane_normal = interaction_anchor(
        "PlaneNormal",
        (0.44, -0.71, 2.34),
        interaction,
        "Forward normal for projecting mouse drag input",
    )
    plane_normal.rotation_euler = (math.radians(90), 0, 0)
    interaction_anchor(
        "HandleRaised",
        (0.44, -0.71, 2.83),
        interaction,
        "Upper cursor reference used to normalize handle rotation",
    )
    interaction_anchor(
        "HandleLowered",
        (0.44, -0.71, 1.85),
        interaction,
        "Lower cursor reference used to normalize handle rotation",
    )
    interaction_anchor(
        "PressTransform",
        (0.44, 0.00, 1.275),
        interaction,
        "Runtime-driven upper punch transform",
    )
    interaction_anchor(
        "PressRaised",
        (0.44, 0.00, 1.275),
        interaction,
        "Upper punch position at normalized handle position zero",
    )
    interaction_anchor(
        "PressLowered",
        (0.44, 0.00, 1.025),
        interaction,
        "Upper punch position at normalized handle position one",
    )
    interaction_anchor(
        "MouldDetector",
        (0.44, 0.00, 1.13),
        interaction,
        "Tablet die input and product detection volume center",
    )
    interaction_anchor(
        "CameraPouring",
        (1.18, -2.05, 1.62),
        interaction,
        "Player camera anchor for filling the tablet die",
    )
    interaction_anchor(
        "CameraPressing",
        (1.43, -2.15, 1.64),
        interaction,
        "Player camera anchor for rotating the handle",
    )
    interaction_anchor(
        "StandPoint",
        (0.42, -2.15, 0.0),
        root,
        "Player alignment point for station use",
    )
    interaction_anchor(
        "ContainerSpawnPoint",
        (-0.20, -0.72, 1.02),
        interaction,
        "Input container placement point",
    )
    interaction_anchor(
        "OutputPoint",
        (1.00, -0.02, 0.94),
        interaction,
        "Pressed-tablet output location",
    )

    lever_assembly.rotation_mode = "XYZ"
    lever_assembly.rotation_euler = (0, 0, 0)
    keyframe_transform(
        lever_assembly,
        [FRAME_IDLE, FRAME_FEED_RETRACTED],
        "rotation_euler",
    )
    lever_assembly.rotation_euler = (0, math.radians(360), 0)
    keyframe_transform(
        lever_assembly,
        [FRAME_PRESS, FRAME_PRESS_HOLD],
        "rotation_euler",
    )
    lever_assembly.rotation_euler = (0, math.radians(360), 0)
    keyframe_transform(
        lever_assembly,
        [FRAME_RETRACTED, FRAME_END],
        "rotation_euler",
    )

    ram_assembly.location = (0, 0, 0)
    keyframe_transform(ram_assembly, [FRAME_IDLE, FRAME_FEED_RETRACTED], "location")
    ram_assembly.location = (0, 0, -0.25)
    keyframe_transform(ram_assembly, [FRAME_PRESS, FRAME_PRESS_HOLD], "location")
    ram_assembly.location = (0, 0, 0)
    keyframe_transform(ram_assembly, [FRAME_RETRACTED, FRAME_END], "location")

    feed_assembly.location = (0, 0, 0)
    keyframe_transform(feed_assembly, [FRAME_IDLE, 6], "location")
    feed_assembly.location = (0.59, 0, 0)
    keyframe_transform(feed_assembly, [FRAME_FEED, 17], "location")
    feed_assembly.location = (0, 0, 0)
    keyframe_transform(feed_assembly, [FRAME_FEED_RETRACTED, FRAME_END], "location")

    feed_powder_assembly.scale = (0.001, 0.001, 0.001)
    keyframe_transform(feed_powder_assembly, [FRAME_IDLE, 5], "scale")
    feed_powder_assembly.scale = (1, 1, 1)
    keyframe_transform(feed_powder_assembly, [7, FRAME_FEED], "scale")
    feed_powder_assembly.scale = (0.001, 0.001, 0.001)
    keyframe_transform(feed_powder_assembly, [17, FRAME_END], "scale")

    die_fill_assembly.scale = (0.001, 0.001, 0.001)
    keyframe_transform(die_fill_assembly, [FRAME_IDLE, FRAME_FEED], "scale")
    die_fill_assembly.scale = (1, 1, 1)
    keyframe_transform(die_fill_assembly, [17, FRAME_PRESS - 2], "scale")
    die_fill_assembly.scale = (0.001, 0.001, 0.001)
    keyframe_transform(die_fill_assembly, [FRAME_PRESS, FRAME_END], "scale")

    ejector_assembly.location = (0, 0, 0)
    keyframe_transform(ejector_assembly, [FRAME_IDLE, FRAME_RETRACTED], "location")
    ejector_assembly.location = (0, 0, 0.10)
    keyframe_transform(ejector_assembly, [FRAME_EJECT, FRAME_EJECT_HOLD], "location")
    ejector_assembly.location = (0, 0, 0)
    keyframe_transform(ejector_assembly, [FRAME_COMPLETE, FRAME_END], "location")

    fresh_tablet_assembly.scale = (0.001, 0.001, 0.001)
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_IDLE, FRAME_RETRACTED],
        "scale",
    )
    fresh_tablet_assembly.scale = (1, 1, 1)
    keyframe_transform(
        fresh_tablet_assembly,
        [50, FRAME_EJECT_HOLD, FRAME_END],
        "scale",
    )
    fresh_tablet_assembly.location = (0, 0, 0)
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_IDLE, FRAME_EJECT_HOLD],
        "location",
    )
    fresh_tablet_assembly.location = (0.10, -0.01, 0.055)
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_TABLET_LIFT],
        "location",
    )
    fresh_tablet_assembly.location = (0.37, -0.045, -0.10)
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_TABLET_TRAVEL],
        "location",
    )
    fresh_tablet_assembly.location = (0.57, -0.08, -0.30)
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_TABLET_LAND],
        "location",
    )
    fresh_tablet_assembly.location = (0.60, -0.075, -0.265)
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_TABLET_BOUNCE],
        "location",
    )
    fresh_tablet_assembly.location = (0.61, -0.08, -0.32)
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_END],
        "location",
    )
    fresh_tablet_assembly.rotation_mode = "XYZ"
    fresh_tablet_assembly.rotation_euler = (0, 0, 0)
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_IDLE, FRAME_EJECT_HOLD],
        "rotation_euler",
    )
    fresh_tablet_assembly.rotation_euler = (
        math.radians(-12),
        math.radians(18),
        math.radians(12),
    )
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_TABLET_LIFT],
        "rotation_euler",
    )
    fresh_tablet_assembly.rotation_euler = (
        math.radians(-18),
        math.radians(28),
        math.radians(34),
    )
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_TABLET_TRAVEL],
        "rotation_euler",
    )
    fresh_tablet_assembly.rotation_euler = (
        math.radians(7),
        math.radians(-5),
        math.radians(48),
    )
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_TABLET_LAND],
        "rotation_euler",
    )
    fresh_tablet_assembly.rotation_euler = (
        math.radians(-3),
        math.radians(-2),
        math.radians(43),
    )
    keyframe_transform(
        fresh_tablet_assembly,
        [FRAME_TABLET_BOUNCE],
        "rotation_euler",
    )
    fresh_tablet_assembly.rotation_euler = (
        math.radians(2),
        math.radians(-5),
        math.radians(42),
    )
    keyframe_transform(fresh_tablet_assembly, [FRAME_END], "rotation_euler")
    set_linear_interpolation(
        lever_assembly,
        ram_assembly,
        feed_assembly,
        feed_powder_assembly,
        die_fill_assembly,
        ejector_assembly,
        fresh_tablet_assembly,
    )
    set_bezier_interpolation(
        fresh_tablet_assembly,
        {"location", "rotation_euler"},
    )
    validate_authored_contacts()
    machine.location = (0, 0, PEDESTAL_HEIGHT)

    scene = bpy.context.scene
    scene.frame_start = FRAME_IDLE
    scene.frame_end = FRAME_END
    scene.render.fps = 24

    root.scale = (0.36, 0.36, 0.36)
    root["asset_name"] = "MoreDrugs Manual Tablet Press"
    root["asset_version"] = 2
    root["license"] = "GPL-3.0-or-later"
    root["design"] = "Original MoreDrugs geometry"
    root["front_axis"] = "-Y"
    root["animation"] = "PressCycle"
    root["animation_frames"] = f"{FRAME_IDLE}-{FRAME_END}"
    root["native_interaction_reference"] = "ScheduleOne.ObjectScripts.BrickPressHandle"
    root["handle_rotation_degrees"] = 360
    root["press_travel_meters"] = 0.09
    root["work_surface_height_meters"] = round(
        (PEDESTAL_HEIGHT + 0.89) * 0.36,
        3,
    )
    root["placement"] = "floor-standing"
    root["runtime_contract"] = "Drive HandlePivot rotation and RamAssembly position from normalized handle progress"
    root["units"] = "meters"
    return root


def add_hero_scene() -> None:
    floor_mat = make_material("PreviewFloor", (0.035, 0.042, 0.050, 1), 0.05, 0.86)
    floor = box("PreviewGround", (0, 0, -0.04), (5, 5, 0.08), floor_mat, bevel=0)
    floor["presentation_only"] = True

    target = Vector((0.05, 0.0, 0.92))
    bpy.ops.object.camera_add(location=(1.85, -2.75, 1.72))
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    camera.data.lens = 62
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera["presentation_only"] = True
    bpy.context.scene.camera = camera

    for index, (location, energy, color, size) in enumerate(
        (
            ((-1.3, -1.8, 2.3), 1100, (1.0, 0.82, 0.70), 2.5),
            ((1.6, -0.5, 1.4), 750, (0.50, 0.70, 1.0), 1.8),
            ((-0.4, 1.7, 1.8), 900, (1.0, 0.26, 0.48), 1.4),
        )
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = f"PreviewLight_{index + 1}"
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size
        light["presentation_only"] = True

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(HERO_PREVIEW_PATH)
    scene.world.color = (0.012, 0.016, 0.022)


def save_export_and_render(root: bpy.types.Object) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    export_objects = [root, *root.children_recursive]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root

    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_animation_mode="ACTIVE_ACTIONS",
        export_nla_strips_merged_animation_name="PressCycle",
        export_frame_range=True,
        export_force_sampling=True,
        export_optimize_animation_size=True,
        export_apply=False,
        export_yup=True,
    )

    bpy.context.scene.frame_set(FRAME_IDLE)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    reset_scene()
    root = create_press()
    add_hero_scene()
    save_export_and_render(root)

    meshes = [obj for obj in root.children_recursive if obj.type == "MESH"]
    source_triangles = sum(
        len(polygon.vertices) - 2
        for obj in meshes
        for polygon in obj.data.polygons
    )
    print(f"Created {len(meshes)} source mesh objects ({source_triangles} pre-modifier triangles).")
    print(f"Blend: {BLEND_PATH}")
    print(f"GLB: {GLB_PATH}")
    print(f"Hero preview: {HERO_PREVIEW_PATH}")


if __name__ == "__main__":
    main()
