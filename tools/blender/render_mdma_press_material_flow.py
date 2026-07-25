"""Render a staged MDMA crystal-to-tablet material-flow reference.

Run with:
    blender --background --factory-startup --python-exit-code 1 \
        --python tools/blender/render_mdma_press_material_flow.py

The ignored output scene is a presentation reference. Unity remains
authoritative for press state, inventory changes, and ejection physics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import bpy
from mathutils import Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "src" / "MoreDrugs" / "Assets" / "Models"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "previews" / "mdma-press-material-flow"

PRESS_PATH = MODEL_DIR / "manual_tablet_press.glb"
CRYSTALS_PATH = MODEL_DIR / "mdma_crystals.glb"
HEART_PATH = MODEL_DIR / "heartpill.glb"
REFERENCE_BLEND_PATH = OUTPUT_DIR / "mdma_press_material_flow.blend"

CRYSTAL_VARIANTS = {
    "CrystalPile",
    "CrystalChunk_A",
    "CrystalChunk_B",
    "CrystalGranules",
}
PRESS_STAND_INS = {
    "FeedPowder",
    "DiePowderFill",
    "FreshTablet",
    "FinishedTablet_01",
    "FinishedTablet_02",
    "FinishedTablet_03",
}


@dataclass(frozen=True)
class ImportedAsset:
    container: bpy.types.Object
    objects: list[bpy.types.Object]

    def named(self, name: str) -> bpy.types.Object:
        matches = [obj for obj in self.objects if obj.name == name]
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected one imported object named '{name}', found {len(matches)}."
            )
        return matches[0]


def source_name(obj: bpy.types.Object) -> str:
    """Return the GLB node name before Blender's duplicate-name suffix."""
    return obj.name.rsplit(".", 1)[0] if obj.name.rsplit(".", 1)[-1].isdigit() else obj.name


@dataclass(frozen=True)
class Stage:
    slug: str
    frame: int
    show_hopper: bool
    show_shoe: bool
    show_die: bool
    show_heart: bool
    heart_anchor: str


STAGES = (
    Stage("01_loaded", 1, True, True, False, False, "FreshTablet"),
    Stage("02_feeding", 14, True, True, False, False, "FreshTablet"),
    Stage("03_die_filled", 24, True, False, True, False, "FreshTablet"),
    Stage("04_compressed", 42, True, False, False, True, "HeartDieInsert"),
    Stage("05_ejected", 62, True, False, False, True, "FreshTablet"),
    Stage("06_collected", 84, True, False, False, True, "FreshTablet"),
)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_asset(path: Path, container_name: str) -> ImportedAsset:
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
    return ImportedAsset(container, imported)


def mesh_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    if not corners:
        raise RuntimeError("Expected at least one mesh object.")
    return (
        Vector(
            (
                min(corner.x for corner in corners),
                min(corner.y for corner in corners),
                min(corner.z for corner in corners),
            )
        ),
        Vector(
            (
                max(corner.x for corner in corners),
                max(corner.y for corner in corners),
                max(corner.z for corner in corners),
            )
        ),
    )


def bounds_center(obj: bpy.types.Object) -> Vector:
    minimum, maximum = mesh_bounds([obj])
    return (minimum + maximum) / 2


def place_asset_on(
    asset: ImportedAsset,
    visible_meshes: list[bpy.types.Object],
    target_xy: tuple[float, float],
    surface_z: float,
) -> None:
    bpy.context.view_layer.update()
    minimum, maximum = mesh_bounds(visible_meshes)
    center = (minimum + maximum) / 2
    asset.container.location += Vector(
        (
            target_xy[0] - center.x,
            target_xy[1] - center.y,
            surface_z - minimum.z,
        )
    )
    bpy.context.view_layer.update()


def set_asset_visible(asset: ImportedAsset, visible: bool) -> None:
    asset.container.hide_render = not visible
    for obj in asset.objects:
        obj.hide_render = not visible


def set_variant_visibility(
    asset: ImportedAsset,
    visible_variants: set[str],
) -> list[bpy.types.Object]:
    visible_meshes = []
    for obj in asset.objects:
        if obj.type != "MESH":
            continue
        obj.hide_render = source_name(obj) not in visible_variants
        if not obj.hide_render:
            visible_meshes.append(obj)
    if {source_name(obj) for obj in visible_meshes} != visible_variants:
        raise RuntimeError(
            "Unexpected crystal variants: "
            f"{[source_name(obj) for obj in visible_meshes]}"
        )
    asset.container.hide_render = False
    return visible_meshes


def move_asset_to_anchor(
    asset: ImportedAsset,
    visible_meshes: list[bpy.types.Object],
    anchor: bpy.types.Object,
    z_offset: float = 0.0,
) -> None:
    center = bounds_center(anchor)
    _, anchor_maximum = mesh_bounds([anchor])
    place_asset_on(
        asset,
        visible_meshes,
        (center.x, center.y),
        anchor_maximum.z + z_offset,
    )


def center_asset_on(
    asset: ImportedAsset,
    visible_meshes: list[bpy.types.Object],
    anchor: bpy.types.Object,
) -> None:
    minimum, maximum = mesh_bounds(visible_meshes)
    asset_center = (minimum + maximum) / 2
    anchor_center = bounds_center(anchor)
    asset.container.location += anchor_center - asset_center
    bpy.context.view_layer.update()


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    return material


