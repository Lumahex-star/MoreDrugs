"""Validate the exported DrugExpansion MDMA crystals GLB in a clean scene."""

from __future__ import annotations

import json
from pathlib import Path
import struct

import bpy
from mathutils import Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
GLB_PATH = (
    REPO_ROOT
    / "src"
    / "DrugExpansion"
    / "Assets"
    / "Models"
    / "mdma_crystals.glb"
)
EVIDENCE_DIR = (
    REPO_ROOT
    / "artifacts"
    / "validation"
    / "mdma-crystals"
    / "controlled-evidence"
)
TRIANGLE_BUDGET = 3_000
MAXIMUM_EXTENT_METERS = 0.12
REQUIRED_NODES = {
    "MdmaCrystals",
    "CrystalPile",
    "CrystalChunk_A",
    "CrystalChunk_B",
    "CrystalGranules",
}
REQUIRED_MATERIALS = {
    "CrystalWarmWhite",
    "CrystalCoolWhite",
    "CrystalPaleRose",
}


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


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


def make_preview_material() -> bpy.types.Material:
    material = bpy.data.materials.new("CrystalValidationFloor")
    material.diffuse_color = (0.022, 0.026, 0.032, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = material.diffuse_color
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Roughness"].default_value = 0.82
    return material


def render_controlled_evidence(target: Vector) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    bpy.ops.mesh.primitive_plane_add(size=0.32, location=(0.0, 0.0, -0.0018))
    floor = bpy.context.object
    floor.name = "CrystalValidationFloor"
    floor.data.materials.append(make_preview_material())

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "CrystalValidationCamera"
    camera.data.lens = 60
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
        light.name = f"CrystalValidationLight_{index}"
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size

    views = (
        ("perspective", "PERSP", (0.105, -0.135, 0.087)),
        ("front", "ORTHO", (0.0, -0.18, 0.030)),
        ("back", "ORTHO", (0.0, 0.18, 0.030)),
        ("left", "ORTHO", (-0.18, 0.0, 0.030)),
        ("right", "ORTHO", (0.18, 0.0, 0.030)),
        ("top", "ORTHO", (0.0, 0.0, 0.20)),
    )

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.008, 0.010, 0.014)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.75

    for name, camera_type, location in views:
        camera.data.type = camera_type
        camera.data.ortho_scale = 0.14
        camera.location = location
        camera.rotation_euler = (
            target - camera.location
        ).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(EVIDENCE_DIR / f"{name}.png")
        bpy.ops.render.render(write_still=True)


def main() -> None:
    if not GLB_PATH.exists():
        raise FileNotFoundError(GLB_PATH)

    gltf = read_glb_json()
    node_names = [node.get("name", "") for node in gltf.get("nodes", [])]
    duplicates = {
        name for name in node_names if name and node_names.count(name) > 1
    }
    missing_nodes = REQUIRED_NODES.difference(node_names)
    if duplicates:
        raise RuntimeError(f"Duplicate GLB node names: {sorted(duplicates)}")
    if missing_nodes:
        raise RuntimeError(f"Missing required nodes: {sorted(missing_nodes)}")
    if gltf.get("animations"):
        raise RuntimeError("The crystal asset must not contain animations.")

    reset_scene()
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    imported = list(bpy.context.scene.objects)
    meshes = [obj for obj in imported if obj.type == "MESH"]
    mesh_names = {obj.name for obj in meshes}
    expected_mesh_names = REQUIRED_NODES.difference({"MdmaCrystals"})
    if mesh_names != expected_mesh_names:
        raise RuntimeError(
            "Expected exactly four runtime mesh variants, found "
            f"{sorted(mesh_names)}"
        )
    materials = {
        slot.material.name
        for obj in meshes
        for slot in obj.material_slots
        if slot.material is not None
    }
    missing_materials = REQUIRED_MATERIALS.difference(materials)
    if missing_materials:
        raise RuntimeError(
            f"Missing required materials: {sorted(missing_materials)}"
        )

    depsgraph = bpy.context.evaluated_depsgraph_get()
    triangles = 0
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
    if not 300 <= triangles <= TRIANGLE_BUDGET:
        raise RuntimeError(f"Unexpected triangle count: {triangles}")
    for variant in ("CrystalPile", "CrystalChunk_A", "CrystalChunk_B", "CrystalGranules"):
        obj = next(mesh for mesh in meshes if mesh.name == variant)
        variant_triangles = sum(
            len(polygon.vertices) - 2 for polygon in obj.data.polygons
        )
        if variant_triangles <= 0:
            raise RuntimeError(f"Runtime variant '{variant}' is empty.")

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
    if max(dimensions) > MAXIMUM_EXTENT_METERS:
        raise RuntimeError(f"Maximum extent exceeded: {tuple(dimensions)}")
    if not 0.045 <= dimensions.x <= MAXIMUM_EXTENT_METERS:
        raise RuntimeError(f"Unexpected X dimension: {dimensions.x}")
    if not 0.035 <= dimensions.y <= 0.10:
        raise RuntimeError(f"Unexpected Y dimension: {dimensions.y}")
    if not 0.012 <= dimensions.z <= 0.055:
        raise RuntimeError(f"Unexpected Z dimension: {dimensions.z}")
    if not -0.003 <= minimum.z <= 0.002:
        raise RuntimeError(
            f"Crystal pile does not have a credible ground contact: z={minimum.z}"
        )

    missing_assignments = [
        obj.name
        for obj in meshes
        if not obj.material_slots
        or any(polygon.material_index >= len(obj.material_slots) for polygon in obj.data.polygons)
    ]
    if missing_assignments:
        raise RuntimeError(
            f"Visible meshes are missing materials: {missing_assignments}"
        )

    print(f"Validated GLB: {GLB_PATH}")
    print(f"File size: {GLB_PATH.stat().st_size} bytes")
    print(f"Mesh objects: {len(meshes)}")
    print(f"Triangles: {triangles}")
    print(f"Materials: {sorted(materials)}")
    print(
        "Dimensions: "
        f"{tuple(round(value, 4) for value in dimensions)} meters"
    )
    print(
        "Bounds: "
        f"{tuple(round(value, 4) for value in minimum)} to "
        f"{tuple(round(value, 4) for value in maximum)}"
    )
    render_controlled_evidence((minimum + maximum) / 2)
    print(f"Controlled evidence: {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
