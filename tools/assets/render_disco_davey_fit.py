"""Render Disco Davey's sling bag against the exported avatar body reference."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", required=True)
    parser.add_argument("--bag", required=True)
    parser.add_argument("--output-dir", required=True)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(corner[i] for corner in corners) for i in range(3))),
        Vector(tuple(max(corner[i] for corner in corners) for i in range(3))),
    )


def neutral_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = 0.82
    return mat


def import_body(path: Path) -> bpy.types.Object:
    bpy.ops.wm.fbx_import(filepath=str(path))
    body = bpy.data.objects.get("Body_LOD0")
    if body is None or body.type != "MESH":
        raise RuntimeError("Body_LOD0.fbx did not contain the expected mesh.")

    body.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    bounds_min, _ = world_bounds(body)
    body.location.z -= bounds_min.z
    bpy.context.view_layer.update()

    body.data.materials.clear()
    body.data.materials.append(
        neutral_material("FitReference", (0.18, 0.20, 0.23, 1.0))
    )
    return body


def import_bag(path: Path) -> bpy.types.Object:
    bpy.ops.import_scene.gltf(filepath=str(path))
    bag = bpy.data.objects.get("FestivalSlingBag")
    if bag is None or bag.type != "MESH":
        raise RuntimeError("Bag GLB did not contain FestivalSlingBag.")
    return bag


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat(
        "-Z", "Y"
    ).to_euler()


def area_light(
    name: str,
    location: Vector,
    target: Vector,
    energy: float,
    size: float,
    color: tuple[float, float, float],
) -> None:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (target - location).to_track_quat(
        "-Z", "Y"
    ).to_euler()


def setup_scene() -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.0

    world = bpy.data.worlds.new("FitWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.008,
        0.010,
        0.016,
        1.0,
    )
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.18
    scene.world = world

    camera_data = bpy.data.cameras.new("FitCamera")
    camera_data.lens = 58
    camera = bpy.data.objects.new("FitCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

    target = Vector((0.0, 0.10, 1.18))
    area_light(
        "SoftKey",
        Vector((1.8, 2.6, 2.8)),
        target,
        240.0,
        3.2,
        (1.0, 0.88, 0.78),
    )
    area_light(
        "SoftFill",
        Vector((-2.2, 1.5, 1.8)),
        target,
        70.0,
        4.0,
        (0.62, 0.74, 1.0),
    )
    area_light(
        "EdgeRim",
        Vector((-1.0, -2.0, 2.5)),
        target,
        110.0,
        2.4,
        (0.52, 0.60, 1.0),
    )

    bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0.0, 0.0, -0.006))
    floor = bpy.context.object
    floor.name = "FitFloor"
    floor.data.materials.append(
        neutral_material("FitFloorMaterial", (0.025, 0.030, 0.040, 1.0))
    )
    return camera


def render_views(camera: bpy.types.Object, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = Vector((0.0, 0.10, 1.18))
    views = {
        "rear": Vector((0.0, 3.35, 1.48)),
        "rear_three_quarter": Vector((1.55, 3.15, 1.52)),
        "side": Vector((3.35, 0.42, 1.42)),
    }
    for name, location in views.items():
        camera.location = location
        point_camera(camera, target)
        bpy.context.scene.render.filepath = str(output_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    reset_scene()
    body = import_body(Path(args.body))
    bag = import_bag(Path(args.bag))
    body.hide_render = False
    bag.hide_render = False
    camera = setup_scene()
    render_views(camera, Path(args.output_dir))


if __name__ == "__main__":
    main()