def add_floor() -> None:
    material = make_material(
        "FlowReferenceFloor",
        (0.022, 0.026, 0.032, 1.0),
        0.86,
    )
    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, -0.04))
    floor = bpy.context.object
    floor.name = "FlowReferenceFloor"
    floor.scale = (3.0, 3.0, 0.04)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    floor.data.materials.append(material)


def add_lighting_and_camera() -> bpy.types.Object:
    lights = (
        ((-1.8, -2.2, 3.0), 1100, (1.0, 0.83, 0.72), 2.0),
        ((1.7, -0.6, 2.2), 760, (0.58, 0.72, 1.0), 1.5),
        ((-0.1, 2.0, 2.5), 800, (1.0, 0.38, 0.56), 1.3),
    )
    for index, (location, energy, color, size) in enumerate(lights, start=1):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = f"FlowReferenceLight_{index}"
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "FlowReferenceCamera"
    camera.data.lens = 72
    camera.location = (0.90, -1.25, 1.72)
    camera.rotation_euler = (
        Vector((0.12, 0.0, 1.15)) - camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera
    return camera


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.008, 0.010, 0.014)
    scene.view_settings.look = "AgX - Medium High Contrast"


def prepare_crystal_asset(
    name: str,
    visible_variants: set[str],
) -> tuple[ImportedAsset, list[bpy.types.Object]]:
    asset = import_asset(CRYSTALS_PATH, name)
    mesh_names = {
        source_name(obj)
        for obj in asset.objects
        if obj.type == "MESH"
    }
    if mesh_names != CRYSTAL_VARIANTS:
        raise RuntimeError(f"Unexpected crystal hierarchy: {sorted(mesh_names)}")
    visible_meshes = set_variant_visibility(asset, visible_variants)
    return asset, visible_meshes


def main() -> None:
    for path in (PRESS_PATH, CRYSTALS_PATH, HEART_PATH):
        if not path.exists():
            raise FileNotFoundError(path)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reset_scene()
    press = import_asset(PRESS_PATH, "Flow_TabletPress")
    hopper_crystals, hopper_meshes = prepare_crystal_asset(
        "Flow_HopperCrystals",
        {"CrystalPile", "CrystalChunk_A", "CrystalChunk_B"},
    )
    shoe_crystals, shoe_meshes = prepare_crystal_asset(
        "Flow_ShoeGranules",
        {"CrystalGranules"},
    )
    die_crystals, die_meshes = prepare_crystal_asset(
        "Flow_DieGranules",
        {"CrystalGranules"},
    )
    shoe_crystals.container.scale = (0.58, 0.58, 0.58)
    die_crystals.container.scale = (0.52, 0.52, 0.52)
    heart = import_asset(HEART_PATH, "Flow_HeartPill")
    heart.container.scale = (0.06, 0.06, 0.06)

    for obj in press.objects:
        if obj.name in PRESS_STAND_INS:
            obj.hide_render = True

    add_floor()
    add_lighting_and_camera()
    configure_scene()

    # The hopper contents sit just inside the rim instead of floating above it.
    hopper_rim = press.named("PowderHopperRim")
    hopper_center = bounds_center(hopper_rim)
    _, hopper_maximum = mesh_bounds([hopper_rim])
    place_asset_on(
        hopper_crystals,
        hopper_meshes,
        (hopper_center.x, hopper_center.y),
        hopper_maximum.z - 0.018,
    )

    # The shoe and die use only the fine, transferable granule variant.
    move_asset_to_anchor(
        shoe_crystals,
        shoe_meshes,
        press.named("FeedPowder"),
        z_offset=-0.003,
    )
    move_asset_to_anchor(
        die_crystals,
        die_meshes,
        press.named("DiePowderFill"),
        z_offset=-0.003,
    )

    heart_meshes = [obj for obj in heart.objects if obj.type == "MESH"]
    if not heart_meshes:
        raise RuntimeError("Heart-pill asset does not contain a mesh.")

    for stage in STAGES:
        bpy.context.scene.frame_set(stage.frame)
        bpy.context.view_layer.update()

        set_asset_visible(hopper_crystals, stage.show_hopper)
        set_asset_visible(shoe_crystals, stage.show_shoe)
        set_asset_visible(die_crystals, stage.show_die)
        set_asset_visible(heart, stage.show_heart)

        if stage.show_shoe:
            move_asset_to_anchor(
                shoe_crystals,
                shoe_meshes,
                press.named("FeedPowder"),
                z_offset=-0.003,
            )
        if stage.show_die:
            move_asset_to_anchor(
                die_crystals,
                die_meshes,
                press.named("DiePowderFill"),
                z_offset=-0.003,
            )
        if stage.show_heart:
            anchor = press.named(stage.heart_anchor)
            if stage.heart_anchor == "FreshTablet":
                center_asset_on(heart, heart_meshes, anchor)
            else:
                center = bounds_center(anchor)
                _, maximum = mesh_bounds([anchor])
                place_asset_on(
                    heart,
                    heart_meshes,
                    (center.x, center.y),
                    maximum.z - 0.005,
                )

        scene = bpy.context.scene
        scene.render.filepath = str(OUTPUT_DIR / f"{stage.slug}.png")
        bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(REFERENCE_BLEND_PATH))
    print(f"Material-flow reference: {REFERENCE_BLEND_PATH}")
    print(f"Stage renders: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
