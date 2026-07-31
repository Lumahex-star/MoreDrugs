"""Render close station-state evidence for an opened precursor bottle mouth."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--cap", required=True)
    parser.add_argument("--neck", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(arguments)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_area_light(name: str, location: Vector, target: Vector, energy: float) -> None:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = 0.12
    light = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(light)
    light.location = location
    look_at(light, target)


def render(camera: bpy.types.Object, target: Vector, location: Vector, output: Path) -> None:
    camera.location = location
    look_at(camera, target)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))

    cap = bpy.data.objects.get(args.cap)
    neck = bpy.data.objects.get(args.neck)
    if cap is None or neck is None:
        raise RuntimeError("Required cap or neck object was not imported.")
    cap.hide_render = True

    scene = bpy.context.scene
    engine_ids = {
        item.identifier
        for item in scene.render.bl_rna.properties["engine"].enum_items
    }
    scene.render.engine = (
        "BLENDER_EEVEE" if "BLENDER_EEVEE" in engine_ids else "BLENDER_WORKBENCH"
    )
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.5

    world = bpy.data.worlds.new("MouthEvidenceWorld")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.02, 0.025, 0.035, 1.0)
    background.inputs["Strength"].default_value = 0.15

    target = neck.matrix_world.translation
    add_area_light("Key", target + Vector((0.10, -0.12, 0.10)), target, 25.0)
    add_area_light("Fill", target + Vector((-0.08, -0.02, 0.04)), target, 10.0)

    camera_data = bpy.data.cameras.new("MouthEvidenceCamera")
    camera_data.lens = 72
    camera = bpy.data.objects.new("MouthEvidenceCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    scene.camera = camera

    args.output_dir.mkdir(parents=True, exist_ok=True)
    render(
        camera,
        target,
        target + Vector((0.075, -0.095, 0.065)),
        args.output_dir / "mouth_perspective.png",
    )
    render(
        camera,
        target,
        target + Vector((0.0, 0.0, 0.14)),
        args.output_dir / "mouth_top.png",
    )


if __name__ == "__main__":
    main()
