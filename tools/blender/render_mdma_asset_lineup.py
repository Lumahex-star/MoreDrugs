"""Render the MoreDrugs tablet press, crystals, and heart pill together.

Run with:
    blender --background --factory-startup --python-exit-code 1 \
        --python tools/blender/render_mdma_asset_lineup.py

The comparison scene is written under ignored artifacts. The bundled source GLBs
remain the authoritative assets.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Euler, Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "src" / "MoreDrugs" / "Assets" / "Models"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "previews" / "mdma-asset-lineup"

PRESS_PATH = MODEL_DIR / "manual_tablet_press.glb"
CRYSTALS_PATH = MODEL_DIR / "mdma_crystals.glb"
HEART_PATH = MODEL_DIR / "heartpill.glb"
COMPARISON_BLEND_PATH = OUTPUT_DIR / "mdma_asset_lineup.blend"


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_asset(path: Path, container_name: str) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    before = {obj.as_pointer() for obj in bpy.context.scene.objects}
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [
        obj
        for obj in bpy.context.scene.objects
        if obj.as_pointer() not in before
    ]
    roots = [obj for obj in imported if obj.parent is None]
    container = bpy.data.objects.new(container_name, None)
    bpy.context.collection.objects.link(container)
    for root in roots:
        world_matrix = root.matrix_world.copy()
        root.parent = container
        root.matrix_world = world_matrix
    return container, imported


def mesh_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    if not corners:
        raise RuntimeError("Imported asset does not contain a mesh.")
    minimum = Vector(
        (
            min(corner.x for corner in corners),
            min(corner.y for corner in corners),
            min(corner.z for corner in corners),
        )
    )
    maximum = Vector(
        (
            max(corner.x for corner in corners),
            max(corner.y for corner in corners),
            max(corner.z for corner in corners),
        )
    )
    return minimum, maximum


def place_asset(
    container: bpy.types.Object,
    objects: list[bpy.types.Object],
    target_xy: tuple[float, float],
    ground_z: float,
) -> None:
    bpy.context.view_layer.update()
    minimum, maximum = mesh_bounds(objects)
    center = (minimum + maximum) / 2
    container.location += Vector(
        (
            target_xy[0] - center.x,
            target_xy[1] - center.y,
            ground_z - minimum.z,
        )
    )
    bpy.context.view_layer.update()


def place_mesh(
    obj: bpy.types.Object,
    target_xy: tuple[float, float],
    ground_z: float,
) -> None:
    minimum, maximum = mesh_bounds([obj])
    center = (minimum + maximum) / 2
    obj.location += Vector(
        (
            target_xy[0] - center.x,
            target_xy[1] - center.y,
            ground_z - minimum.z,
        )
    )
    bpy.context.view_layer.update()


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    return material


def box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
    bevel: float,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(value / 2 for value in dimensions)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel > 0:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return obj


def add_stage() -> tuple[bpy.types.Object, bpy.types.Object]:
    floor_material = make_material(
        "LineupFloor",
        (0.025, 0.030, 0.038, 1.0),
        0.84,
    )
    plinth_material = make_material(
        "LineupPlinth",
        (0.11, 0.14, 0.17, 1.0),
        0.52,
        0.12,
    )
    floor = box(
        "LineupFloor",
        (0.0, 0.0, -0.04),
        (6.0, 6.0, 0.08),
        floor_material,
        0.0,
    )
    plinth = box(
        "ProductComparisonPlinth",
        (0.0, 0.0, -1.0),
        (0.56, 0.24, 0.06),
        plinth_material,
        0.012,
    )
    return floor, plinth


def add_lighting() -> bpy.types.Object:
    for index, (location, energy, color, size) in enumerate(
        (
            ((-2.0, -2.3, 3.2), 1250, (1.0, 0.82, 0.70), 2.3),
            ((2.2, -0.5, 2.1), 850, (0.56, 0.72, 1.0), 1.7),
            ((-0.3, 2.2, 2.6), 950, (1.0, 0.34, 0.52), 1.4),
        ),
        start=1,
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = f"LineupLight_{index}"
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "LineupCamera"
    bpy.context.scene.camera = camera
    return camera


def point_camera(
    camera: bpy.types.Object,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    lens: float,
) -> None:
    camera.data.type = "PERSP"
    camera.data.lens = lens
    camera.location = location
    camera.rotation_euler = (
        Vector(target) - camera.location
    ).to_track_quat("-Z", "Y").to_euler()


def render(
    camera: bpy.types.Object,
    filename: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    lens: float,
    resolution: tuple[int, int],
) -> None:
    point_camera(camera, location, target, lens)
    scene = bpy.context.scene
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.filepath = str(OUTPUT_DIR / filename)
    bpy.ops.render.render(write_still=True)


def set_hidden(container: bpy.types.Object, hidden: bool) -> None:
    container.hide_render = hidden
    for child in container.children_recursive:
        child.hide_render = hidden


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.frame_set(1)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.008, 0.010, 0.014)
    scene.view_settings.look = "AgX - Medium High Contrast"


def main() -> None:
    for path in (PRESS_PATH, CRYSTALS_PATH, HEART_PATH):
        if not path.exists():
            raise FileNotFoundError(path)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reset_scene()
    press, press_objects = import_asset(PRESS_PATH, "Lineup_TabletPress")
    crystals, crystal_objects = import_asset(CRYSTALS_PATH, "Lineup_MdmaCrystals")
    heart, heart_objects = import_asset(HEART_PATH, "Lineup_HeartPill")
    floor, plinth = add_stage()
    camera = add_lighting()
    configure_scene()

    place_asset(press, press_objects, (0.0, 0.0), 0.0)

    place_asset(crystals, crystal_objects, (0.03, -0.025), 1.108)

    heart.scale = (0.06, 0.06, 0.06)
    first_rotation = Euler((math.radians(78), 0.0, math.radians(-8))).to_quaternion()
    second_rotation = Euler((0.0, math.radians(90), 0.0)).to_quaternion()
    heart.rotation_euler = (first_rotation @ second_rotation).to_euler()
    place_asset(heart, heart_objects, (0.35, -0.015), 1.062)

    render(
        camera,
        "lineup_full.png",
        (1.70, -2.65, 1.65),
        (0.02, 0.0, 0.92),
        60,
        (1200, 1000),
    )
    render(
        camera,
        "lineup_work_area.png",
        (0.88, -1.22, 1.35),
        (0.10, -0.01, 1.12),
        72,
        (1200, 900),
    )

    bpy.ops.wm.save_as_mainfile(filepath=str(COMPARISON_BLEND_PATH))

    set_hidden(press, True)
    floor.location.z = -0.04
    plinth.location = (0.0, 0.0, 0.03)
    place_asset(crystals, crystal_objects, (-0.085, 0.0), 0.062)
    place_asset(heart, heart_objects, (0.105, 0.0), 0.062)
    render(
        camera,
        "lineup_product_scale.png",
        (0.31, -0.44, 0.26),
        (0.0, 0.0, 0.085),
        66,
        (1200, 800),
    )

    crystal_variants = {
        obj.name: obj
        for obj in crystal_objects
        if obj.type == "MESH"
        and obj.name in {
            "CrystalPile",
            "CrystalChunk_A",
            "CrystalChunk_B",
            "CrystalGranules",
        }
    }
    if set(crystal_variants) != {
        "CrystalPile",
        "CrystalChunk_A",
        "CrystalChunk_B",
        "CrystalGranules",
    }:
        raise RuntimeError(
            f"Unexpected crystal variants: {sorted(crystal_variants)}"
        )

    crystals.location = (0.0, 0.0, 0.0)
    crystals.rotation_euler = (0.0, 0.0, 0.0)
    crystals.scale = (1.0, 1.0, 1.0)
    for obj, target_x in (
        (crystal_variants["CrystalPile"], -0.17),
        (crystal_variants["CrystalChunk_A"], -0.065),
        (crystal_variants["CrystalChunk_B"], 0.005),
        (crystal_variants["CrystalGranules"], 0.10),
    ):
        place_mesh(obj, (target_x, 0.0), 0.062)
    place_asset(heart, heart_objects, (0.205, 0.0), 0.062)
    plinth.dimensions = (0.56, 0.24, 0.06)
    render(
        camera,
        "lineup_variants.png",
        (0.36, -0.56, 0.30),
        (0.015, 0.0, 0.085),
        68,
        (1400, 800),
    )

    print(f"Comparison blend: {COMPARISON_BLEND_PATH}")
    print(f"Renders: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
