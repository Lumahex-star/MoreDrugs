"""Render the MoreDrugs MDMA crystal-to-tablet press showcase.

Run with:
    blender --background --factory-startup --python-exit-code 1 \
        --python tools/blender/render_mdma_press_crystal_showcase.py

This scene is a presentation reference. Unity remains authoritative for
inventory changes, press interaction, and the final physics-assisted landing.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_mdma_press_material_flow import (
    CRYSTAL_VARIANTS,
    CRYSTALS_PATH,
    HEART_PATH,
    PRESS_PATH,
    PRESS_STAND_INS,
    ImportedAsset,
    add_floor,
    bounds_center,
    center_asset_on,
    import_asset,
    make_material,
    mesh_bounds,
    move_asset_to_anchor,
    place_asset_on,
    prepare_crystal_asset,
    reset_scene,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = (
    REPO_ROOT
    / "artifacts"
    / "previews"
    / "mdma-press-crystal-showcase"
)
SHOWCASE_BLEND_PATH = OUTPUT_DIR / "mdma_press_crystal_showcase.blend"
SHOWCASE_VIDEO_PATH = OUTPUT_DIR / "mdma_press_crystal_showcase.mp4"
ANIMATION_FRAMES_DIR = OUTPUT_DIR / "animation-frames"

SOURCE_START = 1
SOURCE_END = 96
ACTION_START = 25
TIME_SCALE = 1.5


def showcase_frame(source_frame: float) -> float:
    return ACTION_START + (source_frame - SOURCE_START) * TIME_SCALE


FRAME_END = round(showcase_frame(SOURCE_END))
CRITICAL_FRAMES = (
    ("01_machine_loaded", 1),
    ("02_crystals_dispensing", round(showcase_frame(7))),
    ("03_feed_shoe_travelling", round(showcase_frame(14))),
    ("04_die_filled", round(showcase_frame(24))),
    ("05_compressed", round(showcase_frame(42))),
    ("06_tablet_ejected", round(showcase_frame(62))),
    ("07_tablet_collected", round(showcase_frame(84))),
    ("08_settled", FRAME_END),
)


def action_fcurves(action: bpy.types.Action):
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                yield from channelbag.fcurves


def retime_press_actions(press: ImportedAsset) -> None:
    actions = {
        obj.animation_data.action
        for obj in press.objects
        if obj.animation_data is not None
        and obj.animation_data.action is not None
    }
    if not actions:
        raise RuntimeError(
            "Imported press does not contain an animation action."
        )

    for action in actions:
        for fcurve in action_fcurves(action):
            for point in fcurve.keyframe_points:
                for coordinate in (
                    point.co,
                    point.handle_left,
                    point.handle_right,
                ):
                    coordinate.x = showcase_frame(coordinate.x)


def set_constant_visibility(
    asset: ImportedAsset,
    states: tuple[tuple[int, bool], ...],
) -> None:
    animated_objects = [asset.container, *asset.objects]
    for obj in animated_objects:
        for frame, visible in states:
            obj.hide_render = not visible
            obj.hide_viewport = not visible
            obj.keyframe_insert(data_path="hide_render", frame=frame)
            obj.keyframe_insert(data_path="hide_viewport", frame=frame)

        if obj.animation_data is None or obj.animation_data.action is None:
            continue
        for fcurve in action_fcurves(obj.animation_data.action):
            if fcurve.data_path not in {"hide_render", "hide_viewport"}:
                continue
            for point in fcurve.keyframe_points:
                point.interpolation = "CONSTANT"


def parent_keep_world(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    world_matrix = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = world_matrix


def animate_tablet_ejection(tablet: bpy.types.Object) -> None:
    start_location = tablet.location.copy()
    start_rotation = tablet.rotation_euler.copy()
    tablet.rotation_mode = "XYZ"

    poses = (
        (
            round(showcase_frame(50)),
            start_location,
            start_rotation,
        ),
        (
            round(showcase_frame(56)),
            start_location + Vector((0.035, -0.005, 0.055)),
            Vector(
                (
                    math.radians(-10),
                    math.radians(12),
                    math.radians(10),
                )
            ),
        ),
        (
            round(showcase_frame(70)),
            start_location + Vector((0.135, -0.010, 0.035)),
            Vector(
                (
                    math.radians(-15),
                    math.radians(20),
                    math.radians(28),
                )
            ),
        ),
        (
            round(showcase_frame(82)),
            start_location + Vector((0.205, -0.005, -0.098)),
            Vector(
                (
                    math.radians(6),
                    math.radians(-4),
                    math.radians(42),
                )
            ),
        ),
        (
            round(showcase_frame(88)),
            start_location + Vector((0.215, 0.0, -0.073)),
            Vector(
                (
                    math.radians(-3),
                    math.radians(-2),
                    math.radians(38),
                )
            ),
        ),
        (
            FRAME_END,
            start_location + Vector((0.210, 0.0, -0.098)),
            Vector(
                (
                    math.radians(2),
                    math.radians(-4),
                    math.radians(40),
                )
            ),
        ),
    )
    for frame, location, rotation in poses:
        tablet.location = location
        tablet.rotation_euler = rotation
        tablet.keyframe_insert(data_path="location", frame=frame)
        tablet.keyframe_insert(data_path="rotation_euler", frame=frame)

    if tablet.animation_data is None or tablet.animation_data.action is None:
        raise RuntimeError("Tablet ejection path did not create an action.")
    for fcurve in action_fcurves(tablet.animation_data.action):
        if fcurve.data_path not in {"location", "rotation_euler"}:
            continue
        for point in fcurve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"


def create_lighting() -> None:
    lights = (
        ((-1.8, -2.4, 3.2), 1250, (1.0, 0.82, 0.70), 2.2),
        ((1.8, -0.6, 2.2), 850, (0.55, 0.72, 1.0), 1.7),
        ((-0.2, 2.2, 2.5), 900, (1.0, 0.34, 0.56), 1.5),
    )
    for index, (location, energy, color, size) in enumerate(
        lights,
        start=1,
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = f"ShowcaseLight_{index}"
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size


def create_animated_camera() -> bpy.types.Object:
    target = bpy.data.objects.new("ShowcaseCameraTarget", None)
    bpy.context.collection.objects.link(target)
    target.location = (0.02, 0.0, 0.95)

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "ShowcaseCamera"
    camera.data.lens = 58
    camera.location = (2.30, -3.60, 1.72)
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.name = "TrackPress"
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    bpy.context.scene.camera = camera

    for frame, camera_location, target_location in (
        (1, (3.00, -4.50, 2.10), (0.02, 0.0, 0.92)),
        (
            ACTION_START,
            (3.00, -4.50, 2.10),
            (0.02, 0.0, 0.92),
        ),
        (
            round(showcase_frame(18)),
            (1.25, -1.95, 1.58),
            (0.08, 0.0, 1.16),
        ),
        (
            round(showcase_frame(72)),
            (1.08, -1.70, 1.48),
            (0.20, 0.0, 1.14),
        ),
        (
            FRAME_END,
            (0.55, -0.78, 1.65),
            (0.36, 0.0, 1.05),
        ),
    ):
        camera.location = camera_location
        target.location = target_location
        camera.keyframe_insert(data_path="location", frame=frame)
        target.keyframe_insert(data_path="location", frame=frame)

    for animated in (camera, target):
        if animated.animation_data is None:
            continue
        action = animated.animation_data.action
        if action is None:
            continue
        for fcurve in action_fcurves(action):
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"

    return camera


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.render.fps = 24
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.010, 0.014)
    scene.view_settings.look = "AgX - Medium High Contrast"


def render_critical_frames() -> None:
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    for slug, frame in CRITICAL_FRAMES:
        scene.frame_set(frame)
        scene.render.filepath = str(OUTPUT_DIR / f"{slug}.png")
        bpy.ops.render.render(write_still=True)


def render_animation_frames() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    ANIMATION_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for stale_frame in ANIMATION_FRAMES_DIR.glob("frame_*.png"):
        stale_frame.unlink()
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(ANIMATION_FRAMES_DIR / "frame_")
    bpy.ops.render.render(animation=True)


def main() -> None:
    for path in (PRESS_PATH, CRYSTALS_PATH, HEART_PATH):
        if not path.exists():
            raise FileNotFoundError(path)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reset_scene()
    press = import_asset(PRESS_PATH, "Showcase_TabletPress")
    retime_press_actions(press)
    for obj in press.objects:
        if obj.name in PRESS_STAND_INS:
            obj.hide_render = True
            obj.hide_viewport = True

    hopper_crystals, hopper_meshes = prepare_crystal_asset(
        "Showcase_HopperCrystals",
        {"CrystalPile", "CrystalChunk_A", "CrystalChunk_B"},
    )
    outlet_crystals, outlet_meshes = prepare_crystal_asset(
        "Showcase_OutletGranules",
        {"CrystalGranules"},
    )
    shoe_crystals, shoe_meshes = prepare_crystal_asset(
        "Showcase_ShoeGranules",
        {"CrystalGranules"},
    )
    die_crystals, die_meshes = prepare_crystal_asset(
        "Showcase_DieGranules",
        {"CrystalGranules"},
    )
    compressed_heart = import_asset(
        HEART_PATH,
        "Showcase_CompressedHeart",
    )
    moving_heart = import_asset(HEART_PATH, "Showcase_MovingHeart")

    if {
        source_name
        for source_name in (
            obj.name.rsplit(".", 1)[0]
            if obj.name.rsplit(".", 1)[-1].isdigit()
            else obj.name
            for asset in (
                hopper_crystals,
                outlet_crystals,
                shoe_crystals,
                die_crystals,
            )
            for obj in asset.objects
            if obj.type == "MESH"
        )
    } != CRYSTAL_VARIANTS:
        raise RuntimeError("Crystal showcase imports lost a required variant.")

    outlet_crystals.container.scale = (0.40, 0.40, 0.48)
    shoe_crystals.container.scale = (0.82, 0.82, 0.82)
    die_crystals.container.scale = (0.72, 0.72, 0.72)
    compressed_heart.container.scale = (0.06, 0.06, 0.06)
    moving_heart.container.scale = (0.06, 0.06, 0.06)

    add_floor()
    create_lighting()
    create_animated_camera()
    configure_scene()

    scene = bpy.context.scene
    scene.frame_set(1)
    hopper_rim = press.named("PowderHopperRim")
    hopper_center = bounds_center(hopper_rim)
    _, hopper_maximum = mesh_bounds([hopper_rim])
    place_asset_on(
        hopper_crystals,
        hopper_meshes,
        (hopper_center.x, hopper_center.y),
        hopper_maximum.z - 0.018,
    )

    outlet_start = round(showcase_frame(4))
    outlet_end = round(showcase_frame(9))
    scene.frame_set(outlet_start)
    move_asset_to_anchor(
        outlet_crystals,
        outlet_meshes,
        press.named("FeedPowder"),
        z_offset=0.010,
    )

    shoe_start = round(showcase_frame(6))
    shoe_end = round(showcase_frame(17))
    scene.frame_set(ACTION_START)
    move_asset_to_anchor(
        shoe_crystals,
        shoe_meshes,
        press.named("FeedPowder"),
        z_offset=-0.001,
    )
    parent_keep_world(
        shoe_crystals.container,
        press.named("FeedShoeAssembly"),
    )

    die_start = round(showcase_frame(17))
    die_end = round(showcase_frame(34))
    scene.frame_set(die_start)
    move_asset_to_anchor(
        die_crystals,
        die_meshes,
        press.named("DiePowderFill"),
        z_offset=-0.001,
    )

    compressed_start = round(showcase_frame(35))
    moving_start = round(showcase_frame(50))
    scene.frame_set(compressed_start)
    compressed_meshes = [
        obj for obj in compressed_heart.objects if obj.type == "MESH"
    ]
    if not compressed_meshes:
        raise RuntimeError("Compressed heart asset has no mesh.")
    center_asset_on(
        compressed_heart,
        compressed_meshes,
        press.named("HeartDieInsert"),
    )

    scene.frame_set(moving_start)
    moving_meshes = [
        obj for obj in moving_heart.objects if obj.type == "MESH"
    ]
    if not moving_meshes:
        raise RuntimeError("Moving heart asset has no mesh.")
    tablet_material = make_material(
        "Showcase_MDMA_Pink",
        (0.95, 0.035, 0.30, 1.0),
        0.30,
    )
    for mesh in compressed_meshes + moving_meshes:
        mesh.data.materials.clear()
        mesh.data.materials.append(tablet_material)
    center_asset_on(
        moving_heart,
        moving_meshes,
        press.named("HeartDieInsert"),
    )
    animate_tablet_ejection(moving_heart.container)

    set_constant_visibility(
        hopper_crystals,
        ((1, True), (FRAME_END, True)),
    )
    set_constant_visibility(
        outlet_crystals,
        ((1, False), (outlet_start, True), (outlet_end, False)),
    )
    set_constant_visibility(
        shoe_crystals,
        ((1, False), (shoe_start, True), (shoe_end, False)),
    )
    set_constant_visibility(
        die_crystals,
        ((1, False), (die_start, True), (die_end, False)),
    )
    set_constant_visibility(
        compressed_heart,
        ((1, False), (compressed_start, True), (moving_start, False)),
    )
    set_constant_visibility(
        moving_heart,
        ((1, False), (moving_start, True), (FRAME_END, True)),
    )

    bpy.ops.wm.save_as_mainfile(filepath=str(SHOWCASE_BLEND_PATH))
    render_critical_frames()
    render_animation_frames()
    print(f"Showcase blend: {SHOWCASE_BLEND_PATH}")
    print(f"Showcase frames: {ANIMATION_FRAMES_DIR}")
    print(f"Encode target: {SHOWCASE_VIDEO_PATH}")
    print(f"Critical frames: {CRITICAL_FRAMES}")


if __name__ == "__main__":
    main()
