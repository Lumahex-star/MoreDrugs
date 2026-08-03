"""Validate and render the exported DrugExpansion manual tablet press GLB."""

from __future__ import annotations

import json
from pathlib import Path
import struct

import bpy
from mathutils import Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
GLB_PATH = REPO_ROOT / "src" / "DrugExpansion" / "Assets" / "Models" / "manual_tablet_press.glb"
PREVIEW_DIR = REPO_ROOT / "artifacts" / "previews" / "manual-tablet-press"
PREVIEW_VIEWS = (
    ("idle_front", 1, (1.65, -2.75, 1.45)),
    ("feed_left", 14, (-1.90, -2.45, 1.42)),
    ("pressed_front", 36, (1.65, -2.75, 1.45)),
    ("ejected_right", 84, (2.20, 2.10, 1.38)),
)
ANIMATION_PREVIEW_PATH = PREVIEW_DIR / "manual_tablet_press_cycle.mp4"
ANIMATION_FRAMES_DIR = PREVIEW_DIR / "cycle-frames"

EXPECTED_NODES = {
    "ManualTabletPress",
    "PedestalAssembly",
    "MachineAssembly",
    "StaticAssembly",
    "HandlePivot",
    "RamAssembly",
    "FeedShoeAssembly",
    "FeedPowderAssembly",
    "DieFillAssembly",
    "EjectorAssembly",
    "FreshTabletAssembly",
    "Interaction",
    "HandleClickableAnchor",
    "PlaneNormal",
    "HandleRaised",
    "HandleLowered",
    "PressTransform",
    "PressRaised",
    "PressLowered",
    "MouldDetector",
    "CameraPouring",
    "CameraPressing",
    "StandPoint",
    "ContainerSpawnPoint",
    "OutputPoint",
}


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def add_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    return result


def read_glb_json() -> dict:
    with GLB_PATH.open("rb") as glb_file:
        if glb_file.read(4) != b"glTF":
            raise RuntimeError("Export does not have a valid GLB header.")
        version, total_length = struct.unpack("<II", glb_file.read(8))
        if version != 2 or total_length != GLB_PATH.stat().st_size:
            raise RuntimeError("GLB header length or version is invalid.")
        json_length, json_type = struct.unpack("<II", glb_file.read(8))
        if json_type != 0x4E4F534A:
            raise RuntimeError("First GLB chunk is not JSON.")
        return json.loads(glb_file.read(json_length).decode("utf-8"))


def add_preview_scene(target: Vector, dimensions: Vector) -> bpy.types.Object:
    floor_material = add_material("Validation Floor", (0.04, 0.045, 0.05, 1), 0.88)
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, -0.02))
    floor = bpy.context.object
    floor.name = "ValidationFloor"
    floor.data.materials.append(floor_material)

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.lens = 58
    bpy.context.scene.camera = camera

    for location, energy, color, size in (
        ((-1.7, -1.9, 2.5), 1200, (1.0, 0.82, 0.70), 2.0),
        ((1.8, -0.5, 1.5), 800, (0.55, 0.72, 1.0), 1.5),
        ((0.0, 1.7, 1.9), 900, (1.0, 0.30, 0.52), 1.0),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.015, 0.018, 0.022)
    return camera


def render_evidence(
    camera: bpy.types.Object,
    target: Vector,
) -> None:
    scene = bpy.context.scene
    for name, frame, camera_location in PREVIEW_VIEWS:
        scene.frame_set(frame)
        camera.location = camera_location
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(PREVIEW_DIR / f"manual_tablet_press_{name}.png")
        bpy.ops.render.render(write_still=True)

    scene.frame_start = 1
    scene.frame_end = 96
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    ANIMATION_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(ANIMATION_FRAMES_DIR / "frame_")
    camera.location = (1.65, -2.75, 1.45)
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(animation=True)


