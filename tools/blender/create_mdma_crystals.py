"""Generate the original DrugExpansion MDMA crystals asset.

Run with:
    blender --background --factory-startup --python tools/blender/create_mdma_crystals.py

The asset is intentionally stylized and fictionalized. It is generated entirely
from Blender primitives and deterministic vertex deformation; no third-party
geometry or textures are used.
"""

from __future__ import annotations

import math
from pathlib import Path
import random

import bpy
from mathutils import Matrix, Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "src" / "DrugExpansion" / "Assets" / "Models"
SOURCE_DIR = REPO_ROOT / "assets" / "source"
PREVIEW_DIR = REPO_ROOT / "artifacts" / "previews" / "mdma-crystals"

BLEND_PATH = SOURCE_DIR / "mdma_crystals.blend"
GLB_PATH = MODEL_DIR / "mdma_crystals.glb"
HERO_PREVIEW_PATH = PREVIEW_DIR / "mdma_crystals_hero.png"

SEED = 0x4D444D41
TRIANGLE_BUDGET = 3_000
MAXIMUM_EXTENT_METERS = 0.12


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
    color: tuple[float, float, float, float],
    roughness: float,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["IOR"].default_value = 1.47
    return material


def parent_keep_transform(
    child: bpy.types.Object,
    parent: bpy.types.Object,
) -> None:
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def empty(
    name: str,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    result = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(result)
    if parent is not None:
        parent_keep_transform(result, parent)
    return result


def deform_icosphere(
    obj: bpy.types.Object,
    dimensions: tuple[float, float, float],
    rng: random.Random,
    *,
    vertical_bias: float,
) -> None:
    half_dimensions = Vector(value / 2 for value in dimensions)
    for vertex in obj.data.vertices:
        direction = vertex.co.normalized()
        irregularity = 1.0 + rng.uniform(-0.15, 0.17)
        directional = Vector(
            (
                1.0 + 0.08 * direction.y,
                1.0 - 0.06 * direction.x,
                1.0 + vertical_bias * max(direction.z, 0.0),
            )
        )
        vertex.co = Vector(
            (
                vertex.co.x * half_dimensions.x,
                vertex.co.y * half_dimensions.y,
                vertex.co.z * half_dimensions.z,
            )
        )
        vertex.co.x *= irregularity * directional.x
        vertex.co.y *= irregularity * directional.y
        vertex.co.z *= irregularity * directional.z
    obj.data.update()


def place_on_surface(
    obj: bpy.types.Object,
    surface_height: float,
) -> None:
    bpy.context.view_layer.update()
    minimum_z = min((obj.matrix_world @ vertex.co).z for vertex in obj.data.vertices)
    obj.location.z += surface_height - minimum_z
    bpy.context.view_layer.update()


def create_fragment(
    name: str,
    location_xy: tuple[float, float],
    dimensions: tuple[float, float, float],
    rotation_degrees: tuple[float, float, float],
    material: bpy.types.Material,
    parent: bpy.types.Object,
    rng: random.Random,
    *,
    surface_height: float,
    subdivisions: int = 1,
    vertical_bias: float = 0.16,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions,
        radius=1.0,
        location=(location_xy[0], location_xy[1], 0.0),
    )
    fragment = bpy.context.object
    fragment.name = name
    fragment.data.name = f"{name}_Mesh"
    deform_icosphere(
        fragment,
        dimensions,
        rng,
        vertical_bias=vertical_bias,
    )
    fragment.rotation_euler = tuple(math.radians(value) for value in rotation_degrees)
    fragment.data.materials.append(material)
    for polygon in fragment.data.polygons:
        polygon.use_smooth = False
    place_on_surface(fragment, surface_height)
    parent_keep_transform(fragment, parent)
    return fragment


def create_fractured_chunk(
    name: str,
    location_xy: tuple[float, float],
    dimensions: tuple[float, float, float],
    rotation_degrees: tuple[float, float, float],
    material: bpy.types.Material,
    parent: bpy.types.Object,
    rng: random.Random,
    *,
    surface_height: float,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=(location_xy[0], location_xy[1], 0.0))
    chunk = bpy.context.object
    chunk.name = name
    chunk.data.name = f"{name}_Mesh"
    chunk.scale = tuple(value / 2 for value in dimensions)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bevel = chunk.modifiers.new("FracturedEdges", "BEVEL")
    bevel.width = min(dimensions) * rng.uniform(0.16, 0.24)
    bevel.segments = 1
    bevel.limit_method = "NONE"
    bpy.context.view_layer.objects.active = chunk
    bpy.ops.object.modifier_apply(modifier=bevel.name)

    jitter = Vector(
        (
            dimensions[0] * 0.11,
            dimensions[1] * 0.11,
            dimensions[2] * 0.13,
        )
    )
    for vertex in chunk.data.vertices:
        vertex.co.x += rng.uniform(-jitter.x, jitter.x)
        vertex.co.y += rng.uniform(-jitter.y, jitter.y)
        vertex.co.z += rng.uniform(-jitter.z, jitter.z)
        if vertex.co.z > 0:
            vertex.co.x += dimensions[0] * 0.05 * (vertex.co.z / dimensions[2])
    chunk.data.update()

    chunk.rotation_euler = tuple(math.radians(value) for value in rotation_degrees)
    chunk.data.materials.append(material)
    for polygon in chunk.data.polygons:
        polygon.use_smooth = False
    place_on_surface(chunk, surface_height)
    parent_keep_transform(chunk, parent)
    return chunk


def join_meshes(
    objects: list[bpy.types.Object],
    name: str,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    if not objects:
        raise RuntimeError(f"Cannot build empty mesh variant '{name}'.")

    for obj in objects:
        world_matrix = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world_matrix
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(
            location=True,
            rotation=True,
            scale=True,
        )

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()

    result = bpy.context.object
    result.name = name
    result.data.name = f"{name}_Mesh"
    result.parent = parent
    result.matrix_parent_inverse = Matrix.Identity(4)
    result.location = (0.0, 0.0, 0.0)
    result.rotation_euler = (0.0, 0.0, 0.0)
    result.scale = (1.0, 1.0, 1.0)
    return result


def rename_mesh_variant(
    obj: bpy.types.Object,
    name: str,
    parent: bpy.types.Object,
) -> None:
    world_matrix = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world_matrix
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    obj.select_set(False)
    world_matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = world_matrix


def create_crystals() -> bpy.types.Object:
    rng = random.Random(SEED)
    warm_white = make_material(
        "CrystalWarmWhite",
        (0.38, 0.31, 0.25, 1.0),
        0.29,
    )
    cool_white = make_material(
        "CrystalCoolWhite",
        (0.30, 0.34, 0.38, 1.0),
        0.25,
    )
    pale_rose = make_material(
        "CrystalPaleRose",
        (0.43, 0.25, 0.29, 1.0),
        0.32,
    )
    materials = (warm_white, cool_white, pale_rose)

    root = empty("MdmaCrystals")
    pile = empty("CrystalPile", root)
    fines = empty("CrystalFinesAssembly", pile)
    chunks = empty("CrystalChunksAssembly", pile)
    granules = empty("CrystalGranulesAssembly", pile)

    fines_mesh = create_fragment(
        "CrystalFines",
        (0.0, 0.0),
        (0.054, 0.040, 0.005),
        (0.0, 0.0, 7.0),
        warm_white,
        fines,
        rng,
        surface_height=-0.001,
        subdivisions=2,
        vertical_bias=0.02,
    )

    chunk_specs = (
        ((-0.021, -0.006), (0.030, 0.015, 0.012), (8, -12, -18), 0),
        ((0.002, -0.010), (0.034, 0.017, 0.014), (-8, 7, 24), 1),
        ((0.025, -0.003), (0.027, 0.014, 0.011), (10, -7, 54), 0),
        ((-0.014, 0.013), (0.029, 0.014, 0.013), (-5, 13, 10), 2),
        ((0.015, 0.014), (0.031, 0.014, 0.012), (8, 5, -36), 1),
        ((-0.035, 0.009), (0.021, 0.011, 0.009), (12, -5, 33), 1),
        ((0.037, 0.010), (0.020, 0.010, 0.009), (-8, 10, -22), 2),
        ((-0.008, -0.025), (0.022, 0.010, 0.008), (6, 12, 68), 0),
        ((0.020, -0.023), (0.019, 0.009, 0.008), (-10, -6, 41), 2),
    )
    created_chunks: list[bpy.types.Object] = []
    for index, (location, dimensions, rotation, material_index) in enumerate(
        chunk_specs,
        start=1,
    ):
        creator = (
            create_fragment
            if index in {4, 6, 7, 9}
            else create_fractured_chunk
        )
        created_chunks.append(
            creator(
                f"CrystalChunk_{index:02d}",
                location,
                dimensions,
                rotation,
                materials[material_index],
                chunks,
                rng,
                surface_height=0.002,
            )
        )

    # Three elevated fragments establish a piled silhouette. Their overlap with
    # lower chunks is deliberate and prevents the pieces from reading as floating.
    stacked_specs = (
        ((-0.010, 0.000), (0.028, 0.013, 0.011), (16, 8, 18), 2, 0.010),
        ((0.012, 0.002), (0.026, 0.012, 0.010), (-13, 10, -24), 0, 0.011),
        ((0.001, 0.008), (0.022, 0.011, 0.009), (9, -15, 47), 1, 0.017),
    )
    for offset, (location, dimensions, rotation, material_index, height) in enumerate(
        stacked_specs,
        start=len(created_chunks) + 1,
    ):
        creator = create_fragment if offset == 12 else create_fractured_chunk
        created_chunks.append(
            creator(
                f"CrystalChunk_{offset:02d}",
                location,
                dimensions,
                rotation,
                materials[material_index],
                chunks,
                rng,
                surface_height=height,
            )
        )

    created_granules: list[bpy.types.Object] = []
    granule_specs = (
        (-0.044, -0.018, 0),
        (-0.036, -0.027, 1),
        (-0.023, -0.032, 0),
        (0.008, -0.031, 2),
        (0.031, -0.026, 1),
        (0.046, -0.014, 0),
        (0.044, 0.013, 2),
        (0.028, 0.028, 1),
        (-0.002, 0.031, 0),
        (-0.031, 0.026, 2),
        (-0.045, 0.012, 1),
        (-0.049, -0.003, 0),
        (0.036, 0.021, 2),
        (-0.018, -0.034, 1),
    )
    for index, (x, y, material_index) in enumerate(granule_specs, start=1):
        width = rng.uniform(0.0042, 0.0072)
        created_granules.append(
            create_fragment(
                f"CrystalGranule_{index:02d}",
                (x, y),
                (
                    width,
                    width * rng.uniform(0.70, 1.10),
                    width * rng.uniform(0.55, 0.90),
                ),
                (
                    rng.uniform(-18, 18),
                    rng.uniform(-18, 18),
                    rng.uniform(-180, 180),
                ),
                materials[material_index],
                granules,
                rng,
                surface_height=0.0002,
                vertical_bias=0.04,
            )
        )

    pile_variant = join_meshes(
        [fines_mesh, *created_chunks[:10]],
        "CrystalPileVariant",
        root,
    )
    rename_mesh_variant(created_chunks[10], "CrystalChunk_A", root)
    rename_mesh_variant(created_chunks[11], "CrystalChunk_B", root)
    join_meshes(created_granules, "CrystalGranules", root)
    for assembly in (fines, chunks, granules, pile):
        bpy.data.objects.remove(assembly, do_unlink=True)
    pile_variant.name = "CrystalPile"
    pile_variant.data.name = "CrystalPile_Mesh"

    root["asset_name"] = "DrugExpansion MDMA Crystals"
    root["asset_version"] = 1
    root["design"] = "Original deterministic DrugExpansion geometry"
    root["license"] = "GPL-3.0-or-later"
    root["units"] = "meters"
    root["front_axis"] = "-Y"
    root["up_axis"] = "+Z"
    root["intended_contexts"] = "loose, icon, station, native packaging"
    root["triangle_budget"] = TRIANGLE_BUDGET
    root["maximum_extent_meters"] = MAXIMUM_EXTENT_METERS
    root["appearance"] = "cloudy fractured crystalline batch"
    root["runtime_variants"] = (
        "CrystalPile, CrystalChunk_A, CrystalChunk_B, CrystalGranules"
    )
    return root


def add_preview_scene() -> None:
    floor_material = make_material(
        "PreviewFloor",
        (0.022, 0.026, 0.032, 1.0),
        0.82,
    )
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=0.105,
        depth=0.006,
        location=(0.0, 0.0, -0.004),
    )
    floor = bpy.context.object
    floor.name = "PreviewPlinth"
    floor.data.materials.append(floor_material)
    floor["presentation_only"] = True

    target = Vector((0.0, 0.0, 0.011))
    bpy.ops.object.camera_add(location=(0.105, -0.135, 0.087))
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    camera.data.lens = 60
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera["presentation_only"] = True
    bpy.context.scene.camera = camera

    for index, (location, energy, color, size) in enumerate(
        (
            ((-0.09, -0.10, 0.13), 7.0, (1.0, 0.82, 0.70), 0.11),
            ((0.11, -0.03, 0.08), 4.5, (0.64, 0.76, 1.0), 0.08),
            ((-0.02, 0.10, 0.10), 3.0, (1.0, 0.45, 0.57), 0.07),
        ),
        start=1,
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = f"PreviewLight_{index}"
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
    scene.world.color = (0.008, 0.010, 0.014)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.75


def evaluated_triangle_count(root: bpy.types.Object) -> int:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    triangles = 0
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
    return triangles


def save_export_and_render(root: bpy.types.Object) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    triangles = evaluated_triangle_count(root)
    if triangles > TRIANGLE_BUDGET:
        raise RuntimeError(
            f"Evaluated triangle budget exceeded: {triangles} > {TRIANGLE_BUDGET}"
        )

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
        export_animations=False,
        export_apply=False,
        export_yup=True,
    )
    bpy.ops.render.render(write_still=True)

    print(f"Created {triangles} evaluated triangles.")
    print(f"Blend: {BLEND_PATH}")
    print(f"GLB: {GLB_PATH}")
    print(f"Hero preview: {HERO_PREVIEW_PATH}")


def main() -> None:
    reset_scene()
    root = create_crystals()
    add_preview_scene()
    save_export_and_render(root)


if __name__ == "__main__":
    main()
