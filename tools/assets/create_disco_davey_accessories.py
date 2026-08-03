"""Generate Disco Davey's game-ready festival sling bag.

The model is intentionally chunky and low-poly to match Schedule I's art style.
All visible parts are joined into the runtime-required FestivalSlingBag mesh.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


MESH_NAME = "FestivalSlingBag"
TRIANGLE_BUDGET = 3500

POUCH_CENTER = Vector((-0.075, 0.160, 1.185))
POUCH_SIZE = Vector((0.245, 0.095, 0.210))
POUCH_TILT_RADIANS = math.radians(-8.0)
AVATAR_FIT_OFFSET = Vector((0.0, -0.060, 0.090))


def pouch_point(offset: Vector) -> Vector:
    return POUCH_CENTER + (
        Matrix.Rotation(POUCH_TILT_RADIANS, 4, "Y") @ offset
    )


def tilt_pouch_object(obj: bpy.types.Object) -> bpy.types.Object:
    obj.rotation_euler.rotate_axis("Y", POUCH_TILT_RADIANS)
    return obj


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", required=True)
    parser.add_argument("--blend", required=True)
    parser.add_argument("--texture-dir", required=True)
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(script_args)


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


def generate_woven_texture(
    output_dir: Path,
    stem: str,
    base_color: tuple[float, float, float],
    vertical_weight: float,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    size = 128
    albedo_pixels: list[float] = []
    normal_pixels: list[float] = []

    for y in range(size):
        for x in range(size):
            warp = math.sin((x + 0.5) * math.tau / 8.0)
            weft = math.sin((y + 0.5) * math.tau / 8.0)
            fine = math.sin((x + y) * math.tau / 31.0)
            weave = 0.026 * (vertical_weight * warp + (1.0 - vertical_weight) * weft)
            weave += 0.009 * fine
            albedo_pixels.extend(
                (
                    max(0.0, min(1.0, base_color[0] + weave)),
                    max(0.0, min(1.0, base_color[1] + weave)),
                    max(0.0, min(1.0, base_color[2] + weave)),
                    1.0,
                )
            )

            dx = 0.045 * math.cos((x + 0.5) * math.tau / 8.0)
            dy = 0.045 * math.cos((y + 0.5) * math.tau / 8.0)
            normal = Vector((-dx, -dy, 1.0)).normalized()
            normal_pixels.extend(
                (
                    normal.x * 0.5 + 0.5,
                    normal.y * 0.5 + 0.5,
                    normal.z * 0.5 + 0.5,
                    1.0,
                )
            )

    albedo_path = output_dir / f"{stem}_albedo.png"
    normal_path = output_dir / f"{stem}_normal.png"
    for name, path, pixels, is_data in (
        (f"{stem}_albedo", albedo_path, albedo_pixels, False),
        (f"{stem}_normal", normal_path, normal_pixels, True),
    ):
        image = bpy.data.images.new(name, width=size, height=size, alpha=True)
        image.pixels.foreach_set(pixels)
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        if is_data:
            image.colorspace_settings.name = "Non-Color"
        image.save()

    return albedo_path, normal_path


def material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
    textures: tuple[Path, Path] | None = None,
    normal_strength: float = 0.35,
) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    if textures is not None:
        albedo_path, normal_path = textures
        albedo_node = result.node_tree.nodes.new("ShaderNodeTexImage")
        albedo_node.name = f"{name}_Albedo"
        albedo_node.image = bpy.data.images.load(str(albedo_path), check_existing=True)
        albedo_node.interpolation = "Linear"
        result.node_tree.links.new(
            albedo_node.outputs["Color"],
            principled.inputs["Base Color"],
        )

        normal_texture = result.node_tree.nodes.new("ShaderNodeTexImage")
        normal_texture.name = f"{name}_Normal"
        normal_texture.image = bpy.data.images.load(str(normal_path), check_existing=True)
        normal_texture.image.colorspace_settings.name = "Non-Color"
        normal_texture.interpolation = "Linear"
        normal_map = result.node_tree.nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = normal_strength
        result.node_tree.links.new(
            normal_texture.outputs["Color"],
            normal_map.inputs["Color"],
        )
        result.node_tree.links.new(
            normal_map.outputs["Normal"],
            principled.inputs["Normal"],
        )
    return result


def beveled_box(
    name: str,
    location: Vector,
    scale: Vector,
    bevel: float,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale * 0.5
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    modifier = obj.modifiers.new("SoftEdges", "BEVEL")
    modifier.width = bevel
    modifier.segments = 4
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.materials.append(mat)
    return obj


def tube(
    name: str,
    points: list[Vector],
    radius: float,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    curve.twist_smooth = 0

    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for index, (point, coordinate) in enumerate(
        zip(spline.bezier_points, points)
    ):
        point.co = coordinate
        handle_type = (
            "VECTOR"
            if index == 0 or index == len(points) - 1
            else "AUTO"
        )
        point.handle_left_type = handle_type
        point.handle_right_type = handle_type

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    return obj


def webbing_strip(
    name: str,
    points: list[Vector],
    width: float,
    thickness: float,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.resolution_v = 0
    curve.twist_smooth = 8
    curve.use_fill_caps = True

    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for index, (point, coordinate) in enumerate(
        zip(spline.bezier_points, points)
    ):
        point.co = coordinate
        handle_type = (
            "VECTOR"
            if index == 0 or index == len(points) - 1
            else "AUTO"
        )
        point.handle_left_type = handle_type
        point.handle_right_type = handle_type

    profile_curve = bpy.data.curves.new(f"{name}_Profile", "CURVE")
    profile_curve.dimensions = "2D"
    profile = profile_curve.splines.new("POLY")
    profile.points.add(3)
    for point, coordinate in zip(
        profile.points,
        (
            (-thickness * 0.5, -width * 0.5, 0.0, 1.0),
            (thickness * 0.5, -width * 0.5, 0.0, 1.0),
            (thickness * 0.5, width * 0.5, 0.0, 1.0),
            (-thickness * 0.5, width * 0.5, 0.0, 1.0),
        ),
    ):
        point.co = coordinate
    profile.use_cyclic_u = True

    profile_object = bpy.data.objects.new(f"{name}_Profile", profile_curve)
    bpy.context.collection.objects.link(profile_object)
    curve.bevel_mode = "OBJECT"
    curve.bevel_object = profile_object

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)

    bpy.data.objects.remove(profile_object, do_unlink=True)
    if profile_curve.users == 0:
        bpy.data.curves.remove(profile_curve)
    return obj


def torus(
    name: str,
    location: Vector,
    major_radius: float,
    minor_radius: float,
    rotation: tuple[float, float, float],
    mat: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD",
        major_segments=12,
        minor_segments=4,
        location=location,
        rotation=rotation,
        major_radius=major_radius,
        minor_radius=minor_radius,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def cylinder_between(
    name: str,
    start: Vector,
    end: Vector,
    radius: float,
    mat: bpy.types.Material,
    vertices: int = 8,
) -> bpy.types.Object:
    direction = end - start
    midpoint = (start + end) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=direction.length,
        location=midpoint,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.data.materials.append(mat)
    return obj


def build_model(texture_dir: Path) -> bpy.types.Object:
    bag_textures = generate_woven_texture(
        texture_dir,
        "disco_davey_bag_fabric",
        (0.20, 0.16, 0.24),
        0.52,
    )
    webbing_textures = generate_woven_texture(
        texture_dir,
        "disco_davey_bag_webbing",
        (0.26, 0.045, 0.42),
        0.80,
    )
    lining_textures = generate_woven_texture(
        texture_dir,
        "disco_davey_bag_lining",
        (0.47, 0.39, 0.52),
        0.50,
    )
    fabric = material(
        "Davey_BagFabric",
        (0.20, 0.16, 0.24, 1.0),
        0.86,
        bag_textures,
        0.30,
    )
    webbing = material(
        "Davey_PurpleWebbing",
        (0.26, 0.045, 0.42, 1.0),
        0.74,
        webbing_textures,
        0.38,
    )
    accent = material("Davey_NeonGreen", (0.39, 0.96, 0.10, 1.0), 0.58)
    hardware = material("Davey_DarkMetal", (0.055, 0.06, 0.075, 1.0), 0.42)
    lining = material(
        "Davey_Lining",
        (0.47, 0.39, 0.52, 1.0),
        0.82,
        lining_textures,
        0.24,
    )

    parts: list[bpy.types.Object] = []

    # Compact asymmetrical pouch, worn on the lower-left back.
    parts.append(
        tilt_pouch_object(
            beveled_box(
            "PouchBody",
            POUCH_CENTER,
            POUCH_SIZE,
            0.034,
            fabric,
            )
        )
    )
    parts.append(
        tilt_pouch_object(
            beveled_box(
            "FrontPocket",
            pouch_point(Vector((0.010, 0.056, -0.021))),
            Vector((0.190, 0.024, 0.108)),
            0.018,
            lining,
            )
        )
    )
    parts.append(
        tilt_pouch_object(
            beveled_box(
            "TopFlap",
            pouch_point(Vector((0.0, 0.057, 0.075))),
            Vector((0.225, 0.023, 0.052)),
            0.014,
            fabric,
            )
        )
    )

    # Purple zipper piping and a small neon pull.
    parts.append(
        tube(
            "ZipperPiping",
            [
                pouch_point(Vector((-0.098, 0.073, 0.080))),
                pouch_point(Vector((-0.050, 0.078, 0.095))),
                pouch_point(Vector((0.046, 0.078, 0.095))),
                pouch_point(Vector((0.098, 0.073, 0.080))),
            ],
            0.008,
            webbing,
        )
    )
    parts.append(
        cylinder_between(
            "ZipperPull",
            pouch_point(Vector((0.098, 0.078, 0.080))),
            pouch_point(Vector((0.120, 0.082, 0.063))),
            0.006,
            accent,
            6,
        )
    )

    # One continuous sling loop crosses the back, turns over the shoulder,
    # follows the chest, and returns around the waist to the lower anchor.
    upper_anchor = pouch_point(Vector((0.108, 0.065, 0.073)))
    lower_anchor = pouch_point(Vector((-0.112, 0.050, -0.064)))
    strap_points = [
        upper_anchor,
        Vector((0.040, 0.158, 1.300)),
        Vector((0.060, 0.148, 1.390)),
        Vector((0.075, 0.132, 1.475)),
        Vector((0.085, 0.070, 1.515)),
        Vector((0.080, 0.000, 1.510)),
        Vector((0.060, -0.070, 1.445)),
        Vector((0.010, -0.090, 1.325)),
        Vector((-0.100, -0.075, 1.160)),
        Vector((-0.142, 0.005, 1.112)),
        lower_anchor,
    ]
    parts.append(
        webbing_strip(
            "ShoulderStrap",
            strap_points,
            width=0.034,
            thickness=0.008,
            mat=webbing,
        )
    )

    for name, anchor_offset in (
        ("UpperAnchor", Vector((0.108, 0.075, 0.073))),
        ("LowerAnchor", Vector((-0.112, 0.060, -0.064))),
    ):
        parts.append(
            tilt_pouch_object(
                beveled_box(
                    name,
                    pouch_point(anchor_offset),
                    Vector((0.035, 0.022, 0.047)),
                    0.006,
                    hardware,
                )
            )
        )

    # Readable adjuster on the exposed diagonal without excessive detail.
    adjuster = beveled_box(
        "StrapAdjuster",
        Vector((0.065, 0.143, 1.425)),
        Vector((0.050, 0.022, 0.065)),
        0.007,
        hardware,
    )
    adjuster.rotation_euler[1] = math.radians(-22)
    parts.append(adjuster)
    parts.append(
        beveled_box(
            "AdjusterInset",
            Vector((0.065, 0.155, 1.425)),
            Vector((0.025, 0.012, 0.037)),
            0.004,
            webbing,
        )
    )

    # A simple festival smile mark keeps the prop legible at gameplay scale.
    logo_center = pouch_point(Vector((0.017, 0.075, -0.027)))
    parts.append(
        torus(
            "FestivalLogoRing",
            logo_center,
            0.032,
            0.005,
            (math.radians(90), POUCH_TILT_RADIANS, 0.0),
            accent,
        )
    )
    parts.append(
        cylinder_between(
            "LogoSlash",
            pouch_point(Vector((-0.005, 0.077, -0.045))),
            pouch_point(Vector((0.039, 0.077, -0.009))),
            0.0045,
            accent,
            6,
        )
    )

    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    result = bpy.context.object
    result.name = MESH_NAME
    result.data.name = f"{MESH_NAME}_Mesh"
    result.location += AVATAR_FIT_OFFSET
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    mesh_data = bmesh.new()
    mesh_data.from_mesh(result.data)
    bmesh.ops.dissolve_degenerate(
        mesh_data,
        dist=1e-7,
        edges=list(mesh_data.edges),
    )
    bmesh.ops.remove_doubles(
        mesh_data,
        verts=list(mesh_data.verts),
        dist=1e-7,
    )
    mesh_data.to_mesh(result.data)
    mesh_data.free()
    result.data.update()

    triangle_count = sum(len(poly.vertices) - 2 for poly in result.data.polygons)
    if triangle_count > TRIANGLE_BUDGET:
        raise RuntimeError(
            f"{MESH_NAME} has {triangle_count} triangles; budget is {TRIANGLE_BUDGET}."
        )
    return result


def save_outputs(result: bpy.types.Object, glb_path: Path, blend_path: Path) -> None:
    glb_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.object.select_all(action="DESELECT")
    result.select_set(True)
    bpy.context.view_layer.objects.active = result
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )


def main() -> None:
    args = parse_args()
    reset_scene()
    result = build_model(Path(args.texture_dir))
    save_outputs(result, Path(args.glb), Path(args.blend))


if __name__ == "__main__":
    main()