def main() -> None:
    if not GLB_PATH.exists():
        raise FileNotFoundError(GLB_PATH)
    gltf = read_glb_json()
    gltf_node_names = [node.get("name", "") for node in gltf.get("nodes", [])]
    duplicate_node_names = {
        name for name in gltf_node_names if name and gltf_node_names.count(name) > 1
    }
    missing_nodes = EXPECTED_NODES.difference(gltf_node_names)
    animations = gltf.get("animations", [])
    animation_names = [animation.get("name", "") for animation in animations]

    if duplicate_node_names:
        raise RuntimeError(f"Duplicate GLB node names: {sorted(duplicate_node_names)}")
    if missing_nodes:
        raise RuntimeError(f"Missing required runtime nodes: {sorted(missing_nodes)}")
    if animation_names != ["PressCycle"]:
        raise RuntimeError(f"Expected one PressCycle animation, found {animation_names}.")

    animated_node_names = {
        gltf_node_names[channel["target"]["node"]]
        for channel in animations[0].get("channels", [])
    }
    expected_animated_nodes = {
        "HandlePivot",
        "RamAssembly",
        "FeedShoeAssembly",
        "FeedPowderAssembly",
        "DieFillAssembly",
        "EjectorAssembly",
        "FreshTabletAssembly",
    }
    if not expected_animated_nodes.issubset(animated_node_names):
        raise RuntimeError(
            "PressCycle does not animate all runtime assemblies: "
            f"{sorted(expected_animated_nodes.difference(animated_node_names))}"
        )

    reset_scene()
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))

    imported = list(bpy.context.scene.objects)
    meshes = [obj for obj in imported if obj.type == "MESH"]
    materials = {slot.material.name for obj in meshes for slot in obj.material_slots if slot.material}
    animated = [
        obj
        for obj in imported
        if obj.animation_data is not None
        and (
            obj.animation_data.action is not None
            or len(obj.animation_data.nla_tracks) > 0
        )
    ]
    triangles = sum(
        len(polygon.vertices) - 2
        for obj in meshes
        for polygon in obj.data.polygons
    )

    if not any(obj.name.startswith("ManualTabletPress") for obj in imported):
        raise RuntimeError("ManualTabletPress root was not preserved in the GLB.")
    if triangles > 6000:
        raise RuntimeError(f"Triangle budget exceeded: {triangles}")
    if len(materials) < 6:
        raise RuntimeError(f"Expected at least six authored materials, found {len(materials)}.")
    if len(animated) < len(expected_animated_nodes):
        raise RuntimeError(
            f"Expected {len(expected_animated_nodes)} animated assemblies, found {len(animated)}."
        )

    world_corners = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    minimum = Vector(
        (
            min(corner.x for corner in world_corners),
            min(corner.y for corner in world_corners),
            min(corner.z for corner in world_corners),
        )
    )
    maximum = Vector(
        (
            max(corner.x for corner in world_corners),
            max(corner.y for corner in world_corners),
            max(corner.z for corner in world_corners),
        )
    )
    dimensions = maximum - minimum
    if max(dimensions) > 4.0 or min(dimensions) <= 0:
        raise RuntimeError(f"Unexpected imported dimensions: {tuple(dimensions)}")
    if not 1.6 <= dimensions.z <= 2.0:
        raise RuntimeError(
            f"Tablet press must remain a floor-standing player-height station: {tuple(dimensions)}"
        )

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    target = (minimum + maximum) / 2
    camera = add_preview_scene(target, dimensions)
    render_evidence(camera, target)

    print(f"Validated GLB: {GLB_PATH}")
    print(f"File size: {GLB_PATH.stat().st_size} bytes")
    print(f"Mesh objects: {len(meshes)}")
    print(f"Triangles: {triangles}")
    print(f"Materials: {len(materials)}")
    print(f"Animation: {animation_names[0]} ({len(animations[0]['channels'])} channels)")
    print(f"Animated nodes: {[obj.name for obj in animated]}")
    print(f"Dimensions: {tuple(round(value, 3) for value in dimensions)} meters")
    print(f"Evidence views: {[name for name, _, _ in PREVIEW_VIEWS]}")
    print(f"Animation frames: {ANIMATION_FRAMES_DIR}")


if __name__ == "__main__":
    main()
