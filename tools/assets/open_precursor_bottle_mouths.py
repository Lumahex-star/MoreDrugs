"""Open the station-pour mouths while preserving the capped prop meshes.

Modeling contract:
- Preserve hierarchy, names, materials, transforms, scale, labels, liquid markers,
  pour points, and the separate cap objects.
- Remove the planar top and bottom seals from the requested neck mesh.
- Preserve the outer sidewall and add inward thickness to form a hollow tube.
- Export a game-ready GLB that can be imported again in a clean Blender process.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--neck", required=True)
    parser.add_argument("--liquid")
    parser.add_argument("--liquid-drop", type=float, default=0.0)
    parser.add_argument("--blend-output", type=Path)
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(arguments)


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def open_neck(neck_name: str) -> tuple[int, int]:
    neck = bpy.data.objects.get(neck_name)
    if neck is None or neck.type != "MESH":
        raise RuntimeError(f"Mesh object '{neck_name}' was not imported.")

    mesh = neck.data
    if not mesh.vertices or not mesh.polygons:
        raise RuntimeError(f"Mesh object '{neck_name}' is empty.")

    removed_faces = len(mesh.polygons)
    minimum_x = min(vertex.co.x for vertex in mesh.vertices)
    maximum_x = max(vertex.co.x for vertex in mesh.vertices)
    minimum_y = min(vertex.co.y for vertex in mesh.vertices)
    maximum_y = max(vertex.co.y for vertex in mesh.vertices)
    minimum_z = min(vertex.co.z for vertex in mesh.vertices)
    maximum_z = max(vertex.co.z for vertex in mesh.vertices)
    center_x = (minimum_x + maximum_x) * 0.5
    center_y = (minimum_y + maximum_y) * 0.5
    radius = max(maximum_x - minimum_x, maximum_y - minimum_y) * 0.5
    height = maximum_z - minimum_z
    inner_radius = radius * 0.72
    bevel = height * 0.2
    segments = 24

    rings = (
        (radius * 0.95, minimum_z),
        (radius, minimum_z + bevel),
        (radius, maximum_z - bevel),
        (radius * 0.95, maximum_z),
        (inner_radius, maximum_z),
        (inner_radius, minimum_z),
    )
    vertices = []
    for ring_radius, z in rings:
        for index in range(segments):
            angle = index * math.tau / segments
            vertices.append(
                (
                    center_x + math.cos(angle) * ring_radius,
                    center_y + math.sin(angle) * ring_radius,
                    z,
                )
            )

    faces = []
    for ring_index in range(len(rings)):
        next_ring = (ring_index + 1) % len(rings)
        for index in range(segments):
            next_index = (index + 1) % segments
            faces.append(
                (
                    ring_index * segments + index,
                    ring_index * segments + next_index,
                    next_ring * segments + next_index,
                    next_ring * segments + index,
                )
            )

    mesh.clear_geometry()
    mesh.from_pydata(vertices, [], faces)
    mesh.validate(clean_customdata=False)
    mesh.update(calc_edges=True)
    neck["station_open_mouth"] = True

    for vertex in mesh.vertices:
        if not all(math.isfinite(value) for value in vertex.co):
            raise RuntimeError(f"'{neck_name}' contains a non-finite vertex.")

    return removed_faces, len(mesh.polygons)


def export_glb(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.glb")
    bpy.ops.export_scene.gltf(
        filepath=str(temporary),
        export_format="GLB",
        export_extras=True,
        export_yup=True,
    )
    os.replace(temporary, output)


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    reset_scene()
    bpy.ops.import_scene.gltf(filepath=str(input_path))
    removed_faces, remaining_faces = open_neck(args.neck)
    if args.liquid_drop:
        if not args.liquid:
            raise RuntimeError("--liquid is required when --liquid-drop is non-zero.")
        liquid = bpy.data.objects.get(args.liquid)
        if liquid is None:
            raise RuntimeError(f"Liquid marker '{args.liquid}' was not imported.")
        liquid.location.z -= args.liquid_drop

    if args.blend_output:
        blend_output = args.blend_output.resolve()
        blend_output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_output))

    export_glb(output_path)
    print(
        json.dumps(
            {
                "input": str(input_path),
                "output": str(output_path),
                "neck": args.neck,
                "removed_top_faces": removed_faces,
                "remaining_faces": remaining_faces,
                "liquid_drop": args.liquid_drop,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
